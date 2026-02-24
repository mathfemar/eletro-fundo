import { apiClient, type APIResponse } from './client';

export interface SimPortfolio {
    ID_PORTFOLIO: number;
    NM_PORTFOLIO: string;
    DT_INICIO: string;
    BENCHMARK: string | null;
    MOEDA_BASE: string | null;
    ST_ATIVO: number | null;
    ID_FUNDO: number | null;
    NM_FUNDO: string | null;
    ID_TITULAR: number | null;
    NM_TITULAR: string | null;
    ID_CORRETORA: number | null;
    NM_CORRETORA: string | null;
    CONTA_REF: string | null;
    DT_CRIACAO: string | null;
    DT_ATUALIZACAO: string | null;
}

export interface SimFundo {
    ID_FUNDO: number;
    NM_FUNDO: string;
    DS_ESTRATEGIA: string | null;
    BENCHMARK: string | null;
    MOEDA_BASE: string | null;
    ST_ATIVO: number | null;
    DT_CRIACAO: string | null;
    DT_ATUALIZACAO: string | null;
}

export interface SimTitular {
    ID_TITULAR: number;
    NM_TITULAR: string;
    NR_DOCUMENTO: string | null;
    ST_ATIVO: number | null;
    DT_CRIACAO: string | null;
    DT_ATUALIZACAO: string | null;
}

export interface SimCorretora {
    ID_CORRETORA: number;
    NM_CORRETORA: string;
    CD_CORRETORA: string | null;
    ST_ATIVO: number | null;
    DT_CRIACAO: string | null;
    DT_ATUALIZACAO: string | null;
}

export interface SimFundPnlFechamento {
    ID_FUNDO: number;
    DT_REFERENCIA: string;
    DT_HORA_CAPTURA: string;
    VL_VALOR_MERCADO_TOTAL: number;
    VL_PNL_ABERTO_TOTAL: number;
    VL_PNL_REALIZADO_TOTAL: number;
    VL_PNL_TOTAL: number;
    CD_METODO: string;
    FL_REPROCESSADO: number;
    DT_CARGA: string;
}

export interface SimFundCotaDiaria {
    ID_FUNDO: number;
    DT_REFERENCIA: string;
    VL_COTA: number;
    QT_COTAS: number;
    VL_PL: number;
    DT_HORA_FECHAMENTO: string | null;
    CD_METODO: string;
    FL_REPROCESSADO: number;
    DT_CARGA: string;
}

export interface SimTrade {
    ID_TRADE: number;
    ID_PORTFOLIO: number;
    ID_ATIVO: number;
    CD_ATIVO: string;
    DT_HORA_EXEC: string;
    DT_TRADE: string;
    SIDE: 'BUY' | 'SELL' | 'SHORT' | 'COVER';
    QTD: number;
    PU: number;
    CUSTO: number | null;
    OBSERVACAO: string | null;
    DT_CARGA: string | null;
}

export interface SimPosition {
    ID_PORTFOLIO: number;
    ID_ATIVO: number;
    CD_ATIVO: string;
    MOEDA: string;
    FX_ATUAL: number;
    QTD_LIQ: number;
    PRECO_MEDIO: number | null;
    PRECO_ATUAL: number | null;
    CUSTO_TOTAL: number | null;
    VALOR_MERCADO: number | null;
    PNL_REALIZADO: number | null;
    PNL_ABERTO: number | null;
    PNL_TOTAL: number | null;
}

export interface SimPositionResumo {
    VALOR_MERCADO_TOTAL: number;
    PNL_ABERTO_TOTAL: number;
    PNL_REALIZADO_TOTAL: number;
    PNL_TOTAL: number;
}

export interface SimPortfolioInput {
    NM_PORTFOLIO: string;
    DT_INICIO: string;
    BENCHMARK?: string | null;
    MOEDA_BASE?: string;
    ST_ATIVO?: number;
    ID_FUNDO?: number | null;
    ID_TITULAR?: number | null;
    ID_CORRETORA?: number | null;
    CONTA_REF?: string | null;
}

export interface SimFundoInput {
    NM_FUNDO: string;
    DS_ESTRATEGIA?: string | null;
    BENCHMARK?: string | null;
    MOEDA_BASE?: string;
    ST_ATIVO?: number;
}

export interface SimTitularInput {
    NM_TITULAR: string;
    NR_DOCUMENTO?: string | null;
    ST_ATIVO?: number;
}

export interface SimCorretoraInput {
    NM_CORRETORA: string;
    CD_CORRETORA?: string | null;
    ST_ATIVO?: number;
}

export interface SimTradeInput {
    ID_PORTFOLIO: number;
    ID_ATIVO: number;
    DT_HORA_EXEC?: string;
    DT_TRADE: string;
    SIDE: 'BUY' | 'SELL' | 'SHORT' | 'COVER';
    QTD: number;
    PU: number;
    CUSTO?: number;
    OBSERVACAO?: string | null;
}

interface ListResponse<T> {
    items: T[];
    total: number;
}

interface PositionResponse {
    items: SimPosition[];
    total: number;
    resumo: SimPositionResumo;
}

export type SimPositionResponse = PositionResponse;

export async function getSimPortfolios(): Promise<SimPortfolio[]> {
    const res = await apiClient.get<APIResponse<ListResponse<SimPortfolio>>>('/api/sim/portfolios');
    return res.data.data.items;
}

export async function createSimPortfolio(payload: SimPortfolioInput): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_PORTFOLIO: number }>>('/api/sim/portfolios', payload);
    return res.data.data.ID_PORTFOLIO;
}

export async function getSimFundos(): Promise<SimFundo[]> {
    const res = await apiClient.get<APIResponse<ListResponse<SimFundo>>>('/api/sim/fundos');
    return res.data.data.items;
}

export async function createSimFundo(payload: SimFundoInput): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_FUNDO: number }>>('/api/sim/fundos', payload);
    return res.data.data.ID_FUNDO;
}

export async function getSimTitulares(): Promise<SimTitular[]> {
    const res = await apiClient.get<APIResponse<ListResponse<SimTitular>>>('/api/sim/titulares');
    return res.data.data.items;
}

export async function createSimTitular(payload: SimTitularInput): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_TITULAR: number }>>('/api/sim/titulares', payload);
    return res.data.data.ID_TITULAR;
}

export async function getSimCorretoras(): Promise<SimCorretora[]> {
    const res = await apiClient.get<APIResponse<ListResponse<SimCorretora>>>('/api/sim/corretoras');
    return res.data.data.items;
}

export async function createSimCorretora(payload: SimCorretoraInput): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_CORRETORA: number }>>('/api/sim/corretoras', payload);
    return res.data.data.ID_CORRETORA;
}

export async function deleteSimPortfolio(portfolioId: number): Promise<number> {
    const res = await apiClient.delete<APIResponse<{ ID_PORTFOLIO: number }>>(`/api/sim/portfolios/${portfolioId}`);
    return res.data.data.ID_PORTFOLIO;
}

export async function getSimTrades(
    portfolioId: number,
    dtInicio?: string,
    dtFim?: string,
): Promise<SimTrade[]> {
    const params = new URLSearchParams();
    params.set('portfolio_id', String(portfolioId));
    if (dtInicio) params.set('dt_inicio', dtInicio);
    if (dtFim) params.set('dt_fim', dtFim);

    const res = await apiClient.get<APIResponse<ListResponse<SimTrade>>>(`/api/sim/trades?${params.toString()}`);
    return res.data.data.items;
}

export async function createSimTrade(payload: SimTradeInput): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_TRADE: number }>>('/api/sim/trades', payload);
    return res.data.data.ID_TRADE;
}

export async function updateSimTrade(tradeId: number, payload: SimTradeInput): Promise<number> {
    const res = await apiClient.put<APIResponse<{ ID_TRADE: number }>>(`/api/sim/trades/${tradeId}`, payload);
    return res.data.data.ID_TRADE;
}

export async function deleteSimTrade(tradeId: number): Promise<number> {
    const res = await apiClient.delete<APIResponse<{ ID_TRADE: number }>>(`/api/sim/trades/${tradeId}`);
    return res.data.data.ID_TRADE;
}

export async function getSimPositions(portfolioId: number): Promise<PositionResponse> {
    const res = await apiClient.get<APIResponse<PositionResponse>>(
        `/api/sim/positions?portfolio_id=${portfolioId}`,
    );
    return res.data.data;
}

export async function getSimFundPositions(fundoId: number): Promise<PositionResponse> {
    const res = await apiClient.get<APIResponse<PositionResponse>>(
        `/api/sim/fundos/positions?fundo_id=${fundoId}`,
    );
    return res.data.data;
}

export async function getSimFundPnlFechamentoSerie(
    fundoId: number,
    dtInicio?: string,
    dtFim?: string,
): Promise<SimFundPnlFechamento[]> {
    const params = new URLSearchParams();
    params.set('fundo_id', String(fundoId));
    if (dtInicio) params.set('dt_inicio', dtInicio);
    if (dtFim) params.set('dt_fim', dtFim);

    const res = await apiClient.get<APIResponse<ListResponse<SimFundPnlFechamento>>>(
        `/api/sim/fundos/pnl/fechamento/serie?${params.toString()}`,
    );
    return res.data.data.items;
}

export async function postSimFundPnlLiveCapture(fundoId: number): Promise<void> {
    await apiClient.post<APIResponse>(`/api/sim/fundos/pnl/live/capture?fundo_id=${fundoId}`);
}

export async function postSimFundPnlFechamento(fundoId: number, dtReferencia?: string): Promise<void> {
    const params = new URLSearchParams();
    params.set('fundo_id', String(fundoId));
    if (dtReferencia) params.set('dt_referencia', dtReferencia);
    await apiClient.post<APIResponse>(`/api/sim/fundos/pnl/fechamento?${params.toString()}`);
}

export async function postSimFundPnlBackfill(
    fundoId: number,
    dtInicio: string,
    dtFim: string,
): Promise<void> {
    const params = new URLSearchParams();
    params.set('fundo_id', String(fundoId));
    params.set('dt_inicio', dtInicio);
    params.set('dt_fim', dtFim);
    await apiClient.post<APIResponse>(`/api/sim/fundos/pnl/backfill?${params.toString()}`);
}

export async function getSimFundCotaSerie(
    fundoId: number,
    dtInicio?: string,
    dtFim?: string,
): Promise<SimFundCotaDiaria[]> {
    const params = new URLSearchParams();
    params.set('fundo_id', String(fundoId));
    if (dtInicio) params.set('dt_inicio', dtInicio);
    if (dtFim) params.set('dt_fim', dtFim);

    const res = await apiClient.get<APIResponse<ListResponse<SimFundCotaDiaria>>>(
        `/api/sim/fundos/cotas/serie?${params.toString()}`,
    );
    return res.data.data.items;
}

export async function postSimFundCotaRecalcular(fundoId: number): Promise<void> {
    await apiClient.post<APIResponse>(`/api/sim/fundos/cotas/recalcular?fundo_id=${fundoId}`);
}
