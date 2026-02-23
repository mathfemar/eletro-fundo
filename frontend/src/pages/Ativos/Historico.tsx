import { useState, useMemo } from 'react';
import Plot from 'react-plotly.js';
import { useResumoHistorico, useHistoricoAtivo } from '@/hooks/usePrecos';
import { useAtivos } from '@/hooks/useAtivos';
import { formatNumero } from '@/utils/formatBR';
import type { CandleRow } from '@/api/precos';
import './Historico.css';

// ─── Período ──────────────────────────────────────────────────────────────────

type Periodo = '1M' | '3M' | '6M' | '1A' | '5A' | 'MAX';

const PERIODOS: { label: string; value: Periodo }[] = [
    { label: '1M',  value: '1M'  },
    { label: '3M',  value: '3M'  },
    { label: '6M',  value: '6M'  },
    { label: '1A',  value: '1A'  },
    { label: '5A',  value: '5A'  },
    { label: 'Máx', value: 'MAX' },
];

function dtLimite(periodo: Periodo): string | null {
    const hoje = new Date();
    const map: Record<Periodo, number | null> = {
        '1M': 1, '3M': 3, '6M': 6, '1A': 12, '5A': 60, 'MAX': null,
    };
    const meses = map[periodo];
    if (meses === null) return null;
    const d = new Date(hoje);
    d.setMonth(d.getMonth() - meses);
    return d.toISOString().slice(0, 10);
}

// ─── Gráfico ──────────────────────────────────────────────────────────────────

function GraficoFechamento({ rows, cdAtivo }: { rows: CandleRow[]; cdAtivo: string }) {
    if (rows.length === 0) {
        return <div className="hist-chart-empty">Sem dados para o período selecionado.</div>;
    }

    const datas = rows.map(r => r.DT_REFERENCIA);
    const precos = rows.map(r => r.VL_FECHAMENTO_AJ);
    const moeda = rows[0].CD_MOEDA ?? '';

    const primeiro = precos[0] ?? 0;
    const ultimo = precos[precos.length - 1] ?? 0;
    const cor = ultimo >= primeiro ? '#10b981' : '#ef4444';

    return (
        <Plot
            data={[
                {
                    type: 'scatter',
                    mode: 'lines',
                    x: datas,
                    y: precos,
                    name: cdAtivo,
                    line: { color: cor, width: 2 },
                    fill: 'tozeroy',
                    fillcolor: ultimo >= primeiro
                        ? 'rgba(16,185,129,0.08)'
                        : 'rgba(239,68,68,0.08)',
                    hovertemplate: '%{x}<br>%{y:.2f} ' + moeda + '<extra></extra>',
                },
            ] as never}
            layout={{
                template: 'plotly_dark' as never,
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#fff', family: 'Inter, sans-serif', size: 12 },
                margin: { t: 16, r: 16, b: 44, l: 60 },
                xaxis: {
                    gridcolor: 'rgba(255,255,255,0.06)',
                    linecolor: 'rgba(255,255,255,0.1)',
                    tickfont: { size: 11 },
                },
                yaxis: {
                    gridcolor: 'rgba(255,255,255,0.06)',
                    linecolor: 'rgba(255,255,255,0.1)',
                    tickfont: { size: 11 },
                    side: 'right',
                    title: { text: moeda, font: { size: 11 } },
                },
                showlegend: false,
                hovermode: 'x unified',
            } as never}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%', height: 440 }}
            useResizeHandler
        />
    );
}

// ─── Página ───────────────────────────────────────────────────────────────────

export default function Historico() {
    const { data: ativos, isLoading: loadingAtivos } = useAtivos();
    const { data: resumo } = useResumoHistorico();
    const [cdAtivo, setCdAtivo] = useState<string | null>(null);
    const [periodo, setPeriodo] = useState<Periodo>('1A');

    // Calcula dt_inicio com base no período selecionado
    const dtInicio = useMemo(() => dtLimite(periodo), [periodo]);

    const { data: series, isLoading: loadingSeries } = useHistoricoAtivo(
        cdAtivo,
        dtInicio ?? undefined,
    );

    // Deduplica por CD_ATIVO
    const ativosUnicos = useMemo(() => {
        if (!ativos) return [];
        const seen = new Set<string>();
        return ativos.filter(a => seen.has(a.CD_ATIVO) ? false : seen.add(a.CD_ATIVO));
    }, [ativos]);

    // Para MAX, mostra tudo que o servidor retornou.
    // Para outros períodos, o servidor já filtra via dt_inicio.
    const seriesFiltrada = useMemo(
        () => series ?? [],
        [series],
    );

    const meta = resumo?.find(r => r.CD_ATIVO === cdAtivo);

    // Resumo de variação
    const primeiro = seriesFiltrada.length > 0 ? seriesFiltrada[0].VL_FECHAMENTO_AJ : null;
    const ultimo   = seriesFiltrada.length > 0 ? seriesFiltrada[seriesFiltrada.length - 1].VL_FECHAMENTO_AJ : null;
    const variacao = primeiro && ultimo ? ((ultimo - primeiro) / primeiro) * 100 : null;

    return (
        <div className="pg-page">

            {/* ── Header ── */}
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon">
                        <i className="fas fa-chart-line" />
                    </div>
                    <div className="pg-header-text">
                        <h1>Histórico de Preços</h1>
                        <p>Fechamento ajustado ao longo do tempo</p>
                    </div>
                </div>
            </div>

            {/* ── Controles ── */}
            <div className="pg-controls">
                <div className="pg-select-group">
                    <label className="pg-select-label" htmlFor="hist-sel">Ativo</label>
                    <div className="pg-select-wrap">
                        <select
                            id="hist-sel"
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

                {/* Botões de período — só aparecem quando há ativo selecionado */}
                {cdAtivo && (
                    <div className="hist-periodo-group">
                        <span className="pg-select-label">Período</span>
                        <div className="hist-periodo-btns">
                            {PERIODOS.map(p => (
                                <button
                                    key={p.value}
                                    className={`hist-periodo-btn${periodo === p.value ? ' active' : ''}`}
                                    onClick={() => setPeriodo(p.value)}
                                >
                                    {p.label}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* ── Card do gráfico ── */}
            {cdAtivo && (
                <div className="pg-card">
                    <div className="pg-card-header">
                        <div className="hist-card-info">
                            <span className="pg-card-title">{cdAtivo}</span>
                            {meta && (
                                <span className="pg-card-meta">
                                    {meta.DT_INICIO} → {meta.DT_FIM}
                                    {' · '}{meta.QT_REGISTROS.toLocaleString('pt-BR')} pregões
                                </span>
                            )}
                        </div>
                        {variacao !== null && (
                            <span className={`hist-variacao ${variacao >= 0 ? 'positivo' : 'negativo'}`}>
                                {variacao >= 0 ? '+' : ''}{formatNumero(variacao)}%
                                <span className="hist-variacao-label"> no período</span>
                            </span>
                        )}
                    </div>

                    {loadingSeries ? (
                        <div className="pg-loading" style={{ borderRadius: 0, border: 'none', borderTop: '1px solid var(--color-border)' }}>
                            <i className="fas fa-circle-notch fa-spin" />
                            <span>Carregando histórico…</span>
                        </div>
                    ) : (
                        <GraficoFechamento rows={seriesFiltrada} cdAtivo={cdAtivo} />
                    )}
                </div>
            )}

            {/* ── Hint ── */}
            {!cdAtivo && !loadingAtivos && ativosUnicos.length > 0 && (
                <div className="pg-hint">
                    <i className="fas fa-chart-line" />
                    <span>Selecione um ativo para visualizar o fechamento ajustado ao longo do tempo.</span>
                </div>
            )}
        </div>
    );
}
