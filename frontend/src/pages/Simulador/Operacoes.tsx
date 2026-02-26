import { useEffect, useMemo, useState } from 'react';
import { useAtivos } from '@/hooks/useAtivos';
import {
    useSimPortfolios,
    useSimFundCarteiras,
    useCreateSimTrade,
    useUpdateSimTrade,
    useDeleteSimTrade,
    useSimTrades,
    useSimFundFluxos,
    useSimFundCotaSerie,
} from '@/hooks/useSimulador';
import { formatNumero } from '@/utils/formatBR';
import './Simulador.css';

const SIDES = ['BUY', 'SELL'] as const;

type Side = (typeof SIDES)[number];

function hojeISO() {
    return new Date().toISOString().slice(0, 10);
}

function agoraLocalDateTime() {
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function toLocalDateTime(value?: string | null) {
    if (!value) return '';
    return value.replace(' ', 'T').slice(0, 16);
}

function getApiErrorDetail(error: unknown): string {
    const err = error as {
        response?: {
            data?: {
                detail?: unknown;
                error?: string;
                message?: string;
            };
        };
        message?: string;
    };

    const detail = err.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;

    if (Array.isArray(detail)) {
        const msgs = detail
            .map(item => {
                if (typeof item === 'string') return item;
                if (item && typeof item === 'object' && 'msg' in item) {
                    return String((item as { msg?: unknown }).msg ?? '');
                }
                return '';
            })
            .filter(Boolean);
        if (msgs.length > 0) return msgs.join(' | ');
    }

    const fallback = err.response?.data?.error || err.response?.data?.message || err.message;
    return fallback || 'Não foi possível concluir a operação. Verifique os dados e tente novamente.';
}

export default function SimuladorOperacoes() {
    const { data: portfolios } = useSimPortfolios();
    const { data: ativos } = useAtivos();

    const [portfolioId, setPortfolioId] = useState<number | null>(null);
    const [idAtivo, setIdAtivo] = useState<number | null>(null);
    const [dtTrade, setDtTrade] = useState(hojeISO());
    const [dtHoraExec, setDtHoraExec] = useState(agoraLocalDateTime());
    const [side, setSide] = useState<Side>('BUY');
    const [qtd, setQtd] = useState('100');
    const [pu, setPu] = useState('0');
    const [custo, setCusto] = useState('0');
    const [obs, setObs] = useState('');
    const [editingTradeId, setEditingTradeId] = useState<number | null>(null);
    const [formError, setFormError] = useState<string>('');

    const createTrade = useCreateSimTrade();
    const updateTrade = useUpdateSimTrade();
    const deleteTrade = useDeleteSimTrade();
    const { data: trades, isLoading, error } = useSimTrades(portfolioId);
    const selectedPortfolio = useMemo(
        () => (portfolios ?? []).find(p => p.ID_PORTFOLIO === portfolioId) ?? null,
        [portfolios, portfolioId],
    );
    const fundoIdSelecionado = selectedPortfolio?.ID_FUNDO ?? null;
    const carteirasFundoQuery = useSimFundCarteiras(fundoIdSelecionado);
    const fluxosAteDataQuery = useSimFundFluxos(fundoIdSelecionado, undefined, dtTrade);
    const cotaAteDataQuery = useSimFundCotaSerie(fundoIdSelecionado, undefined, dtTrade);

    const caixaDisponivelCarteira = useMemo(() => {
        if (!portfolioId) return null;
        const row = (carteirasFundoQuery.data ?? []).find(c => c.ID_CARTEIRA === portfolioId);
        if (!row) return null;
        return Number(row.VL_SALDO_CAIXA ?? 0);
    }, [carteirasFundoQuery.data, portfolioId]);

    const valorEstimadoOrdem = useMemo(() => {
        const q = Number(qtd);
        const p = Number(pu);
        const c = Number(custo || 0);
        if (!Number.isFinite(q) || !Number.isFinite(p) || !Number.isFinite(c)) return 0;
        return q * p + c;
    }, [qtd, pu, custo]);

    const ativosUnicos = useMemo(() => {
        if (!ativos) return [];
        const map = new Map<number, (typeof ativos)[number]>();
        for (const a of ativos) {
            if (!map.has(a.ID_ATIVO)) map.set(a.ID_ATIVO, a);
        }
        return Array.from(map.values());
    }, [ativos]);

    const carteirasOperaveis = useMemo(
        () =>
            (portfolios ?? []).filter(p => {
                const contaRef = String(p.CONTA_REF ?? '').toUpperCase();
                const nome = String(p.NM_PORTFOLIO ?? '').toUpperCase();
                return contaRef !== 'CAIXA' && !nome.startsWith('CAIXA -');
            }),
        [portfolios],
    );

    useEffect(() => {
        if (portfolioId && !carteirasOperaveis.some(p => p.ID_PORTFOLIO === portfolioId)) {
            setPortfolioId(null);
        }
    }, [portfolioId, carteirasOperaveis]);

    const fluxoLiquidoAteData = useMemo(() => {
        const rows = fluxosAteDataQuery.data ?? [];
        return rows.reduce((acc, item) => acc + (item.TP_FLUXO === 'APORTE' ? Number(item.VL_FLUXO ?? 0) : -Number(item.VL_FLUXO ?? 0)), 0);
    }, [fluxosAteDataQuery.data]);

    const temPlInicialAteData = useMemo(() => {
        const rows = cotaAteDataQuery.data ?? [];
        return rows.some(item => Number(item.VL_PL ?? 0) > 0);
    }, [cotaAteDataQuery.data]);

    const bloqueadoSemAporte = !!portfolioId && (fundoIdSelecionado == null || (fluxoLiquidoAteData <= 0 && !temPlInicialAteData));

    function resetForm() {
        setIdAtivo(null);
        setDtTrade(hojeISO());
        setDtHoraExec(agoraLocalDateTime());
        setSide('BUY');
        setQtd('100');
        setPu('0');
        setCusto('0');
        setObs('');
        setEditingTradeId(null);
    }

    async function onSaveTrade() {
        setFormError('');
        if (!portfolioId || !idAtivo) return;
        if (bloqueadoSemAporte) {
            setFormError('Fundo sem capitalização líquida até a data da operação. Faça aporte inicial antes de operar.');
            return;
        }

        const payload = {
            ID_PORTFOLIO: portfolioId,
            ID_ATIVO: idAtivo,
            DT_HORA_EXEC: dtHoraExec ? dtHoraExec.replace('T', ' ') + ':00' : undefined,
            DT_TRADE: dtTrade,
            SIDE: side,
            QTD: Number(qtd),
            PU: Number(pu),
            CUSTO: Number(custo || 0),
            OBSERVACAO: obs || null,
        };

        try {
            if (editingTradeId) {
                await updateTrade.mutateAsync({ tradeId: editingTradeId, payload });
            } else {
                await createTrade.mutateAsync(payload);
            }

            setObs('');
            setEditingTradeId(null);
        } catch (error) {
            setFormError(getApiErrorDetail(error));
        }
    }

    function onEditTrade(tradeId: number) {
        const trade = (trades ?? []).find(t => t.ID_TRADE === tradeId);
        if (!trade) return;

        setEditingTradeId(trade.ID_TRADE);
        setIdAtivo(trade.ID_ATIVO);
        setDtTrade(trade.DT_TRADE);
        setDtHoraExec(toLocalDateTime(trade.DT_HORA_EXEC));
        setSide(trade.SIDE);
        setQtd(String(trade.QTD));
        setPu(String(trade.PU));
        setCusto(String(trade.CUSTO ?? 0));
        setObs(trade.OBSERVACAO ?? '');
    }

    async function onDeleteTrade(tradeId: number) {
        const ok = window.confirm('Excluir esta operação?');
        if (!ok) return;

        await deleteTrade.mutateAsync(tradeId);
        if (editingTradeId === tradeId) {
            resetForm();
        }
    }

    const isSaving = createTrade.isPending || updateTrade.isPending;
    const isDeleting = deleteTrade.isPending;

    return (
        <div className="pg-page">
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon"><i className="fas fa-right-left" /></div>
                    <div className="pg-header-text">
                        <h1>Operações Simuladas</h1>
                        <p>Lançamento manual de operações BUY/SELL da carteira.</p>
                    </div>
                </div>
            </div>

            <div className="sim-card">
                <div className="sim-card-title">Nova operação</div>
                <div className="sim-form">
                    <div>
                        <label className="pg-select-label">Carteira</label>
                        <select className="sim-select" value={portfolioId ?? ''} onChange={e => setPortfolioId(e.target.value ? Number(e.target.value) : null)}>
                            <option value="">— selecione —</option>
                            {carteirasOperaveis.map(p => <option key={p.ID_PORTFOLIO} value={p.ID_PORTFOLIO}>{p.NM_PORTFOLIO}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="pg-select-label">Ativo</label>
                        <select className="sim-select" value={idAtivo ?? ''} onChange={e => setIdAtivo(e.target.value ? Number(e.target.value) : null)}>
                            <option value="">— selecione —</option>
                            {ativosUnicos.map(a => <option key={a.ID_ATIVO} value={a.ID_ATIVO}>{a.CD_ATIVO}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="pg-select-label">Data/hora execução</label>
                        <input className="sim-input" type="datetime-local" value={dtHoraExec} onChange={e => setDtHoraExec(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Data</label>
                        <input className="sim-input" type="date" value={dtTrade} onChange={e => setDtTrade(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Side</label>
                        <select className="sim-select" value={side} onChange={e => setSide(e.target.value as Side)}>
                            {SIDES.map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="pg-select-label">Qtd</label>
                        <input className="sim-input" type="number" value={qtd} onChange={e => setQtd(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Preço</label>
                        <input className="sim-input" type="number" step="0.0001" value={pu} onChange={e => setPu(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Custo</label>
                        <input className="sim-input" type="number" step="0.01" value={custo} onChange={e => setCusto(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Obs</label>
                        <input className="sim-input" value={obs} onChange={e => setObs(e.target.value)} placeholder="Opcional" />
                    </div>
                    <div>
                        <button className="sim-btn" onClick={onSaveTrade} disabled={isSaving || isDeleting || !portfolioId || !idAtivo || bloqueadoSemAporte}>
                            {isSaving ? 'Salvando…' : editingTradeId ? 'Atualizar operação' : 'Salvar operação'}
                        </button>
                    </div>
                    {editingTradeId && (
                        <div>
                            <button className="sim-btn sim-btn--neutral" onClick={resetForm} disabled={isSaving || isDeleting}>
                                Cancelar edição
                            </button>
                        </div>
                    )}
                </div>
                {portfolioId && (
                    <p style={{ marginTop: '0.65rem', marginBottom: 0, color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                        {carteirasFundoQuery.isLoading
                            ? 'Carregando caixa disponível da carteira…'
                            : caixaDisponivelCarteira == null
                                ? 'Caixa disponível: não identificado para a carteira selecionada.'
                                : `Caixa disponível: ${formatNumero(caixaDisponivelCarteira, 2)} • Valor estimado da ordem: ${formatNumero(valorEstimadoOrdem, 2)}`}
                    </p>
                )}
                {bloqueadoSemAporte && (
                    <p style={{ marginTop: '0.65rem', marginBottom: 0, color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                        Operação bloqueada: este fundo ainda não possui aporte líquido até {dtTrade}. Cadastre PL inicial no fundo ou registre aporte em Fundos.
                    </p>
                )}
                {formError && (
                    <div className="pg-error" style={{ marginTop: '0.65rem' }}>
                        <i className="fas fa-triangle-exclamation" /> {formError}
                    </div>
                )}
            </div>

            {isLoading && <div className="pg-loading"><i className="fas fa-circle-notch fa-spin" /> Carregando operações…</div>}
            {error && <div className="pg-error"><i className="fas fa-triangle-exclamation" /> {(error as Error).message}</div>}

            {!isLoading && !error && (
                <div className="sim-table-wrap">
                    <table className="sim-table">
                        <thead>
                            <tr>
                                <th>Execução</th>
                                <th>Data</th>
                                <th>Ativo</th>
                                <th>Side</th>
                                <th>Qtd</th>
                                <th>Preço</th>
                                <th>Custo</th>
                                <th>Obs</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(trades ?? []).map(t => (
                                <tr key={t.ID_TRADE}>
                                    <td>{t.DT_HORA_EXEC}</td>
                                    <td>{t.DT_TRADE}</td>
                                    <td>{t.CD_ATIVO}</td>
                                    <td>{t.SIDE}</td>
                                    <td>{formatNumero(t.QTD, 2)}</td>
                                    <td>{formatNumero(t.PU, 2)}</td>
                                    <td>{formatNumero(t.CUSTO ?? 0, 2)}</td>
                                    <td>{t.OBSERVACAO ?? '—'}</td>
                                    <td>
                                        <div className="sim-row-actions">
                                            <button
                                                className="sim-btn sim-btn--neutral"
                                                onClick={() => onEditTrade(t.ID_TRADE)}
                                                disabled={isSaving || isDeleting}
                                            >
                                                Editar
                                            </button>
                                            <button
                                                className="sim-btn sim-btn--danger"
                                                onClick={() => onDeleteTrade(t.ID_TRADE)}
                                                disabled={isSaving || isDeleting}
                                            >
                                                Excluir
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
