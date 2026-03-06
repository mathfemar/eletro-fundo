import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fetchAssetHistory, fetchAssets, syncHistory } from '../api/client'
import type { Asset, AssetHistoryPoint } from '../types'

const PERIOD_OPTIONS = [
  { label: '1D', value: 1 },
  { label: '7D', value: 7 },
  { label: '14D', value: 14 },
  { label: '1M', value: 30 },
  { label: '3M', value: 90 },
  { label: '6M', value: 180 },
  { label: '1A', value: 365 },
  { label: '3A', value: 1095 },
  { label: '5A', value: 1825 },
  { label: 'MÁX', value: 'MAX' as const },
]

export function AssetHistoryPage() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null)
  const [history, setHistory] = useState<AssetHistoryPoint[]>([])
  const [selectedPeriod, setSelectedPeriod] = useState<number | 'MAX'>(90)

  useEffect(() => {
    void (async () => {
      const items = await fetchAssets(true, true)
      setAssets(items)
      if (items[0]) {
        setSelectedAssetId(items[0].id_ativo)
      }
    })()
  }, [])

  useEffect(() => {
    if (!selectedAssetId) return
    void (async () => {
      const points = await fetchAssetHistory(selectedAssetId, selectedPeriod === 'MAX' ? undefined : selectedPeriod)
      setHistory(points)
    })()
  }, [selectedAssetId, selectedPeriod])

  async function handleSync() {
    await syncHistory()
    if (selectedAssetId) {
      const points = await fetchAssetHistory(selectedAssetId, selectedPeriod === 'MAX' ? undefined : selectedPeriod)
      setHistory(points)
    }
  }

  return (
    <section className="stack-lg">
      <div className="hero">
        <div>
          <p className="eyebrow">Ativos</p>
          <h2>Preço histórico</h2>
          <p className="muted">Mesma leitura visual da página live, agora usando a série histórica ajustada.</p>
        </div>
        <button className="primary-button" onClick={() => void handleSync()}>Sincronizar histórico</button>
      </div>

      <div className="panel">
        <div className="field-row">
          <div>
            <label htmlFor="asset-select-history" className="field-label">Ativo</label>
            <select id="asset-select-history" className="input" value={selectedAssetId ?? ''} onChange={(e) => setSelectedAssetId(Number(e.target.value))}>
              <option value="">Selecione</option>
              {assets.map((asset) => (
                <option key={asset.id_ativo} value={asset.id_ativo}>{asset.cd_ativo}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="history-period" className="field-label">Período</label>
            <select
              id="history-period"
              className="input"
              value={String(selectedPeriod)}
              onChange={(e) => setSelectedPeriod(e.target.value === 'MAX' ? 'MAX' : Number(e.target.value))}
            >
              {PERIOD_OPTIONS.map((option) => (
                <option key={option.label} value={String(option.value)}>{option.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="section-header">
          <h3>Resumo do ativo</h3>
          <span className="muted">
            {assets.find((asset) => asset.id_ativo === selectedAssetId)?.cd_yf ?? 'Sem ticker Yahoo'}
          </span>
        </div>
        {selectedAssetId ? (() => {
          const selectedAsset = assets.find((asset) => asset.id_ativo === selectedAssetId)
          return (
            <div className="card-grid">
              <article className="metric-card">
                <span>Ativo</span>
                <strong>{selectedAsset?.cd_ativo ?? '-'}</strong>
              </article>
              <article className="metric-card">
                <span>Último close</span>
                <strong>{selectedAsset?.last_close?.toFixed(2) ?? '-'}</strong>
              </article>
              <article className="metric-card">
                <span>Último adj close</span>
                <strong>{selectedAsset?.last_adj_close?.toFixed(2) ?? '-'}</strong>
              </article>
            </div>
          )
        })() : null}
      </div>

      <div className="panel chart-panel">
        {history.length > 0 ? (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart
              data={history.map((point) => ({
                label: new Date(point.price_date).toLocaleDateString('pt-BR'),
                price: point.adj_close_price,
              }))}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
              <XAxis dataKey="label" stroke="#a1a1aa" minTickGap={24} />
              <YAxis stroke="#a1a1aa" domain={["auto", "auto"]} />
              <Tooltip />
              <Line type="linear" dataKey="price" stroke="#facc15" strokeWidth={2} dot={{ r: 3, fill: '#fde047', stroke: '#ca8a04' }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="chart-empty">Sem histórico salvo ainda. Faça a sincronização para preencher o gráfico.</div>
        )}
      </div>
    </section>
  )
}
