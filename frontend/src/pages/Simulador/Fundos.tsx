import { useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import {
    useSimFundos,
    useSimFundPnlFechamentoSerie,
    useSimFundCotaSerie,
    useCaptureSimFundPnlLive,
    useCloseSimFundPnlDia,
    useBackfillSimFundPnl,
    useRecalcSimFundCotas,
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

    const [fundoId, setFundoId] = useState<number | null>(null);
    const [dtInicio, setDtInicio] = useState(diasAtrasISO(60));
    const [dtFim, setDtFim] = useState(hojeISO());

    const serieQuery = useSimFundPnlFechamentoSerie(fundoId, dtInicio, dtFim);
    const cotaQuery = useSimFundCotaSerie(fundoId, dtInicio, dtFim);
    const captureLive = useCaptureSimFundPnlLive();
    const closeDia = useCloseSimFundPnlDia();
    const backfill = useBackfillSimFundPnl();
    const recalcCotas = useRecalcSimFundCotas();

    const rows = serieQuery.data ?? [];
    const cotaRows = cotaQuery.data ?? [];
    const last = rows.length ? rows[rows.length - 1] : null;
    const lastCota = cotaRows.length ? cotaRows[cotaRows.length - 1] : null;

    const x = useMemo(() => rows.map(r => r.DT_REFERENCIA), [rows]);
    const yPL = useMemo(() => rows.map(r => Number(r.VL_VALOR_MERCADO_TOTAL ?? 0)), [rows]);
    const yPnl = useMemo(() => rows.map(r => Number(r.VL_PNL_TOTAL ?? 0)), [rows]);
    const xCota = useMemo(() => cotaRows.map(r => r.DT_REFERENCIA), [cotaRows]);
    const yCota = useMemo(() => cotaRows.map(r => Number(r.VL_COTA ?? 0)), [cotaRows]);

    const loadingAction = captureLive.isPending || closeDia.isPending || backfill.isPending || recalcCotas.isPending;

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
                </div>
            )}

            {fundoId && (
                <div className="sim-kpis">
                    <div className="sim-kpi">
                        <div className="sim-kpi-label">Cota (último fechamento)</div>
                        <div className="sim-kpi-value">{formatNumero(lastCota?.VL_COTA ?? 0, 4)}</div>
                    </div>
                    <div className="sim-kpi">
                        <div className="sim-kpi-label">PL (último fechamento)</div>
                        <div className="sim-kpi-value">{formatNumero(last?.VL_VALOR_MERCADO_TOTAL ?? 0, 2)}</div>
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
                </div>
            )}

            {fundoId && serieQuery.isLoading && <div className="pg-loading"><i className="fas fa-circle-notch fa-spin" /> Carregando série…</div>}
            {fundoId && serieQuery.error && <div className="pg-error"><i className="fas fa-triangle-exclamation" /> {(serieQuery.error as Error).message}</div>}

            {fundoId && !serieQuery.isLoading && !serieQuery.error && (
                <div className="sim-chart-grid">
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

                    <div className="sim-card sim-chart-card">
                        <div className="sim-card-title">Evolução do PnL Total (secundário)</div>
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
                </div>
            )}
        </div>
    );
}
