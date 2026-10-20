from datetime import datetime, timedelta, timezone
import os
import sys
from math import isfinite
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy.orm import Session
from typing import List

from app.database import Base, engine, get_db
from app.models import Trade
from app.accounting import FINANCIAL_INPUTS, apply_accounting, cost_coverage
from app.schemas import TradeCreate, TradeRead, TradeUpdate, PositionSizeRequest, PositionSizeResponse
from app.services import (
    calculate_position_size,
    calculate_trade_metrics,
    calendar_month,
    dashboard_summary,
    group_analytics,
    serialize_trade,
)

# Importing/starting the API must not create or migrate database tables.
# Tests explicitly initialize the existing model on a disposable engine.


# Schema changes live exclusively in the explicit migration runner.

app = FastAPI(
    title="TradePulse AI Engine",
    description="FastAPI Backend & Quantitative Engine",
    version="1.0.0"
)

# Enable CORS for local frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    # Verify DB connectivity
    trade_count = db.query(Trade).count()
    return {
        "status": "healthy",
        "service": "TradePulse AI FastAPI",
        "database": "sqlite",
        "trades_count": trade_count,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def _payload_dict(payload):
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=True)
    return payload.dict(exclude_unset=True)


def _apply_trade_payload(trade: Trade, data: dict):
    aliases = {
        "entry": "entry_price",
        "exit": "exit_price",
        "date": "trade_date",
        "chartUrl": "chart_url",
    }
    normalized = {}
    for key, value in data.items():
        normalized[aliases.get(key, key)] = value

    if "symbol" in normalized and normalized["symbol"]:
        normalized["symbol"] = normalized["symbol"].strip().upper()
    if "side" in normalized and normalized["side"]:
        normalized["side"] = normalized["side"].strip().upper()

    new = trade.id is None
    try:
        merged = {} if new else {
            k: getattr(trade, k, None) for k in TradeCreate.model_fields if k != "cost_model"
        }
        merged.update(normalized)
        validated = TradeCreate.model_validate(merged).model_dump()
        for key, value in (validated if new else normalized).items():
            if key != "cost_model" and hasattr(trade, key):
                setattr(trade, key, value)
        if new or FINANCIAL_INPUTS & normalized.keys():
            apply_accounting(trade, normalized, calculate_trade_metrics)
            for field in ("pnl", "return_pct", "risk_amount", "r_multiple", "gross_pnl", "net_pnl", "total_costs"):
                value = getattr(trade, field)
                if value is not None and not isfinite(value):
                    raise ValueError("Financial calculation exceeds finite numeric range")
    except (ValueError, ValidationError) as error:
        raise HTTPException(422, str(error)) from error

    if new:
        trade.trade_date = trade.trade_date or datetime.now(timezone.utc).date().isoformat()
        trade.asset = trade.asset or "Stock"
        trade.emotion = trade.emotion or "Disciplined"
        trade.mistake = trade.mistake or "None"
        trade.rating = trade.rating if trade.rating is not None else 5
    trade.updated_at = datetime.now(timezone.utc)
    return trade


def _query_trades(db: Session):
    return db.query(Trade).order_by(Trade.trade_date.desc().nullslast(), Trade.id.desc()).all()


@app.get("/api/v1/trades", response_model=List[TradeRead])
def list_trades(db: Session = Depends(get_db)):
    return _query_trades(db)


@app.get("/api/trades")
def list_trades_compat(db: Session = Depends(get_db)):
    return [serialize_trade(trade) for trade in _query_trades(db)]


@app.get("/api/v1/trades/{trade_id}", response_model=TradeRead)
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    trade = db.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@app.post("/api/v1/trades", response_model=TradeRead, status_code=201)
def create_trade(payload: TradeCreate, db: Session = Depends(get_db)):
    trade = _apply_trade_payload(Trade(), _payload_dict(payload))
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


@app.put("/api/v1/trades/{trade_id}", response_model=TradeRead)
def update_trade(trade_id: int, payload: TradeUpdate, db: Session = Depends(get_db)):
    trade = db.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    _apply_trade_payload(trade, _payload_dict(payload))
    db.commit()
    db.refresh(trade)
    return trade


@app.delete("/api/v1/trades/{trade_id}", status_code=204)
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    trade = db.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    db.delete(trade)
    db.commit()
    return Response(status_code=204)


@app.get("/api/v1/calendar/{year}/{month}")
def get_calendar_month(year: int, month: int, db: Session = Depends(get_db)):
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    return calendar_month(_query_trades(db), year, month)


@app.get("/api/v1/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    return dashboard_summary(_query_trades(db))


@app.get("/api/v1/analytics/strategy")
def get_strategy_analytics(db: Session = Depends(get_db)):
    return group_analytics(_query_trades(db), "strategy")


@app.get("/api/v1/analytics/cost-coverage")
def get_cost_coverage(db: Session = Depends(get_db)):
    return cost_coverage(_query_trades(db))


@app.get("/api/v1/analytics/emotion")
def get_emotion_analytics(db: Session = Depends(get_db)):
    return group_analytics(_query_trades(db), "emotion")


@app.get("/api/v1/analytics/mistakes")
def get_mistake_analytics(db: Session = Depends(get_db)):
    return group_analytics(_query_trades(db), "mistake")


@app.post("/api/v1/risk/position-size", response_model=PositionSizeResponse)
def get_position_size(payload: PositionSizeRequest):
    return calculate_position_size(
        payload.account_balance,
        payload.risk_pct,
        payload.entry_price,
        payload.stop_loss,
    )


@app.get("/api/v1/market/{ticker}")
def get_market_data(ticker: str):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from analytics import calculate_bollinger_bands, calculate_macd, calculate_moving_averages, calculate_rsi
    from data_loader import fetch_stock_data, preprocess_data

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=140)
    raw = fetch_stock_data(ticker, start_date.isoformat(), end_date.isoformat())
    df = preprocess_data(raw)
    df = calculate_moving_averages(df, sma_windows=[20, 50], ema_windows=[])
    df = calculate_bollinger_bands(df)
    df = calculate_rsi(df)
    df = calculate_macd(df)
    df = df.tail(90).reset_index()

    records = []
    for row in df.to_dict(orient="records"):
        day = row.get("Date")
        records.append({
            "date": day.date().isoformat() if hasattr(day, "date") else str(day)[:10],
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
            "sma20": round(float(row["SMA_20"]), 4) if row.get("SMA_20") == row.get("SMA_20") else None,
            "sma50": round(float(row["SMA_50"]), 4) if row.get("SMA_50") == row.get("SMA_50") else None,
            "rsi": round(float(row["RSI"]), 4) if row.get("RSI") == row.get("RSI") else None,
            "macd": round(float(row["MACD"]), 4) if row.get("MACD") == row.get("MACD") else None,
            "macd_signal": round(float(row["MACD_Signal"]), 4) if row.get("MACD_Signal") == row.get("MACD_Signal") else None,
        })

    latest = records[-1] if records else None
    previous = records[-2] if len(records) > 1 else latest
    change = (latest["close"] - previous["close"]) if latest and previous else 0
    change_pct = (change / previous["close"] * 100) if previous and previous["close"] else 0

    return {
        "ticker": ticker.strip().upper(),
        "latest": latest,
        "change": round(float(change), 4),
        "change_pct": round(float(change_pct), 4),
        "candles": records,
    }
