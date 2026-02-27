import { useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import { useSimFundos, useSimPortfolios, useSimPositions, useSimFundPositions } from '@/hooks/useSimulador';
import { formatNumero } from '@/utils/formatBR';
import './Simulador.css';

export default function SimuladorPosicoes() {
    const { data: portfolios } = useSimPortfolios();
    const { data: fundos } = useSimFundos();

    const [viewMode, setViewMode] = useState<'portfolio' | 'fundo'>('portfolio');
    const [portfolioId, setPortfolioId] = useState<number | null>(null);
    const [fundoId, setFundoId] = useState<number | null>(null);

    const portfolioQuery = useSimPositions(viewMode === 'portfolio' ? portfolioId : null);
    const fundoQuery = useSimFundPositions(viewMode === 'fundo' ? fundoId : null);

    const data = viewMode === 'portfolio' ? portfolioQuery.data : fundoQuery.data;
    const isLoading = viewMode === 'portfolio' ? portfolioQuery.isLoading : fundoQuery.isLoading;
    const error = viewMode === 'portfolio' ? portfolioQuery.error : fundoQuery.error;

    const hasSelection = viewMode === 'portfolio' ? !!portfolioId : !!fundoId;

    const items = data?.items ?? [];
    const resumo = data?.resumo;

    const exposicaoLiquida = useMemo(
        () => items.reduce((acc, row) => acc + Number(row.VALOR_MERCADO ?? 0), 0),
        [items],
    );

    return (
        <div className="pg-page">
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon"><i className="fas fa-layer-group" /></div>
                    <div className="pg-header-text">
                        <h1>Posições Consolidadas</h1>
                        <p>Visão consolidada por carteira ou por fundo.</p>
                    </div>
                </div>
            </div>

            <div className="pg-controls">
                <div className="pg-select-group">
                    <label className="pg-select-label">Visão</label>
                    <div className="pg-select-wrap">
                        <select
                            className="pg-select"
                            value={viewMode}
                            onChange={e => setViewMode(e.target.value === 'fundo' ? 'fundo' : 'portfolio')}
                        >
                            <option value="portfolio">Carteira</option>
                            <option value="fundo">Fundo</option>
                        </select>
                    </div>
                </div>

                {viewMode === 'portfolio' ? (
                    <div className="pg-select-group">
                        <label className="pg-select-label">Carteira</label>
                        <div className="pg-select-wrap">
                            <select className="pg-select" value={portfolioId ?? ''} onChange={e => setPortfolioId(e.target.value ? Number(e.target.value) : null)}>
                                <option value="">— selecione —</option>
                                {(portfolios ?? []).map(p => (
                                    <option key={p.ID_PORTFOLIO} value={p.ID_PORTFOLIO}>{p.NM_PORTFOLIO}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                ) : (
                    <div className="pg-select-group">
                        <label className="pg-select-label">Fundo</label>
                        <div className="pg-select-wrap">
                            <select className="pg-select" value={fundoId ?? ''} onChange={e => setFundoId(e.target.value ? Number(e.target.value) : null)}>
                                <option value="">— selecione —</option>
                                {(fundos ?? []).map(f => (
                                    <option key={f.ID_FUNDO} value={f.ID_FUNDO}>{f.NM_FUNDO}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                )}
            </div>

            {hasSelection && (
                <div className="sim-kpis">
                    <div className="sim-kpi">
                        <div className="sim-kpi-label">Valor de Mercado</div>
                        <div className="sim-kpi-value">{formatNumero(resumo?.VALOR_MERCADO_TOTAL ?? 0, 2)}</div>
                    </div>
                    <div className="sim-kpi">
                        <div className="sim-kpi-label">PnL Aberto</div>
                        <div className={`sim-kpi-value ${(resumo?.PNL_ABERTO_TOTAL ?? 0) >= 0 ? 'positivo' : 'negativo'}`}>
                            {formatNumero(resumo?.PNL_ABERTO_TOTAL ?? 0, 2)}
                        </div>
                    </div>
                    <div className="sim-kpi">
                        <div className="sim-kpi-label">PnL Realizado</div>
                        <div className={`sim-kpi-value ${(resumo?.PNL_REALIZADO_TOTAL ?? 0) >= 0 ? 'positivo' : 'negativo'}`}>
                            {formatNumero(resumo?.PNL_REALIZADO_TOTAL ?? 0, 2)}
                        </div>
                    </div>
                    <div className="sim-kpi">
                        <div className="sim-kpi-label">PnL Total</div>
                        <div className={`sim-kpi-value ${(resumo?.PNL_TOTAL ?? 0) >= 0 ? 'positivo' : 'negativo'}`}>
                            {formatNumero(resumo?.PNL_TOTAL ?? 0, 2)}
                        </div>
                    </div>
                    <div className="sim-kpi">
                        <div className="sim-kpi-label">Exposição Líquida</div>
                        <div className="sim-kpi-value">{formatNumero(exposicaoLiquida, 2)}</div>
                    </div>
                </div>
            )}

            {hasSelection && items.length > 0 && (
                <div className="sim-chart-grid" style={{ marginBottom: '0.8rem', gridTemplateColumns: 'minmax(0, 400px)' }}>
                    <div className="sim-card sim-chart-card">
                        <div className="sim-card-title">Composição (Market Value)</div>
                        <Plot
                            data={[
                                {
                                    values: items.filter(r => Math.abs(Number(r.VALOR_MERCADO ?? 0)) > 1).map(r => Math.abs(Number(r.VALOR_MERCADO))),
                                    labels: items.filter(r => Math.abs(Number(r.VALOR_MERCADO ?? 0)) > 1).map(r => r.CD_ATIVO),
                                    type: 'pie',
                                    hole: 0.6,
                                    textinfo: 'label+percent',
                                    hoverinfo: 'label+value',
                                    hovertemplate: '<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>'
                                }
                            ]}
                            layout={{
                                template: 'plotly_dark' as never,
                                paper_bgcolor: 'rgba(0,0,0,0)',
                                plot_bgcolor: 'rgba(0,0,0,0)',
                                margin: { l: 20, r: 20, t: 20, b: 20 },
                                showlegend: false,
                            }}
                            style={{ width: '100%', height: 260 }}
                            config={{ displayModeBar: false, responsive: true }}
                        />
                    </div>
                </div>
            )}

            {hasSelection && isLoading && <div className="pg-loading"><i className="fas fa-circle-notch fa-spin" /> Carregando posições…</div>}
            {hasSelection && error && <div className="pg-error"><i className="fas fa-triangle-exclamation" /> {(error as Error).message}</div>}

            {hasSelection && !isLoading && !error && (
                <div className="sim-table-wrap">
                    <table className="sim-table">
                        <thead>
                            <tr>
                                <th>Ativo</th>
                                <th>Moeda</th>
                                <th>FX BRL</th>
                                <th>Qtd líquida</th>
                                <th>Preço médio</th>
                                <th>Preço atual</th>
                                <th>Valor mercado</th>
                                <th>PnL realizado</th>
                                <th>PnL aberto</th>
                                <th>PnL total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items.map(r => (
                                <tr key={r.ID_ATIVO} className={r.ALERTAS ? 'row-alerta' : ''}>
                                    <td>
                                        {r.CD_ATIVO}
                                        {r.ALERTAS && (
                                            <span className="alerta-preco" title={r.ALERTAS.join(' ')}>
                                                <i className="fas fa-exclamation-triangle" />
                                            </span>
                                        )}
                                    </td>
                                    <td>{r.MOEDA}</td>
                                    <td>{formatNumero(r.FX_ATUAL, 2)}</td>
                                    <td>{formatNumero(r.QTD_LIQ, 2)}</td>
                                    <td>{formatNumero(r.PRECO_MEDIO, 2)}</td>
                                    <td>
                                        {formatNumero(r.PRECO_ATUAL, 2)}
                                        {r.SEM_PRECO_MERCADO && <span className="badge-pm">PM</span>}
                                    </td>
                                    <td>{formatNumero(r.VALOR_MERCADO, 2)}</td>
                                    <td className={(r.PNL_REALIZADO ?? 0) >= 0 ? 'positivo' : 'negativo'}>{formatNumero(r.PNL_REALIZADO, 2)}</td>
                                    <td className={(r.PNL_ABERTO ?? 0) >= 0 ? 'positivo' : 'negativo'}>{formatNumero(r.PNL_ABERTO, 2)}</td>
                                    <td className={(r.PNL_TOTAL ?? 0) >= 0 ? 'positivo' : 'negativo'}>{formatNumero(r.PNL_TOTAL, 2)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
