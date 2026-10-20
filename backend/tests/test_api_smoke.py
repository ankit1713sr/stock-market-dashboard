"""API verification must never connect to the repository database."""
import hashlib
import importlib
import sqlite3
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import database
from app.models import Trade
from data_loader import generate_synthetic_data


@pytest.fixture(scope='module',autouse=True)
def protect_existing_database(legacy_source):
    path=legacy_source
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as conn:
        rows=conn.execute('SELECT * FROM trades ORDER BY id').fetchall()
        assert len(rows)==29
    def refuse_connection(*args,**kwargs):
        raise AssertionError('Tests attempted to connect to the real application database')
    event.listen(database.engine,'do_connect',refuse_connection)
    yield
    event.remove(database.engine,'do_connect',refuse_connection)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as conn:
        assert conn.execute('SELECT * FROM trades ORDER BY id').fetchall()==rows


@pytest.fixture
def client(monkeypatch):
    # Import under a DDL prohibition BEFORE creating a disposable database.
    with patch.object(database.Base.metadata,'create_all',side_effect=AssertionError('DDL during API import')):
        main=importlib.import_module('app.main')
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    database.Base.metadata.create_all(engine)
    sessions=sessionmaker(bind=engine)
    def get_test_db():
        with sessions() as session:
            yield session
    main.app.dependency_overrides[database.get_db]=get_test_db
    monkeypatch.setattr(main,'engine',engine)
    monkeypatch.setattr('data_loader.fetch_stock_data',generate_synthetic_data)
    with TestClient(main.app) as client:
        yield client
    main.app.dependency_overrides.clear()
    engine.dispose()


def payload(**updates):
    return dict(symbol='TEST',side='BUY',trade_date='2026-01-01',qty=10,
                entry_price=100,exit_price=110,stop_loss=95,**updates)


def test_api_import_never_initializes_or_migrates():
    main=importlib.import_module('app.main')
    with patch.object(database.Base.metadata,'create_all',side_effect=AssertionError('DDL during import')):
        importlib.reload(main)


def test_api_health_and_existing_response_shapes(client):
    response=client.get('/health')
    assert response.status_code==200 and response.json()['trades_count']==0
    assert client.get('/api/trades').json()==[]
    assert client.get('/api/v1/trades').json()==[]
    summary=client.get('/api/v1/dashboard/summary').json()
    assert set(summary)=={'total_trades','net_pnl','win_rate','wins','losses','profit_factor',
        'avg_trade_pnl','win_loss_ratio','avg_r_multiple','expectancy','sharpe','sortino',
        'max_drawdown_pct','var_95','best_trade','worst_trade','equity_curve'}
    assert summary['total_trades']==0


def test_api_crud_roundtrip_aliases_and_completed_trade_summary(client):
    response=client.post('/api/v1/trades',json=payload())
    assert response.status_code==201,response.text
    trade=response.json(); trade_id=trade['id']
    assert trade['pnl']==100 and trade['r_multiple']==2
    compat=client.get('/api/trades').json()[0]
    assert compat['entry']==compat['entry_price']==100
    assert compat['exit']==compat['exit_price']==110
    assert compat['date']==compat['trade_date']=='2026-01-01'
    assert 'chartUrl' in compat and 'chart_url' in compat
    assert client.get(f'/api/v1/trades/{trade_id}').status_code==200
    summary=client.get('/api/v1/dashboard/summary').json()
    assert summary['profit_factor'] is None  # no losses: never a dollar-valued ratio
    assert summary['total_trades']==1
    updated=client.put(f'/api/v1/trades/{trade_id}',json={'exit_price':90})
    assert updated.status_code==200 and updated.json()['pnl']==-100
    summary=client.get('/api/v1/dashboard/summary').json()
    assert summary['max_drawdown_pct']==-1
    assert client.get('/api/v1/calendar/2026/1').json()['days'][0]['pnl']==-100
    for kind in ('strategy','emotion','mistakes'):
        response=client.get(f'/api/v1/analytics/{kind}')
        assert response.status_code==200 and response.json()[0]['count']==1
    assert client.delete(f'/api/v1/trades/{trade_id}').status_code==204
    assert client.get(f'/api/v1/trades/{trade_id}').status_code==404
    assert client.get('/health').json()['trades_count']==0


def test_api_open_trades_remain_readable_but_not_completed_statistics(client):
    data=payload();data['exit_price']=None
    response=client.post('/api/v1/trades',json=data)
    assert response.status_code==201 and response.json()['pnl'] is None
    assert len(client.get('/api/trades').json())==1
    assert client.get('/api/v1/dashboard/summary').json()['total_trades']==0
    assert client.get('/api/v1/analytics/strategy').json()==[]


def test_api_position_sizing_validation_and_market_quant_integration(client):
    response=client.post('/api/v1/risk/position-size',json={
        'account_balance':25000,'risk_pct':1,'entry_price':100,'stop_loss':98})
    assert response.status_code==200 and response.json()['quantity']==125
    assert client.post('/api/v1/trades',json={'symbol':'BAD'}).status_code==422
    assert client.get('/api/v1/calendar/2026/13').status_code==400
    response=client.get('/api/v1/market/TEST')
    assert response.status_code==200,response.text
    market=response.json()
    assert set(market)=={'ticker','latest','change','change_pct','candles'}
    assert market['candles'] and 0<=market['latest']['rsi']<=100
