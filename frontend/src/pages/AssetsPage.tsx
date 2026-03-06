import { useEffect, useState } from 'react'
import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fetchAssetHistory, fetchAssets } from '../api/client'
import type { Asset, AssetHistoryPoint } from '../types'

export function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null)
  const [history, setHistory] = useState<AssetHistoryPoint[]>([])

  useEffect(() => {
    void (async () => {
      const items = await fetchAssets()
      setAssets(items)
      if (items[0]) {
        setSelectedAssetId(items[0].id_ativo)
      }
    })()
  }, [])

  useEffect(() => {
    if (!selectedAssetId) return
    void (async () => {
      const points = await fetchAssetHistory(selectedAssetId)
      setHistory(points)
    })()
  }, [selectedAssetId])

  return (
    <section className="stack-lg">
      <div className="hero">
        <div>
          <p className="eyebrow">Mercado</p>
          <h2>Histórico por ativo</h2>
          <p className="muted">Visualização de `adj_close` e retorno diário persistido.</p>
        </div>
      </div>

      <div className="panel">
        <label htmlFor="asset-select" className="field-label">Ativo</label>
        <select id="asset-select" className="input" value={selectedAssetId ?? ''} onChange={(e) => setSelectedAssetId(Number(e.target.value))}>
          <option value="">Selecione</option>
          {assets.map((asset) => (
            <option key={asset.id_ativo} value={asset.id_ativo}>{asset.cd_ativo}</option>
          ))}
        </select>
      </div>

      <div className="panel table-panel">
        <table>
          <thead>
            <tr>
              <th>Ativo</th>
              <th>Ticker YF</th>
              <th>Último close</th>
              <th>Último adj close</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((asset) => (
              <tr key={asset.id_ativo}>
                <td>{asset.cd_ativo}</td>
                <td>{asset.cd_yf ?? '-'}</td>
                <td>{asset.last_close?.toFixed(2) ?? '-'}</td>
                <td>{asset.last_adj_close?.toFixed(2) ?? '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel chart-panel">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={history}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="price_date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="adj_close_price" stroke="#10b981" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
