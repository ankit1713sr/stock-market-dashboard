from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CostEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    fee_per_order: float = Field(default=0, ge=0)
    fee_bps: float = Field(default=0, ge=0)
    slippage_bps: float = Field(default=0, ge=0)
    min_fee: float = Field(default=0, ge=0)
    max_fee: Optional[float] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def valid_cap(self):
        if self.max_fee is not None and self.max_fee < self.min_fee:
            raise ValueError("max_fee must be at least min_fee")
        return self


class AccountingInputs(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    brokerage_fee: Optional[float] = Field(default=None, ge=0)
    transaction_fee: Optional[float] = Field(default=None, ge=0)
    slippage_cost: Optional[float] = Field(default=None, ge=0)
    contract_multiplier: Optional[float] = Field(default=None, gt=0)
    cost_status: Optional[Literal["unknown", "reported", "estimated"]] = None
    slippage_treatment: Optional[Literal["included", "additional"]] = None
    cost_model: Optional[CostEstimate] = None


def reject_derived(data):
    if isinstance(data, dict) and set(data) & {
        "gross_pnl", "net_pnl", "total_costs", "cost_model_json", "accounting_version", "pnl_basis",
        "pnl", "return_pct", "risk_amount", "r_multiple"
    }:
        raise ValueError("Accounting results are server-controlled")
    return data


class TradeBase(AccountingInputs):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., pattern="^(BUY|SELL)$")
    trade_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    asset: Optional[str] = Field(default="Stock", max_length=50)
    qty: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    exit_price: Optional[float] = Field(default=None, gt=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    target_price: Optional[float] = Field(default=None, gt=0)
    strategy: Optional[str] = Field(default=None, max_length=50)
    emotion: Optional[str] = Field(default=None, max_length=50)
    mistake: Optional[str] = Field(default=None, max_length=80)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None
    chart_url: Optional[str] = None
    is_demo: bool = False


class TradeCreate(TradeBase):
    @model_validator(mode="before")
    @classmethod
    def server_owned_results(cls, data):
        return reject_derived(data)


class TradeUpdate(AccountingInputs):
    @model_validator(mode="before")
    @classmethod
    def server_owned_results(cls, data):
        return reject_derived(data)
    symbol: Optional[str] = Field(default=None, min_length=1, max_length=20)
    side: Optional[str] = Field(default=None, pattern="^(BUY|SELL)$")
    trade_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    asset: Optional[str] = Field(default=None, max_length=50)
    qty: Optional[float] = Field(default=None, gt=0)
    entry_price: Optional[float] = Field(default=None, gt=0)
    exit_price: Optional[float] = Field(default=None, gt=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    target_price: Optional[float] = Field(default=None, gt=0)
    strategy: Optional[str] = Field(default=None, max_length=50)
    emotion: Optional[str] = Field(default=None, max_length=50)
    mistake: Optional[str] = Field(default=None, max_length=80)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None
    chart_url: Optional[str] = None
    is_demo: Optional[bool] = None


class TradeRead(TradeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pnl: Optional[float] = None
    return_pct: Optional[float] = None
    risk_amount: Optional[float] = None
    r_multiple: Optional[float] = None
    gross_pnl: Optional[float] = None
    total_costs: Optional[float] = None
    net_pnl: Optional[float] = None
    accounting_version: Optional[int] = None
    cost_model_json: Optional[str] = None
    pnl_basis: str = "legacy_unknown"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class PositionSizeRequest(BaseModel):
    account_balance: float = Field(..., gt=0)
    risk_pct: float = Field(..., gt=0, le=100)
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)


class PositionSizeResponse(BaseModel):
    dollar_risk: float
    risk_per_unit: float
    quantity: int
