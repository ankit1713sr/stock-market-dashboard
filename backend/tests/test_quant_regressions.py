"""Mathematical references and deliberate future-leakage probes."""
import math
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from app.quant.technicals import calculate_rsi_wilder
from app.quant.metrics import (calculate_annualized_metrics, calculate_drawdown_series,
    calculate_sharpe_ratio, calculate_sortino_ratio, calculate_expectancy, calculate_var_historical)
from app.quant.cost_model import CostModel, calculate_cost_aware_pnl
from app.quant.backtesting import BacktestEngine
from app.services import dashboard_summary, group_analytics
from analytics import calculate_rsi, calculate_performance_summary, generate_trading_signals
from data_loader import preprocess_data, generate_synthetic_data


def backtest(prices, signals, **kwargs):
    df = pd.DataFrame({'Close': prices})
    return BacktestEngine(**kwargs).run_signal_backtest(df, lambda prefix: signals[len(prefix)-1])


@pytest.mark.parametrize('prices,expected', [([10]*8,50), (list(range(10,18)),100), (list(range(18,10,-1)),0)])
def test_rsi_edges(prices, expected):
    result = calculate_rsi_wilder(prices, period=3)
    assert result.iloc[:3].isna().all()
    assert (result.iloc[3:] == expected).all()


def test_rsi_exact_seed_and_recurrence():
    # +2,-1,+3 => gain=5/3, loss=1/3, RSI=100*5/6.
    # next change -2 => gain=10/9, loss=8/9, RSI=100*10/18.
    r = calculate_rsi_wilder([10,12,11,14,12],period=3)
    assert r.iloc[3] == pytest.approx(100*5/6)
    assert r.iloc[4] == pytest.approx(100*10/18)


def test_rsi_missing_seed_requires_new_contiguous_window():
    r = calculate_rsi_wilder([10,11,np.nan,12,13,14,15],period=3)
    assert r.iloc[:6].isna().all()
    assert r.iloc[6] == 100


def test_rsi_missing_after_seed_resets_and_neutral_never_fills_missing():
    prices=[10,11,12,13,np.nan,20,19,18,17]
    r=calculate_rsi_wilder(prices,period=3)
    assert r.iloc[3] == 100 and r.iloc[4:8].isna().all() and r.iloc[8] == 0
    neutral=calculate_rsi_wilder(prices,period=3,warmup_neutral=True)
    assert math.isnan(neutral.iloc[4]) and neutral.iloc[5] == 50


@pytest.mark.parametrize('period',[0,-1,1.5,True])
def test_rsi_bad_period(period):
    with pytest.raises(ValueError): calculate_rsi_wilder([1,2,3],period=period)


def test_empty_and_short_rsi():
    assert calculate_rsi_wilder([]).empty
    assert calculate_rsi_wilder([1,2],period=2).isna().all()
    assert calculate_rsi_wilder([1,2],period=2,warmup_neutral=True).tolist()==[50,50]


def test_sharpe_arithmetic_excess_frequency_and_sample_std():
    r=np.array([.03,-.02,.01,.05])
    rf=.001
    expected=(r.mean()-rf)/r.std(ddof=1)
    assert calculate_sharpe_ratio(r,rf)==pytest.approx(expected)
    assert calculate_sharpe_ratio(r,rf,True,12)==pytest.approx(expected*math.sqrt(12))
    annual=calculate_annualized_metrics(r,risk_free_rate=.06,trading_days=12)
    assert annual['sharpe_ratio']==pytest.approx((r.mean()-((1.06)**(1/12)-1))/r.std(ddof=1)*math.sqrt(12),abs=5e-5)
    assert annual['ann_return']==pytest.approx(np.prod(1+r)**3-1,abs=5e-7)


def test_sortino_target_and_all_observations():
    r=np.array([.03,-.02,.01,.05]); target=.015
    excess=r-target
    expected=excess.mean()/np.sqrt(np.mean(np.minimum(excess,0)**2))
    assert calculate_sortino_ratio(r,target)==pytest.approx(expected)
    assert calculate_sortino_ratio(r,target,True,12)==pytest.approx(expected*math.sqrt(12))


@pytest.mark.parametrize('values',[[],[.1],[.1,.1],[np.nan]])
def test_undefined_sharpe_is_finite_compatibility_zero(values):
    assert calculate_sharpe_ratio(values)==0


@pytest.mark.parametrize('values',[[],[.1],[.1,.2],[0,0]])
def test_undefined_sortino_is_finite_compatibility_zero(values):
    assert calculate_sortino_ratio(values)==0


def test_drawdown_includes_first_loss_and_single_observation():
    assert calculate_annualized_metrics([-.1,0])['max_drawdown_pct']==-10
    single=calculate_annualized_metrics([-.2])
    assert single['total_return']==-.2 and single['max_drawdown_pct']==-20
    assert single['ann_volatility']==0
    assert calculate_drawdown_series([90,80,110],100)['drawdown_pct'].tolist()==[-10,-20,0]
    assert calculate_drawdown_series([-10],100)['drawdown_pct'].iloc[0]==pytest.approx(-110)


def test_metrics_empty_and_total_loss():
    assert calculate_drawdown_series([]).empty
    assert all(v==0 for v in calculate_annualized_metrics([]).values())
    loss=calculate_annualized_metrics([-1,0])
    assert loss['total_return']==-1 and loss['ann_return']==-1 and loss['max_drawdown_pct']==-100


@pytest.mark.parametrize('call',[
    lambda:calculate_sharpe_ratio([1,np.inf]), lambda:calculate_sortino_ratio([1,np.inf]),
    lambda:calculate_annualized_metrics([-.5,-1.1]), lambda:calculate_annualized_metrics([.1],-1),
    lambda:calculate_drawdown_series([np.nan]), lambda:calculate_drawdown_series([0]),
    lambda:calculate_sharpe_ratio([1,2],annualize=True,periods_per_year=0),
    lambda:calculate_var_historical([1],1), lambda:calculate_expectancy([np.inf]),
])
def test_invalid_metrics_rejected(call):
    with pytest.raises(ValueError): call()


def test_trade_stats_breakevens_and_undefined_profit_factor():
    stats=calculate_expectancy([100,-50,0])
    assert stats['win_rate']==33.33 and stats['profit_factor']==2 and stats['expectancy']==16.67
    assert calculate_expectancy([10,20])['profit_factor'] is None
    assert calculate_expectancy([-10])['profit_factor']==0
    assert calculate_expectancy([])['total_trades']==0


def test_cost_caps_floor_fixed_and_slippage_not_capped():
    m=CostModel(fee_per_order=2,fee_bps=10,slippage_bps=5,min_fee=5,max_fee=8)
    assert m.calculate_order_cost(100,1)==pytest.approx(5.05)
    assert m.calculate_order_cost(100,100)==pytest.approx(13)
    assert m.calculate_order_cost(100,1,100)==pytest.approx(13)
    assert m.calculate_order_cost(100,0)==0


def test_roundtrip_explicit_slippage_and_multiplier():
    result=calculate_cost_aware_pnl('SELL',4,2,5,100,fees_paid=6,slippage_per_unit=.02)
    assert result['gross_pnl']==1000 and result['total_costs']==16 and result['net_pnl']==984


@pytest.mark.parametrize('call',[
    lambda:CostModel(fee_bps=-1), lambda:CostModel(min_fee=10,max_fee=5),
    lambda:CostModel(slippage_bps=np.inf), lambda:calculate_cost_aware_pnl('BUY',10,11,-1),
    lambda:calculate_cost_aware_pnl('BUY',10,11,1,fees_paid=-1),
    lambda:calculate_cost_aware_pnl('BUY',10,11,1,slippage_per_unit=-1),
    lambda:calculate_cost_aware_pnl('BUY',10,11,1,cost_model=CostModel(),fees_paid=0),
    lambda:calculate_cost_aware_pnl('BUY',10,11,1,stop_loss=12),
    lambda:calculate_cost_aware_pnl('SELL',10,11,1,stop_loss=9),
    lambda:calculate_cost_aware_pnl('BUY',10,np.nan,1),
])
def test_invalid_cost_inputs_rejected(call):
    with pytest.raises(ValueError): call()


def test_next_close_execution_cannot_capture_entry_bar_gap():
    r=backtest([100,200,220],[1,1,1],initial_capital=1000,risk_free_rate=0)
    assert r.history.Quantity.tolist()==[0,5,5]
    assert r.history.Gross_Strategy_Return.tolist()==pytest.approx([0,0,.1])
    assert r.total_return==.1 and r.trades_count==0


def test_execution_lag_two():
    df=pd.DataFrame({'Close':[100,110,120,150]})
    r=BacktestEngine(initial_capital=1000).run_signal_backtest(df,lambda p:1,execution_lag=2)
    assert r.history.Quantity.iloc[:2].tolist()==[0,0]
    assert r.total_return==.25


def test_signal_callback_only_sees_prefix_and_cannot_mutate_market_data():
    df=pd.DataFrame({'Close':[100,150,120,180]})
    lengths=[]
    def malicious(prefix):
        lengths.append(len(prefix))
        signal=prefix.Close.shift(-1).gt(prefix.Close).astype(float)
        prefix.iloc[-1,0]=99999
        return signal
    r=BacktestEngine().run_signal_backtest(df,malicious)
    assert lengths==[1,2,3,4] and r.total_return==0
    assert df.Close.tolist()==[100,150,120,180]


def test_future_perturbation_leaves_earlier_signals_orders_equity_unchanged():
    a=pd.DataFrame({'Close':[100,105,103,108,110,115]})
    b=a.copy();b.loc[4:,'Close']=[500,1]
    strategy=lambda prefix: float(prefix.Close.iloc[-1]>prefix.Close.mean())
    ea=BacktestEngine().run_signal_backtest(a,strategy).history
    eb=BacktestEngine().run_signal_backtest(b,strategy).history
    pd.testing.assert_frame_equal(ea.iloc[:4],eb.iloc[:4])


def test_fixed_fee_is_per_execution_not_allocation_fraction():
    r=backtest([100]*4,[.5,0,0,0],initial_capital=1000,cost_model=CostModel(fee_per_order=10))
    assert r.history.Cost.tolist()==[0,10,10,0]
    assert r.total_return==-.02 and r.completed_trades[0]['net_pnl']==-20
    assert r.max_drawdown_pct==-2


def test_backtest_floor_cap_and_multiplier_use_shared_order_model():
    m=CostModel(fee_per_order=1,fee_bps=100,min_fee=4,max_fee=6,slippage_bps=10)
    r=backtest([10,10,12,12],[.5,0,0,0],initial_capital=1000,cost_model=m,multiplier=100)
    assert r.history.Quantity.iloc[1]==.5
    entry=m.calculate_order_cost(10,.5,100);exit_fee=m.calculate_order_cost(12,.5,100)
    assert r.history.Cost.sum()==pytest.approx(entry+exit_fee)
    assert r.completed_trades[0]['net_pnl']==pytest.approx(100-entry-exit_fee)


def test_completed_trade_stats_count_episodes_not_bars_and_include_costs():
    r=backtest([100,100,110,105,100,100],[1,1,0,1,0,0],initial_capital=1000,cost_model=CostModel(fee_per_order=1))
    assert r.trades_count==2
    assert r.completed_trades[0]['net_pnl']==48
    assert r.completed_trades[1]['net_pnl']==-2
    assert r.win_rate==50 and r.profit_factor==24
    assert r.history.Portfolio_Value.iloc[-1]==1046


def test_reversal_closes_episode_and_charges_two_fees():
    r=backtest([100]*5,[1,-1,0,0,0],initial_capital=1000,cost_model=CostModel(fee_per_order=2))
    assert r.history.Cost.tolist()==[0,2,4,2,0]
    assert r.trades_count==2 and r.win_rate==0
    assert sum(t['net_pnl'] for t in r.completed_trades)==-8


def test_partial_exits_remain_one_completed_episode():
    r=backtest([100]*5,[1,.5,0,0,0],initial_capital=1000,cost_model=CostModel(fee_per_order=2))
    assert r.trades_count==1 and r.completed_trades[0]['net_pnl']==-6
    assert r.history.Portfolio_Value.iloc[-1]==994


def test_empty_backtest_and_one_bar_do_not_crash_or_trade():
    for prices in ([],[100]):
        r=backtest(prices,[1]*len(prices))
        assert r.total_return==0 and r.trades_count==0 and r.max_drawdown_pct==0


@pytest.mark.parametrize('prices',[[100,np.nan],[100,0],[100,np.inf]])
def test_bad_execution_prices_rejected(prices):
    with pytest.raises(ValueError): backtest(prices,[1]*len(prices))


@pytest.mark.parametrize('lag',[0,-1,1.5,True])
def test_bad_execution_lag_rejected(lag):
    with pytest.raises(ValueError):
        BacktestEngine().run_signal_backtest(pd.DataFrame({'Close':[100]}),lambda p:1,execution_lag=lag)


def test_bad_signal_alignment_and_nonfinite_target_rejected():
    df=pd.DataFrame({'Close':[100,101]})
    for callback in (lambda p:pd.Series([1,1]),lambda p:np.inf,lambda p:2):
        with pytest.raises(ValueError): BacktestEngine().run_signal_backtest(df,callback)
    with pytest.raises(ValueError):
        BacktestEngine().run_signal_backtest(df.set_axis([1,0]),lambda p:1)


def test_preprocessing_never_uses_future_price_to_fill_leading_missing():
    original=pd.DataFrame({'Close':[np.nan,100,np.nan,110]},index=pd.date_range('2026-01-01',periods=4))
    result=preprocess_data(original)
    assert original.index[0] not in result.index
    assert result.Close.tolist()==[100,100,110]
    changed=original.copy();changed.iloc[-1,0]=999
    pd.testing.assert_frame_equal(result.iloc[:2],preprocess_data(changed).iloc[:2])


def test_legacy_rsi_and_metrics_delegate_to_corrected_quant():
    df=pd.DataFrame({'Close':range(100,125)})
    pd.testing.assert_series_equal(calculate_rsi(df).RSI,calculate_rsi_wilder(df),check_names=False)
    assert calculate_rsi(df).RSI.iloc[-1]==100
    assert calculate_performance_summary(pd.DataFrame({'Close':[]}))['total_return']==0
    df=pd.DataFrame({'Close':[100,90,95,85]})
    expected=calculate_annualized_metrics([-.1,95/90-1,85/95-1])
    assert calculate_performance_summary(df)['sharpe_ratio']==expected['sharpe_ratio']


def test_streamlit_strategy_future_perturbation_and_cost_integration():
    a=pd.DataFrame({'Close':[100,101,102,103,104,105,106]})
    b=a.copy();b.loc[5:,'Close']=[99,98]
    ea=generate_trading_signals(a,2,3)
    eb=generate_trading_signals(b,2,3)
    pd.testing.assert_frame_equal(ea.iloc[:5],eb.iloc[:5])
    costly=generate_trading_signals(a,2,3,cost_model=CostModel(fee_per_order=10))
    assert costly.Strategy_Cumulative_Return.iloc[-1] < ea.Strategy_Cumulative_Return.iloc[-1]


def test_journal_completed_trades_breakevens_initial_loss_and_returns():
    def t(i,pnl,closed=True):
        return SimpleNamespace(id=i,trade_date='2026-01-01',exit_price=100 if closed else None,
                               pnl=pnl,r_multiple=None,strategy='Test')
    trades=[t(1,-100),t(2,200),t(3,0),t(4,999,False)]
    summary=dashboard_summary(trades,1000)
    assert summary['total_trades']==3 and summary['win_rate']==33.33
    assert summary['expectancy']==33.33 and summary['max_drawdown_pct']==-10
    assert summary['sharpe']==round(calculate_sharpe_ratio([-.1,200/900,0]),4)
    assert summary['sortino']==round(calculate_sortino_ratio([-.1,200/900,0]),4)
    assert group_analytics(trades,'strategy')[0]['count']==3


def test_synthetic_data_is_repeatable_without_mutating_global_rng():
    np.random.seed(123);expected=np.random.random()
    np.random.seed(123)
    a=generate_synthetic_data('TEST','2026-01-01','2026-02-01')
    assert np.random.random()==expected
    pd.testing.assert_frame_equal(a,generate_synthetic_data('TEST','2026-01-01','2026-02-01'))
