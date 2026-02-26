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
                <Link className="sim-link-card" to="/simulador/fundos/cadastro">
                    <div className="sim-link-title"><i className="fas fa-file-circle-plus" /> Setup do Fundo</div>
                    <div className="sim-link-desc">Criação transacional do fundo com cotistas iniciais e validação de soma do PL.</div>
                </Link>

                <Link className="sim-link-card" to="/simulador/cotistas">
                    <div className="sim-link-title"><i className="fas fa-users" /> Cotistas</div>
                    <div className="sim-link-desc">Cadastro dos participantes econômicos que aportam e resgatam no fundo.</div>
                </Link>

                <Link className="sim-link-card" to="/simulador/alocacoes">
                    <div className="sim-link-title"><i className="fas fa-wallet" /> Carteiras e Alocação</div>
                    <div className="sim-link-desc">Criar carteiras de estratégia e alocar caixa com validação de saldo.</div>
                </Link>

                <Link className="sim-link-card" to="/simulador/renda-fixa">
                    <div className="sim-link-title"><i className="fas fa-file-invoice-dollar" /> Renda Fixa</div>
                    <div className="sim-link-desc">Cadastro de títulos RF e visualização de liquidez por data fixa (resgate ou vencimento).</div>
                </Link>

                <Link className="sim-link-card" to="/simulador/operacoes">
                    <div className="sim-link-title"><i className="fas fa-right-left" /> Operações</div>
                    <div className="sim-link-desc">Lançar trades manuais de compra e venda nas carteiras de estratégia.</div>
                </Link>

                <Link className="sim-link-card" to="/simulador/resgates">
                    <div className="sim-link-title"><i className="fas fa-hand-holding-dollar" /> Resgates</div>
                    <div className="sim-link-desc">Solicitação e plano manual de liquidação por ativo, com controle de dias de liquidez.</div>
                </Link>

                <Link className="sim-link-card" to="/simulador/fundos">
                    <div className="sim-link-title"><i className="fas fa-building-columns" /> Visão Consolidada</div>
                    <div className="sim-link-desc">Acompanhamento agregado de PL, cota, fluxos e posição econômica por cotista.</div>
                </Link>
            </div>
        </div>
    );
}
