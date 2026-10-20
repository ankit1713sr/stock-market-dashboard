import importlib
import json
import math
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from app import database
from app.models import Trade
from app.schemas import TradeCreate, TradeUpdate
from app.accounting import cost_coverage, pnl_basis
from backend.migrations.runner import upgrade
from backend.tools.db_safety import backup_database, sha256


def payload(**updates):
    data = dict(symbol="TEST", side="BUY", trade_date="2026-10-20", qty=10,
                entry_price=100, exit_price=110, stop_loss=95, strategy="Step2")
    data.update(updates)
    return data


def reported(**updates):
    data = payload(contract_multiplier=1, brokerage_fee=2, transaction_fee=3,
                   slippage_cost=5, slippage_treatment="additional", cost_status="reported")
    data.update(updates)
    return data


@pytest.fixture
def api(tmp_path, monkeypatch, legacy_source):
    original_hash = sha256(legacy_source)
    path = tmp_path / "api.db"
    backup_database(legacy_source, path)
    with sqlite3.connect(path) as conn:
        original_columns = [r[1] for r in conn.execute("PRAGMA table_info(trades)")]
        original_rows = conn.execute("SELECT * FROM trades ORDER BY id").fetchall()
    upgrade(path, tmp_path / "pre-migration.db")
    with patch.object(database.Base.metadata, "create_all", side_effect=AssertionError("No implicit DDL")):
        main = importlib.import_module("app.main")
    engine = create_engine(URL.create("sqlite", database=str(path)), connect_args={"check_same_thread": False})
    sessions = sessionmaker(bind=engine)
    def disposable_session():
        with sessions() as session:
            yield session
    def forbid(*args, **kwargs):
        raise AssertionError("Attempted repository engine connection")
    event.listen(database.engine, "do_connect", forbid)
    main.app.dependency_overrides[database.get_db] = disposable_session
    monkeypatch.setattr(main, "engine", engine)
    try:
        with TestClient(main.app) as client:
            yield client
    finally:
        main.app.dependency_overrides.clear()
        event.remove(database.engine, "do_connect", forbid)
        engine.dispose()
        with sqlite3.connect(path) as conn:
            quoted = ",".join(f'"{c}"' for c in original_columns)
            assert conn.execute(f"SELECT {quoted} FROM trades WHERE id<=29 ORDER BY id").fetchall() == original_rows
            assert conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert sha256(legacy_source) == original_hash


def create(api, data):
    response = api.post("/api/v1/trades", json=data)
    assert response.status_code == 201, response.text
    return response.json()


def test_migrated_legacy_gets_never_recalculate_or_infer_multipliers(api):
    trades = api.get("/api/v1/trades").json()
    assert len(trades) == 29
    futures = [t for t in trades if t["asset"] == "Futures"]
    assert len(futures) == 4
    for trade in trades:
        assert trade["pnl_basis"] == "legacy_unknown"
        for key in ("contract_multiplier", "brokerage_fee", "transaction_fee", "slippage_cost", "net_pnl", "gross_pnl"):
            assert trade[key] is None
    coverage = api.get("/api/v1/analytics/cost-coverage").json()
    assert coverage["counts"]["legacy_unknown"] == 29
    assert not coverage["fully_costed"] and "unknown" in coverage["label"]


def test_reported_net_returns_risk_and_every_report_agree(api):
    before = api.get("/api/v1/dashboard/summary").json()["net_pnl"]
    trade = create(api, reported())
    assert trade["gross_pnl"] == 100 and trade["total_costs"] == 10
    assert trade["pnl"] == trade["net_pnl"] == 90
    assert trade["return_pct"] == 9 and trade["risk_amount"] == 50 and trade["r_multiple"] == 1.8
    assert trade["pnl_basis"] == "net_reported"
    assert api.get("/api/v1/dashboard/summary").json()["net_pnl"] == pytest.approx(before + 90)
    assert api.get("/api/v1/calendar/2026/10").json()["days"][-1]["pnl"] == 90
    for endpoint in ("strategy", "emotion", "mistakes"):
        response = api.get(f"/api/v1/analytics/{endpoint}")
        assert response.status_code == 200
    strategy = next(t for t in api.get("/api/v1/analytics/strategy").json() if t["name"] == "Step2")
    assert strategy["pnl"] == 90 and strategy["count"] == 1
    compat = next(t for t in api.get("/api/trades").json() if t["id"] == trade["id"])
    assert compat["pnl"] == 90 and compat["net_pnl"] == 90 and compat["entry"] == 100
    coverage = api.get("/api/v1/analytics/cost-coverage").json()
    assert coverage["basis"] == "mixed" and coverage["counts"]["net_reported"] == 1


@pytest.mark.parametrize("side,entry,exit_price,mult,qty,gross", [
    ("SELL", 200, 180, 1, 5, 100), ("BUY", 2.5, 4, 100, 5, 750),
    ("SELL", 2, 3, 50, 0.5, -25), ("BUY", 100, 101, 1, 0.5, 0.5),
])
def test_short_fractional_and_contract_accounting(api, side, entry, exit_price, mult, qty, gross):
    trade = create(api, reported(side=side, entry_price=entry, exit_price=exit_price,
                                 qty=qty, contract_multiplier=mult, stop_loss=None))
    assert trade["gross_pnl"] == gross and trade["net_pnl"] == gross - 10
    assert trade["return_pct"] == pytest.approx(round((gross - 10) / (entry * qty * mult) * 100, 4))


def test_unknown_costs_are_not_zero_and_explicit_zero_is_known(api):
    unknown = create(api, payload(contract_multiplier=1))
    zero = create(api, reported(brokerage_fee=0, transaction_fee=0, slippage_cost=0))
    assert unknown["cost_status"] == "unknown" and unknown["net_pnl"] is None
    assert unknown["total_costs"] is None and unknown["pnl_basis"] == "gross_unknown_costs"
    assert zero["total_costs"] == 0 and zero["net_pnl"] == 100
    assert zero["pnl_basis"] == "net_reported"
    partial = create(api, payload(contract_multiplier=1, brokerage_fee=2))
    assert partial["brokerage_fee"] == 2 and partial["net_pnl"] is None


def test_modeled_roundtrip_floor_cap_and_multiplier(api):
    model = dict(fee_per_order=2, fee_bps=10, min_fee=5, max_fee=8, slippage_bps=5)
    trade = create(api, payload(contract_multiplier=100, cost_status="estimated",
                                slippage_treatment="additional", cost_model=model))
    # notionals 100,000 and 110,000 => capped commissions 8+8; slippage 50+55.
    assert trade["gross_pnl"] == 10000 and trade["total_costs"] == 121
    assert trade["net_pnl"] == 9879 and trade["r_multiple"] == pytest.approx(9879 / 5000)
    assert json.loads(trade["cost_model_json"])["max_fee"] == 8
    changed = api.put(f'/api/v1/trades/{trade["id"]}', json={"exit_price": 120}).json()
    assert changed["total_costs"] == 126 and changed["net_pnl"] == 19874


def test_open_close_reopen_and_metadata_updates_preserve_accounting(api):
    trade = create(api, reported(exit_price=None))
    assert trade["pnl"] is None and trade["net_pnl"] is None and trade["gross_pnl"] is None
    assert api.get("/api/v1/analytics/cost-coverage").json()["completed_trades"] == 29
    uri = f'/api/v1/trades/{trade["id"]}'
    closed = api.put(uri, json={"exit_price":110}).json()
    updated = api.put(uri, json={"notes":"metadata only"}).json()
    for key in ("pnl", "net_pnl", "gross_pnl", "return_pct", "r_multiple", "total_costs"):
        assert updated[key] == closed[key]
    reopened = api.put(uri, json={"exit_price": None}).json()
    assert reopened["pnl"] is None and reopened["net_pnl"] is None


def test_cost_edit_zero_and_null_are_distinct_and_validation_is_atomic(api):
    trade = create(api, reported())
    uri = f'/api/v1/trades/{trade["id"]}'
    assert api.put(uri, json={"brokerage_fee":0}).json()["net_pnl"] == 92
    assert api.put(uri, json={"brokerage_fee":None}).status_code == 422
    assert api.get(uri).json()["brokerage_fee"] == 0
    unknown = api.put(uri, json={"brokerage_fee":None,"cost_status":"unknown"}).json()
    assert unknown["net_pnl"] is None and unknown["total_costs"] is None and unknown["pnl"] == 100


@pytest.mark.parametrize("updates", [
    {"contract_multiplier":None}, {"contract_multiplier":0}, {"brokerage_fee":-1},
    {"brokerage_fee":None}, {"qty":None}, {"entry_price":None},
    {"slippage_treatment":"included"}, {"cost_status":"estimated"},
    {"cost_status":"reported","cost_model":{"fee_per_order":1}},
    {"cost_model":{"max_fee":1,"min_fee":2}}, {"net_pnl":999}, {"pnl":999},
])
def test_invalid_or_ambiguous_accounting_payloads_rejected(api, updates):
    response = api.post("/api/v1/trades", json=reported(**updates))
    assert response.status_code == 422, response.text
    assert api.get("/health").json()["trades_count"] == 29


@pytest.mark.parametrize("value", [float("inf"), float("nan"), -float("inf")])
def test_nonfinite_values_rejected_by_input_schemas(value):
    with pytest.raises(ValueError):
        TradeCreate.model_validate(reported(brokerage_fee=value))
    with pytest.raises(ValueError):
        TradeUpdate.model_validate({"contract_multiplier":value})


def test_included_slippage_is_not_deducted_twice(api):
    trade = create(api, reported(slippage_treatment="included", slippage_cost=0))
    assert trade["net_pnl"] == 95 and trade["total_costs"] == 5


def test_costs_can_turn_a_winning_gross_trade_into_a_net_loss(api):
    trade = create(api, reported(exit_price=100.5))
    assert trade["gross_pnl"] == 5 and trade["net_pnl"] == -5 and trade["r_multiple"] == -.1
    strategy = next(t for t in api.get("/api/v1/analytics/strategy").json() if t["name"] == "Step2")
    assert strategy["pnl"] == -5 and strategy["win_rate"] == 0


def test_metadata_only_edits_do_not_recalculate_legacy_metrics():
    from app import main
    trade = Trade(id=1, symbol="OLD", side="SELL", qty=1, entry_price=100, exit_price=90,
                  pnl=9.99, return_pct=9.99, risk_amount=17, r_multiple=.5876,
                  stop_loss=95, is_demo=False)
    with patch.object(main, "calculate_trade_metrics", side_effect=AssertionError("Legacy recalc")):
        main._apply_trade_payload(trade, {"notes":"edited metadata"})
    assert trade.pnl == 9.99 and trade.r_multiple == .5876 and trade.asset is None
    assert trade.accounting_version is None and trade.net_pnl is None


def test_default_repository_database_connection_is_readonly():
    assert "mode=ro" in database.engine.url.database


def test_unmigrated_database_returns_503_without_ddl(tmp_path, monkeypatch, legacy_source):
    from app import main
    path = tmp_path / "unmigrated.db"
    backup_database(legacy_source, path)
    before = sha256(path)
    engine = create_engine(URL.create("sqlite", database=str(path)))
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine))
    main.app.dependency_overrides.clear()
    try:
        with TestClient(main.app) as client:
            response = client.get("/api/v1/trades")
        assert response.status_code == 503 and "schema pending" in response.text
        assert sha256(path) == before
    finally:
        engine.dispose()


def test_huge_finite_inputs_return_validation_error_not_nonfinite_json(api):
    response = api.post("/api/v1/trades", json=reported(qty=1e308, contract_multiplier=1e308))
    assert response.status_code == 422


def test_switch_from_estimate_to_reported_requires_explicit_model_clear(api):
    trade = create(api, payload(contract_multiplier=1, cost_status="estimated",
                                slippage_treatment="additional", cost_model={"fee_per_order":1}))
    uri = f'/api/v1/trades/{trade["id"]}'
    assert api.put(uri, json={"cost_status":"reported", "brokerage_fee":0,
                             "transaction_fee":0,"slippage_cost":0}).status_code == 422
    response = api.put(uri, json={"cost_model":None, "cost_status":"reported", "brokerage_fee":0,
                                 "transaction_fee":0,"slippage_cost":0})
    assert response.status_code == 200
    assert response.json()["net_pnl"] == 100 and response.json()["cost_model_json"] is None
