import { FormEvent, useEffect, useState } from 'react'
import { createFund, createInvestor, fetchFunds, fetchInvestors } from '../api/client'
import type { Fund, FundCreatePayload, Investor, InvestorCreatePayload } from '../types'

export function FundRegistryPage() {
  const [funds, setFunds] = useState<Fund[]>([])
  const [investors, setInvestors] = useState<Investor[]>([])
  const [fundForm, setFundForm] = useState<FundCreatePayload>({ name: '', inception_date: '', base_currency: 'BRL' })
  const [investorForm, setInvestorForm] = useState<InvestorCreatePayload>({ name: '' })
  const [status, setStatus] = useState('')

  async function loadData() {
    const [fundRows, investorRows] = await Promise.all([fetchFunds(), fetchInvestors()])
    setFunds(fundRows)
    setInvestors(investorRows)
  }

  useEffect(() => {
    void loadData()
  }, [])

  async function handleFundSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setStatus('Salvando fundo...')
    try {
      await createFund(fundForm)
      setFundForm({ name: '', inception_date: '', base_currency: 'BRL' })
      await loadData()
      setStatus('Fundo criado com sucesso.')
    } catch {
      setStatus('Não foi possível criar o fundo.')
    }
  }

  async function handleInvestorSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setStatus('Salvando cotista...')
    try {
      await createInvestor(investorForm)
      setInvestorForm({ name: '' })
      await loadData()
      setStatus('Cotista criado com sucesso.')
    } catch {
      setStatus('Não foi possível criar o cotista.')
    }
  }

  return (
    <section className="stack-lg">
      <div className="hero">
        <div>
          <p className="eyebrow">Fundos</p>
          <h2>Cadastro de fundos e cotistas</h2>
          <p className="muted">Crie o fundo, defina a data de início e cadastre os cotistas antes das operações.</p>
        </div>
      </div>

      <div className="two-column-grid">
        <form className="panel stack-md" onSubmit={handleFundSubmit}>
          <h3>Novo fundo</h3>
          <div>
            <label className="field-label" htmlFor="fund-name">Nome do fundo</label>
            <input id="fund-name" className="input" value={fundForm.name} onChange={(e) => setFundForm((current) => ({ ...current, name: e.target.value }))} required />
          </div>
          <div className="field-row">
            <div>
              <label className="field-label" htmlFor="fund-date">Data de início</label>
              <input id="fund-date" className="input" type="date" value={fundForm.inception_date} onChange={(e) => setFundForm((current) => ({ ...current, inception_date: e.target.value }))} required />
            </div>
            <div>
              <label className="field-label" htmlFor="fund-currency">Moeda base</label>
              <input id="fund-currency" className="input" value={fundForm.base_currency} onChange={(e) => setFundForm((current) => ({ ...current, base_currency: e.target.value.toUpperCase() }))} required />
            </div>
          </div>
          <button className="primary-button" type="submit">Criar fundo</button>
        </form>

        <form className="panel stack-md" onSubmit={handleInvestorSubmit}>
          <h3>Novo cotista</h3>
          <div>
            <label className="field-label" htmlFor="investor-name">Nome do cotista</label>
            <input id="investor-name" className="input" value={investorForm.name} onChange={(e) => setInvestorForm({ name: e.target.value })} required />
          </div>
          <button className="primary-button" type="submit">Criar cotista</button>
          {status ? <div className="status-box">{status}</div> : null}
        </form>
      </div>

      <div className="two-column-grid">
        <div className="panel table-panel">
          <div className="section-header">
            <h3>Fundos</h3>
            <span className="muted">Selecione depois nas telas de operação e análise.</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nome</th>
                <th>Início</th>
                <th>Moeda</th>
              </tr>
            </thead>
            <tbody>
              {funds.map((fund) => (
                <tr key={fund.id}>
                  <td>{fund.id}</td>
                  <td>{fund.name}</td>
                  <td>{fund.inception_date}</td>
                  <td>{fund.base_currency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel table-panel">
          <div className="section-header">
            <h3>Cotistas</h3>
            <span className="muted">Disponíveis para aporte inicial, aporte e resgate.</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nome</th>
              </tr>
            </thead>
            <tbody>
              {investors.map((investor) => (
                <tr key={investor.id}>
                  <td>{investor.id}</td>
                  <td>{investor.name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
