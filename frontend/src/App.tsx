import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { AssetHistoryPage, AssetRegistryPage, DashboardPage, FundOperationsPage, FundRegistryPage, LivePricesPage } from './pages'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/fundos/visao-geral" replace />} />
        <Route path="/fundos/visao-geral" element={<DashboardPage />} />
        <Route path="/fundos/cadastro" element={<FundRegistryPage />} />
        <Route path="/fundos/operacoes" element={<FundOperationsPage />} />
        <Route path="/ativos/cadastro" element={<AssetRegistryPage />} />
        <Route path="/ativos/preco-historico" element={<AssetHistoryPage />} />
        <Route path="/ativos/preco-live" element={<LivePricesPage />} />
        <Route path="*" element={<Navigate to="/fundos/visao-geral" replace />} />
      </Route>
    </Routes>
  )
}
