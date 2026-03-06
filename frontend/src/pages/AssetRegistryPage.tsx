import { FormEvent, useEffect, useMemo, useState } from 'react'
import { createAsset, fetchAssets, updateAsset } from '../api/client'
import type { Asset, AssetCreatePayload } from '../types'

const initialForm: AssetCreatePayload = {
  cd_ativo: '',
  cd_yf: '',
  preco_online: true,
  moeda: 'BRL',
  fator_preco: 1,
}

export function AssetRegistryPage() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [form, setForm] = useState<AssetCreatePayload>(initialForm)
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')

  async function loadAssets() {
    const rows = await fetchAssets(false, false)
    setAssets(rows)
  }

  useEffect(() => {
    void loadAssets()
  }, [])

  const filteredAssets = useMemo(() => {
    const term = search.trim().toUpperCase()
    if (!term) return assets
    return assets.filter((asset) => asset.cd_ativo.toUpperCase().includes(term) || (asset.cd_yf ?? '').toUpperCase().includes(term))
  }, [assets, search])

  function startNewAsset() {
    setSelectedAssetId(null)
    setForm(initialForm)
    setStatus('')
  }

  function selectAsset(asset: Asset) {
    setSelectedAssetId(asset.id_ativo)
    setForm({
      cd_ativo: asset.cd_ativo,
      cd_yf: asset.cd_yf ?? '',
      preco_online: asset.preco_online,
      moeda: asset.moeda || 'BRL',
      fator_preco: asset.fator_preco || 1,
    })
    setStatus('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setStatus(selectedAssetId ? 'Atualizando ativo...' : 'Salvando ativo...')
    try {
      if (selectedAssetId) {
        await updateAsset(selectedAssetId, { ...form, cd_yf: form.cd_yf || null })
      } else {
        await createAsset({ ...form, cd_yf: form.cd_yf || null })
      }
      await loadAssets()
      setStatus(selectedAssetId ? 'Ativo atualizado com sucesso.' : 'Ativo cadastrado com sucesso.')
      if (!selectedAssetId) {
        setForm(initialForm)
      }
    } catch {
      setStatus(selectedAssetId ? 'Não foi possível atualizar o ativo.' : 'Não foi possível cadastrar o ativo.')
    }
  }

  return (
    <section className="stack-lg">
      <div className="hero">
        <div>
          <p className="eyebrow">Ativos</p>
          <h2>Cadastro de ativos</h2>
          <p className="muted">O cadastro usa `DIM_ATIVO` e `DIM_ATIVO_MAPPING` como fonte principal.</p>
        </div>
      </div>

      <div className="two-column-grid">
        <div className="panel stack-md">
          <div className="section-header">
            <h3>Pesquisar ativos</h3>
            <button className="secondary-button" type="button" onClick={startNewAsset}>Novo ativo</button>
          </div>
          <div>
            <label className="field-label" htmlFor="asset-search">Buscar por código ou ticker</label>
            <input id="asset-search" className="input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Ex.: PETR4 ou PETR4.SA" />
          </div>
          <div className="asset-search-results">
            {filteredAssets.map((asset) => (
              <button
                key={asset.id_ativo}
                type="button"
                className={selectedAssetId === asset.id_ativo ? 'asset-result active' : 'asset-result'}
                onClick={() => selectAsset(asset)}
              >
                <strong>{asset.cd_ativo}</strong>
                <span>{asset.cd_yf ?? 'Sem ticker Yahoo'}</span>
              </button>
            ))}
          </div>
        </div>

        <form className="panel stack-md" onSubmit={handleSubmit}>
          <h3>{selectedAssetId ? 'Editar ativo' : 'Novo ativo'}</h3>
          <div>
            <label className="field-label" htmlFor="cd-ativo">Código do ativo</label>
            <input id="cd-ativo" className="input" value={form.cd_ativo} onChange={(e) => setForm((current) => ({ ...current, cd_ativo: e.target.value.toUpperCase() }))} required />
          </div>
          <div>
            <label className="field-label" htmlFor="cd-yf">Ticker yfinance</label>
            <input id="cd-yf" className="input" value={form.cd_yf ?? ''} onChange={(e) => setForm((current) => ({ ...current, cd_yf: e.target.value.toUpperCase() }))} placeholder="PETR4.SA" />
          </div>
          <div className="field-row">
            <div>
              <label className="field-label" htmlFor="moeda">Moeda</label>
              <input id="moeda" className="input" value={form.moeda} onChange={(e) => setForm((current) => ({ ...current, moeda: e.target.value.toUpperCase() }))} />
            </div>
            <div>
              <label className="field-label" htmlFor="fator-preco">Fator preço</label>
              <input id="fator-preco" className="input" type="number" min="0.000001" step="0.000001" value={form.fator_preco} onChange={(e) => setForm((current) => ({ ...current, fator_preco: Number(e.target.value) }))} />
            </div>
          </div>
          <label className="checkbox-row">
            <input type="checkbox" checked={form.preco_online} onChange={(e) => setForm((current) => ({ ...current, preco_online: e.target.checked }))} />
            <span>Habilitar `PRECO_ONLINE`</span>
          </label>
          <div className="button-row">
            <button className="primary-button" type="submit">{selectedAssetId ? 'Salvar alterações' : 'Cadastrar ativo'}</button>
            {selectedAssetId ? <button className="secondary-button" type="button" onClick={startNewAsset}>Cancelar edição</button> : null}
          </div>
          {status ? <div className="status-box">{status}</div> : null}
        </form>
      </div>
    </section>
  )
}
