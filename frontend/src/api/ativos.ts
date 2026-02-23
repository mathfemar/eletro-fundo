import { apiClient, type APIResponse } from './client';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface Ativo {
    ID_ATIVO: number;
    CD_ATIVO: string;
    ID_TIPO_ATIVO: number | null;
    ID_SETOR_FILHO: number | null;
    ID_SETOR_PAI: number | null;
    DT_EMISSAO: string | null;
    DT_VENCIMENTO: string | null;
    CD_SELIC: string | null;
    MOEDA: string | null;
    PRECO_ONLINE: number | null;
    FATOR_PRECO: number | null;
    CALL_PUT: string | null;
    LOTE: number | null;
    CD_BBG: string | null;
    CD_CUSIP: string | null;
    CD_FIGI: string | null;
    CD_ISIN: string | null;
    CD_YF: string | null;
    TIPO_ATIVO: string | null;
    ClasseRisco: string | null;
    SetorFilho: string | null;
    SetorPai: string | null;
}

export interface AtivoInput {
    CD_ATIVO: string;
    ID_TIPO_ATIVO: number | null;
    DT_EMISSAO: string | null;
    DT_VENCIMENTO: string | null;
    CD_SELIC: string | null;
    ID_SETOR_PAI: number | null;
    ID_SETOR_FILHO: number | null;
    MOEDA: string | null;
    PRECO_ONLINE: number | null;
    FATOR_PRECO: number | null;
    CALL_PUT: string | null;
    LOTE: number | null;
    CD_BBG: string | null;
    CD_YF: string | null;
    CD_FIGI: string | null;
    CD_ISIN: string | null;
    CD_CUSIP: string | null;
}

export interface TipoAtivo {
    ID_TIPO_ATIVO: number;
    TIPO_ATIVO: string;
    ClasseRisco: string | null;
}

export interface SetorPaiItem {
    ID_SETOR_PAI: number;
    SetorPai: string;
}

export interface SetorFilhoItem {
    ID_SETOR_FILHO: number;
    SetorFilho: string;
}

export interface AtivosMeta {
    tipos: TipoAtivo[];
    setores_pai: SetorPaiItem[];
    setores_filho: SetorFilhoItem[];
}

interface AtivosResponse {
    items: Ativo[];
    total: number;
}

export async function getAtivos(): Promise<Ativo[]> {
    const res = await apiClient.get<APIResponse<AtivosResponse>>('/api/ativos');
    return res.data.data.items;
}

export async function getAtivo(cdAtivo: string): Promise<Ativo> {
    const res = await apiClient.get<APIResponse<Ativo>>(`/api/ativos/${cdAtivo}`);
    return res.data.data;
}

export async function getAtivosMeta(): Promise<AtivosMeta> {
    const res = await apiClient.get<APIResponse<AtivosMeta>>('/api/ativos/meta');
    return res.data.data;
}

export async function criarAtivo(payload: AtivoInput): Promise<{ CD_ATIVO: string; ID_ATIVO: number }> {
    const res = await apiClient.post<APIResponse<{ CD_ATIVO: string; ID_ATIVO: number }>>('/api/ativos', payload);
    return res.data.data;
}

export async function atualizarAtivo(
    cdAtivo: string,
    payload: AtivoInput,
): Promise<{ CD_ATIVO: string; ID_ATIVO: number }> {
    const res = await apiClient.put<APIResponse<{ CD_ATIVO: string; ID_ATIVO: number }>>(
        `/api/ativos/${cdAtivo}`,
        payload,
    );
    return res.data.data;
}
