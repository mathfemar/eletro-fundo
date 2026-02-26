import { useMemo, useState } from 'react';
import { useSetupSimFundo, useSimTitulares, useCreateSimTitular } from '@/hooks/useSimulador';
import './Simulador.css';

function hojeISO() {
    return new Date().toISOString().slice(0, 10);
}

export default function SimuladorFundosCadastro() {
    const setupFundo = useSetupSimFundo();
    const { data: titulares } = useSimTitulares();
    const createTitular = useCreateSimTitular();

    const [nome, setNome] = useState('');
    const [estrategia, setEstrategia] = useState('');
    const [benchmark, setBenchmark] = useState('CDI');
    const [moedaBase, setMoedaBase] = useState('BRL');
    const [dtInicio, setDtInicio] = useState(hojeISO());
    const [plInicial, setPlInicial] = useState('3000');
    const [cotaInicial, setCotaInicial] = useState('1');
    const [titularSelecionado, setTitularSelecionado] = useState<number | null>(null);
    const [aporteSelecionado, setAporteSelecionado] = useState('1000');
    const [novoCotista, setNovoCotista] = useState('');
    const [cotistasIniciais, setCotistasIniciais] = useState<Array<{ ID_TITULAR: number; NM_TITULAR: string; VL_APORTE: number }>>([]);

    const totalCotistas = useMemo(
        () => cotistasIniciais.reduce((acc, item) => acc + Number(item.VL_APORTE || 0), 0),
        [cotistasIniciais],
    );
    const diferencaPl = Number(plInicial || 0) - totalCotistas;

    function onAddCotistaInicial() {
        if (!titularSelecionado) return;
        const aporte = Number(aporteSelecionado);
        if (!Number.isFinite(aporte) || aporte <= 0) {
            window.alert('Aporte inicial deve ser maior que zero.');
            return;
        }
        if (cotistasIniciais.some(c => c.ID_TITULAR === titularSelecionado)) {
            window.alert('Cotista já adicionado na composição inicial.');
            return;
        }
        const nm = (titulares ?? []).find(t => t.ID_TITULAR === titularSelecionado)?.NM_TITULAR ?? `Cotista ${titularSelecionado}`;
        setCotistasIniciais(prev => [...prev, { ID_TITULAR: titularSelecionado, NM_TITULAR: nm, VL_APORTE: aporte }]);
    }

    function onRemoveCotistaInicial(idTitular: number) {
        setCotistasIniciais(prev => prev.filter(item => item.ID_TITULAR !== idTitular));
    }

    async function onCreateCotistaRapido() {
        if (!novoCotista.trim()) return;
        const id = await createTitular.mutateAsync({ NM_TITULAR: novoCotista.trim(), ST_ATIVO: 1 });
        setTitularSelecionado(id);
        setNovoCotista('');
    }

    async function onSalvar() {
        if (!nome.trim()) {
            window.alert('Informe o nome do fundo.');
            return;
        }

        const pl = Number(plInicial);
        const cota = Number(cotaInicial);

        if (!Number.isFinite(pl) || pl < 0) {
            window.alert('PL inicial deve ser zero ou maior.');
            return;
        }

        if (!Number.isFinite(cota) || cota <= 0) {
            window.alert('Cota inicial deve ser maior que zero.');
            return;
        }

        if (!Number.isFinite(pl) || pl <= 0) {
            window.alert('PL inicial deve ser maior que zero.');
            return;
        }

        if (cotistasIniciais.length === 0) {
            window.alert('Adicione ao menos um cotista inicial.');
            return;
        }

        if (Math.abs(diferencaPl) > 0.0001) {
            window.alert('A soma dos aportes dos cotistas precisa ser igual ao PL inicial.');
            return;
        }

        await setupFundo.mutateAsync({
            NM_FUNDO: nome.trim(),
            DS_ESTRATEGIA: estrategia || null,
            BENCHMARK: benchmark || null,
            MOEDA_BASE: moedaBase || 'BRL',
            ST_ATIVO: 1,
            DT_INICIO: dtInicio,
            VL_COTA_INICIAL: cota,
            COTISTAS_INICIAIS: cotistasIniciais.map(item => ({
                ID_TITULAR: item.ID_TITULAR,
                VL_APORTE: Number(item.VL_APORTE || 0),
            })),
        });

        setNome('');
        setEstrategia('');
        setPlInicial('3000');
        setCotaInicial('1');
        setCotistasIniciais([]);
    }

    return (
        <div className="pg-page">
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon"><i className="fas fa-file-circle-plus" /></div>
                    <div className="pg-header-text">
                        <h1>Cadastro de Fundo</h1>
                        <p>Crie o fundo com seed inicial de PL e cota para iniciar operações de forma consistente.</p>
                    </div>
                </div>
            </div>

            <div className="sim-card">
                <div className="sim-card-title">Dados do fundo</div>
                <div className="sim-form">
                    <div>
                        <label className="pg-select-label">Nome</label>
                        <input className="sim-input" value={nome} onChange={e => setNome(e.target.value)} placeholder="Ex: Fundinho Master" />
                    </div>
                    <div>
                        <label className="pg-select-label">Estratégia</label>
                        <input className="sim-input" value={estrategia} onChange={e => setEstrategia(e.target.value)} placeholder="Ex: Long Bias" />
                    </div>
                    <div>
                        <label className="pg-select-label">Benchmark</label>
                        <input className="sim-input" value={benchmark} onChange={e => setBenchmark(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Moeda base</label>
                        <input className="sim-input" value={moedaBase} onChange={e => setMoedaBase(e.target.value.toUpperCase())} />
                    </div>
                    <div>
                        <label className="pg-select-label">Data de início</label>
                        <input className="sim-input" type="date" value={dtInicio} onChange={e => setDtInicio(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">PL inicial</label>
                        <input className="sim-input" type="number" min="0" step="0.01" value={plInicial} onChange={e => setPlInicial(e.target.value)} />
                    </div>
                    <div>
                        <label className="pg-select-label">Cota inicial</label>
                        <input className="sim-input" type="number" min="0.000001" step="0.000001" value={cotaInicial} onChange={e => setCotaInicial(e.target.value)} />
                    </div>
                </div>
            </div>

            <div className="sim-card" style={{ marginTop: '0.8rem' }}>
                <div className="sim-card-title">Cotistas iniciais (obrigatório)</div>
                <div className="sim-form">
                    <div>
                        <label className="pg-select-label">Cotista</label>
                        <select className="sim-select" value={titularSelecionado ?? ''} onChange={e => setTitularSelecionado(e.target.value ? Number(e.target.value) : null)}>
                            <option value="">— selecione —</option>
                            {(titulares ?? []).map(t => <option key={t.ID_TITULAR} value={t.ID_TITULAR}>{t.NM_TITULAR}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="pg-select-label">Aporte</label>
                        <input className="sim-input" type="number" step="0.01" value={aporteSelecionado} onChange={e => setAporteSelecionado(e.target.value)} />
                    </div>
                    <div>
                        <button className="sim-btn sim-btn--neutral" onClick={onAddCotistaInicial} disabled={!titularSelecionado}>
                            Adicionar cotista
                        </button>
                    </div>

                    <div>
                        <label className="pg-select-label">Novo cotista</label>
                        <input className="sim-input" value={novoCotista} onChange={e => setNovoCotista(e.target.value)} placeholder="Cadastro rápido" />
                    </div>
                    <div>
                        <button className="sim-btn sim-btn--neutral" onClick={onCreateCotistaRapido} disabled={createTitular.isPending || !novoCotista.trim()}>
                            {createTitular.isPending ? 'Criando…' : 'Criar cotista'}
                        </button>
                    </div>
                </div>

                {cotistasIniciais.length > 0 && (
                    <div className="sim-table-wrap" style={{ marginTop: '0.8rem' }}>
                        <table className="sim-table">
                            <thead>
                                <tr>
                                    <th>Cotista</th>
                                    <th>Aporte</th>
                                    <th>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                {cotistasIniciais.map(item => (
                                    <tr key={item.ID_TITULAR}>
                                        <td>{item.NM_TITULAR}</td>
                                        <td>
                                            <input
                                                className="sim-input"
                                                type="number"
                                                step="0.01"
                                                value={item.VL_APORTE}
                                                onChange={e => setCotistasIniciais(prev => prev.map(p => p.ID_TITULAR === item.ID_TITULAR ? { ...p, VL_APORTE: Number(e.target.value || 0) } : p))}
                                            />
                                        </td>
                                        <td>
                                            <button className="sim-btn sim-btn--danger" onClick={() => onRemoveCotistaInicial(item.ID_TITULAR)}>
                                                Remover
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                <p style={{ marginTop: '0.8rem', marginBottom: 0, color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                    PL inicial informado: <strong>{Number(plInicial || 0).toFixed(2)}</strong> | Soma dos cotistas: <strong>{totalCotistas.toFixed(2)}</strong> | Diferença: <strong>{diferencaPl.toFixed(2)}</strong>
                </p>

                <div className="sim-row-actions" style={{ marginTop: '0.8rem' }}>
                    <button className="sim-btn" onClick={onSalvar} disabled={setupFundo.isPending || cotistasIniciais.length === 0 || Math.abs(diferencaPl) > 0.0001}>
                        {setupFundo.isPending ? 'Salvando…' : 'Criar fundo (setup completo)'}
                    </button>
                </div>
            </div>

            <div className="sim-card" style={{ marginTop: '0.8rem' }}>
                <div className="sim-card-title">Regra operacional</div>
                <p style={{ margin: 0, color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', lineHeight: 1.6 }}>
                    A criação do fundo exige composição inicial de cotistas. A soma dos aportes deve ser exatamente igual ao PL inicial.
                </p>
            </div>
        </div>
    );
}
