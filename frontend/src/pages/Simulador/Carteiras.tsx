import { useMemo, useState } from 'react';
import {
    useSimPortfolios,
    useCreateSimPortfolio,
    useDeleteSimPortfolio,
    useSimFundos,
    useCreateSimFundo,
    useSimTitulares,
    useCreateSimTitular,
    useSimCorretoras,
    useCreateSimCorretora,
} from '@/hooks/useSimulador';
import './Simulador.css';

function hojeISO() {
    return new Date().toISOString().slice(0, 10);
}

export default function SimuladorCarteiras() {
    const { data, isLoading, error } = useSimPortfolios();
    const { data: fundos } = useSimFundos();
    const { data: titulares } = useSimTitulares();
    const { data: corretoras } = useSimCorretoras();

    const createMutation = useCreateSimPortfolio();
    const deleteMutation = useDeleteSimPortfolio();
    const createFundoMutation = useCreateSimFundo();
    const createTitularMutation = useCreateSimTitular();
    const createCorretoraMutation = useCreateSimCorretora();

    const [nome, setNome] = useState('Carteira Simulada 1');
    const [dtInicio, setDtInicio] = useState(hojeISO());
    const [benchmark, setBenchmark] = useState('CDI');
    const [moeda, setMoeda] = useState('BRL');
    const [idFundo, setIdFundo] = useState<number | null>(null);
    const [idTitular, setIdTitular] = useState<number | null>(null);
    const [idCorretora, setIdCorretora] = useState<number | null>(null);
    const [contaRef, setContaRef] = useState('');

    const [novoFundo, setNovoFundo] = useState('');
    const [novoTitular, setNovoTitular] = useState('');
    const [novaCorretora, setNovaCorretora] = useState('');

    const portfolios = data ?? [];
    const fundosList = fundos ?? [];
    const titularesList = titulares ?? [];
    const corretorasList = corretoras ?? [];

    const ativosCount = useMemo(
        () => portfolios.filter(p => Number(p.ST_ATIVO ?? 1) === 1).length,
        [portfolios],
    );

    async function onCreate() {
        if (!nome.trim()) return;
        await createMutation.mutateAsync({
            NM_PORTFOLIO: nome.trim(),
            DT_INICIO: dtInicio,
            BENCHMARK: benchmark || null,
            MOEDA_BASE: moeda || 'BRL',
            ST_ATIVO: 1,
            ID_FUNDO: idFundo,
            ID_TITULAR: idTitular,
            ID_CORRETORA: idCorretora,
            CONTA_REF: contaRef || null,
        });
    }

    async function onCreateFundo() {
        if (!novoFundo.trim()) return;
        const id = await createFundoMutation.mutateAsync({
            NM_FUNDO: novoFundo.trim(),
            BENCHMARK: benchmark || null,
            MOEDA_BASE: moeda || 'BRL',
            ST_ATIVO: 1,
        });
        setIdFundo(id);
        setNovoFundo('');
    }

    async function onCreateTitular() {
        if (!novoTitular.trim()) return;
        const id = await createTitularMutation.mutateAsync({
            NM_TITULAR: novoTitular.trim(),
            ST_ATIVO: 1,
        });
        setIdTitular(id);
        setNovoTitular('');
    }

    async function onCreateCorretora() {
        if (!novaCorretora.trim()) return;
        const id = await createCorretoraMutation.mutateAsync({
            NM_CORRETORA: novaCorretora.trim(),
            CD_CORRETORA: novaCorretora.trim().toUpperCase(),
            ST_ATIVO: 1,
        });
        setIdCorretora(id);
        setNovaCorretora('');
    }

    async function onDeletePortfolio(portfolioId: number) {
        const ok = window.confirm('Excluir carteira e todas as operações dela?');
        if (!ok) return;
        await deleteMutation.mutateAsync(portfolioId);
    }

    return (
        <div className="pg-page">
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon"><i className="fas fa-wallet" /></div>
                    <div className="pg-header-text">
                        <h1>Carteiras Simuladas</h1>
                        <p>Criação e gestão de carteiras para testes.</p>
                    </div>
                </div>
                <div className="pg-header-meta">
                    Total: <strong>{portfolios.length}</strong><br />
                    Ativas: <strong>{ativosCount}</strong>
                </div>
            </div>

            <div className="sim-card">
                <div className="sim-card-title">Nova carteira</div>
                <div className="sim-form">
                    <div>
                        <label className="pg-select-label">Nome</label>
                        <input className="sim-input" value={nome} onChange={e => setNome(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Data início</label>
                        <input className="sim-input" type="date" value={dtInicio} onChange={e => setDtInicio(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Benchmark</label>
                        <input className="sim-input" value={benchmark} onChange={e => setBenchmark(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Moeda base</label>
                        <input className="sim-input" value={moeda} onChange={e => setMoeda(e.target.value.toUpperCase())} />
                    </div>
                    <div>
                        <label className="pg-select-label">Fundo</label>
                        <select className="sim-select" value={idFundo ?? ''} onChange={e => setIdFundo(e.target.value ? Number(e.target.value) : null)}>
                            <option value="">— automático —</option>
                            {fundosList.map(f => (
                                <option key={f.ID_FUNDO} value={f.ID_FUNDO}>{f.NM_FUNDO}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="pg-select-label">Titular</label>
                        <select className="sim-select" value={idTitular ?? ''} onChange={e => setIdTitular(e.target.value ? Number(e.target.value) : null)}>
                            <option value="">— legado —</option>
                            {titularesList.map(t => (
                                <option key={t.ID_TITULAR} value={t.ID_TITULAR}>{t.NM_TITULAR}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="pg-select-label">Corretora</label>
                        <select className="sim-select" value={idCorretora ?? ''} onChange={e => setIdCorretora(e.target.value ? Number(e.target.value) : null)}>
                            <option value="">— legado —</option>
                            {corretorasList.map(c => (
                                <option key={c.ID_CORRETORA} value={c.ID_CORRETORA}>{c.NM_CORRETORA}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="pg-select-label">Conta ref</label>
                        <input className="sim-input" value={contaRef} onChange={e => setContaRef(e.target.value)} placeholder="Opcional" />
                    </div>
                    <div>
                        <button className="sim-btn" onClick={onCreate} disabled={createMutation.isPending}>
                            {createMutation.isPending ? 'Criando…' : 'Criar carteira'}
                        </button>
                    </div>
                </div>
            </div>

            <div className="sim-card">
                <div className="sim-card-title">Cadastros base</div>
                <div className="sim-form">
                    <div>
                        <label className="pg-select-label">Novo fundo</label>
                        <input className="sim-input" value={novoFundo} onChange={e => setNovoFundo(e.target.value)} placeholder="Ex: FUNDINHO LONG BIAS" />
                    </div>
                    <div>
                        <button className="sim-btn" onClick={onCreateFundo} disabled={createFundoMutation.isPending}>
                            {createFundoMutation.isPending ? 'Criando…' : 'Criar fundo'}
                        </button>
                    </div>

                    <div>
                        <label className="pg-select-label">Novo titular</label>
                        <input className="sim-input" value={novoTitular} onChange={e => setNovoTitular(e.target.value)} placeholder="Ex: Matheus" />
                    </div>
                    <div>
                        <button className="sim-btn" onClick={onCreateTitular} disabled={createTitularMutation.isPending}>
                            {createTitularMutation.isPending ? 'Criando…' : 'Criar titular'}
                        </button>
                    </div>

                    <div>
                        <label className="pg-select-label">Nova corretora</label>
                        <input className="sim-input" value={novaCorretora} onChange={e => setNovaCorretora(e.target.value)} placeholder="Ex: BTG" />
                    </div>
                    <div>
                        <button className="sim-btn" onClick={onCreateCorretora} disabled={createCorretoraMutation.isPending}>
                            {createCorretoraMutation.isPending ? 'Criando…' : 'Criar corretora'}
                        </button>
                    </div>
                </div>
            </div>

            {isLoading && <div className="pg-loading"><i className="fas fa-circle-notch fa-spin" /> Carregando carteiras…</div>}
            {error && <div className="pg-error"><i className="fas fa-triangle-exclamation" /> {(error as Error).message}</div>}

            {!isLoading && !error && (
                <div className="sim-table-wrap">
                    <table className="sim-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Nome</th>
                                <th>Início</th>
                                <th>Fundo</th>
                                <th>Titular</th>
                                <th>Corretora</th>
                                <th>Benchmark</th>
                                <th>Moeda</th>
                                <th>Conta</th>
                                <th>Status</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            {portfolios.map(p => (
                                <tr key={p.ID_PORTFOLIO}>
                                    <td>{p.ID_PORTFOLIO}</td>
                                    <td>{p.NM_PORTFOLIO}</td>
                                    <td>{p.DT_INICIO}</td>
                                    <td>{p.NM_FUNDO ?? '—'}</td>
                                    <td>{p.NM_TITULAR ?? '—'}</td>
                                    <td>{p.NM_CORRETORA ?? '—'}</td>
                                    <td>{p.BENCHMARK ?? '—'}</td>
                                    <td>{p.MOEDA_BASE ?? 'BRL'}</td>
                                    <td>{p.CONTA_REF ?? '—'}</td>
                                    <td>{Number(p.ST_ATIVO ?? 1) === 1 ? 'Ativa' : 'Inativa'}</td>
                                    <td>
                                        <button
                                            className="sim-btn sim-btn--danger"
                                            onClick={() => onDeletePortfolio(p.ID_PORTFOLIO)}
                                            disabled={
                                                createMutation.isPending ||
                                                deleteMutation.isPending ||
                                                createFundoMutation.isPending ||
                                                createTitularMutation.isPending ||
                                                createCorretoraMutation.isPending
                                            }
                                        >
                                            Excluir
                                        </button>
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
