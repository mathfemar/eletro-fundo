import { FormEvent, useEffect, useMemo, useState } from 'react'
import {
  createCapitalEvent,
  createTrade,
  fetchAssets,
  fetchFunds,
  fetchInvestors,
  fetchTradePreview,
  recalculateFund,
  syncDividends,
  syncHistory,
  syncLive,
} from '../api/client'
import type { Asset, CapitalEventCreatePayload, CapitalEventType, Fund, Investor, TradeCreatePayload, TradePreview, TradeSide } from '../types'

const initialCapitalEvent: CapitalEventCreatePayload = {
  investor_id: 0,
  event_type: 'INITIAL',
  event_date: '',
  amount: 0,
  notes: '',
}

const initialTrade: TradeCreatePayload = {
  asset_id: 0,
  trade_date: '',
  side: 'BUY',
  quantity: 0,
  unit_price: 0,
  fees: 0,
  notes: '',
}

export function FundOperationsPage() {
  const [funds, setFunds] = useState<Fund[]>([])
  const [investors, setInvestors] = useState<Investor[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [selectedFundId, setSelectedFundId] = useState<number>(0)
  const [capitalEvent, setCapitalEvent] = useState<CapitalEventCreatePayload>(initialCapitalEvent)
  const [trade, setTrade] = useState<TradeCreatePayload>(initialTrade)
  const [tradePreview, setTradePreview] = useState<TradePreview | null>(null)
  const [tradePreviewError, setTradePreviewError] = useState('')
  const [status, setStatus] = useState('')

  const selectedTradeAsset = useMemo(
    () => assets.find((asset) => asset.id_ativo === trade.asset_id) ?? null,
    [assets, trade.asset_id],
  )

  async function loadData() {
    const [fundRows, investorRows, assetRows] = await Promise.all([
      fetchFunds(),
      fetchInvestors(),
      fetchAssets(false, false),
    ])
    setFunds(fundRows)
    setInvestors(investorRows)
    setAssets(assetRows)
    if (fundRows[0] && !selectedFundId) {
      setSelectedFundId(fundRows[0].id)
    }
    if (investorRows[0] && !capitalEvent.investor_id) {
      setCapitalEvent((current) => ({ ...current, investor_id: investorRows[0].id }))
    }
    if (assetRows[0] && !trade.asset_id) {
      setTrade((current) => ({ ...current, asset_id: assetRows[0].id_ativo }))
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  useEffect(() => {
    if (!selectedFundId || !trade.asset_id || !trade.trade_date || trade.quantity <= 0 || trade.unit_price <= 0 || trade.fees < 0) {
      setTradePreview(null)
      setTradePreviewError('')
      return
    }

    let cancelled = false

    void (async () => {
      try {
        const preview = await fetchTradePreview(selectedFundId, trade.asset_id, trade.trade_date, trade.quantity, trade.unit_price, trade.fees)
        if (!cancelled) {
          setTradePreview(preview)
          setTradePreviewError('')
        }
      } catch {
        if (!cancelled) {
          setTradePreview(null)
          setTradePreviewError('Não foi possível montar a prévia do trade para esta data.')
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [selectedFundId, trade.asset_id, trade.trade_date, trade.quantity, trade.unit_price, trade.fees])

  async function handleCapitalEventSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedFundId) return
    setStatus('Salvando evento de capital...')
    try {
      await createCapitalEvent(selectedFundId, capitalEvent)
      setCapitalEvent((current) => ({ ...initialCapitalEvent, investor_id: current.investor_id, event_type: current.event_type }))
      setStatus('Evento registrado e fundo recalculado.')
    } catch {
      setStatus('Não foi possível registrar o evento de capital.')
    }
  }

  async function handleTradeSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedFundId) return
    setStatus('Salvando trade...')
    try {
      await createTrade(selectedFundId, trade)
      setTrade((current) => ({ ...initialTrade, asset_id: current.asset_id, side: current.side }))
      setStatus('Trade registrado e fundo recalculado.')
    } catch {
      setStatus('Não foi possível registrar o trade.')
    }
  }

  async function handleAction(action: 'history' | 'live' | 'dividends' | 'recalc') {
    setStatus('Processando ação...')
    try {
      if (action === 'history') await syncHistory()
      if (action === 'live') await syncLive()
      if (action === 'dividends') await syncDividends()
      if (action === 'recalc' && selectedFundId) await recalculateFund(selectedFundId)
      setStatus('Ação executada com sucesso.')
    } catch {
      setStatus('Falha ao executar a ação.')
    }
  }

  return (
    <section className="stack-lg">
      <div className="hero">
        <div>
          <p className="eyebrow">Fundos</p>
          <h2>Operações e recálculo</h2>
          <p className="muted">Cadastre aportes, resgates, trades e force recálculo retroativo quando precisar.</p>
        </div>
      </div>

      <div className="panel stack-md">
        <div>
          <label className="field-label" htmlFor="selected-fund">Fundo</label>
          <select id="selected-fund" className="input" value={selectedFundId || ''} onChange={(e) => setSelectedFundId(Number(e.target.value))}>
            <option value="">Selecione</option>
            {funds.map((fund) => (
              <option key={fund.id} value={fund.id}>{fund.name}</option>
            ))}
          </select>
        </div>
        <div className="button-row">
          <button className="secondary-button" type="button" onClick={() => void handleAction('history')}>Sincronizar histórico</button>
          <button className="secondary-button" type="button" onClick={() => void handleAction('live')}>Sincronizar live</button>
          <button className="secondary-button" type="button" onClick={() => void handleAction('dividends')}>Sincronizar proventos</button>
          <button className="primary-button" type="button" onClick={() => void handleAction('recalc')}>Recalcular fundo</button>
        </div>
        {status ? <div className="status-box">{status}</div> : null}
      </div>

      <div className="two-column-grid">
        <form className="panel stack-md" onSubmit={handleCapitalEventSubmit}>
          <h3>Aporte, resgate ou aporte inicial</h3>
          <div className="field-row">
            <div>
              <label className="field-label" htmlFor="capital-investor">Cotista</label>
              <select id="capital-investor" className="input" value={capitalEvent.investor_id || ''} onChange={(e) => setCapitalEvent((current) => ({ ...current, investor_id: Number(e.target.value) }))}>
                <option value="">Selecione</option>
                {investors.map((investor) => (
                  <option key={investor.id} value={investor.id}>{investor.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="capital-type">Tipo</label>
              <select id="capital-type" className="input" value={capitalEvent.event_type} onChange={(e) => setCapitalEvent((current) => ({ ...current, event_type: e.target.value as CapitalEventType }))}>
                <option value="INITIAL">Aporte inicial</option>
                <option value="CONTRIBUTION">Aporte</option>
                <option value="REDEMPTION">Resgate</option>
              </select>
            </div>
          </div>
          <div className="field-row">
            <div>
              <label className="field-label" htmlFor="capital-date">Data</label>
              <input id="capital-date" className="input" type="date" value={capitalEvent.event_date} onChange={(e) => setCapitalEvent((current) => ({ ...current, event_date: e.target.value }))} required />
            </div>
            <div>
              <label className="field-label" htmlFor="capital-amount">Valor</label>
              <input id="capital-amount" className="input" type="number" min="0.01" step="0.01" value={capitalEvent.amount || ''} onChange={(e) => setCapitalEvent((current) => ({ ...current, amount: Number(e.target.value) }))} required />
            </div>
          </div>
          <div>
            <label className="field-label" htmlFor="capital-notes">Observações</label>
            <textarea id="capital-notes" className="input" value={capitalEvent.notes ?? ''} onChange={(e) => setCapitalEvent((current) => ({ ...current, notes: e.target.value }))} rows={4} />
          </div>
          <button className="primary-button" type="submit">Salvar evento de capital</button>
        </form>

        <form className="panel stack-md" onSubmit={handleTradeSubmit}>
          <h3>Trade retroativo</h3>
          <div className="field-row">
            <div>
              <label className="field-label" htmlFor="trade-asset">Ativo</label>
              <select id="trade-asset" className="input" value={trade.asset_id || ''} onChange={(e) => setTrade((current) => ({ ...current, asset_id: Number(e.target.value) }))}>
                <option value="">Selecione</option>
                {assets.map((asset) => (
                  <option key={asset.id_ativo} value={asset.id_ativo}>{asset.cd_ativo}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="trade-side">Lado</label>
              <select id="trade-side" className="input" value={trade.side} onChange={(e) => setTrade((current) => ({ ...current, side: e.target.value as TradeSide }))}>
                <option value="BUY">Compra</option>
                <option value="SELL">Venda</option>
              </select>
            </div>
          </div>
          <div className="field-row">
            <div>
              <label className="field-label" htmlFor="trade-date">Data</label>
              <input id="trade-date" className="input" type="date" value={trade.trade_date} onChange={(e) => setTrade((current) => ({ ...current, trade_date: e.target.value }))} required />
            </div>
            <div>
              <label className="field-label" htmlFor="trade-qty">Quantidade</label>
              <input id="trade-qty" className="input" type="number" min="0.000001" step="0.000001" value={trade.quantity || ''} onChange={(e) => setTrade((current) => ({ ...current, quantity: Number(e.target.value) }))} required />
            </div>
          </div>
          <div className="field-row">
            <div>
              <label className="field-label" htmlFor="trade-price">Preço unitário</label>
              <input id="trade-price" className="input" type="number" min="0.000001" step="0.000001" value={trade.unit_price || ''} onChange={(e) => setTrade((current) => ({ ...current, unit_price: Number(e.target.value) }))} required />
            </div>
            <div>
              <label className="field-label" htmlFor="trade-fees">Custos</label>
              <input id="trade-fees" className="input" type="number" min="0" step="0.01" value={trade.fees || ''} onChange={(e) => setTrade((current) => ({ ...current, fees: Number(e.target.value) }))} />
            </div>
          </div>
          <div>
            <label className="field-label" htmlFor="trade-notes">Observações</label>
            <textarea id="trade-notes" className="input" value={trade.notes ?? ''} onChange={(e) => setTrade((current) => ({ ...current, notes: e.target.value }))} rows={4} />
          </div>

          <div className="preview-panel stack-md">
            <div className="section-header">
              <h3>Prévia do trade</h3>
              <span className="muted">Cálculo em BRL com FX do dia.</span>
            </div>
            {tradePreview ? (
              <div className="card-grid">
                <article className="metric-card">
                  <span>Ativo</span>
                  <strong>{tradePreview.asset_code}</strong>
                </article>
                <article className="metric-card">
                  <span>Moeda</span>
                  <strong>{tradePreview.asset_currency}</strong>
                </article>
                <article className="metric-card">
                  <span>FX do dia</span>
                  <strong>{tradePreview.fx_rate.toFixed(6)}</strong>
                </article>
                <article className="metric-card">
                  <span>Caixa antes do trade</span>
                  <strong>{tradePreview.cash_before_trade_brl.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</strong>
                </article>
                <article className="metric-card">
                  <span>Financeiro local</span>
                  <strong>{tradePreview.gross_value_local.toLocaleString('pt-BR', { style: 'currency', currency: tradePreview.asset_currency })}</strong>
                </article>
                <article className="metric-card">
                  <span>Custos em BRL</span>
                  <strong>{tradePreview.fees_brl.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</strong>
                </article>
                <article className="metric-card">
                  <span>Financeiro em BRL</span>
                  <strong>{tradePreview.gross_value_brl.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</strong>
                </article>
                <article className="metric-card">
                  <span>Total do trade</span>
                  <strong>{tradePreview.total_value_brl.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</strong>
                </article>
              </div>
            ) : (
              <div className="chart-empty compact-empty">
                {tradePreviewError || `Preencha ativo, data, quantidade e preço para ver a prévia${selectedTradeAsset ? ` de ${selectedTradeAsset.cd_ativo}` : ''}.`}
              </div>
            )}
          </div>

          <button className="primary-button" type="submit">Salvar trade</button>
        </form>
      </div>
    </section>
  )
}
