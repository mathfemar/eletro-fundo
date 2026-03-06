import { NavLink, Outlet, useLocation } from 'react-router-dom'

const sessions = {
  fundos: {
    label: 'Fundos',
    description: 'Cadastro, cotistas, operações e evolução do PL.',
    items: [
      { to: '/fundos/visao-geral', label: 'Visão Geral' },
      { to: '/fundos/cadastro', label: 'Cadastro e Cotistas' },
      { to: '/fundos/operacoes', label: 'Operações' },
    ],
  },
  ativos: {
    label: 'Ativos',
    description: 'Cadastro, preço histórico e preço live 1D.',
    items: [
      { to: '/ativos/cadastro', label: 'Cadastro de Ativos' },
      { to: '/ativos/preco-historico', label: 'Preço Histórico' },
      { to: '/ativos/preco-live', label: 'Preço Live' },
    ],
  },
} as const

export function Layout() {
  const location = useLocation()
  const activeSession = location.pathname.startsWith('/ativos') ? 'ativos' : 'fundos'
  const session = sessions[activeSession]

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="eyebrow">Fund analyzer</p>
          <h1>Analisador de Fundos</h1>
          <p className="muted">FastAPI + React + SQLite + yfinance</p>
        </div>

        <div className="sidebar-session">
          <p className="section-kicker">Sessão atual</p>
          <h2>{session.label}</h2>
          <p className="muted">{session.description}</p>
        </div>

        <nav className="sidebar-nav">
          {session.items.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="content-area">
        <header className="topbar">
          <div>
            <p className="eyebrow">Navegação</p>
            <h2 className="topbar-title">{session.label}</h2>
          </div>
          <div className="topbar-tabs">
            {Object.entries(sessions).map(([key, value]) => (
              <NavLink
                key={key}
                to={value.items[0].to}
                className={({ isActive }) => (activeSession === key || isActive ? 'topbar-tab active' : 'topbar-tab')}
              >
                {value.label}
              </NavLink>
            ))}
          </div>
        </header>

        <section className="content">
        <Outlet />
        </section>
      </main>
    </div>
  )
}
