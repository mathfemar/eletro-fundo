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
    DT_INICIO: string | null;
}

export interface SimFundoCarteira {
    ID_CARTEIRA: number;
    NM_CARTEIRA: string;
    ID_TITULAR: number;
    NM_TITULAR: string | null;
    ID_CORRETORA: number | null;
    NM_CORRETORA: string | null;
    CONTA_REF: string | null;
    MOEDA_BASE: string | null;
    DT_INICIO: string;
    DT_FIM: string | null;
    ST_ATIVO: number;
    VL_SALDO_CAIXA: number;
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

export interface SimFundFluxoCapital {
    ID_FLUXO: number;
    ID_FUNDO: number;
    ID_TITULAR: number | null;
    NM_TITULAR: string | null;
    DT_REFERENCIA: string;
    TP_FLUXO: 'APORTE' | 'RESGATE';
    VL_FLUXO: number;
    OBSERVACAO: string | null;
    DT_CARGA: string;
}

export interface SimFundCotistaPosicao {
    ID_TITULAR: number;
    NM_TITULAR: string;
    DT_REFERENCIA: string;
    VL_COTA: number;
    VL_APORTADO_BRUTO: number;
    VL_RESGATADO_BRUTO: number;
    VL_INVERTIDO_LIQ: number;
    QT_COTAS: number;
    VL_PL_COTISTA: number;
    VL_PNL_COTISTA: number;
}

export interface SimAtivoLiquidez {
    ID_ATIVO: number;
    CD_ATIVO: string;
    NR_DIAS_LIQUIDEZ: number;
    DS_REGRA: string | null;
    ST_ATIVO: number;
    DT_ATUALIZACAO: string | null;
}

export interface SimFundoLiquidezOpcao {
    ID_ATIVO: number;
    CD_ATIVO: string;
    VALOR_MERCADO: number;
    QTD_LIQ: number;
    NR_DIAS_LIQUIDEZ: number;
    DS_REGRA: string | null;
}

export interface SimRFTitulo {
    ID_TITULO: number;
    CD_TITULO: string;
    NM_TITULO: string | null;
    ID_ATIVO: number | null;
    CD_ATIVO: string | null;
    DT_VENCIMENTO: string;
    DT_RESGATE: string | null;
    DT_LIQUIDEZ: string;
    VL_TAXA_CONTRATADA: number | null;
    ST_ATIVO: number;
    DT_CRIACAO: string | null;
    DT_ATUALIZACAO: string | null;
}

export interface SimRFTituloInput {
    CD_TITULO: string;
    NM_TITULO?: string | null;
    ID_ATIVO?: number | null;
    DT_VENCIMENTO: string;
    DT_RESGATE?: string | null;
    VL_TAXA_CONTRATADA?: number | null;
    ST_ATIVO?: number;
}

export interface SimResgateSolicitacao {
    ID_SOLICITACAO: number;
    ID_FUNDO: number;
    ID_TITULAR: number | null;
    NM_TITULAR: string | null;
    DT_SOLICITACAO: string;
    VL_RESGATE: number;
    ST_STATUS: 'ABERTA' | 'PLANEJADA' | 'PARCIAL' | 'LIQUIDADA' | 'CANCELADA';
    DS_OBSERVACAO: string | null;
    DT_CARGA: string;
}

export interface SimResgatePlanoItem {
    ID_ITEM: number;
    ID_PLANO: number;
    ID_ATIVO: number;
    CD_ATIVO: string;
    VL_LIQUIDAR: number;
    NR_DIAS_LIQUIDEZ: number;
    DT_LIQUIDEZ_PREVISTA: string;
    DS_OBSERVACAO: string | null;
    DT_CARGA: string;
}

export interface SimResgatePlano {
    ID_PLANO: number;
    ID_SOLICITACAO: number;
    NR_REVISAO: number;
    CD_METODO: string;
    ST_STATUS: string;
    DS_JUSTIFICATIVA: string | null;
    DT_CARGA: string;
    VL_TOTAL_PLANEJADO: number;
    VL_TOTAL_EXECUTADO?: number;
    items: SimResgatePlanoItem[];
}

export interface SimResgateEvento {
    ID_EVENTO: number;
    ID_FUNDO: number;
    ID_SOLICITACAO: number;
    ID_PLANO: number;
    DT_REFERENCIA: string;
    TP_EVENTO: 'EXEC_PARCIAL' | 'EXEC_TOTAL' | 'OVERRIDE_MTM';
    VL_EVENTO: number;
    DS_JUSTIFICATIVA: string | null;
    DS_OBSERVACAO: string | null;
    DT_CARGA: string;
}

interface SimFundCotistaPosicaoResponse {
    items: SimFundCotistaPosicao[];
    total: number;
    DT_REFERENCIA: string | null;
    VL_COTA: number | null;
}

export interface SimFundDashboard {
    ID_FUNDO: number;
    periodo: {
        DT_INICIO: string | null;
        DT_FIM: string | null;
    };
    resumo: {
        ULTIMA_DATA_PNL: string | null;
        ULTIMA_DATA_COTA: string | null;
        VL_PL_ULTIMO: number;
        VL_PNL_ULTIMO: number;
        VL_COTA_ULTIMA: number;
        VL_CAIXA_REAL: number;
    };
    pnl_fechamento: {
        items: SimFundPnlFechamento[];
        total: number;
    };
    cotas: {
        items: SimFundCotaDiaria[];
        total: number;
    };
    fluxos: {
        items: SimFundFluxoCapital[];
        total: number;
    };
    cotistas_posicao: SimFundCotistaPosicaoResponse;
}

export interface SimTrade {
    ID_TRADE: number;
    ID_PORTFOLIO: number;
    ID_ATIVO: number;
    CD_ATIVO: string;
    DT_HORA_EXEC: string;
    DT_TRADE: string;
    SIDE: 'BUY' | 'SELL';
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
    PRECO_ONLINE: boolean;
    SEM_PRECO_MERCADO: boolean;
    ALERTAS: string[] | null;
    CUSTO_TOTAL: number | null;
    VALOR_MERCADO: number | null;
    PNL_REALIZADO: number | null;
    PNL_ABERTO: number | null;
    PNL_TOTAL: number | null;
}

export interface SimCarteiraPosicaoDiaria {
    ID_PORTFOLIO: number;
    DT_REFERENCIA: string;
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
    DT_CARGA: string;
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
    DT_INICIO?: string;
    VL_PL_INICIAL?: number;
    VL_COTA_INICIAL?: number;
}

export interface SimFundoSetupInput {
    NM_FUNDO: string;
    DS_ESTRATEGIA?: string | null;
    BENCHMARK?: string | null;
    MOEDA_BASE?: string;
    ST_ATIVO?: number;
    DT_INICIO?: string;
    VL_COTA_INICIAL?: number;
    COTISTAS_INICIAIS: Array<{
        ID_TITULAR: number;
        VL_APORTE: number;
    }>;
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
    SIDE: 'BUY' | 'SELL';
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

export async function setupSimFundo(payload: SimFundoSetupInput): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_FUNDO: number }>>('/api/sim/fundos/setup', payload);
    return res.data.data.ID_FUNDO;
}

export async function getSimFundCarteiras(fundoId: number): Promise<SimFundoCarteira[]> {
    const res = await apiClient.get<APIResponse<ListResponse<SimFundoCarteira>>>(`/api/sim/fundos/${fundoId}/carteiras`);
    return res.data.data.items;
}

export async function createSimFundCarteira(
    fundoId: number,
    payload: {
        ID_TITULAR: number;
        NM_CARTEIRA: string;
        ID_CORRETORA?: number | null;
        CONTA_REF?: string | null;
        MOEDA_BASE?: string;
        DT_INICIO?: string;
    },
): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_CARTEIRA: number }>>(`/api/sim/fundos/${fundoId}/carteiras`, payload);
    return res.data.data.ID_CARTEIRA;
}

export async function postSimFundAlocacao(
    fundoId: number,
    payload: {
        ID_CARTEIRA_ORIGEM: number;
        ID_CARTEIRA_DESTINO: number;
        VL_ALOCACAO: number;
        DT_MOVIMENTO?: string;
        DS_OBSERVACAO?: string | null;
    },
): Promise<void> {
    await apiClient.post<APIResponse>(`/api/sim/fundos/${fundoId}/alocacoes`, payload);
}

export async function deleteSimFundo(fundoId: number): Promise<number> {
    const res = await apiClient.delete<APIResponse<{ ID_FUNDO: number }>>(`/api/sim/fundos/${fundoId}`);
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

export async function getSimCarteiraPosicaoSerie(
    portfolioId: number,
    dtInicio?: string,
    dtFim?: string,
): Promise<SimCarteiraPosicaoDiaria[]> {
    const params = new URLSearchParams();
    params.set('portfolio_id', String(portfolioId));
    if (dtInicio) params.set('dt_inicio', dtInicio);
    if (dtFim) params.set('dt_fim', dtFim);

    const res = await apiClient.get<APIResponse<ListResponse<SimCarteiraPosicaoDiaria>>>(
        `/api/sim/carteiras/posicao/serie?${params.toString()}`,
    );
    return res.data.data.items;
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

export async function getSimFundDashboard(
    fundoId: number,
    dtInicio?: string,
    dtFim?: string,
    dtReferencia?: string,
): Promise<SimFundDashboard> {
    const params = new URLSearchParams();
    params.set('fundo_id', String(fundoId));
    if (dtInicio) params.set('dt_inicio', dtInicio);
    if (dtFim) params.set('dt_fim', dtFim);
    if (dtReferencia) params.set('dt_referencia', dtReferencia);

    const res = await apiClient.get<APIResponse<SimFundDashboard>>(`/api/sim/fundos/dashboard?${params.toString()}`);
    return res.data.data;
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

export async function postSimFundFluxoCapital(
    payload: {
        ID_FUNDO: number;
        ID_TITULAR?: number | null;
        DT_REFERENCIA: string;
        TP_FLUXO: 'APORTE' | 'RESGATE';
        VL_FLUXO: number;
        OBSERVACAO?: string | null;
    },
): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_FLUXO: number }>>('/api/sim/fundos/fluxos', payload);
    return res.data.data.ID_FLUXO;
}

export async function getSimFundFluxos(
    fundoId: number,
    dtInicio?: string,
    dtFim?: string,
): Promise<SimFundFluxoCapital[]> {
    const params = new URLSearchParams();
    params.set('fundo_id', String(fundoId));
    if (dtInicio) params.set('dt_inicio', dtInicio);
    if (dtFim) params.set('dt_fim', dtFim);

    const res = await apiClient.get<APIResponse<ListResponse<SimFundFluxoCapital>>>(
        `/api/sim/fundos/fluxos?${params.toString()}`,
    );
    return res.data.data.items;
}

export async function getSimFundCotistasPosicao(
    fundoId: number,
    dtReferencia?: string,
): Promise<SimFundCotistaPosicaoResponse> {
    const params = new URLSearchParams();
    params.set('fundo_id', String(fundoId));
    if (dtReferencia) params.set('dt_referencia', dtReferencia);

    const res = await apiClient.get<APIResponse<SimFundCotistaPosicaoResponse>>(
        `/api/sim/fundos/cotistas/posicao?${params.toString()}`,
    );
    return res.data.data;
}

export async function getSimFundCotistasPosicaoSerie(
    fundoId: number,
    dtInicio?: string,
    dtFim?: string,
): Promise<SimFundCotistaPosicao[]> {
    const params = new URLSearchParams();
    params.set('fundo_id', String(fundoId));
    if (dtInicio) params.set('dt_inicio', dtInicio);
    if (dtFim) params.set('dt_fim', dtFim);

    const res = await apiClient.get<APIResponse<ListResponse<SimFundCotistaPosicao>>>(
        `/api/sim/fundos/cotistas/posicao/serie?${params.toString()}`,
    );
    return res.data.data.items;
}

export async function getSimAtivosLiquidez(): Promise<SimAtivoLiquidez[]> {
    const res = await apiClient.get<APIResponse<ListResponse<SimAtivoLiquidez>>>('/api/sim/ativos/liquidez');
    return res.data.data.items;
}

export async function postSimAtivoLiquidez(payload: {
    ID_ATIVO: number;
    NR_DIAS_LIQUIDEZ: number;
    DS_REGRA?: string | null;
    ST_ATIVO?: number;
}): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_ATIVO: number }>>('/api/sim/ativos/liquidez', payload);
    return res.data.data.ID_ATIVO;
}

export async function getSimFundoLiquidezOpcoes(fundoId: number): Promise<SimFundoLiquidezOpcao[]> {
    const params = new URLSearchParams();
    params.set('fundo_id', String(fundoId));
    const res = await apiClient.get<APIResponse<ListResponse<SimFundoLiquidezOpcao>>>(
        `/api/sim/fundos/liquidez/opcoes?${params.toString()}`,
    );
    return res.data.data.items;
}

export async function getSimRFTitulos(stAtivo?: number): Promise<SimRFTitulo[]> {
    const params = new URLSearchParams();
    if (stAtivo !== undefined) params.set('st_ativo', String(stAtivo));
    const qs = params.toString();
    const res = await apiClient.get<APIResponse<ListResponse<SimRFTitulo>>>(
        `/api/sim/rf/titulos${qs ? `?${qs}` : ''}`,
    );
    return res.data.data.items;
}

export async function postSimRFTitulo(payload: SimRFTituloInput): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_TITULO: number }>>('/api/sim/rf/titulos', payload);
    return res.data.data.ID_TITULO;
}

export async function postSimResgateSolicitacao(payload: {
    ID_FUNDO: number;
    ID_TITULAR?: number | null;
    DT_SOLICITACAO: string;
    VL_RESGATE: number;
    DS_OBSERVACAO?: string | null;
}): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_SOLICITACAO: number }>>('/api/sim/fundos/resgates/solicitacoes', payload);
    return res.data.data.ID_SOLICITACAO;
}

export async function getSimResgateSolicitacoes(
    fundoId: number,
    stStatus?: string,
): Promise<SimResgateSolicitacao[]> {
    const params = new URLSearchParams();
    params.set('fundo_id', String(fundoId));
    if (stStatus) params.set('st_status', stStatus);
    const res = await apiClient.get<APIResponse<ListResponse<SimResgateSolicitacao>>>(
        `/api/sim/fundos/resgates/solicitacoes?${params.toString()}`,
    );
    return res.data.data.items;
}

export async function postSimResgatePlano(payload: {
    ID_SOLICITACAO: number;
    CD_METODO?: string;
    DS_JUSTIFICATIVA?: string | null;
    ST_STATUS?: string;
    items: Array<{
        ID_ATIVO: number;
        VL_LIQUIDAR: number;
        NR_DIAS_LIQUIDEZ?: number;
        DS_OBSERVACAO?: string | null;
    }>;
}): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_PLANO: number }>>('/api/sim/fundos/resgates/planos', payload);
    return res.data.data.ID_PLANO;
}

export async function getSimResgatePlanos(solicitacaoId: number): Promise<SimResgatePlano[]> {
    const params = new URLSearchParams();
    params.set('solicitacao_id', String(solicitacaoId));
    const res = await apiClient.get<APIResponse<ListResponse<SimResgatePlano>>>(
        `/api/sim/fundos/resgates/planos?${params.toString()}`,
    );
    return res.data.data.items;
}

export async function postSimResgateExecutarPlano(
    planoId: number,
    payload: {
        DT_REFERENCIA?: string;
        VL_EXECUTADO?: number;
        DS_OBSERVACAO?: string | null;
    },
): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_EVENTO: number }>>(
        `/api/sim/fundos/resgates/planos/${planoId}/executar`,
        payload,
    );
    return res.data.data.ID_EVENTO;
}

export async function postSimResgateOverridePlano(
    planoId: number,
    payload: {
        DT_REFERENCIA?: string;
        DS_JUSTIFICATIVA: string;
        VL_EVENTO?: number;
    },
): Promise<number> {
    const res = await apiClient.post<APIResponse<{ ID_EVENTO: number }>>(
        `/api/sim/fundos/resgates/planos/${planoId}/override-mtm`,
        payload,
    );
    return res.data.data.ID_EVENTO;
}

export async function getSimResgateEventosPlano(planoId: number): Promise<SimResgateEvento[]> {
    const res = await apiClient.get<APIResponse<ListResponse<SimResgateEvento>>>(
        `/api/sim/fundos/resgates/planos/${planoId}/eventos`,
    );
    return res.data.data.items;
}

// ─── Retorno consolidado do fundo ────────────────────────────────────────────

export interface SimFundRetornoItem {
    DT_REFERENCIA: string;
    VL_COTA: number;
    RETORNO_DIA_PCT: number;
    RETORNO_ACUM_PCT: number;
}

export async function getSimFundRetorno(
    fundoId: number,
    dtInicio?: string,
    dtFim?: string,
): Promise<SimFundRetornoItem[]> {
    const params = new URLSearchParams({ fundo_id: String(fundoId) });
    if (dtInicio) params.set('dt_inicio', dtInicio);
    if (dtFim) params.set('dt_fim', dtFim);
    const res = await apiClient.get<APIResponse<ListResponse<SimFundRetornoItem>>>(
        `/api/sim/fundos/retorno?${params}`,
    );
    return res.data.data.items;
}

export interface SimFxRateResult {
    moeda: string;
    dt: string | null;
    fx_rate: number;
}

export async function getSimFxRate(moeda: string, dt: string): Promise<SimFxRateResult> {
    const params = new URLSearchParams({ moeda, dt });
    const res = await apiClient.get<APIResponse<SimFxRateResult>>(`/api/sim/fx-rate?${params}`);
    return res.data.data;
}
