import { useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import {
    useSimFundos,
    useSimTitulares,
    useSimFundDashboard,
    useSimFundPositions,
    useCaptureSimFundPnlLive,
    useCloseSimFundPnlDia,
    useBackfillSimFundPnl,
    useRecalcSimFundCotas,
    useDeleteSimFundo,
    usePostSimFundFluxoCapital,
    useSimFundRetorno,
} from '@/hooks/useSimulador';
import { formatNumero } from '@/utils/formatBR';
import './Simulador.css';

function hojeISO() {
    return new Date().toISOString().slice(0, 10);
}

function diasAtrasISO(days: number) {
    const d = new Date();
    d.setDate(d.getDate() - days);
    return d.toISOString().slice(0, 10);
}

export default function SimuladorFundos() {
    const { data: fundos } = useSimFundos();
    const { data: titulares } = useSimTitulares();

    const [fundoId, setFundoId] = useState<number | null>(null);
    const [dtInicio, setDtInicio] = useState(diasAtrasISO(60));
    const [dtFim, setDtFim] = useState(hojeISO());

    const dashboardQuery = useSimFundDashboard(fundoId, dtInicio, dtFim, dtFim);
    const fundPositionsQuery = useSimFundPositions(fundoId);
    const captureLive = useCaptureSimFundPnlLive();
    const closeDia = useCloseSimFundPnlDia();
    const backfill = useBackfillSimFundPnl();
    const recalcCotas = useRecalcSimFundCotas();
    const deleteFundo = useDeleteSimFundo();
    const postFluxo = usePostSimFundFluxoCapital();

    const [dtFluxo, setDtFluxo] = useState(hojeISO());
    const [titularFluxoId, setTitularFluxoId] = useState<number | null>(null);
    const [vlFluxo, setVlFluxo] = useState('0');
    const [obsFluxo, setObsFluxo] = useState('');

    const rows = dashboardQuery.data?.pnl_fechamento?.items ?? [];
    const cotaRows = dashboardQuery.data?.cotas?.items ?? [];
    const fundPosItems = fundPositionsQuery.data?.items ?? [];
    const fundPosResumo = fundPositionsQuery.data?.resumo;
    const baseExposicao = Number(fundPosResumo?.VALOR_MERCADO_TOTAL ?? 0);
    const fluxosRows = dashboardQuery.data?.fluxos?.items ?? [];
    const cotistasItems = dashboardQuery.data?.cotistas_posicao?.items ?? [];
    const last = rows.length ? rows[rows.length - 1] : null;
    const lastCota = cotaRows.length ? cotaRows[cotaRows.length - 1] : null;
    const plKpi = Number(lastCota?.VL_PL ?? last?.VL_VALOR_MERCADO_TOTAL ?? 0);

    const x = useMemo(() => rows.map(r => r.DT_REFERENCIA), [rows]);
    const yPL = useMemo(() => rows.map(r => Number(r.VL_VALOR_MERCADO_TOTAL ?? 0)), [rows]);
    const yPnl = useMemo(() => rows.map(r => Number(r.VL_PNL_TOTAL ?? 0)), [rows]);
    const xCota = useMemo(() => cotaRows.map(r => r.DT_REFERENCIA), [cotaRows]);
    const yCota = useMemo(() => cotaRows.map(r => Number(r.VL_COTA ?? 0)), [cotaRows]);

    const retornoQuery = useSimFundRetorno(fundoId, dtInicio, dtFim);
    const retornoItems = retornoQuery.data ?? [];
    const xRetorno = useMemo(() => retornoItems.map(r => r.DT_REFERENCIA), [retornoItems]);
    const yRetorno = useMemo(() => retornoItems.map(r => r.RETORNO_ACUM_PCT), [retornoItems]);
    const lastRetorno = retornoItems.length ? retornoItems[retornoItems.length - 1] : null;

    const loadingAction = captureLive.isPending || closeDia.isPending || backfill.isPending || recalcCotas.isPending || deleteFundo.isPending || postFluxo.isPending;

    async function onCaptureNow() {
        if (!fundoId) return;
        await captureLive.mutateAsync(fundoId);
    }

    async function onCloseToday() {
        if (!fundoId) return;
        await closeDia.mutateAsync({ fundoId, dtReferencia: hojeISO() });
    }

    async function onBackfill() {
        if (!fundoId) return;
        await backfill.mutateAsync({ fundoId, dtInicio, dtFim });
    }

    async function onRecalcCotas() {
        if (!fundoId) return;
        await recalcCotas.mutateAsync(fundoId);
    }

    async function onDeleteFundo() {
        if (!fundoId) return;
        const ok = window.confirm('Excluir este fundo? Esta ação remove histórico de PnL e cota do fundo e não pode ser desfeita.');
        if (!ok) return;

        try {
            await deleteFundo.mutateAsync(fundoId);
            setFundoId(null);
        } catch (err: unknown) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            window.alert(detail ?? 'Não foi possível excluir o fundo.');
        }
    }

    async function onRegistrarFluxo(tpFluxo: 'APORTE' | 'RESGATE') {
        if (!fundoId) return;
        const valor = Number(vlFluxo);
        if (!Number.isFinite(valor) || valor <= 0) {
            window.alert('Informe um valor de fluxo maior que zero.');
            return;
        }

        try {
            await postFluxo.mutateAsync({
                ID_FUNDO: fundoId,
                DT_REFERENCIA: dtFluxo,
                TP_FLUXO: tpFluxo,
                VL_FLUXO: valor,
                ID_TITULAR: titularFluxoId,
                OBSERVACAO: obsFluxo || null,
            });
            setObsFluxo('');
            setVlFluxo('0');
        } catch (err: unknown) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            window.alert(detail ?? 'Não foi possível registrar o fluxo.');
        }
    }

    return (
        <div className="pg-page">
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon"><i className="fas fa-building-columns" /></div>
                    <div className="pg-header-text">
                        <h1>Fundos</h1>
                        <p>Visão operacional do fundo com histórico de PL e PnL de fechamento.</p>
                    </div>
                </div>
            </div>

            <div className="pg-controls">
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

                <div className="pg-select-group">
                    <label className="pg-select-label">Início</label>
                    <input className="sim-input" type="date" value={dtInicio} onChange={e => setDtInicio(e.target.value)} />
                </div>

                <div className="pg-select-group">
                    <label className="pg-select-label">Fim</label>
                    <input className="sim-input" type="date" value={dtFim} onChange={e => setDtFim(e.target.value)} />
                </div>
            </div>

            {fundoId && (
                <div className="sim-row-actions" style={{ marginBottom: '0.8rem' }}>
                    <button className="sim-btn" onClick={onCaptureNow} disabled={loadingAction}>
                        {captureLive.isPending ? 'Capturando…' : 'Capturar Live Agora'}
                    </button>
                    <button className="sim-btn sim-btn--neutral" onClick={onCloseToday} disabled={loadingAction}>
                        {closeDia.isPending ? 'Fechando…' : 'Fechar Dia (Hoje)'}
                    </button>
                    <button className="sim-btn sim-btn--neutral" onClick={onBackfill} disabled={loadingAction}>
                        {backfill.isPending ? 'Reprocessando…' : 'Backfill Período'}
                    </button>
                    <button className="sim-btn sim-btn--neutral" onClick={onRecalcCotas} disabled={loadingAction}>
                        {recalcCotas.isPending ? 'Calculando…' : 'Recalcular Cotas'}
                    </button>
                    <button className="sim-btn sim-btn--danger" onClick={onDeleteFundo} disabled={loadingAction}>
                        {deleteFundo.isPending ? 'Excluindo…' : 'Excluir Fundo'}
                    </button>
                </div>
            )}

            {fundoId && (
                <div className="sim-kpis">
                    <div className="sim-kpi">
                        <div className="sim-kpi-label">Cota (último fechamento)</div>
                        <div className="sim-kpi-value">{formatNumero(lastCota?.VL_COTA ?? 0, 4)}</div>
                    </div>
                    <div className="sim-kpi">
                        <div className="sim-kpi-label">PL (última data)</div>
                        <div className="sim-kpi-value">{formatNumero(plKpi, 2)}</div>
                    </div>
                    <div className="sim-kpi">
                        <div className="sim-kpi-label">PnL Total (último fechamento)</div>
                        <div className={`sim-kpi-value ${(last?.VL_PNL_TOTAL ?? 0) >= 0 ? 'positivo' : 'negativo'}`}>
                            {formatNumero(last?.VL_PNL_TOTAL ?? 0, 2)}
                        </div>
                    </div>
                    <div className="sim-kpi">
                        <div className="sim-kpi-label">Última data</div>
                        <div className="sim-kpi-value">{last?.DT_REFERENCIA ?? '—'}</div>
                    </div>
                    <div className="sim-kpi">
                        <div className="sim-kpi-label">Retorno Acumulado</div>
                        <div className={`sim-kpi-value ${(lastRetorno?.RETORNO_ACUM_PCT ?? 0) >= 0 ? 'positivo' : 'negativo'}`}>
                            {lastRetorno ? `${formatNumero(lastRetorno.RETORNO_ACUM_PCT, 2)}%` : '—'}
                        </div>
                    </div>
                </div>
            )}

            {fundoId && dashboardQuery.isLoading && <div className="pg-loading"><i className="fas fa-circle-notch fa-spin" /> Carregando série…</div>}
            {fundoId && dashboardQuery.error && <div className="pg-error"><i className="fas fa-triangle-exclamation" /> {(dashboardQuery.error as Error).message}</div>}

            {fundoId && !dashboardQuery.isLoading && !dashboardQuery.error && (
                <>
                    <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                        <div className="sim-card-title">Fluxo de Capital (aporte/resgate)</div>
                        <div className="sim-form">
                            <div>
                                <label className="pg-select-label">Data</label>
                                <input className="sim-input" type="date" value={dtFluxo} onChange={e => setDtFluxo(e.target.value)} />
                            </div>
                            <div>
                                <label className="pg-select-label">Titular</label>
                                <div className="pg-select-wrap">
                                    <select
                                        className="pg-select"
                                        value={titularFluxoId ?? ''}
                                        onChange={e => setTitularFluxoId(e.target.value ? Number(e.target.value) : null)}
                                    >
                                        <option value="">— sem titular (geral) —</option>
                                        {(titulares ?? []).map(t => (
                                            <option key={t.ID_TITULAR} value={t.ID_TITULAR}>{t.NM_TITULAR}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label className="pg-select-label">Valor</label>
                                <input className="sim-input" type="number" step="0.01" value={vlFluxo} onChange={e => setVlFluxo(e.target.value)} />
                            </div>
                            <div>
                                <label className="pg-select-label">Observação</label>
                                <input className="sim-input" value={obsFluxo} onChange={e => setObsFluxo(e.target.value)} placeholder="Opcional" />
                            </div>
                            <div className="sim-row-actions">
                                <button className="sim-btn" onClick={() => onRegistrarFluxo('APORTE')} disabled={loadingAction}>
                                    {postFluxo.isPending ? 'Registrando…' : 'Registrar Aporte'}
                                </button>
                                <button className="sim-btn sim-btn--neutral" onClick={() => onRegistrarFluxo('RESGATE')} disabled={loadingAction}>
                                    {postFluxo.isPending ? 'Registrando…' : 'Registrar Resgate'}
                                </button>
                            </div>
                        </div>
                        {fluxosRows.length > 0 && (
                            <div style={{ marginTop: '0.7rem', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
                                Fluxos no período: {fluxosRows.map(f => `${f.DT_REFERENCIA} ${f.NM_TITULAR ?? 'GERAL'} ${f.TP_FLUXO} ${formatNumero(f.VL_FLUXO, 2)}`).join(' • ')}
                            </div>
                        )}
                    </div>

                    <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                        <div className="sim-card-title">Posição por Cotista</div>
                        {(
                            <>
                                {cotistasItems.length === 0 ? (
                                    <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                                        Sem posição por cotista no período/data selecionado.
                                    </div>
                                ) : (
                                    <div className="sim-table-wrap" style={{ marginTop: '0.5rem' }}>
                                        <table className="sim-table sim-table--cotistas">
                                            <colgroup>
                                                <col style={{ minWidth: '180px' }} />
                                                <col style={{ width: '18%' }} />
                                                <col style={{ width: '16%' }} />
                                                <col style={{ width: '14%' }} />
                                                <col style={{ width: '18%' }} />
                                                <col style={{ width: '16%' }} />
                                            </colgroup>
                                            <thead>
                                                <tr>
                                                    <th>Titular</th>
                                                    <th className="sim-num">Investido Líquido</th>
                                                    <th className="sim-num">Qtd Cotas</th>
                                                    <th className="sim-num">Cota</th>
                                                    <th className="sim-num">PL Cotista</th>
                                                    <th className="sim-num">PnL Cotista</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {cotistasItems.map(item => (
                                                    <tr key={item.ID_TITULAR}>
                                                        <td>{item.NM_TITULAR}</td>
                                                        <td className="sim-num">{formatNumero(item.VL_INVERTIDO_LIQ, 2)}</td>
                                                        <td className="sim-num">{formatNumero(item.QT_COTAS, 6)}</td>
                                                        <td className="sim-num">{formatNumero(item.VL_COTA, 6)}</td>
                                                        <td className="sim-num">{formatNumero(item.VL_PL_COTISTA, 2)}</td>
                                                        <td className={`sim-num ${item.VL_PNL_COTISTA >= 0 ? 'positivo' : 'negativo'}`}>{formatNumero(item.VL_PNL_COTISTA, 2)}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </>
                        )}
                    </div>

                    <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                        <div className="sim-card-title">Posições Consolidadas do Fundo</div>
                        {fundPositionsQuery.isLoading ? (
                            <div className="pg-loading"><i className="fas fa-circle-notch fa-spin" /> Carregando posições…</div>
                        ) : fundPositionsQuery.error ? (
                            <div className="pg-error"><i className="fas fa-triangle-exclamation" /> {(fundPositionsQuery.error as Error).message}</div>
                        ) : fundPosItems.length === 0 ? (
                            <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                                Sem posições consolidadas para este fundo no momento.
                            </div>
                        ) : (
                            <div className="sim-table-wrap" style={{ marginTop: '0.5rem' }}>
                                <table className="sim-table">
                                    <thead>
                                        <tr>
                                            <th>Ativo</th>
                                            <th>Moeda</th>
                                            <th className="sim-num">FX BRL</th>
                                            <th className="sim-num">Qtd Líquida</th>
                                            <th className="sim-num">Preço Médio</th>
                                            <th className="sim-num">Preço Atual</th>
                                            <th className="sim-num">Financeiro</th>
                                            <th className="sim-num">Exposição</th>
                                            <th className="sim-num">PnL Realizado</th>
                                            <th className="sim-num">PnL Aberto</th>
                                            <th className="sim-num">PnL Total</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {fundPosItems.map(row => {
                                            const valorMercado = Number(row.VALOR_MERCADO ?? 0);
                                            const exposicaoPct = baseExposicao > 0 ? (valorMercado / baseExposicao) * 100 : 0;
                                            return (
                                                <tr key={row.ID_ATIVO}>
                                                    <td>{row.CD_ATIVO}</td>
                                                    <td>{row.MOEDA}</td>
                                                    <td className="sim-num">{formatNumero(row.FX_ATUAL, 2)}</td>
                                                    <td className="sim-num">{formatNumero(row.QTD_LIQ, 2)}</td>
                                                    <td className="sim-num">{formatNumero(row.PRECO_MEDIO, 2)}</td>
                                                    <td className="sim-num">{formatNumero(row.PRECO_ATUAL, 2)}</td>
                                                    <td className="sim-num">{formatNumero(valorMercado, 2)}</td>
                                                    <td className="sim-num">{formatNumero(exposicaoPct, 2)}%</td>
                                                    <td className={`sim-num ${(row.PNL_REALIZADO ?? 0) >= 0 ? 'positivo' : 'negativo'}`}>
                                                        {formatNumero(row.PNL_REALIZADO, 2)}
                                                    </td>
                                                    <td className={`sim-num ${(row.PNL_ABERTO ?? 0) >= 0 ? 'positivo' : 'negativo'}`}>
                                                        {formatNumero(row.PNL_ABERTO, 2)}
                                                    </td>
                                                    <td className={`sim-num ${(row.PNL_TOTAL ?? 0) >= 0 ? 'positivo' : 'negativo'}`}>
                                                        {formatNumero(row.PNL_TOTAL, 2)}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>

                    <div className="sim-chart-grid">
                        <div className="sim-card sim-chart-card" style={{ gridColumn: '1 / -1' }}>
                            <div className="sim-card-title">Retorno Acumulado do Fundo (%)</div>
                            <Plot
                                data={[
                                    {
                                        x: xRetorno,
                                        y: yRetorno,
                                        type: 'scatter',
                                        mode: 'lines',
                                        line: { color: '#818cf8', width: 2.5 },
                                        fill: 'tozeroy',
                                        fillcolor: 'rgba(129,140,248,0.10)',
                                        hovertemplate: '%{x}<br>Retorno: %{y:.2f}%<extra></extra>',
                                    },
                                ]}
                                layout={{
                                    template: 'plotly_dark' as never,
                                    paper_bgcolor: 'rgba(0,0,0,0)',
                                    plot_bgcolor: 'rgba(0,0,0,0)',
                                    margin: { l: 50, r: 10, t: 10, b: 30 },
                                    xaxis: { showgrid: true, gridcolor: 'rgba(255,255,255,0.08)' },
                                    yaxis: {
                                        showgrid: true,
                                        gridcolor: 'rgba(255,255,255,0.08)',
                                        ticksuffix: '%',
                                        zeroline: true,
                                        zerolinecolor: 'rgba(255,255,255,0.25)',
                                        zerolinewidth: 1,
                                    },
                                    showlegend: false,
                                }}
                                style={{ width: '100%', height: 360 }}
                                config={{ displayModeBar: false, responsive: true }}
                            />
                        </div>

                        <div className="sim-card sim-chart-card">
                            <div className="sim-card-title">Evolução do PnL Total</div>
                            <Plot
                                data={[
                                    {
                                        x,
                                        y: yPnl,
                                        type: 'scatter',
                                        mode: 'lines+markers',
                                        line: { color: '#f59e0b', width: 2 },
                                        marker: { size: 5 },
                                        hovertemplate: '%{x}<br>PnL: %{y:.2f}<extra></extra>',
                                    },
                                ]}
                                layout={{
                                    template: 'plotly_dark' as never,
                                    paper_bgcolor: 'rgba(0,0,0,0)',
                                    plot_bgcolor: 'rgba(0,0,0,0)',
                                    margin: { l: 40, r: 10, t: 10, b: 30 },
                                    xaxis: { showgrid: true, gridcolor: 'rgba(255,255,255,0.08)' },
                                    yaxis: { showgrid: true, gridcolor: 'rgba(255,255,255,0.08)' },
                                    showlegend: false,
                                }}
                                style={{ width: '100%', height: 320 }}
                                config={{ displayModeBar: false, responsive: true }}
                            />
                        </div>

                        <div className="sim-card sim-chart-card">
                            <div className="sim-card-title">Evolução da Cota</div>
                            <Plot
                                data={[
                                    {
                                        x: xCota,
                                        y: yCota,
                                        type: 'scatter',
                                        mode: 'lines+markers',
                                        line: { color: '#22c55e', width: 2 },
                                        marker: { size: 5 },
                                        hovertemplate: '%{x}<br>Cota: %{y:.4f}<extra></extra>',
                                    },
                                ]}
                                layout={{
                                    template: 'plotly_dark' as never,
                                    paper_bgcolor: 'rgba(0,0,0,0)',
                                    plot_bgcolor: 'rgba(0,0,0,0)',
                                    margin: { l: 40, r: 10, t: 10, b: 30 },
                                    xaxis: { showgrid: true, gridcolor: 'rgba(255,255,255,0.08)' },
                                    yaxis: { showgrid: true, gridcolor: 'rgba(255,255,255,0.08)' },
                                    showlegend: false,
                                }}
                                style={{ width: '100%', height: 320 }}
                                config={{ displayModeBar: false, responsive: true }}
                            />
                        </div>

                        <div className="sim-card sim-chart-card">
                            <div className="sim-card-title">Evolução do PL</div>
                            <Plot
                                data={[
                                    {
                                        x,
                                        y: yPL,
                                        type: 'scatter',
                                        mode: 'lines+markers',
                                        line: { color: '#4f8cff', width: 2 },
                                        marker: { size: 5 },
                                        hovertemplate: '%{x}<br>PL: %{y:.2f}<extra></extra>',
                                    },
                                ]}
                                layout={{
                                    template: 'plotly_dark' as never,
                                    paper_bgcolor: 'rgba(0,0,0,0)',
                                    plot_bgcolor: 'rgba(0,0,0,0)',
                                    margin: { l: 40, r: 10, t: 10, b: 30 },
                                    xaxis: { showgrid: true, gridcolor: 'rgba(255,255,255,0.08)' },
                                    yaxis: { showgrid: true, gridcolor: 'rgba(255,255,255,0.08)' },
                                    showlegend: false,
                                }}
                                style={{ width: '100%', height: 320 }}
                                config={{ displayModeBar: false, responsive: true }}
                            />
                        </div>
                    </div>

                    <div className="sim-card" style={{ marginTop: '0.8rem' }}>
                        <div className="sim-card-title">O que cada botão faz</div>
                        <p style={{ margin: 0, color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', lineHeight: 1.6 }}>
                            <strong>Capturar Live Agora:</strong> grava um snapshot intradiário do PnL/PL atual do fundo. {' '}
                            <strong>Fechar Dia (Hoje):</strong> fecha o PnL do dia usando o último snapshot e também atualiza a cota diária. {' '}
                            <strong>Backfill Período:</strong> refaz os fechamentos no intervalo informado e recalcula as cotas do fundo. {' '}
                            <strong>Recalcular Cotas:</strong> recalcula somente a série de cotas a partir dos fechamentos já existentes.
                        </p>
                    </div>
                </>
            )}
        </div>
    );
}
