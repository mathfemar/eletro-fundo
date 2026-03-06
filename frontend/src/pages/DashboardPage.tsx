import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fetchFundDetail, fetchFunds, fetchFundTimeline, syncHistory } from '../api/client'
import type { Fund, FundDetail, TimelinePoint } from '../types'

export function DashboardPage() {
  const [funds, setFunds] = useState<Fund[]>([])
  const [selectedFundId, setSelectedFundId] = useState<number | null>(null)
  const [detail, setDetail] = useState<FundDetail | null>(null)
  const [timeline, setTimeline] = useState<TimelinePoint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void (async () => {
      setLoading(true)
      try {
        const items = await fetchFunds()
        setFunds(items)
        if (items[0]) {
          setSelectedFundId(items[0].id)
        }
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  useEffect(() => {
    if (!selectedFundId) return
    void (async () => {
      const [fundDetail, fundTimeline] = await Promise.all([fetchFundDetail(selectedFundId), fetchFundTimeline(selectedFundId)])
      setDetail(fundDetail)
      setTimeline(fundTimeline)
    })()
  }, [selectedFundId])

  const cards = useMemo(() => {
    if (!detail?.snapshot) return []
    return [
      { label: 'PL', value: detail.snapshot.nav.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) },
      { label: 'Caixa', value: detail.snapshot.cash_balance.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) },
      { label: 'Valor da cota', value: detail.snapshot.unit_value.toFixed(6) },
      { label: 'Qtd. cotas', value: detail.snapshot.unit_count.toFixed(4) },
    ]
  }, [detail])

  if (loading) {
    return <section className="panel">Carregando fundos...</section>
  }

  if (funds.length === 0) {
    return (
      <section className="stack-lg">
        <div className="hero">
          <div>
            <p className="eyebrow">Simulação e análise</p>
            <h2>Painel do fundo</h2>
            <p className="muted">Comece criando o primeiro fundo e ao menos um cotista.</p>
          </div>
        </div>

        <div className="empty-state">
          <h3>Nenhum fundo cadastrado</h3>
          <p className="muted">Sem fundo e sem eventos, não há PL, cotas nem gráfico para exibir.</p>
          <div className="button-row">
            <Link className="primary-button link-button" to="/fundos/cadastro">Cadastrar fundo e cotista</Link>
            <Link className="secondary-button link-button" to="/fundos/operacoes">Lançar operações</Link>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="stack-lg">
      <div className="hero">
        <div>
          <p className="eyebrow">Simulação e análise</p>
          <h2>Painel do fundo</h2>
          <p className="muted">Linha do tempo com reprocessamento retroativo, PL, cotas e caixa.</p>
        </div>
        <button className="primary-button" onClick={() => void syncHistory()}>
          Atualizar histórico
        </button>
      </div>

      <div className="panel">
        <label className="field-label" htmlFor="fund-select">Fundo</label>
        <select id="fund-select" className="input" value={selectedFundId ?? ''} onChange={(e) => setSelectedFundId(Number(e.target.value))}>
          <option value="">Selecione</option>
          {funds.map((fund) => (
            <option key={fund.id} value={fund.id}>{fund.name}</option>
          ))}
        </select>
      </div>

      <div className="card-grid">
        {cards.map((card) => (
          <article key={card.label} className="metric-card">
            <span>{card.label}</span>
            <strong>{card.value}</strong>
          </article>
        ))}
      </div>

      {detail?.investors?.length ? (
        <div className="panel table-panel">
          <div className="section-header">
            <h3>Cotistas</h3>
            <span className="muted">Posição mais recente por cotista.</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>Cotista</th>
                <th>% do fundo</th>
                <th>Qtd. cotas</th>
                <th>Cota média</th>
                <th>Valor da posição</th>
                <th>PnL</th>
              </tr>
            </thead>
            <tbody>
              {detail.investors.map((investor) => (
                <tr key={investor.investor_id}>
                  <td>{investor.investor_name}</td>
                  <td>{investor.ownership_percent.toFixed(2)}%</td>
                  <td>{investor.unit_count.toFixed(4)}</td>
                  <td>{investor.average_unit_cost.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</td>
                  <td>{investor.position_value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</td>
                  <td className={investor.pnl >= 0 ? 'positive-text' : 'negative-text'}>
                    {investor.pnl.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {detail?.positions?.length ? (
        <div className="panel table-panel">
          <div className="section-header">
            <h3>Posições do fundo</h3>
            <span className="muted">Resumo consolidado por ativo na data mais recente.</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>Ativo</th>
                <th>Moeda</th>
                <th>Quantidade</th>
                <th>Preço atual</th>
                <th>FX</th>
                <th>Custo médio</th>
                <th>Valor de mercado</th>
                <th>Alocação</th>
                <th>PnL</th>
              </tr>
            </thead>
            <tbody>
              {detail.positions.map((position) => (
                <tr key={position.asset_id}>
                  <td>{position.asset_code}</td>
                  <td>{position.currency}</td>
                  <td>{position.quantity.toFixed(4)}</td>
                  <td>{position.current_price_local.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}</td>
                  <td>{position.fx_rate.toFixed(6)}</td>
                  <td>{position.average_cost_brl.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</td>
                  <td>{position.market_value_brl.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</td>
                  <td>{position.allocation_percent.toFixed(2)}%</td>
                  <td className={position.pnl_brl >= 0 ? 'positive-text' : 'negative-text'}>
                    {position.pnl_brl.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <div className="panel chart-panel">
        <div className="section-header">
          <h3>Evolução do PL</h3>
          <span className="muted">Recalculado sempre que houver evento retroativo.</span>
        </div>
        {timeline.length > 0 ? (
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
              <XAxis dataKey="ref_date" stroke="#a1a1aa" />
              <YAxis stroke="#a1a1aa" />
              <Tooltip />
              <Area dataKey="nav" stroke="#facc15" fill="#ca8a04" fillOpacity={0.24} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="chart-empty">Ainda não há timeline. Cadastre aporte inicial e trades para gerar o gráfico.</div>
        )}
      </div>
    </section>
  )
}
