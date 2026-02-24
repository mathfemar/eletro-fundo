import { useState, useMemo, useEffect } from 'react';
import { useAtivos, useAtivosMeta, useCriarAtivo, useAtualizarAtivo } from '@/hooks/useAtivos';
import type { Ativo, AtivoInput } from '@/api/ativos';
import './Lista.css';

// ─── Helpers ──────────────────────────────────────────────────────────────────

type Mode = 'table' | 'edit' | 'new';

const EMPTY_FORM: AtivoInput = {
    CD_ATIVO: '', ID_TIPO_ATIVO: null, DT_EMISSAO: null, DT_VENCIMENTO: null,
    CD_SELIC: null, ID_SETOR_PAI: null, ID_SETOR_FILHO: null, MOEDA: null,
    PRECO_ONLINE: null, FATOR_PRECO: null, CALL_PUT: null, LOTE: null,
    CD_BBG: null, CD_YF: null, CD_FIGI: null, CD_ISIN: null, CD_CUSIP: null,
};

function ativoToForm(a: Ativo): AtivoInput {
    return {
        CD_ATIVO: a.CD_ATIVO,
        ID_TIPO_ATIVO: a.ID_TIPO_ATIVO,
        DT_EMISSAO: a.DT_EMISSAO,
        DT_VENCIMENTO: a.DT_VENCIMENTO,
        CD_SELIC: a.CD_SELIC,
        ID_SETOR_PAI: a.ID_SETOR_PAI,
        ID_SETOR_FILHO: a.ID_SETOR_FILHO,
        MOEDA: a.MOEDA,
        PRECO_ONLINE: a.PRECO_ONLINE,
        FATOR_PRECO: a.FATOR_PRECO,
        CALL_PUT: a.CALL_PUT,
        LOTE: a.LOTE,
        CD_BBG: a.CD_BBG,
        CD_YF: a.CD_YF,
        CD_FIGI: a.CD_FIGI,
        CD_ISIN: a.CD_ISIN,
        CD_CUSIP: a.CD_CUSIP,
    };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function FormField({
    label, children, hint,
}: {
    label: string;
    children: React.ReactNode;
    hint?: string;
}) {
    return (
        <div className="form-field">
            <label className="form-field-label">{label}</label>
            {children}
            {hint && <span className="form-field-hint">{hint}</span>}
        </div>
    );
}

function FormInput({
    value, onChange, placeholder, disabled, type = 'text',
}: {
    value: string | number | null;
    onChange: (v: string) => void;
    placeholder?: string;
    disabled?: boolean;
    type?: string;
}) {
    return (
        <input
            className="form-input"
            type={type}
            value={value ?? ''}
            onChange={e => onChange(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
        />
    );
}

function FormSelect({
    value, onChange, options, placeholder,
}: {
    value: number | string | null;
    onChange: (v: string) => void;
    options: { value: number | string; label: string }[];
    placeholder?: string;
}) {
    return (
        <div className="pg-select-wrap">
            <select
                className="pg-select form-select"
                value={value ?? ''}
                onChange={e => onChange(e.target.value)}
            >
                <option value="">{placeholder ?? '— selecione —'}</option>
                {options.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                ))}
            </select>
        </div>
    );
}

// ─── Formulário de cadastro/edição ────────────────────────────────────────────

function AtivoForm({
    mode,
    form,
    setForm,
    onSave,
    onCancel,
    saving,
    error,
}: {
    mode: 'edit' | 'new';
    form: AtivoInput;
    setForm: React.Dispatch<React.SetStateAction<AtivoInput>>;
    onSave: () => void;
    onCancel: () => void;
    saving: boolean;
    error: string | null;
}) {
    const { data: meta } = useAtivosMeta();

    const set = <K extends keyof AtivoInput>(field: K, raw: string) => {
        setForm(prev => {
            const numFields: (keyof AtivoInput)[] = ['ID_TIPO_ATIVO', 'ID_SETOR_PAI', 'ID_SETOR_FILHO', 'PRECO_ONLINE', 'FATOR_PRECO', 'LOTE'];
            if (numFields.includes(field)) {
                return { ...prev, [field]: raw === '' ? null : Number(raw) };
            }
            return { ...prev, [field]: raw === '' ? null : raw };
        });
    };

    const tipoOpts = (meta?.tipos ?? []).map(t => ({
        value: t.ID_TIPO_ATIVO,
        label: `${t.TIPO_ATIVO}${t.FL_CLASSE_RISCO ? ` — Risco: ${t.FL_CLASSE_RISCO}` : ''}`,
    }));
    const setorPaiOpts = (meta?.setores_pai ?? []).map(s => ({ value: s.ID_SETOR_PAI, label: s.SetorPai }));
    const setorFilhoOpts = (meta?.setores_filho ?? []).map(s => ({ value: s.ID_SETOR_FILHO, label: s.SetorFilho }));

    return (
        <div className="ativo-form-panel">
            {/* Cabeçalho do painel */}
            <div className="ativo-form-header">
                <div className="ativo-form-header-left">
                    <i className={mode === 'new' ? 'fas fa-plus-circle' : 'fas fa-pen'} />
                    <span>{mode === 'new' ? 'Novo Ativo' : `Editando: ${form.CD_ATIVO}`}</span>
                </div>
                <div className="ativo-form-actions">
                    <button className="btn btn-ghost" onClick={onCancel} disabled={saving}>
                        <i className="fas fa-times" /> Cancelar
                    </button>
                    <button className="btn btn-primary" onClick={onSave} disabled={saving}>
                        {saving
                            ? <><i className="fas fa-circle-notch fa-spin" /> Salvando…</>
                            : <><i className="fas fa-check" /> {mode === 'new' ? 'Criar Ativo' : 'Salvar'}</>
                        }
                    </button>
                </div>
            </div>

            {error && (
                <div className="ativo-form-error">
                    <i className="fas fa-triangle-exclamation" />
                    {error}
                </div>
            )}

            <div className="ativo-form-body">
                {/* ── Identificação ── */}
                <section className="form-section">
                    <h3 className="form-section-title">
                        <i className="fas fa-tag" /> Identificação
                    </h3>
                    <div className="form-grid">
                        <FormField label="Código *" hint={mode === 'edit' ? 'Código não pode ser alterado' : undefined}>
                            <FormInput
                                value={form.CD_ATIVO}
                                onChange={v => setForm(p => ({ ...p, CD_ATIVO: v.toUpperCase() }))}
                                placeholder="Ex: PETR4"
                                disabled={mode === 'edit'}
                            />
                        </FormField>
                        <FormField label="Tipo de Ativo">
                            <FormSelect
                                value={form.ID_TIPO_ATIVO}
                                onChange={v => set('ID_TIPO_ATIVO', v)}
                                options={tipoOpts}
                                placeholder="— selecione o tipo —"
                            />
                        </FormField>
                        <FormField label="Moeda">
                            <FormInput value={form.MOEDA} onChange={v => set('MOEDA', v)} placeholder="Ex: BRL, USD" />
                        </FormField>
                        <FormField label="Call / Put">
                            <FormSelect
                                value={form.CALL_PUT}
                                onChange={v => set('CALL_PUT', v)}
                                options={[{ value: 'C', label: 'Call' }, { value: 'P', label: 'Put' }]}
                                placeholder="— N/A —"
                            />
                        </FormField>
                        <FormField label="Lote">
                            <FormInput value={form.LOTE} onChange={v => set('LOTE', v)} type="number" placeholder="Ex: 100" />
                        </FormField>
                        <FormField label="Fator de Preço">
                            <FormInput value={form.FATOR_PRECO} onChange={v => set('FATOR_PRECO', v)} type="number" placeholder="Ex: 1.0" />
                        </FormField>
                        <FormField label="Preço Online">
                            <FormSelect
                                value={form.PRECO_ONLINE}
                                onChange={v => set('PRECO_ONLINE', v)}
                                options={[{ value: 1, label: 'Sim' }, { value: 0, label: 'Não' }]}
                                placeholder="— selecione —"
                            />
                        </FormField>
                        <FormField label="Código SELIC">
                            <FormInput value={form.CD_SELIC} onChange={v => set('CD_SELIC', v)} placeholder="Código SELIC" />
                        </FormField>
                    </div>
                </section>

                {/* ── Datas ── */}
                <section className="form-section">
                    <h3 className="form-section-title">
                        <i className="fas fa-calendar" /> Datas
                    </h3>
                    <div className="form-grid form-grid--2">
                        <FormField label="Data de Emissão">
                            <FormInput value={form.DT_EMISSAO} onChange={v => set('DT_EMISSAO', v)} type="date" />
                        </FormField>
                        <FormField label="Data de Vencimento">
                            <FormInput value={form.DT_VENCIMENTO} onChange={v => set('DT_VENCIMENTO', v)} type="date" />
                        </FormField>
                    </div>
                </section>

                {/* ── Classificação Setorial ── */}
                <section className="form-section">
                    <h3 className="form-section-title">
                        <i className="fas fa-sitemap" /> Classificação Setorial
                    </h3>
                    <div className="form-grid form-grid--2">
                        <FormField label="Setor (Pai)">
                            <FormSelect
                                value={form.ID_SETOR_PAI}
                                onChange={v => set('ID_SETOR_PAI', v)}
                                options={setorPaiOpts}
                                placeholder="— selecione o setor —"
                            />
                        </FormField>
                        <FormField label="Subsetor (Filho)">
                            <FormSelect
                                value={form.ID_SETOR_FILHO}
                                onChange={v => set('ID_SETOR_FILHO', v)}
                                options={setorFilhoOpts}
                                placeholder="— selecione o subsetor —"
                            />
                        </FormField>
                    </div>
                </section>

                {/* ── Códigos de Mercado ── */}
                <section className="form-section">
                    <h3 className="form-section-title">
                        <i className="fas fa-barcode" /> Códigos de Mercado
                    </h3>
                    <div className="form-grid">
                        <FormField label="Yahoo Finance (CD_YF)">
                            <FormInput value={form.CD_YF} onChange={v => set('CD_YF', v)} placeholder="Ex: PETR4.SA" />
                        </FormField>
                        <FormField label="Bloomberg (CD_BBG)">
                            <FormInput value={form.CD_BBG} onChange={v => set('CD_BBG', v)} placeholder="Ex: PETR4 BZ Equity" />
                        </FormField>
                        <FormField label="ISIN">
                            <FormInput value={form.CD_ISIN} onChange={v => set('CD_ISIN', v)} placeholder="Ex: BRPETRACNPR6" />
                        </FormField>
                        <FormField label="FIGI">
                            <FormInput value={form.CD_FIGI} onChange={v => set('CD_FIGI', v)} placeholder="FIGI" />
                        </FormField>
                        <FormField label="CUSIP">
                            <FormInput value={form.CD_CUSIP} onChange={v => set('CD_CUSIP', v)} placeholder="CUSIP" />
                        </FormField>
                    </div>
                </section>
            </div>
        </div>
    );
}

// ─── Tabela de ativos ─────────────────────────────────────────────────────────

function TabelaAtivos({ ativos, onSelect }: { ativos: Ativo[]; onSelect: (a: Ativo) => void }) {
    return (
        <div className="lista-table-wrapper">
            <table className="lista-table">
                <thead>
                    <tr>
                        <th>Código</th>
                        <th>Tipo</th>
                        <th>Classe Risco</th>
                        <th>Setor</th>
                        <th>Subsetor</th>
                        <th>Moeda</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {ativos.map(a => (
                        <tr key={a.CD_ATIVO} className="lista-table-row-clickable" onClick={() => onSelect(a)}>
                            <td className="col-ativo">{a.CD_ATIVO}</td>
                            <td>{a.TIPO_ATIVO ?? '—'}</td>
                            <td>{a.FL_CLASSE_RISCO ?? '—'}</td>
                            <td>{a.SetorPai ?? '—'}</td>
                            <td>{a.SetorFilho ?? '—'}</td>
                            <td>{a.MOEDA ?? '—'}</td>
                            <td className="col-action">
                                <i className="fas fa-pen-to-square" />
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

// ─── Página principal ─────────────────────────────────────────────────────────

export default function Lista() {
    const { data: ativos, isLoading, error } = useAtivos();
    const criarMutation = useCriarAtivo();
    const atualizarMutation = useAtualizarAtivo();

    const [mode, setMode] = useState<Mode>('table');
    const [filter, setFilter] = useState('');
    const [form, setForm] = useState<AtivoInput>(EMPTY_FORM);
    const [editingCd, setEditingCd] = useState<string | null>(null);
    const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
    const [formError, setFormError] = useState<string | null>(null);

    const ativosUnicos = useMemo(() => {
        if (!ativos) return [];
        const map = new Map<string, Ativo>();
        for (const a of ativos) {
            if (!map.has(a.CD_ATIVO)) map.set(a.CD_ATIVO, a);
        }
        return Array.from(map.values());
    }, [ativos]);

    const ativosFiltrados = useMemo(() => {
        if (!filter.trim()) return ativosUnicos;
        const q = filter.toLowerCase();
        return ativosUnicos.filter(a =>
            a.CD_ATIVO.toLowerCase().includes(q) ||
            (a.TIPO_ATIVO?.toLowerCase().includes(q)) ||
            (a.SetorPai?.toLowerCase().includes(q)) ||
            (a.SetorFilho?.toLowerCase().includes(q))
        );
    }, [ativosUnicos, filter]);

    // Auto-dismiss feedback
    useEffect(() => {
        if (!feedback) return;
        const t = setTimeout(() => setFeedback(null), 4000);
        return () => clearTimeout(t);
    }, [feedback]);

    function handleSelectAtivo(a: Ativo) {
        setForm(ativoToForm(a));
        setEditingCd(a.CD_ATIVO);
        setFormError(null);
        setMode('edit');
    }

    function handleNew() {
        setForm(EMPTY_FORM);
        setEditingCd(null);
        setFormError(null);
        setMode('new');
    }

    function handleCancel() {
        setMode('table');
        setFormError(null);
    }

    async function handleSave() {
        setFormError(null);
        if (!form.CD_ATIVO.trim()) {
            setFormError('O Código do ativo é obrigatório.');
            return;
        }
        try {
            if (mode === 'new') {
                await criarMutation.mutateAsync(form);
                setFeedback({ type: 'success', msg: `Ativo "${form.CD_ATIVO}" criado com sucesso!` });
            } else {
                await atualizarMutation.mutateAsync({ cdAtivo: editingCd!, payload: form });
                setFeedback({ type: 'success', msg: `Ativo "${form.CD_ATIVO}" atualizado com sucesso!` });
            }
            setMode('table');
        } catch (e: unknown) {
            const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? (e as Error).message;
            setFormError(msg);
        }
    }

    const saving = criarMutation.isPending || atualizarMutation.isPending;

    return (
        <div className="pg-page">
            {/* ── Header ── */}
            <div className="pg-header">
                <div className="pg-header-left">
                    <div className="pg-header-icon">
                        <i className="fas fa-folder-open" />
                    </div>
                    <div className="pg-header-text">
                        <h1>Consulta / Cadastro de Ativos</h1>
                        <p>Visualize, edite ou cadastre novos ativos</p>
                    </div>
                </div>
                {ativosUnicos.length > 0 && (
                    <div className="pg-header-meta">
                        <strong>{ativosUnicos.length}</strong> ativos cadastrados
                    </div>
                )}
            </div>

            {/* ── Feedback toast ── */}
            {feedback && (
                <div className={`lista-toast lista-toast--${feedback.type}`}>
                    <i className={feedback.type === 'success' ? 'fas fa-check-circle' : 'fas fa-triangle-exclamation'} />
                    {feedback.msg}
                    <button className="lista-toast-close" onClick={() => setFeedback(null)}>
                        <i className="fas fa-times" />
                    </button>
                </div>
            )}

            {/* ── Controles (só na tabela) ── */}
            {mode === 'table' && (
                <div className="pg-controls">
                    <div className="pg-select-group" style={{ flex: 1 }}>
                        <label className="pg-select-label">Buscar</label>
                        <input
                            className="form-input"
                            placeholder="Filtrar por código, tipo, setor…"
                            value={filter}
                            onChange={e => setFilter(e.target.value)}
                        />
                    </div>
                    <button className="btn btn-primary" onClick={handleNew}>
                        <i className="fas fa-plus" /> Novo Ativo
                    </button>
                </div>
            )}

            {/* ── Loading / Erro ── */}
            {isLoading && (
                <div className="pg-loading">
                    <i className="fas fa-circle-notch fa-spin" /> Carregando ativos…
                </div>
            )}
            {error && (
                <div className="pg-error">
                    <i className="fas fa-triangle-exclamation" />
                    Erro ao carregar ativos: {(error as Error).message}
                </div>
            )}

            {/* ── Formulário (edit / new) ── */}
            {(mode === 'edit' || mode === 'new') && (
                <AtivoForm
                    mode={mode}
                    form={form}
                    setForm={setForm}
                    onSave={handleSave}
                    onCancel={handleCancel}
                    saving={saving}
                    error={formError}
                />
            )}

            {/* ── Tabela (modo tabela) ── */}
            {mode === 'table' && !isLoading && ativosFiltrados.length > 0 && (
                <TabelaAtivos ativos={ativosFiltrados} onSelect={handleSelectAtivo} />
            )}

            {/* ── Nenhum resultado ── */}
            {mode === 'table' && !isLoading && !error && ativosFiltrados.length === 0 && ativosUnicos.length > 0 && (
                <div className="pg-empty">Nenhum ativo corresponde ao filtro.</div>
            )}
        </div>
    );
}
