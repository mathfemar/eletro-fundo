import { useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import {
    useSimFundos,
    useSimTitulares,
    useSimFundCarteiras,
    useSimFundFluxos,
    useCreateSimFundCarteira,
    usePostSimFundAlocacao,
    useDeleteSimPortfolio,
} from '@/hooks/useSimulador';
import { formatNumero } from '@/utils/formatBR';
import './Simulador.css';

function hojeISO() {
    return new Date().toISOString().slice(0, 10);
}

export default function SimuladorCarteirasAlocacao() {
    const { data: fundos } = useSimFundos();
    const { data: titulares } = useSimTitulares();

    const [fundoId, setFundoId] = useState<number | null>(null);

    const carteirasQuery = useSimFundCarteiras(fundoId);
    const fluxosQuery = useSimFundFluxos(fundoId);
    const createCarteira = useCreateSimFundCarteira();
    const postAlocacao = usePostSimFundAlocacao();
    const deleteCarteira = useDeleteSimPortfolio();

    const [nmCarteira, setNmCarteira] = useState('');
    const [idTitular, setIdTitular] = useState<number | null>(null);
    const [contaRef, setContaRef] = useState('');
    const [dtInicio, setDtInicio] = useState(hojeISO());

    const [carteiraOrigem, setCarteiraOrigem] = useState<number | null>(null);
    const [carteiraDestino, setCarteiraDestino] = useState<number | null>(null);
    const [vlAlocacao, setVlAlocacao] = useState('0');
    const [dtMovimento, setDtMovimento] = useState(hojeISO());
    const [obs, setObs] = useState('');

    const carteiras = carteirasQuery.data ?? [];
    const titularesPermitidos = useMemo(() => {
        const ids = new Set<number>();
        for (const f of fluxosQuery.data ?? []) {
            if (f.ID_TITULAR != null) ids.add(Number(f.ID_TITULAR));
        }
        for (const c of carteiras) {
            if (c.ID_TITULAR != null) ids.add(Number(c.ID_TITULAR));
        }
        return (titulares ?? []).filter(t => ids.has(Number(t.ID_TITULAR)));
    }, [fluxosQuery.data, carteiras, titulares]);

    const caixa = useMemo(
        () => carteiras.find(c => (c.CONTA_REF ?? '').toUpperCase() === 'CAIXA' || (c.NM_CARTEIRA ?? '').toUpperCase().startsWith('CAIXA -')) ?? null,
        [carteiras],
    );

    async function onCriarCarteira() {
        if (!fundoId || !idTitular || !nmCarteira.trim()) return;
        try {
            await createCarteira.mutateAsync({
                fundoId,
                payload: {
                    ID_TITULAR: idTitular,
                    NM_CARTEIRA: nmCarteira.trim(),
                    CONTA_REF: contaRef || null,
                    DT_INICIO: dtInicio,
                    MOEDA_BASE: 'BRL',
                },
            });
            setNmCarteira('');
            setContaRef('');
        } catch (err: unknown) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            window.alert(detail ?? 'Não foi possível criar a carteira.');
        }
    }

    async function onAlocar() {
        if (!fundoId || !carteiraOrigem || !carteiraDestino) return;
        const valor = Number(vlAlocacao);
        if (!Number.isFinite(valor) || valor <= 0) {
            window.alert('Informe um valor de alocação maior que zero.');
            return;
        }
        await postAlocacao.mutateAsync({
            fundoId,
            payload: {
                ID_CARTEIRA_ORIGEM: carteiraOrigem,
                ID_CARTEIRA_DESTINO: carteiraDestino,
                VL_ALOCACAO: valor,
                DT_MOVIMENTO: dtMovimento,
                DS_OBSERVACAO: obs || null,
            },
        });
        setObs('');
        setVlAlocacao('0');
    }

    async function onExcluirCarteira(idCarteira: number, nomeCarteira: string) {
        const ok = window.confirm(
            `Excluir a carteira "${nomeCarteira}"? Esta ação remove operações e vínculos da carteira e não pode ser desfeita.`,
        );
        if (!ok) return;

        try {
            await deleteCarteira.mutateAsync(idCarteira);
            if (carteiraOrigem === idCarteira) setCarteiraOrigem(null);
            if (carteiraDestino === idCarteira) setCarteiraDestino(null);
        } catch (err: unknown) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            window.alert(detail ?? 'Não foi possível excluir a carteira.');
        }
    }

    return (
        <div className="pg-page">
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon"><i className="fas fa-wallet" /></div>
                    <div className="pg-header-text">
                        <h1>Carteiras e Alocação</h1>
                        <p>Gestão de carteiras por fundo e alocação de caixa entre carteiras com validação de saldo.</p>
                    </div>
                </div>
            </div>

            <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                <div className="sim-card-title">Selecionar fundo</div>
                <div className="sim-form">
                    <div>
                        <label className="pg-select-label">Fundo</label>
                        <select className="sim-select" value={fundoId ?? ''} onChange={e => setFundoId(e.target.value ? Number(e.target.value) : null)}>
                            <option value="">— selecione —</option>
                            {(fundos ?? []).map(f => (
                                <option key={f.ID_FUNDO} value={f.ID_FUNDO}>{f.NM_FUNDO}</option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {fundoId && (
                <>
                    <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                        <div className="sim-card-title">Criar carteira de estratégia</div>
                        <div className="sim-form">
                            <div>
                                <label className="pg-select-label">Nome da carteira</label>
                                <input className="sim-input" value={nmCarteira} onChange={e => setNmCarteira(e.target.value)} />
                            </div>
                            <div>
                                <label className="pg-select-label">Titular (cotista)</label>
                                <select className="sim-select" value={idTitular ?? ''} onChange={e => setIdTitular(e.target.value ? Number(e.target.value) : null)}>
                                    <option value="">— selecione —</option>
                                    {titularesPermitidos.map(t => (
                                        <option key={t.ID_TITULAR} value={t.ID_TITULAR}>{t.NM_TITULAR}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="pg-select-label">Conta ref</label>
                                <input className="sim-input" value={contaRef} onChange={e => setContaRef(e.target.value)} placeholder="Opcional" />
                            </div>
                            <div>
                                <label className="pg-select-label">Data início</label>
                                <input className="sim-input" type="date" value={dtInicio} onChange={e => setDtInicio(e.target.value)} />
                            </div>
                            <div>
                                <button className="sim-btn" onClick={onCriarCarteira} disabled={createCarteira.isPending || !nmCarteira.trim() || !idTitular}>
                                    {createCarteira.isPending ? 'Criando…' : 'Criar carteira'}
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                        <div className="sim-card-title">Alocar caixa entre carteiras</div>
                        {caixa && (
                            <p style={{ marginTop: 0, color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                                Saldo da carteira caixa: <strong>{formatNumero(caixa.VL_SALDO_CAIXA ?? 0, 2)}</strong>
                            </p>
                        )}
                        <div className="sim-form">
                            <div>
                                <label className="pg-select-label">Origem</label>
                                <select className="sim-select" value={carteiraOrigem ?? ''} onChange={e => setCarteiraOrigem(e.target.value ? Number(e.target.value) : null)}>
                                    <option value="">— selecione —</option>
                                    {carteiras.map(c => <option key={c.ID_CARTEIRA} value={c.ID_CARTEIRA}>{c.NM_CARTEIRA}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="pg-select-label">Destino</label>
                                <select className="sim-select" value={carteiraDestino ?? ''} onChange={e => setCarteiraDestino(e.target.value ? Number(e.target.value) : null)}>
                                    <option value="">— selecione —</option>
                                    {carteiras.map(c => <option key={c.ID_CARTEIRA} value={c.ID_CARTEIRA}>{c.NM_CARTEIRA}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="pg-select-label">Valor</label>
                                <input className="sim-input" type="number" step="0.01" value={vlAlocacao} onChange={e => setVlAlocacao(e.target.value)} />
                            </div>
                            <div>
                                <label className="pg-select-label">Data</label>
                                <input className="sim-input" type="date" value={dtMovimento} onChange={e => setDtMovimento(e.target.value)} />
                            </div>
                            <div>
                                <label className="pg-select-label">Obs</label>
                                <input className="sim-input" value={obs} onChange={e => setObs(e.target.value)} placeholder="Opcional" />
                            </div>
                            <div>
                                <button className="sim-btn" onClick={onAlocar} disabled={postAlocacao.isPending || !carteiraOrigem || !carteiraDestino}>
                                    {postAlocacao.isPending ? 'Alocando…' : 'Alocar'}
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="sim-chart-grid" style={{ marginBottom: '0.8rem', gridTemplateColumns: 'minmax(0, 400px)' }}>
                        <div className="sim-card sim-chart-card">
                            <div className="sim-card-title">Alocação de Saldo em Conta</div>
                            <Plot
                                data={[
                                    {
                                        values: [
                                            Math.max(0, caixa?.VL_SALDO_CAIXA ?? 0),
                                            ...carteiras.filter(c => c.ID_CARTEIRA !== caixa?.ID_CARTEIRA && Math.abs(c.VL_SALDO_CAIXA ?? 0) > 1).map(c => Math.abs(c.VL_SALDO_CAIXA ?? 0))
                                        ],
                                        labels: [
                                            'CAIXA LIVRE',
                                            ...carteiras.filter(c => c.ID_CARTEIRA !== caixa?.ID_CARTEIRA && Math.abs(c.VL_SALDO_CAIXA ?? 0) > 1).map(c => c.NM_CARTEIRA ?? 'Carteira')
                                        ],
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

                    <div className="sim-card">
                        <div className="sim-card-title">Carteiras do fundo</div>
                        <div className="sim-table-wrap">
                            <table className="sim-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Carteira</th>
                                        <th>Titular</th>
                                        <th>Conta</th>
                                        <th>Saldo Conta Origem</th>
                                        <th>Ações</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {carteiras.map(c => (
                                        <tr key={c.ID_CARTEIRA}>
                                            <td>{c.ID_CARTEIRA}</td>
                                            <td>{c.NM_CARTEIRA}</td>
                                            <td>{c.NM_TITULAR ?? '—'}</td>
                                            <td>{c.CONTA_REF ?? '—'}</td>
                                            <td>{formatNumero(c.VL_SALDO_CAIXA ?? 0, 2)}</td>
                                            <td>
                                                <button
                                                    className="sim-btn sim-btn--danger"
                                                    onClick={() => onExcluirCarteira(c.ID_CARTEIRA, c.NM_CARTEIRA)}
                                                    disabled={deleteCarteira.isPending}
                                                >
                                                    {deleteCarteira.isPending ? 'Excluindo…' : 'Excluir'}
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
