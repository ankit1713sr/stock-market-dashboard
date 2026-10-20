from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone
from app.database import Base


class Trade(Base):
    """Trading journal entry persisted by the FastAPI backend."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    side = Column(String(10), nullable=False)   # "BUY" or "SELL"
    trade_date = Column(String(10), index=True, nullable=True)
    asset = Column(String(50), nullable=True)
    qty = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)   # nullable: open trade support later
    stop_loss = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    return_pct = Column(Float, nullable=True)
    risk_amount = Column(Float, nullable=True)
    r_multiple = Column(Float, nullable=True)
    # No defaults: NULL on legacy rows means unknown, never reported zero.
    brokerage_fee = Column(Float, nullable=True)
    transaction_fee = Column(Float, nullable=True)
    slippage_cost = Column(Float, nullable=True)
    contract_multiplier = Column(Float, nullable=True)
    cost_status = Column(String(20), nullable=True)
    slippage_treatment = Column(String(20), nullable=True)
    cost_model_json = Column(Text, nullable=True)
    gross_pnl = Column(Float, nullable=True)
    total_costs = Column(Float, nullable=True)
    net_pnl = Column(Float, nullable=True)
    accounting_version = Column(Integer, nullable=True)

    @property
    def pnl_basis(self):
        from app.accounting import pnl_basis
        return pnl_basis(self)
    strategy = Column(String(50), nullable=True)
    emotion = Column(String(50), nullable=True)
    mistake = Column(String(80), nullable=True)
    rating = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    chart_url = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
