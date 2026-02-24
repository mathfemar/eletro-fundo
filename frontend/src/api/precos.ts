import { apiClient, type APIResponse } from './client';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface PrecoLive {
    CD_ATIVO: string;
    CD_YF: string | null;
    VL_PRECO_ATUAL: number | null;
    VL_PRECO_ABERTURA: number | null;
    VL_PRECO_MAX: number | null;
    VL_PRECO_MIN: number | null;
    VL_VOLUME_DIA: number | null;
    VL_VAR_DIA: number | null;
    VL_VAR_DIA_PCT: number | null;
    VL_PRECO_FECHAMENTO_ANT: number | null;
    DT_REFERENCIA: string | null;
    DT_HORA_CAPTURA: string | null;
}

interface LiveResponse {
    items: PrecoLive[];
    total: number;
}

interface LiveSerieResponse {
    items: PrecoLive[];
    total: number;
}

// ─── API functions ────────────────────────────────────────────────────────────

export async function getPrecosLive(): Promise<PrecoLive[]> {
    const res = await apiClient.get<APIResponse<LiveResponse>>('/api/precos/live');
    return res.data.data.items;
}

export async function atualizarPrecosLive(): Promise<void> {
    await apiClient.post('/api/precos/live/atualizar');
}

export async function getPrecosLiveSerieAtivo(
    cdAtivo: string,
    horas = 24,
): Promise<PrecoLive[]> {
    const res = await apiClient.get<APIResponse<LiveSerieResponse>>(
        `/api/precos/live/serie/${encodeURIComponent(cdAtivo)}?horas=${horas}`,
    );
    return res.data.data.items;
}

// ─── Histórico ────────────────────────────────────────────────────────────────

export interface ResumoAtivo {
    CD_ATIVO: string;
    CD_YF: string | null;
    QT_REGISTROS: number;
    DT_INICIO: string;
    DT_FIM: string;
}

export interface CandleRow {
    CD_ATIVO: string;
    DT_REFERENCIA: string;
    VL_ABERTURA: number | null;
    VL_MAXIMA: number | null;
    VL_MINIMA: number | null;
    VL_FECHAMENTO: number | null;
    VL_FECHAMENTO_AJ: number | null;
    VL_VOLUME: number | null;
    CD_MOEDA: string | null;
}

interface ResumoResponse  { items: ResumoAtivo[];  total: number; }
interface HistoricoResponse { items: CandleRow[]; total: number; }

export async function getResumoHistorico(): Promise<ResumoAtivo[]> {
    const res = await apiClient.get<APIResponse<ResumoResponse>>('/api/precos/historico/resumo/geral');
    return res.data.data.items;
}

export async function getHistoricoAtivo(
    cdAtivo: string,
    dtInicio?: string,
    dtFim?: string,
): Promise<CandleRow[]> {
    const params = new URLSearchParams();
    if (dtInicio) params.set('dt_inicio', dtInicio);
    if (dtFim)    params.set('dt_fim', dtFim);
    const qs = params.toString();
    const url = `/api/precos/historico/${cdAtivo}${qs ? `?${qs}` : ''}`;
    const res = await apiClient.get<APIResponse<HistoricoResponse>>(url);
    return res.data.data.items;
}
