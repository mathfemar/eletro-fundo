import { useMemo, useState } from 'react';
import {
    useSimFundos,
    useSimTitulares,
    useSimFundoLiquidezOpcoes,
    usePostSimAtivoLiquidez,
    usePostSimFundFluxoCapital,
    usePostSimResgateSolicitacao,
    useSimResgateSolicitacoes,
    usePostSimResgatePlano,
    useSimResgatePlanos,
    usePostSimResgateExecutarPlano,
    usePostSimResgateOverridePlano,
    useSimResgateEventosPlano,
} from '@/hooks/useSimulador';
import { formatNumero } from '@/utils/formatBR';
import './Simulador.css';

function hojeISO() {
    return new Date().toISOString().slice(0, 10);
}

type PlanoItemDraft = {
    ID_ATIVO: number;
    CD_ATIVO: string;
    VL_LIQUIDAR: string;
    NR_DIAS_LIQUIDEZ: number;
};

export default function SimuladorResgates() {
    const { data: fundos } = useSimFundos();
    const { data: titulares } = useSimTitulares();
    const [modoTela, setModoTela] = useState<'APORTE' | 'RESGATE'>('RESGATE');

    const [fundoAporteId, setFundoAporteId] = useState<number | null>(null);
    const [titularAporteId, setTitularAporteId] = useState<number | null>(null);
    const [dtAporte, setDtAporte] = useState(hojeISO());
    const [vlAporte, setVlAporte] = useState('0');
    const [obsAporte, setObsAporte] = useState('');

    const [fundoId, setFundoId] = useState<number | null>(null);
    const [titularId, setTitularId] = useState<number | null>(null);
    const [dtSolicitacao, setDtSolicitacao] = useState(hojeISO());
    const [vlResgate, setVlResgate] = useState('0');
    const [obs, setObs] = useState('');

    const [ativoSelecionado, setAtivoSelecionado] = useState<number | null>(null);
    const [vlLiquidarDraft, setVlLiquidarDraft] = useState('0');
    const [itensPlano, setItensPlano] = useState<PlanoItemDraft[]>([]);
    const [solicitacaoSelecionada, setSolicitacaoSelecionada] = useState<number | null>(null);
    const [planoSelecionadoId, setPlanoSelecionadoId] = useState<number | null>(null);
    const [dtExecucao, setDtExecucao] = useState(hojeISO());
    const [vlExecucao, setVlExecucao] = useState('');
    const [obsExecucao, setObsExecucao] = useState('');
    const [justificativaOverride, setJustificativaOverride] = useState('');
    const [vlOverride, setVlOverride] = useState('0');

    const liquidezOpcoesQuery = useSimFundoLiquidezOpcoes(fundoId);
    const solicitacoesQuery = useSimResgateSolicitacoes(fundoId);
    const planosQuery = useSimResgatePlanos(solicitacaoSelecionada);

    const salvarLiquidez = usePostSimAtivoLiquidez();
    const registrarFluxo = usePostSimFundFluxoCapital();
    const criarSolicitacao = usePostSimResgateSolicitacao();
    const criarPlano = usePostSimResgatePlano();
    const executarPlano = usePostSimResgateExecutarPlano();
    const overridePlano = usePostSimResgateOverridePlano();

    const opcoes = liquidezOpcoesQuery.data ?? [];
    const solicitacoes = solicitacoesQuery.data ?? [];
    const planos = planosQuery.data ?? [];
    const eventosPlanoQuery = useSimResgateEventosPlano(planoSelecionadoId);

    const solicitacaoAtual = useMemo(
        () => solicitacoes.find(item => item.ID_SOLICITACAO === solicitacaoSelecionada) ?? null,
        [solicitacoes, solicitacaoSelecionada],
    );

    const totalPlano = useMemo(
        () => itensPlano.reduce((acc, item) => acc + Number(item.VL_LIQUIDAR || 0), 0),
        [itensPlano],
    );

    const planoSelecionado = useMemo(
        () => planos.find(p => p.ID_PLANO === planoSelecionadoId) ?? null,
        [planos, planoSelecionadoId],
    );

    const saldoPlanoSelecionado = useMemo(() => {
        if (!planoSelecionado) return 0;
        const planejado = Number(planoSelecionado.VL_TOTAL_PLANEJADO ?? 0);
        const executado = Number(planoSelecionado.VL_TOTAL_EXECUTADO ?? 0);
        return Math.max(planejado - executado, 0);
    }, [planoSelecionado]);

    function onAdicionarItemPlano() {
        if (!ativoSelecionado) return;
        const ativo = opcoes.find(item => item.ID_ATIVO === ativoSelecionado);
        if (!ativo) return;
        const valor = Number(vlLiquidarDraft);
        if (!Number.isFinite(valor) || valor <= 0) {
            window.alert('Informe um valor válido para liquidar.');
            return;
        }
        if (itensPlano.some(item => item.ID_ATIVO === ativoSelecionado)) {
            window.alert('Ativo já adicionado no plano. Edite o valor existente.');
            return;
        }

        setItensPlano(prev => [
            ...prev,
            {
                ID_ATIVO: ativo.ID_ATIVO,
                CD_ATIVO: ativo.CD_ATIVO,
                VL_LIQUIDAR: String(valor),
                NR_DIAS_LIQUIDEZ: ativo.NR_DIAS_LIQUIDEZ,
            },
        ]);
    }

    function onRemoverItemPlano(idAtivo: number) {
        setItensPlano(prev => prev.filter(item => item.ID_ATIVO !== idAtivo));
    }

    async function onSalvarLiquidezAtivo(idAtivo: number, dias: number) {
        await salvarLiquidez.mutateAsync({
            ID_ATIVO: idAtivo,
            NR_DIAS_LIQUIDEZ: Math.max(0, Number(dias || 0)),
            ST_ATIVO: 1,
        });
    }

    async function onCriarSolicitacao() {
        if (!fundoId) return;
        const valor = Number(vlResgate);
        if (!Number.isFinite(valor) || valor <= 0) {
            window.alert('Informe um valor de resgate maior que zero.');
            return;
        }

        const id = await criarSolicitacao.mutateAsync({
            ID_FUNDO: fundoId,
            ID_TITULAR: titularId,
            DT_SOLICITACAO: dtSolicitacao,
            VL_RESGATE: valor,
            DS_OBSERVACAO: obs || null,
        });
        setSolicitacaoSelecionada(id);
        setObs('');
    }

    async function onCriarPlano() {
        if (!solicitacaoSelecionada) {
            window.alert('Selecione uma solicitação de resgate.');
            return;
        }
        if (itensPlano.length === 0) {
            window.alert('Adicione ao menos um item no plano.');
            return;
        }

        await criarPlano.mutateAsync({
            ID_SOLICITACAO: solicitacaoSelecionada,
            CD_METODO: 'MANUAL_GESTOR',
            ST_STATUS: 'RASCUNHO',
            items: itensPlano.map(item => ({
                ID_ATIVO: item.ID_ATIVO,
                VL_LIQUIDAR: Number(item.VL_LIQUIDAR || 0),
                NR_DIAS_LIQUIDEZ: Number(item.NR_DIAS_LIQUIDEZ || 0),
            })),
        });

        setItensPlano([]);
    }

    async function onRegistrarAporte() {
        if (!fundoAporteId) return;
        const valor = Number(vlAporte);
        if (!Number.isFinite(valor) || valor <= 0) {
            window.alert('Informe um valor de aporte maior que zero.');
            return;
        }

        await registrarFluxo.mutateAsync({
            ID_FUNDO: fundoAporteId,
            ID_TITULAR: titularAporteId,
            DT_REFERENCIA: dtAporte,
            TP_FLUXO: 'APORTE',
            VL_FLUXO: valor,
            OBSERVACAO: obsAporte || null,
        });

        setVlAporte('0');
        setObsAporte('');
    }

    async function onExecutarPlano() {
        if (!planoSelecionadoId) {
            window.alert('Selecione um plano para executar.');
            return;
        }

        const payload = {
            DT_REFERENCIA: dtExecucao,
            VL_EXECUTADO: vlExecucao.trim() ? Number(vlExecucao) : undefined,
            DS_OBSERVACAO: obsExecucao || null,
        };

        await executarPlano.mutateAsync({ planoId: planoSelecionadoId, payload });
        setVlExecucao('');
        setObsExecucao('');
    }

    async function onRegistrarOverride() {
        if (!planoSelecionadoId) {
            window.alert('Selecione um plano para registrar override.');
            return;
        }
        if (!justificativaOverride.trim()) {
            window.alert('Informe a justificativa do override.');
            return;
        }

        const ok = window.confirm('Confirmar override de MTM com justificativa auditável?');
        if (!ok) return;

        await overridePlano.mutateAsync({
            planoId: planoSelecionadoId,
            payload: {
                DT_REFERENCIA: dtExecucao,
                DS_JUSTIFICATIVA: justificativaOverride.trim(),
                VL_EVENTO: Number(vlOverride || 0),
            },
        });

        setJustificativaOverride('');
        setVlOverride('0');
    }

    return (
        <div className="pg-page">
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon"><i className="fas fa-hand-holding-dollar" /></div>
                    <div className="pg-header-text">
                        <h1>Aportes/Resgates</h1>
                        <p>
                            {modoTela === 'RESGATE'
                                ? 'O gestor escolhe manualmente quais ativos liquidar; o sistema valida e projeta liquidez por ativo.'
                                : 'Registro de aporte de capital por fundo e cotista.'}
                        </p>
                    </div>
                </div>
            </div>

            <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                <div className="sim-card-title">Tipo de fluxo</div>
                <div className="sim-form">
                    <div>
                        <label className="pg-select-label">Selecionar</label>
                        <select className="sim-select" value={modoTela} onChange={e => setModoTela(e.target.value as 'APORTE' | 'RESGATE')}>
                            <option value="APORTE">Aportes</option>
                            <option value="RESGATE">Resgates</option>
                        </select>
                    </div>
                </div>
            </div>

            {modoTela === 'APORTE' ? (
                <div className="sim-card">
                    <div className="sim-card-title">Registro de aporte</div>
                    <div className="sim-form">
                        <div>
                            <label className="pg-select-label">Fundo</label>
                            <select className="sim-select" value={fundoAporteId ?? ''} onChange={e => setFundoAporteId(e.target.value ? Number(e.target.value) : null)}>
                                <option value="">— selecione —</option>
                                {(fundos ?? []).map(f => (
                                    <option key={f.ID_FUNDO} value={f.ID_FUNDO}>{f.NM_FUNDO}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="pg-select-label">Cotista (opcional)</label>
                            <select className="sim-select" value={titularAporteId ?? ''} onChange={e => setTitularAporteId(e.target.value ? Number(e.target.value) : null)}>
                                <option value="">— aporte geral —</option>
                                {(titulares ?? []).map(t => (
                                    <option key={t.ID_TITULAR} value={t.ID_TITULAR}>{t.NM_TITULAR}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="pg-select-label">Data</label>
                            <input className="sim-input" type="date" value={dtAporte} onChange={e => setDtAporte(e.target.value)} />
                        </div>
                        <div>
                            <label className="pg-select-label">Valor aporte</label>
                            <input className="sim-input" type="number" step="0.01" value={vlAporte} onChange={e => setVlAporte(e.target.value)} />
                        </div>
                        <div>
                            <label className="pg-select-label">Obs</label>
                            <input className="sim-input" value={obsAporte} onChange={e => setObsAporte(e.target.value)} placeholder="Opcional" />
                        </div>
                        <div>
                            <button className="sim-btn" onClick={onRegistrarAporte} disabled={!fundoAporteId || registrarFluxo.isPending}>
                                {registrarFluxo.isPending ? 'Registrando…' : 'Registrar aporte'}
                            </button>
                        </div>
                    </div>
                </div>
            ) : (
                <>
                    <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                        <div className="sim-card-title">Solicitação de resgate</div>
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
                            <div>
                                <label className="pg-select-label">Cotista (opcional)</label>
                                <select className="sim-select" value={titularId ?? ''} onChange={e => setTitularId(e.target.value ? Number(e.target.value) : null)}>
                                    <option value="">— resgate geral —</option>
                                    {(titulares ?? []).map(t => (
                                        <option key={t.ID_TITULAR} value={t.ID_TITULAR}>{t.NM_TITULAR}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="pg-select-label">Data solicitação</label>
                                <input className="sim-input" type="date" value={dtSolicitacao} onChange={e => setDtSolicitacao(e.target.value)} />
                            </div>
                            <div>
                                <label className="pg-select-label">Valor resgate</label>
                                <input className="sim-input" type="number" step="0.01" value={vlResgate} onChange={e => setVlResgate(e.target.value)} />
                            </div>
                            <div>
                                <label className="pg-select-label">Obs</label>
                                <input className="sim-input" value={obs} onChange={e => setObs(e.target.value)} placeholder="Opcional" />
                            </div>
                            <div>
                                <button className="sim-btn" onClick={onCriarSolicitacao} disabled={!fundoId || criarSolicitacao.isPending}>
                                    {criarSolicitacao.isPending ? 'Criando…' : 'Criar solicitação'}
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                        <div className="sim-card-title">Opções de liquidação por ativo (fundo)</div>
                        {!fundoId && <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>Selecione um fundo para carregar as opções.</p>}
                        {fundoId && (
                            <div className="sim-table-wrap">
                                <table className="sim-table">
                                    <thead>
                                        <tr>
                                            <th>Ativo</th>
                                            <th>Valor Mercado</th>
                                            <th>Qtd</th>
                                            <th>Dias de liquidez</th>
                                            <th>Ações</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {opcoes.map(item => (
                                            <tr key={item.ID_ATIVO}>
                                                <td>{item.CD_ATIVO}</td>
                                                <td>{formatNumero(item.VALOR_MERCADO, 2)}</td>
                                                <td>{formatNumero(item.QTD_LIQ, 4)}</td>
                                                <td>
                                                    <input
                                                        className="sim-input"
                                                        type="number"
                                                        min="0"
                                                        style={{ width: 100 }}
                                                        defaultValue={item.NR_DIAS_LIQUIDEZ}
                                                        onBlur={e => onSalvarLiquidezAtivo(item.ID_ATIVO, Number(e.target.value))}
                                                    />
                                                </td>
                                                <td>
                                                    <button
                                                        className="sim-btn sim-btn--neutral"
                                                        onClick={() => setAtivoSelecionado(item.ID_ATIVO)}
                                                    >
                                                        Selecionar
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>

                    <div className="sim-card" style={{ marginBottom: '0.8rem' }}>
                        <div className="sim-card-title">Plano manual de liquidação</div>
                        <div className="sim-form">
                            <div>
                                <label className="pg-select-label">Solicitação</label>
                                <select
                                    className="sim-select"
                                    value={solicitacaoSelecionada ?? ''}
                                    onChange={e => {
                                        setSolicitacaoSelecionada(e.target.value ? Number(e.target.value) : null);
                                        setPlanoSelecionadoId(null);
                                    }}
                                >
                                    <option value="">— selecione —</option>
                                    {solicitacoes.map(item => (
                                        <option key={item.ID_SOLICITACAO} value={item.ID_SOLICITACAO}>
                                            #{item.ID_SOLICITACAO} {item.DT_SOLICITACAO} {formatNumero(item.VL_RESGATE, 2)} ({item.ST_STATUS})
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="pg-select-label">Ativo</label>
                                <select className="sim-select" value={ativoSelecionado ?? ''} onChange={e => setAtivoSelecionado(e.target.value ? Number(e.target.value) : null)}>
                                    <option value="">— selecione —</option>
                                    {opcoes.map(item => (
                                        <option key={item.ID_ATIVO} value={item.ID_ATIVO}>
                                            {item.CD_ATIVO} (liq D+{item.NR_DIAS_LIQUIDEZ})
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="pg-select-label">Valor a liquidar</label>
                                <input className="sim-input" type="number" step="0.01" value={vlLiquidarDraft} onChange={e => setVlLiquidarDraft(e.target.value)} />
                            </div>
                            <div>
                                <button className="sim-btn sim-btn--neutral" onClick={onAdicionarItemPlano} disabled={!ativoSelecionado}>
                                    Adicionar item
                                </button>
                            </div>
                            <div>
                                <button className="sim-btn" onClick={onCriarPlano} disabled={!solicitacaoSelecionada || criarPlano.isPending}>
                                    {criarPlano.isPending ? 'Salvando plano…' : 'Salvar plano manual'}
                                </button>
                            </div>
                        </div>

                        {solicitacaoAtual && (
                            <p style={{ marginTop: '0.6rem', marginBottom: 0, color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                                Solicitado: {formatNumero(solicitacaoAtual.VL_RESGATE, 2)} | Planejado atual: {formatNumero(totalPlano, 2)}
                            </p>
                        )}

                        {itensPlano.length > 0 && (
                            <div className="sim-table-wrap" style={{ marginTop: '0.6rem' }}>
                                <table className="sim-table">
                                    <thead>
                                        <tr>
                                            <th>Ativo</th>
                                            <th>Valor</th>
                                            <th>Dias Liquidez</th>
                                            <th>Ações</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {itensPlano.map(item => (
                                            <tr key={item.ID_ATIVO}>
                                                <td>{item.CD_ATIVO}</td>
                                                <td>
                                                    <input
                                                        className="sim-input"
                                                        type="number"
                                                        step="0.01"
                                                        value={item.VL_LIQUIDAR}
                                                        onChange={e => setItensPlano(prev => prev.map(p => p.ID_ATIVO === item.ID_ATIVO ? { ...p, VL_LIQUIDAR: e.target.value } : p))}
                                                    />
                                                </td>
                                                <td>
                                                    <input
                                                        className="sim-input"
                                                        type="number"
                                                        min="0"
                                                        value={item.NR_DIAS_LIQUIDEZ}
                                                        onChange={e => setItensPlano(prev => prev.map(p => p.ID_ATIVO === item.ID_ATIVO ? { ...p, NR_DIAS_LIQUIDEZ: Number(e.target.value || 0) } : p))}
                                                    />
                                                </td>
                                                <td>
                                                    <button className="sim-btn sim-btn--danger" onClick={() => onRemoverItemPlano(item.ID_ATIVO)}>
                                                        Remover
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>

                    <div className="sim-card">
                        <div className="sim-card-title">Histórico de planos (solicitação selecionada)</div>
                        {!solicitacaoSelecionada && <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>Selecione uma solicitação para ver as revisões de plano.</p>}
                        {solicitacaoSelecionada && !planosQuery.isLoading && (
                            <div className="sim-table-wrap">
                                <table className="sim-table">
                                    <thead>
                                        <tr>
                                            <th>Plano</th>
                                            <th>Revisão</th>
                                            <th>Método</th>
                                            <th>Status</th>
                                            <th>Total</th>
                                            <th>Executado</th>
                                            <th>Ações</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {(planosQuery.data ?? []).map(p => (
                                            <tr key={p.ID_PLANO}>
                                                <td>#{p.ID_PLANO}</td>
                                                <td>{p.NR_REVISAO}</td>
                                                <td>{p.CD_METODO}</td>
                                                <td>{p.ST_STATUS}</td>
                                                <td>{formatNumero(p.VL_TOTAL_PLANEJADO ?? 0, 2)}</td>
                                                <td>{formatNumero(p.VL_TOTAL_EXECUTADO ?? 0, 2)}</td>
                                                <td>
                                                    <button className="sim-btn sim-btn--neutral" onClick={() => setPlanoSelecionadoId(p.ID_PLANO)}>
                                                        Selecionar
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>

                    <div className="sim-card" style={{ marginTop: '0.8rem' }}>
                        <div className="sim-card-title">Execução do plano selecionado</div>
                        {!planoSelecionadoId && <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>Selecione um plano no histórico para executar/registrar override.</p>}
                        {planoSelecionadoId && (
                            <>
                                <p style={{ marginTop: 0, color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                                    Plano #{planoSelecionadoId} | Saldo planejado: {formatNumero(saldoPlanoSelecionado, 2)}
                                </p>
                                <div className="sim-form" style={{ marginBottom: '0.6rem' }}>
                                    <div>
                                        <label className="pg-select-label">Data execução</label>
                                        <input className="sim-input" type="date" value={dtExecucao} onChange={e => setDtExecucao(e.target.value)} />
                                    </div>
                                    <div>
                                        <label className="pg-select-label">Valor execução (opcional)</label>
                                        <input className="sim-input" type="number" step="0.01" value={vlExecucao} onChange={e => setVlExecucao(e.target.value)} placeholder="Vazio = executar saldo" />
                                    </div>
                                    <div>
                                        <label className="pg-select-label">Obs execução</label>
                                        <input className="sim-input" value={obsExecucao} onChange={e => setObsExecucao(e.target.value)} placeholder="Opcional" />
                                    </div>
                                    <div>
                                        <button className="sim-btn" onClick={onExecutarPlano} disabled={executarPlano.isPending}>
                                            {executarPlano.isPending ? 'Executando…' : 'Executar resgate'}
                                        </button>
                                    </div>
                                </div>

                                <div className="sim-form" style={{ marginBottom: '0.6rem' }}>
                                    <div>
                                        <label className="pg-select-label">Justificativa override MTM</label>
                                        <input className="sim-input" value={justificativaOverride} onChange={e => setJustificativaOverride(e.target.value)} placeholder="Obrigatória" />
                                    </div>
                                    <div>
                                        <label className="pg-select-label">Valor override</label>
                                        <input className="sim-input" type="number" step="0.01" value={vlOverride} onChange={e => setVlOverride(e.target.value)} />
                                    </div>
                                    <div>
                                        <button className="sim-btn sim-btn--neutral" onClick={onRegistrarOverride} disabled={overridePlano.isPending}>
                                            {overridePlano.isPending ? 'Registrando…' : 'Registrar override'}
                                        </button>
                                    </div>
                                </div>

                                <div className="sim-table-wrap">
                                    <table className="sim-table">
                                        <thead>
                                            <tr>
                                                <th>Data</th>
                                                <th>Evento</th>
                                                <th>Valor</th>
                                                <th>Justificativa</th>
                                                <th>Obs</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {(eventosPlanoQuery.data ?? []).length === 0 && (
                                                <tr>
                                                    <td colSpan={5} style={{ color: 'var(--color-text-muted)' }}>Sem eventos para este plano.</td>
                                                </tr>
                                            )}
                                            {(eventosPlanoQuery.data ?? []).map(ev => (
                                                <tr key={ev.ID_EVENTO}>
                                                    <td>{ev.DT_REFERENCIA}</td>
                                                    <td>{ev.TP_EVENTO}</td>
                                                    <td>{formatNumero(ev.VL_EVENTO ?? 0, 2)}</td>
                                                    <td>{ev.DS_JUSTIFICATIVA ?? '—'}</td>
                                                    <td>{ev.DS_OBSERVACAO ?? '—'}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
