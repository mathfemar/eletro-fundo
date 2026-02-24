import { useState, useMemo } from 'react';
import Plot from 'react-plotly.js';
import { usePrecosLive, usePrecosLiveSerie } from '@/hooks/usePrecos';
import { useAtivosOnline } from '@/hooks/useAtivos';
import { formatNumero, formatPct, variacaoClass } from '@/utils/formatBR';
import type { PrecoLive } from '@/api/precos';
import './PrecosAoVivo.css';

// ─── Formata timestamp de captura ────────────────────────────────────────────

function formatCaptura(dt: string | null): string {
    if (!dt) return '—';
    const d = new Date(dt.replace(' ', 'T'));
    if (isNaN(d.getTime())) return dt;
    return d.toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
}

// ─── Range visual do pregão ───────────────────────────────────────────────────

function RangePregao({ row }: { row: PrecoLive }) {
    const { VL_PRECO_MIN: minV, VL_PRECO_MAX: maxV, VL_PRECO_ATUAL: cur,
            VL_PRECO_ABERTURA: open, VL_PRECO_FECHAMENTO_ANT: prevClose } = row;

    if (minV == null || maxV == null || cur == null) return null;

    const span = maxV - minV || 1;
    const pct = (v: number | null) =>
        v == null ? 50 : Math.min(100, Math.max(0, ((v - minV) / span) * 100));

    const cor = (row.VL_VAR_DIA_PCT ?? 0) >= 0 ? 'var(--color-success)' : 'var(--color-danger)';
    const openPct   = pct(open);
    const curPct    = pct(cur);
    const fillLeft  = Math.min(openPct, curPct);
    const fillWidth = Math.abs(curPct - openPct);

    return (
        <div className="pv-range">
            {/* Track */}
            <div className="pv-range-track">
                {/* Faixa entre abertura e preço atual */}
                <div className="pv-range-fill" style={{ left: `${fillLeft}%`, width: `${fillWidth}%`, background: cor }} />

                {/* Fech. Anterior — linha vertical tracejada */}
                {prevClose != null && (
                    <div className="pv-range-marker pv-range-marker--prev" style={{ left: `${pct(prevClose)}%` }}>
                        <span className="pv-marker-tip pv-marker-tip--prev">{formatNumero(prevClose)}</span>
                    </div>
                )}

                {/* Abertura */}
                {open != null && (
                    <div className="pv-range-marker pv-range-marker--open" style={{ left: `${pct(open)}%` }}>
                        <span className="pv-marker-tip pv-marker-tip--open">{formatNumero(open)}</span>
                    </div>
                )}

                {/* Preço atual */}
                <div className="pv-range-dot" style={{ left: `${curPct}%`, background: cor, boxShadow: `0 0 10px ${cor}88` }}>
                    <span className="pv-marker-tip pv-marker-tip--cur" style={{ color: cor }}>{formatNumero(cur)}</span>
                </div>
            </div>

            {/* Rótulos de extremo */}
            <div className="pv-range-ends">
                <span className="pv-range-end">
                    <span className="pv-range-end-tag">Mín</span>
                    <span className="pv-range-end-val">{formatNumero(minV)}</span>
                </span>
                <span className="pv-range-end pv-range-end--right">
                    <span className="pv-range-end-val">{formatNumero(maxV)}</span>
                    <span className="pv-range-end-tag">Máx</span>
                </span>
            </div>

            {/* Legenda */}
            <div className="pv-legend">
                {prevClose != null && (
                    <span className="pv-legend-item">
                        <span className="pv-legend-line pv-legend-line--prev" />
                        Fech. Ant. {formatNumero(prevClose)}
                    </span>
                )}
                {open != null && (
                    <span className="pv-legend-item">
                        <span className="pv-legend-circle pv-legend-circle--open" />
                        Abertura {formatNumero(open)}
                    </span>
                )}
                <span className="pv-legend-item" style={{ color: cor }}>
                    <span className="pv-legend-circle" style={{ background: cor }} />
                    Atual {formatNumero(cur)}
                </span>
            </div>
        </div>
    );
}

// ─── Série intradiária (24h) ─────────────────────────────────────────────────

function Serie24h({ points }: { points: PrecoLive[] }) {
    if (!points || points.length === 0) return null;

    const x = points.map(p => p.DT_HORA_CAPTURA?.replace(' ', 'T') ?? '');
    const y = points.map(p => p.VL_PRECO_ATUAL ?? null);
    const last = points[points.length - 1];
    const first = points[0];

    const p0 = first?.VL_PRECO_ATUAL ?? null;
    const p1 = last?.VL_PRECO_ATUAL ?? null;
    const cor = (p0 != null && p1 != null && p1 >= p0) ? '#10b981' : '#ef4444';

    const yVals = y.filter((v): v is number => v != null);
    const yMin = yVals.length ? Math.min(...yVals) : 0;
    const yMax = yVals.length ? Math.max(...yVals) : 1;
    const pad = Math.max((yMax - yMin) * 0.15, 0.01);

    return (
        <Plot
            data={[{
                type: 'scatter',
                mode: 'lines+markers',
                x,
                y,
                line: { color: cor, width: 2 },
                marker: { color: cor, size: 6 },
                hovertemplate:
                    `<b>%{x}</b><br>` +
                    `Preço: %{y:.2f}<extra></extra>`,
            }] as never}
            layout={{
                template: 'plotly_dark' as never,
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#fff', family: 'Inter, sans-serif', size: 12 },
                margin: { t: 16, r: 64, b: 44, l: 16 },
                xaxis: {
                    type: 'date',
                    tickfont: { size: 11 },
                    gridcolor: 'rgba(255,255,255,0.06)',
                    linecolor: 'rgba(255,255,255,0.1)',
                },
                yaxis: {
                    gridcolor: 'rgba(255,255,255,0.06)',
                    linecolor: 'rgba(255,255,255,0.1)',
                    tickfont: { size: 11 },
                    side: 'right',
                    range: [yMin - pad, yMax + pad],
                },
                annotations: [
                    // Label do último preço
                    {
                        xref: 'paper' as const,
                        yref: 'y' as const,
                        x: 1.01,
                        y: p1 ?? yMax,
                        text: `Atual<br>${formatNumero(p1)}`,
                        showarrow: false,
                        font: { size: 10, color: cor },
                        xanchor: 'left' as const,
                        align: 'left' as const,
                    },
                ],
                showlegend: false,
                height: 220,
            } as never}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%' }}
            useResizeHandler
        />
    );
}

// ─── Stat card ────────────────────────────────────────────────────────────────

function Stat({ label, value, className }: { label: string; value: string; className?: string }) {
    return (
        <div className="pv-stat">
            <span className="pv-stat-label">{label}</span>
            <span className={`pv-stat-value ${className ?? ''}`}>{value}</span>
        </div>
    );
}

// ─── Página ───────────────────────────────────────────────────────────────────

export default function PrecosAoVivo() {
    const { data: ativos, isLoading: loadingAtivos } = useAtivosOnline();
    const { data, isLoading: loadingPrecos, error, dataUpdatedAt } = usePrecosLive();
    const [cdAtivo, setCdAtivo] = useState<string | null>(null);
    const { data: serie24h, isLoading: loadingSerie } = usePrecosLiveSerie(cdAtivo, 24);

    const ativosUnicos = useMemo(() => {
        if (!ativos) return [];
        const seen = new Set<string>();
        return ativos.filter(a => (seen.has(a.CD_ATIVO) ? false : seen.add(a.CD_ATIVO)));
    }, [ativos]);

    const row = cdAtivo ? (data ?? []).find(r => r.CD_ATIVO === cdAtivo) ?? null : null;

    const ultimaAtualizacao = dataUpdatedAt
        ? new Date(dataUpdatedAt).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })
        : null;

    return (
        <div className="pg-page">

            {/* ── Header ── */}
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon">
                        <i className="fas fa-bolt" />
                    </div>
                    <div className="pg-header-text">
                        <h1>Preços ao Vivo</h1>
                        <p>Cotações do pregão atual por ativo</p>
                    </div>
                </div>
                {ultimaAtualizacao && (
                    <div className="pg-header-meta">
                        Última consulta: <strong>{ultimaAtualizacao}</strong><br />
                        atualiza a cada 30 min
                    </div>
                )}
            </div>

            {/* ── Controles ── */}
            <div className="pg-controls">
                <div className="pg-select-group">
                    <label className="pg-select-label" htmlFor="pv-sel">Ativo</label>
                    <div className="pg-select-wrap">
                        <select
                            id="pv-sel"
                            className="pg-select"
                            value={cdAtivo ?? ''}
                            onChange={e => setCdAtivo(e.target.value || null)}
                            disabled={loadingAtivos}
                        >
                            <option value="">
                                {loadingAtivos ? 'Carregando…' : '— selecione —'}
                            </option>
                            {ativosUnicos.map(a => (
                                <option key={a.CD_ATIVO} value={a.CD_ATIVO}>
                                    {a.CD_ATIVO}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* ── Loading / Erro ── */}
            {(loadingPrecos || (cdAtivo && loadingAtivos)) && (
                <div className="pg-loading">
                    <i className="fas fa-circle-notch fa-spin" />
                    <span>Carregando preços…</span>
                </div>
            )}

            {error && (
                <div className="pg-error">
                    <i className="fas fa-triangle-exclamation" />
                    <span>Erro: {(error as Error).message}</span>
                </div>
            )}

            {/* ── Card principal ── */}
            {cdAtivo && !loadingPrecos && row && (
                <div className="pg-card">
                    {/* Cabeçalho: código + preço grande + variação */}
                    <div className="pv-card-top">
                        <div className="pv-card-info">
                            <span className="pv-card-codigo">{row.CD_ATIVO}</span>
                            {row.DT_REFERENCIA && (
                                <span className="pv-card-data">{row.DT_REFERENCIA}</span>
                            )}
                        </div>
                        <div className="pv-card-preco-group">
                            <span className="pv-card-preco">
                                {row.VL_PRECO_ATUAL != null ? formatNumero(row.VL_PRECO_ATUAL) : '—'}
                            </span>
                            {row.VL_VAR_DIA_PCT != null && (
                                <span className={`pv-card-var ${variacaoClass(row.VL_VAR_DIA_PCT)}`}>
                                    {row.VL_VAR_DIA_PCT >= 0 ? '+' : ''}{formatPct(row.VL_VAR_DIA_PCT)}
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Range visual do pregão */}
                    <div className="pv-range-section">
                        <RangePregao row={row} />
                    </div>

                    {/* Série das últimas 24h (snapshots de 30min) */}
                    <div className="pv-candle-section">
                        <Serie24h points={serie24h ?? []} />
                        {!loadingSerie && (!serie24h || serie24h.length === 0) && (
                            <div className="pg-hint" style={{ marginTop: 0 }}>
                                <i className="fas fa-chart-line" />
                                <span>Sem snapshots suficientes nas últimas 24h para este ativo.</span>
                            </div>
                        )}
                    </div>

                    {/* Grid de stats OHLC */}
                    <div className="pv-stats">
                        <Stat label="Abertura"   value={formatNumero(row.VL_PRECO_ABERTURA)} />
                        <Stat label="Máxima"     value={formatNumero(row.VL_PRECO_MAX)} />
                        <Stat label="Mínima"     value={formatNumero(row.VL_PRECO_MIN)} />
                        <Stat label="Fech. Ant." value={formatNumero(row.VL_PRECO_FECHAMENTO_ANT)} />
                        <Stat
                            label="Var. Abs."
                            value={row.VL_VAR_DIA != null
                                ? (row.VL_VAR_DIA >= 0 ? '+' : '') + formatNumero(row.VL_VAR_DIA)
                                : '—'}
                            className={variacaoClass(row.VL_VAR_DIA)}
                        />
                    </div>

                    {/* Footer: captura */}
                    <div className="pv-card-footer">
                        <i className="fas fa-clock" />
                        Captura: {formatCaptura(row.DT_HORA_CAPTURA)}
                    </div>
                </div>
            )}

            {/* ── Sem dados ── */}
            {cdAtivo && !loadingPrecos && !row && !error && (
                <div className="pg-empty">
                    Nenhum dado ao vivo para <strong style={{ margin: '0 0.3rem' }}>{cdAtivo}</strong>.
                    Execute a atualização de preços no backend.
                </div>
            )}

            {/* ── Hint inicial ── */}
            {!cdAtivo && !loadingAtivos && ativosUnicos.length > 0 && (
                <div className="pg-hint">
                    <i className="fas fa-bolt" />
                    <span>Selecione um ativo para ver a cotação do pregão atual.</span>
                </div>
            )}
        </div>
    );
}