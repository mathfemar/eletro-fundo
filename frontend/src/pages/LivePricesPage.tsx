import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fetchAssetLive, fetchAssets, syncLive } from '../api/client'
import type { Asset, LivePricePoint } from '../types'

export function LivePricesPage() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null)
  const [points, setPoints] = useState<LivePricePoint[]>([])

  useEffect(() => {
    void (async () => {
      const items = await fetchAssets(true, true)
      setAssets(items)
      if (items[0]) setSelectedAssetId(items[0].id_ativo)
    })()
  }, [])

  useEffect(() => {
    if (!selectedAssetId) return
    void (async () => {
      const rows = await fetchAssetLive(selectedAssetId)
      setPoints(rows)
    })()
  }, [selectedAssetId])

  async function handleRefresh() {
    await syncLive()
    if (selectedAssetId) {
      const rows = await fetchAssetLive(selectedAssetId)
      setPoints(rows)
    }
  }

  return (
    <section className="stack-lg">
      <div className="hero">
        <div>
          <p className="eyebrow">Intraday</p>
          <h2>Price live 1D</h2>
          <p className="muted">Atualização a cada 30 minutos, pulando pontos idênticos ao último preço salvo.</p>
        </div>
        <button className="primary-button" onClick={() => void handleRefresh()}>Atualizar agora</button>
      </div>

      <div className="panel">
        <label htmlFor="live-asset-select" className="field-label">Ativo</label>
        <select id="live-asset-select" className="input" value={selectedAssetId ?? ''} onChange={(e) => setSelectedAssetId(Number(e.target.value))}>
          <option value="">Selecione</option>
          {assets.map((asset) => (
            <option key={asset.id_ativo} value={asset.id_ativo}>{asset.cd_ativo}</option>
          ))}
        </select>
      </div>

      <div className="panel chart-panel">
        {points.length > 0 ? (
          <ResponsiveContainer width="100%" height={360}>
            <LineChart
              data={points.map((point) => ({
                label: new Date(point.collected_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
                price: point.price,
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
          <div className="chart-empty">Nenhum ponto intraday salvo ainda. Use o botão de atualização para buscar preços live.</div>
        )}
      </div>
    </section>
  )
}
