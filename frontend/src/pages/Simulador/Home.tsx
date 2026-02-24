import { Link } from 'react-router-dom';
import './Simulador.css';

export default function SimuladorHome() {
    return (
        <div className="pg-page">
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon">
                        <i className="fas fa-flask" />
                    </div>
                    <div className="pg-header-text">
                        <h1>Simulador de Carteiras</h1>
                        <p>Área de simulação (retroativa) e área operacional de fundos.</p>
                    </div>
                </div>
            </div>

            <div className="sim-grid">
                <Link className="sim-link-card" to="/simulador/carteiras">
                    <div className="sim-link-title"><i className="fas fa-wallet" /> Carteiras</div>
                    <div className="sim-link-desc">Criar e gerenciar carteiras simuladas.</div>
                </Link>

                <Link className="sim-link-card" to="/simulador/operacoes">
                    <div className="sim-link-title"><i className="fas fa-right-left" /> Operações</div>
                    <div className="sim-link-desc">Lançar trades manuais de compra, venda, short e cover.</div>
                </Link>

                <Link className="sim-link-card" to="/simulador/posicoes">
                    <div className="sim-link-title"><i className="fas fa-layer-group" /> Posições</div>
                    <div className="sim-link-desc">Consolidado da carteira com valor de mercado e PnL.</div>
                </Link>

                <Link className="sim-link-card" to="/simulador/fundos">
                    <div className="sim-link-title"><i className="fas fa-building-columns" /> Fundos</div>
                    <div className="sim-link-desc">Visualização correta por fundo: PL, PnL e fechamento diário.</div>
                </Link>
            </div>
        </div>
    );
}
