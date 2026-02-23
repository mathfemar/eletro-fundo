import { useState, useMemo } from 'react';
import Plot from 'react-plotly.js';
import { usePrecosLive } from '@/hooks/usePrecos';
import { useAtivos } from '@/hooks/useAtivos';
import { formatNumero, formatPct, variacaoClass } from '@/utils/formatBR';
import type { PrecoLive } from '@/api/precos';
import './PrecosAoVivo.css';

// ─── Formata timestamp de captura ────────────────────────────────────────────

function formatCaptura(dt: string | null): string {
    if (!dt) return '—';
    const d = new Date(dt.replace(' ', 'T') + 'Z');
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

// ─── Candle do dia ───────────────────────────────────────────────────────────

function CandleDia({ row }: { row: PrecoLive }) {
    const { VL_PRECO_ABERTURA: open, VL_PRECO_MAX: high,
            VL_PRECO_MIN: low, VL_PRECO_ATUAL: close, DT_REFERENCIA: dt } = row;

    if (open == null || high == null || low == null || close == null) return null;

    const cor = close >= open ? '#10b981' : '#ef4444';

    return (
        <Plot
            data={[{
                type: 'candlestick',
                x: [dt ?? 'Hoje'],
                open: [open],
                high: [high],
                low:  [low],
                close: [close],
                increasing: { line: { color: '#10b981', width: 2 }, fillcolor: 'rgba(16,185,129,0.25)' },
                decreasing: { line: { color: '#ef4444', width: 2 }, fillcolor: 'rgba(239,68,68,0.25)' },
                hovertemplate:
                    `<b>%{x}</b><br>` +
                    `Abertura: %{open:.2f}<br>` +
                    `Máxima: %{high:.2f}<br>` +
                    `Mínima: %{low:.2f}<br>` +
                    `Atual: %{close:.2f}<extra></extra>`,
            }] as never}
            layout={{
                template: 'plotly_dark' as never,
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#fff', family: 'Inter, sans-serif', size: 12 },
                margin: { t: 16, r: 64, b: 44, l: 16 },
                xaxis: {
                    type: 'category',
                    tickfont: { size: 11 },
                    gridcolor: 'rgba(255,255,255,0.06)',
                    linecolor: 'rgba(255,255,255,0.1)',
                    rangeslider: { visible: false },
                },
                yaxis: {
                    gridcolor: 'rgba(255,255,255,0.06)',
                    linecolor: 'rgba(255,255,255,0.1)',
                    tickfont: { size: 11 },
                    side: 'right',
                    // margem extra em volta do candle
                    range: [low - (high - low) * 0.5, high + (high - low) * 0.5],
                },
                shapes: [
                    // Linha de referência do fechamento anterior
                    ...(row.VL_PRECO_FECHAMENTO_ANT != null ? [{
                        type: 'line' as const,
                        xref: 'paper' as const,
                        yref: 'y' as const,
                        x0: 0, x1: 1,
                        y0: row.VL_PRECO_FECHAMENTO_ANT,
                        y1: row.VL_PRECO_FECHAMENTO_ANT,
                        line: { color: 'rgba(255,255,255,0.3)', width: 1, dash: 'dot' as const },
                    }] : []),
                ],
                annotations: [
                    // Label do fechamento anterior
                    ...(row.VL_PRECO_FECHAMENTO_ANT != null ? [{
                        xref: 'paper' as const,
                        yref: 'y' as const,
                        x: 1.01,
                        y: row.VL_PRECO_FECHAMENTO_ANT,
                        text: `Fech. Ant.<br>${formatNumero(row.VL_PRECO_FECHAMENTO_ANT)}`,
                        showarrow: false,
                        font: { size: 10, color: 'rgba(255,255,255,0.4)' },
                        xanchor: 'left' as const,
                        align: 'left' as const,
                    }] : []),
                    // Label da abertura
                    {
                        xref: 'paper' as const,
                        yref: 'y' as const,
                        x: 1.01,
                        y: open,
                        text: `Abertura<br>${formatNumero(open)}`,
                        showarrow: false,
                        font: { size: 10, color: 'rgba(234,179,8,0.7)' },
                        xanchor: 'left' as const,
                        align: 'left' as const,
                    },
                    // Label do preço atual
                    {
                        xref: 'paper' as const,
                        yref: 'y' as const,
                        x: 1.01,
                        y: close,
                        text: `Atual<br>${formatNumero(close)}`,
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
    const { data: ativos, isLoading: loadingAtivos } = useAtivos();
    const { data, isLoading: loadingPrecos, error, dataUpdatedAt } = usePrecosLive();
    const [cdAtivo, setCdAtivo] = useState<string | null>(null);

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

                    {/* Candle do dia */}
                    <div className="pv-candle-section">
                        <CandleDia row={row} />
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