// Dependency-free compatibility tests: node --test frontend/tests/accounting.test.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../app.js'), 'utf8');

function fixture() {
  const nodes = {};
  const handlers = {};
  const alerts = [];
  const context = vm.createContext({
    document: {
      addEventListener() {},
      querySelectorAll() { return []; },
      getElementById(id) {
        return nodes[id] ??= {value: '', style: {}, classList: {remove() {}, add() {}},
          addEventListener(event, callback) { handlers[`${id}:${event}`] = callback; }};
      },
    },
    window: {addEventListener() {}}, console,
    alert(message) { alerts.push(message); },
    localStorage: {getItem() { return null; }, setItem() {}},
  });
  vm.runInContext(source, context);
  const run = text => vm.runInContext(text, context);
  return {context, nodes, handlers, alerts, run};
}

test('net P&L survives normalization and cache roundtrips including known zero', () => {
  const {run} = fixture();
  run(`input = {id:1, entry_price:100, exit_price:110, qty:10, pnl:100,
    net_pnl:90, brokerage_fee:2, transaction_fee:3, slippage_cost:5,
    contract_multiplier:1, accounting_version:1, cost_status:'reported'};
    result=normalizeTrade(JSON.parse(JSON.stringify(normalizeTrade(input))));`);
  assert.equal(run('result.pnl'), 90);
  assert.equal(run('result.net_pnl'), 90);
  assert.equal(run('result.returnPct'), 9);
  assert.equal(run('result.brokerage_fee'), 2);
  assert.equal(run('result.pnl_basis'), 'net_reported');
  assert.equal(run('normalizeTrade({...input,net_pnl:0}).pnl'), 0);
});

test('legacy futures retain their stored values and unknown cost metadata', () => {
  const {run} = fixture();
  run(`result=normalizeTrade({asset:'Futures',entry:100,exit:110,qty:2,pnl:20});`);
  assert.equal(run('result.pnl'), 20);
  assert.equal(run('result.contract_multiplier'), null);
  assert.equal(run('result.brokerage_fee'), null);
  assert.equal(run('result.pnl_basis'), 'legacy_unknown');
});

test('fallback risk and return calculations use explicit multipliers and net P&L', () => {
  const {run} = fixture();
  run(`result=normalizeTrade({entry:2,exit:3,qty:5,net_pnl:490,contract_multiplier:100,stopLoss:1});`);
  assert.equal(run('result.returnPct'), 49);
  assert.equal(run('result.rMultiple'), 0.98);
});

test('KPI, calendar and basis labels exclude open-trade realized P&L', async () => {
  const {run, nodes} = fixture();
  run(`trades=[normalizeTrade({date:'2026-10-20',entry:100,exit:110,qty:10,net_pnl:90,
      accounting_version:1,cost_status:'reported'}),
      normalizeTrade({date:'2026-10-20',entry:100,exit:100,qty:1,pnl:0}),
      normalizeTrade({date:'2026-10-20',entry:100,exit:null,qty:1,pnl:999})];`);
  await run('updateKPICards()');
  run('updateAccountingLabel()');
  assert.equal(nodes.kpiTotalTrades.innerHTML, 2);
  assert.equal(nodes.kpiNetPnl.innerHTML, '+$90.00');
  assert.equal(nodes.kpiProfitFactor.innerHTML, 'N/A');
  assert.equal(run('buildLocalCalendarDays(2026,9)[0].pnl'), 90);
  assert.match(nodes.accountingBasisLabel.textContent, /1 of 2.*unknown costs/);
});

test('API null ratios remain readable and costs are explicitly labeled', async () => {
  const {run, nodes, context} = fixture();
  context.window.TradePulseAPI = {getDashboardSummary: async () => ({
    total_trades:1, net_pnl:90, profit_factor:null, win_loss_ratio:null,
  })};
  run(`trades=[normalizeTrade({exit:110,entry:100,qty:10,net_pnl:90,
    accounting_version:1,cost_status:'estimated'})]; useApiBackend=true;`);
  await run('updateKPICards()');
  run('updateAccountingLabel()');
  assert.equal(nodes.kpiProfitFactor.innerHTML, 'N/A');
  assert.equal(nodes.kpiWinLossRatio.innerHTML, 'N/A');
  assert.match(nodes.accountingBasisLabel.textContent, /1 estimated-cost/);
});

test('offline editing of cost-aware trades preserves cached accounting', async () => {
  const {run, nodes, handlers, alerts} = fixture();
  run('setupEventListeners()');
  run("document.getElementById('tradeId').value='1'");
  run(`trades=[normalizeTrade({id:1,entry:100,exit:110,qty:10,net_pnl:90,
    accounting_version:1,cost_status:'reported'})];
    buildTradePayloadFromForm=()=>({entry_price:100,exit_price:120,qty:10});`);
  await handlers['tradeForm:submit']({preventDefault(){}});
  assert.equal(run('trades[0].net_pnl'), 90);
  assert.match(alerts[0], /Reconnect/);
});

test('failed API edits preserve cached net results', async () => {
  const {run, nodes, handlers, alerts, context} = fixture();
  context.window.TradePulseAPI = {updateTrade: async () => { throw new Error('offline'); }};
  run('setupEventListeners()');
  run("document.getElementById('tradeId').value='1'");
  run(`useApiBackend=true;
    trades=[normalizeTrade({id:1,entry:100,exit:110,qty:10,net_pnl:90,
    accounting_version:1,cost_status:'reported'})];
    buildTradePayloadFromForm=()=>({entry_price:100,exit_price:120,qty:10});`);
  await handlers['tradeForm:submit']({preventDefault(){}});
  assert.equal(run('trades[0].pnl'), 90);
  assert.match(alerts[0], /not saved/);
});

test('calendar detail labels unknown costs and never counts open trades as wins', () => {
  const {run, nodes} = fixture();
  run(`openDayModal('2026-10-20',[
    normalizeTrade({entry:100,exit:null,qty:1,pnl:999}),
    normalizeTrade({entry:100,exit:110,qty:1,pnl:10})],10)`);
  assert.match(nodes.calDayModalBody.innerHTML, /1 Wins/);
  assert.match(nodes.calDayModalBody.innerHTML, /Open trade; no realized/);
  assert.match(nodes.calDayModalBody.innerHTML, /Legacy\/gross P&L; costs unknown/);
});
