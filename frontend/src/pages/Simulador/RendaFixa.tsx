import { useMemo, useState } from 'react';
import { useAtivos } from '@/hooks/useAtivos';
import { usePostSimRFTitulo, useSimRFTitulos } from '@/hooks/useSimulador';
import { formatNumero } from '@/utils/formatBR';
import './Simulador.css';

function hojeISO() {
    return new Date().toISOString().slice(0, 10);
}

export default function SimuladorRendaFixa() {
    const { data: ativos } = useAtivos();
    const titulosQuery = useSimRFTitulos(1);
    const criarTitulo = usePostSimRFTitulo();

    const [cdTitulo, setCdTitulo] = useState('');
    const [nmTitulo, setNmTitulo] = useState('');
    const [idAtivo, setIdAtivo] = useState<number | null>(null);
    const [dtVencimento, setDtVencimento] = useState(hojeISO());
    const [dtResgate, setDtResgate] = useState('');
    const [txContratada, setTxContratada] = useState('');

    const titulos = titulosQuery.data ?? [];

    const resumo = useMemo(() => {
        const total = titulos.length;
        const comDataResgate = titulos.filter(item => !!item.DT_RESGATE).length;
        const semDataResgate = total - comDataResgate;
        return { total, comDataResgate, semDataResgate };
    }, [titulos]);

    async function onCriarTitulo() {
        if (!cdTitulo.trim()) {
            window.alert('Informe o código do título RF.');
            return;
        }

        try {
            await criarTitulo.mutateAsync({
                CD_TITULO: cdTitulo.trim().toUpperCase(),
                NM_TITULO: nmTitulo.trim() || null,
                ID_ATIVO: idAtivo,
                DT_VENCIMENTO: dtVencimento,
                DT_RESGATE: dtResgate || null,
                VL_TAXA_CONTRATADA: txContratada ? Number(txContratada) : null,
                ST_ATIVO: 1,
            });

            setCdTitulo('');
            setNmTitulo('');
            setIdAtivo(null);
            setDtResgate('');
            setTxContratada('');
        } catch (err: unknown) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            window.alert(detail ?? 'Não foi possível cadastrar o título RF.');
        }
    }

    return (
        <div className="pg-page">
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon"><i className="fas fa-file-invoice-dollar" /></div>
                    <div className="pg-header-text">
                        <h1>Renda Fixa</h1>
                        <p>Cadastro de títulos RF com data de liquidez fixa por resgate antecipado ou vencimento.</p>
                    </div>
                </div>
            </div>

            <div className="sim-kpis" style={{ marginBottom: '0.8rem' }}>
                <div className="sim-kpi">
                    <div className="sim-kpi-label">Títulos RF ativos</div>
                    <div className="sim-kpi-value">{resumo.total}</div>
                </div>
                <div className="sim-kpi">
                    <div className="sim-kpi-label">Com data de resgate</div>
                    <div className="sim-kpi-value">{resumo.comDataResgate}</div>
                </div>
                <div className="sim-kpi">
                    <div className="sim-kpi-label">Liquidez no vencimento</div>
                    <div className="sim-kpi-value">{resumo.semDataResgate}</div>
                </div>
            </div>

            <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                <div className="sim-card-title">Novo título RF</div>
                <div className="sim-form">
                    <div>
                        <label className="pg-select-label">Código</label>
                        <input className="sim-input" value={cdTitulo} onChange={e => setCdTitulo(e.target.value)} placeholder="Ex.: CDB_2028_A" />
                    </div>
                    <div>
                        <label className="pg-select-label">Nome</label>
                        <input className="sim-input" value={nmTitulo} onChange={e => setNmTitulo(e.target.value)} placeholder="Opcional" />
                    </div>
                    <div>
                        <label className="pg-select-label">Ativo vinculado</label>
                        <select className="sim-select" value={idAtivo ?? ''} onChange={e => setIdAtivo(e.target.value ? Number(e.target.value) : null)}>
                            <option value="">— opcional —</option>
                            {(ativos ?? []).map(a => (
                                <option key={a.ID_ATIVO} value={a.ID_ATIVO}>{a.CD_ATIVO}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="pg-select-label">Data vencimento</label>
                        <input className="sim-input" type="date" value={dtVencimento} onChange={e => setDtVencimento(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Data resgate (opcional)</label>
                        <input className="sim-input" type="date" value={dtResgate} onChange={e => setDtResgate(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Taxa contratada (%)</label>
                        <input className="sim-input" type="number" step="0.0001" value={txContratada} onChange={e => setTxContratada(e.target.value)} />
                    </div>
                    <div>
                        <button className="sim-btn" onClick={onCriarTitulo} disabled={criarTitulo.isPending || !cdTitulo.trim()}>
                            {criarTitulo.isPending ? 'Salvando…' : 'Cadastrar título RF'}
                        </button>
                    </div>
                </div>
            </div>

            {titulosQuery.isLoading && <div className="pg-loading"><i className="fas fa-circle-notch fa-spin" /> Carregando títulos RF…</div>}
            {titulosQuery.error && <div className="pg-error"><i className="fas fa-triangle-exclamation" /> {(titulosQuery.error as Error).message}</div>}

            {!titulosQuery.isLoading && !titulosQuery.error && (
                <div className="sim-card">
                    <div className="sim-card-title">Títulos cadastrados</div>
                    <div className="sim-table-wrap">
                        <table className="sim-table">
                            <thead>
                                <tr>
                                    <th>Código</th>
                                    <th>Nome</th>
                                    <th>Ativo</th>
                                    <th>Vencimento</th>
                                    <th>Resgate</th>
                                    <th>Liquidez</th>
                                    <th>Taxa (%)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {titulos.length === 0 && (
                                    <tr>
                                        <td colSpan={7} style={{ color: 'var(--color-text-muted)' }}>
                                            Nenhum título RF cadastrado.
                                        </td>
                                    </tr>
                                )}
                                {titulos.map(item => (
                                    <tr key={item.ID_TITULO}>
                                        <td>{item.CD_TITULO}</td>
                                        <td>{item.NM_TITULO ?? '—'}</td>
                                        <td>{item.CD_ATIVO ?? '—'}</td>
                                        <td>{item.DT_VENCIMENTO}</td>
                                        <td>{item.DT_RESGATE ?? '—'}</td>
                                        <td>{item.DT_RESGATE ? `Data fixa (${item.DT_RESGATE})` : `Data fixa (${item.DT_VENCIMENTO})`}</td>
                                        <td>{item.VL_TAXA_CONTRATADA == null ? '—' : formatNumero(item.VL_TAXA_CONTRATADA, 4)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
