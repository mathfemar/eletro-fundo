import { useMemo, useState } from 'react';
import {
    useSimTitulares,
    useCreateSimTitular,
    useSimFundos,
    useSimFundCotistasPosicao,
    useSimFundCotistasPosicaoSerie,
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

export default function SimuladorCotistas() {
    const { data: fundos } = useSimFundos();
    const { data, isLoading, error } = useSimTitulares();
    const createCotista = useCreateSimTitular();
    const [fundoId, setFundoId] = useState<number | null>(null);
    const [dtReferencia, setDtReferencia] = useState(hojeISO());
    const [dtInicioHist, setDtInicioHist] = useState(diasAtrasISO(30));
    const [cotistaHistId, setCotistaHistId] = useState<number | null>(null);

    const posicaoQuery = useSimFundCotistasPosicao(fundoId, dtReferencia);
    const posicaoSerieQuery = useSimFundCotistasPosicaoSerie(fundoId, dtInicioHist, dtReferencia);

    const [nome, setNome] = useState('');
    const [documento, setDocumento] = useState('');

    const posicaoMap = useMemo(() => {
        const map = new Map<number, (typeof posicaoQuery.data.items)[number]>();
        (posicaoQuery.data?.items ?? []).forEach(item => {
            map.set(item.ID_TITULAR, item);
        });
        return map;
    }, [posicaoQuery.data?.items]);

    const cotistasComContexto = useMemo(
        () =>
            (data ?? []).map(item => {
                const pos = posicaoMap.get(item.ID_TITULAR);
                return {
                    ...item,
                    VL_APORTADO_BRUTO: Number(pos?.VL_APORTADO_BRUTO ?? 0),
                    VL_RESGATADO_BRUTO: Number(pos?.VL_RESGATADO_BRUTO ?? 0),
                    VL_INVERTIDO_LIQ: Number(pos?.VL_INVERTIDO_LIQ ?? 0),
                    QT_COTAS: Number(pos?.QT_COTAS ?? 0),
                    VL_PL_COTISTA: Number(pos?.VL_PL_COTISTA ?? 0),
                    VL_PNL_COTISTA: Number(pos?.VL_PNL_COTISTA ?? 0),
                    TEM_POSICAO: !!pos,
                    PC_PARTICIPACAO_FUNDO: 0,
                };
            }),
        [data, posicaoMap],
    );

    const cotistasComParticipacao = useMemo(() => {
        const totalPl = cotistasComContexto.reduce((acc, item) => acc + item.VL_PL_COTISTA, 0);
        return cotistasComContexto.map(item => ({
            ...item,
            PC_PARTICIPACAO_FUNDO: totalPl > 0 ? (item.VL_PL_COTISTA / totalPl) * 100 : 0,
        }));
    }, [cotistasComContexto]);

    const resumo = useMemo(() => {
        const total = cotistasComParticipacao.length;
        const comPosicao = cotistasComParticipacao.filter(item => item.TEM_POSICAO).length;
        const plTotal = cotistasComParticipacao.reduce((acc, item) => acc + item.VL_PL_COTISTA, 0);
        const pnlTotal = cotistasComParticipacao.reduce((acc, item) => acc + item.VL_PNL_COTISTA, 0);
        return { total, comPosicao, plTotal, pnlTotal };
    }, [cotistasComParticipacao]);

    const serieCotistaSelecionado = useMemo(() => {
        if (!cotistaHistId) return [];
        return (posicaoSerieQuery.data ?? [])
            .filter(item => Number(item.ID_TITULAR) === cotistaHistId)
            .sort((a, b) => String(a.DT_REFERENCIA).localeCompare(String(b.DT_REFERENCIA)));
    }, [posicaoSerieQuery.data, cotistaHistId]);

    const ultimoHist = serieCotistaSelecionado.length > 0 ? serieCotistaSelecionado[serieCotistaSelecionado.length - 1] : null;

    async function onCreate() {
        if (!nome.trim()) return;
        await createCotista.mutateAsync({
            NM_TITULAR: nome.trim(),
            NR_DOCUMENTO: documento || null,
            ST_ATIVO: 1,
        });
        setNome('');
        setDocumento('');
    }

    return (
        <div className="pg-page">
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon"><i className="fas fa-users" /></div>
                    <div className="pg-header-text">
                        <h1>Cotistas</h1>
                        <p>Cadastro de cotistas econômicos do fundo (base para setup inicial e fluxos de aporte/resgate).</p>
                    </div>
                </div>
            </div>

            <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                <div className="sim-card-title">Novo cotista</div>
                <div className="sim-form">
                    <div>
                        <label className="pg-select-label">Nome</label>
                        <input className="sim-input" value={nome} onChange={e => setNome(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Documento</label>
                        <input className="sim-input" value={documento} onChange={e => setDocumento(e.target.value)} placeholder="Opcional" />
                    </div>
                    <div>
                        <button className="sim-btn" onClick={onCreate} disabled={createCotista.isPending || !nome.trim()}>
                            {createCotista.isPending ? 'Criando…' : 'Criar cotista'}
                        </button>
                    </div>
                </div>
            </div>

            <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                <div className="sim-card-title">Contexto econômico</div>
                <div className="sim-form">
                    <div>
                        <label className="pg-select-label">Fundo</label>
                        <select
                            className="sim-select"
                            value={fundoId ?? ''}
                            onChange={e => {
                                const nextFundoId = e.target.value ? Number(e.target.value) : null;
                                setFundoId(nextFundoId);
                                setCotistaHistId(null);
                            }}
                        >
                            <option value="">— selecione para ver posição —</option>
                            {(fundos ?? []).map(f => (
                                <option key={f.ID_FUNDO} value={f.ID_FUNDO}>{f.NM_FUNDO}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="pg-select-label">Data base</label>
                        <input className="sim-input" type="date" value={dtReferencia} onChange={e => setDtReferencia(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Início histórico</label>
                        <input className="sim-input" type="date" value={dtInicioHist} onChange={e => setDtInicioHist(e.target.value)} />
                    </div>
                </div>
                {!fundoId && (
                    <p style={{ marginTop: '0.6rem', marginBottom: 0, color: 'var(--color-text-muted)' }}>
                        Selecione um fundo para carregar aportes, resgates, PL e PnL por cotista.
                    </p>
                )}
            </div>

            <div className="sim-kpis" style={{ marginBottom: '0.8rem' }}>
                <div className="sim-kpi">
                    <div className="sim-kpi-label">Cotistas cadastrados</div>
                    <div className="sim-kpi-value">{resumo.total}</div>
                </div>
                <div className="sim-kpi">
                    <div className="sim-kpi-label">Com posição no fundo</div>
                    <div className="sim-kpi-value">{resumo.comPosicao}</div>
                </div>
                <div className="sim-kpi">
                    <div className="sim-kpi-label">PL dos cotistas</div>
                    <div className="sim-kpi-value">{formatNumero(resumo.plTotal, 2)}</div>
                </div>
                <div className="sim-kpi">
                    <div className="sim-kpi-label">PnL dos cotistas</div>
                    <div className={`sim-kpi-value ${resumo.pnlTotal >= 0 ? 'positivo' : 'negativo'}`}>
                        {formatNumero(resumo.pnlTotal, 2)}
                    </div>
                </div>
            </div>

            {isLoading && <div className="pg-loading"><i className="fas fa-circle-notch fa-spin" /> Carregando cotistas…</div>}
            {error && <div className="pg-error"><i className="fas fa-triangle-exclamation" /> {(error as Error).message}</div>}
            {fundoId && posicaoQuery.isLoading && <div className="pg-loading"><i className="fas fa-circle-notch fa-spin" /> Carregando posição econômica…</div>}
            {fundoId && posicaoQuery.error && <div className="pg-error"><i className="fas fa-triangle-exclamation" /> {(posicaoQuery.error as Error).message}</div>}
            {fundoId && posicaoSerieQuery.isLoading && <div className="pg-loading"><i className="fas fa-circle-notch fa-spin" /> Carregando histórico do cotista…</div>}
            {fundoId && posicaoSerieQuery.error && <div className="pg-error"><i className="fas fa-triangle-exclamation" /> {(posicaoSerieQuery.error as Error).message}</div>}

            {!isLoading && !error && (
                <div className="sim-table-wrap">
                    <table className="sim-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Nome</th>
                                <th>Documento</th>
                                <th>Status</th>
                                <th>Aportes</th>
                                <th>Resgates</th>
                                <th>Investido Líq.</th>
                                <th>Qt Cotas</th>
                                <th>PL Cotista</th>
                                <th>% no Fundo</th>
                                <th>PnL Cotista</th>
                            </tr>
                        </thead>
                        <tbody>
                            {cotistasComParticipacao.map(item => (
                                <tr key={item.ID_TITULAR}>
                                    <td>{item.ID_TITULAR}</td>
                                    <td>{item.NM_TITULAR}</td>
                                    <td>{item.NR_DOCUMENTO ?? '—'}</td>
                                    <td>{Number(item.ST_ATIVO ?? 1) === 1 ? 'Ativo' : 'Inativo'}</td>
                                    <td>{formatNumero(item.VL_APORTADO_BRUTO, 2)}</td>
                                    <td>{formatNumero(item.VL_RESGATADO_BRUTO, 2)}</td>
                                    <td>{formatNumero(item.VL_INVERTIDO_LIQ, 2)}</td>
                                    <td>{formatNumero(item.QT_COTAS, 6)}</td>
                                    <td>{formatNumero(item.VL_PL_COTISTA, 2)}</td>
                                    <td>{formatNumero(item.PC_PARTICIPACAO_FUNDO, 2)}%</td>
                                    <td className={item.VL_PNL_COTISTA >= 0 ? 'positivo' : 'negativo'}>{formatNumero(item.VL_PNL_COTISTA, 2)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {fundoId && !isLoading && !error && (
                <div className="sim-card" style={{ marginTop: '0.8rem' }}>
                    <div className="sim-card-title">Detalhe histórico do cotista</div>
                    <div className="sim-form" style={{ marginBottom: '0.6rem' }}>
                        <div>
                            <label className="pg-select-label">Cotista</label>
                            <select
                                className="sim-select"
                                value={cotistaHistId ?? ''}
                                onChange={e => setCotistaHistId(e.target.value ? Number(e.target.value) : null)}
                            >
                                <option value="">— selecione —</option>
                                {cotistasComParticipacao.map(item => (
                                    <option key={item.ID_TITULAR} value={item.ID_TITULAR}>
                                        {item.NM_TITULAR}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {!cotistaHistId && (
                        <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                            Selecione um cotista para ver evolução de PL/PnL no período.
                        </p>
                    )}

                    {cotistaHistId && (
                        <>
                            <p style={{ marginTop: 0, marginBottom: '0.6rem', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                                Último ponto: {ultimoHist?.DT_REFERENCIA ?? '—'} | PL {formatNumero(Number(ultimoHist?.VL_PL_COTISTA ?? 0), 2)} | PnL {formatNumero(Number(ultimoHist?.VL_PNL_COTISTA ?? 0), 2)}
                            </p>
                            <div className="sim-table-wrap">
                                <table className="sim-table">
                                    <thead>
                                        <tr>
                                            <th>Data</th>
                                            <th>VL Cota</th>
                                            <th>Qt Cotas</th>
                                            <th>PL Cotista</th>
                                            <th>PnL Cotista</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {serieCotistaSelecionado.length === 0 && (
                                            <tr>
                                                <td colSpan={5} style={{ color: 'var(--color-text-muted)' }}>Sem histórico para o período informado.</td>
                                            </tr>
                                        )}
                                        {serieCotistaSelecionado.map(item => (
                                            <tr key={`${item.ID_TITULAR}-${item.DT_REFERENCIA}`}>
                                                <td>{item.DT_REFERENCIA}</td>
                                                <td>{formatNumero(Number(item.VL_COTA ?? 0), 6)}</td>
                                                <td>{formatNumero(Number(item.QT_COTAS ?? 0), 6)}</td>
                                                <td>{formatNumero(Number(item.VL_PL_COTISTA ?? 0), 2)}</td>
                                                <td className={Number(item.VL_PNL_COTISTA ?? 0) >= 0 ? 'positivo' : 'negativo'}>
                                                    {formatNumero(Number(item.VL_PNL_COTISTA ?? 0), 2)}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
