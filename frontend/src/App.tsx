import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Sidebar from '@/components/layout/Sidebar';
import Upbar from '@/components/layout/Upbar';
import Home from '@/pages/Home/Home';
import Ativos from '@/pages/Ativos/Ativos';
import Lista from '@/pages/Ativos/Lista';
import PrecosAoVivo from '@/pages/Ativos/PrecosAoVivo';
import Historico from '@/pages/Ativos/Historico';
import SimuladorHome from '@/pages/Simulador/Home';
import SimuladorCarteiras from '@/pages/Simulador/Carteiras';
import SimuladorCarteirasAlocacao from '@/pages/Simulador/CarteirasAlocacao';
import SimuladorOperacoes from '@/pages/Simulador/Operacoes';
import SimuladorPosicoes from '@/pages/Simulador/Posicoes';
import SimuladorFundos from '@/pages/Simulador/Fundos';
import SimuladorFundosCadastro from '@/pages/Simulador/FundosCadastro';
import SimuladorResgates from '@/pages/Simulador/Resgates';
import SimuladorCotistas from '@/pages/Simulador/Cotistas';
import SimuladorRendaFixa from '@/pages/Simulador/RendaFixa';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

function AppLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <Upbar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/ativos" element={<Ativos />} />
          <Route path="/ativos/lista" element={<Lista />} />
          <Route path="/ativos/precos-ao-vivo" element={<PrecosAoVivo />} />
          <Route path="/ativos/historico" element={<Historico />} />
          <Route path="/simulador" element={<SimuladorHome />} />
          <Route path="/simulador/alocacoes" element={<SimuladorCarteirasAlocacao />} />
          <Route path="/simulador/carteiras" element={<SimuladorCarteiras />} />
          <Route path="/simulador/cotistas" element={<SimuladorCotistas />} />
          <Route path="/simulador/operacoes" element={<SimuladorOperacoes />} />
          <Route path="/simulador/posicoes" element={<SimuladorPosicoes />} />
          <Route path="/simulador/fundos/cadastro" element={<SimuladorFundosCadastro />} />
          <Route path="/simulador/fundos" element={<SimuladorFundos />} />
          <Route path="/simulador/renda-fixa" element={<SimuladorRendaFixa />} />
          <Route path="/simulador/resgates" element={<SimuladorResgates />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
