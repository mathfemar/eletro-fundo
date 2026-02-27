import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    getSimPortfolios,
    createSimPortfolio,
    getSimFundos,
    createSimFundo,
    setupSimFundo,
    getSimFundCarteiras,
    createSimFundCarteira,
    postSimFundAlocacao,
    deleteSimFundo,
    getSimTitulares,
    createSimTitular,
    getSimCorretoras,
    createSimCorretora,
    deleteSimPortfolio,
    getSimTrades,
    createSimTrade,
    updateSimTrade,
    deleteSimTrade,
    getSimPositions,
    getSimCarteiraPosicaoSerie,
    getSimFundPositions,
    getSimFundPnlFechamentoSerie,
    getSimFundDashboard,
    postSimFundPnlLiveCapture,
    postSimFundPnlFechamento,
    postSimFundPnlBackfill,
    getSimFundCotaSerie,
    postSimFundCotaRecalcular,
    postSimFundFluxoCapital,
    getSimFundFluxos,
    getSimFundCotistasPosicao,
    getSimFundCotistasPosicaoSerie,
    getSimAtivosLiquidez,
    postSimAtivoLiquidez,
    getSimFundoLiquidezOpcoes,
    getSimRFTitulos,
    postSimRFTitulo,
    postSimResgateSolicitacao,
    getSimResgateSolicitacoes,
    postSimResgatePlano,
    getSimResgatePlanos,
    postSimResgateExecutarPlano,
    postSimResgateOverridePlano,
    getSimResgateEventosPlano,
    getSimFundRetorno,
    getSimFxRate,
    type SimPortfolioInput,
    type SimFundoInput,
    type SimFundoSetupInput,
    type SimTitularInput,
    type SimCorretoraInput,
    type SimTradeInput,
} from '@/api/simulador';

const STALE = 5 * 60 * 1000;

export function useSimPortfolios() {
    return useQuery({
        queryKey: ['sim', 'portfolios'],
        queryFn: getSimPortfolios,
        staleTime: STALE,
    });
}

export function useCreateSimPortfolio() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: SimPortfolioInput) => createSimPortfolio(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'portfolios'] });
        },
    });
}

export function useSimFundos() {
    return useQuery({
        queryKey: ['sim', 'fundos'],
        queryFn: getSimFundos,
        staleTime: STALE,
    });
}

export function useCreateSimFundo() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: SimFundoInput) => createSimFundo(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'fundos'] });
            qc.invalidateQueries({ queryKey: ['sim', 'portfolios'] });
        },
    });
}

export function useSetupSimFundo() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: SimFundoSetupInput) => setupSimFundo(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'fundos'] });
            qc.invalidateQueries({ queryKey: ['sim', 'portfolios'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-cota-serie'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-cotistas-posicao'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-fluxos'] });
        },
    });
}

export function useSimFundCarteiras(fundoId: number | null) {
    return useQuery({
        queryKey: ['sim', 'fund-carteiras', fundoId],
        queryFn: () => getSimFundCarteiras(fundoId!),
        enabled: !!fundoId,
        staleTime: STALE,
    });
}

export function useCreateSimFundCarteira() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            fundoId,
            payload,
        }: {
            fundoId: number;
            payload: {
                ID_TITULAR: number;
                NM_CARTEIRA: string;
                ID_CORRETORA?: number | null;
                CONTA_REF?: string | null;
                MOEDA_BASE?: string;
                DT_INICIO?: string;
            };
        }) => createSimFundCarteira(fundoId, payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'fund-carteiras'] });
            qc.invalidateQueries({ queryKey: ['sim', 'portfolios'] });
        },
    });
}

export function usePostSimFundAlocacao() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            fundoId,
            payload,
        }: {
            fundoId: number;
            payload: {
                ID_CARTEIRA_ORIGEM: number;
                ID_CARTEIRA_DESTINO: number;
                VL_ALOCACAO: number;
                DT_MOVIMENTO?: string;
                DS_OBSERVACAO?: string | null;
            };
        }) => postSimFundAlocacao(fundoId, payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'fund-carteiras'] });
        },
    });
}

export function useDeleteSimFundo() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (fundoId: number) => deleteSimFundo(fundoId),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'fundos'] });
            qc.invalidateQueries({ queryKey: ['sim', 'portfolios'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-positions'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-pnl-fechamento'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-cota-serie'] });
        },
    });
}

export function useSimTitulares() {
    return useQuery({
        queryKey: ['sim', 'titulares'],
        queryFn: getSimTitulares,
        staleTime: STALE,
    });
}

export function useCreateSimTitular() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: SimTitularInput) => createSimTitular(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'titulares'] });
            qc.invalidateQueries({ queryKey: ['sim', 'portfolios'] });
        },
    });
}

export function useSimCorretoras() {
    return useQuery({
        queryKey: ['sim', 'corretoras'],
        queryFn: getSimCorretoras,
        staleTime: STALE,
    });
}

export function useCreateSimCorretora() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: SimCorretoraInput) => createSimCorretora(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'corretoras'] });
            qc.invalidateQueries({ queryKey: ['sim', 'portfolios'] });
        },
    });
}

export function useDeleteSimPortfolio() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (portfolioId: number) => deleteSimPortfolio(portfolioId),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'portfolios'] });
            qc.invalidateQueries({ queryKey: ['sim', 'trades'] });
            qc.invalidateQueries({ queryKey: ['sim', 'positions'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-positions'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-carteiras'] });
        },
    });
}

export function useSimTrades(portfolioId: number | null, dtInicio?: string, dtFim?: string) {
    return useQuery({
        queryKey: ['sim', 'trades', portfolioId, dtInicio, dtFim],
        queryFn: () => getSimTrades(portfolioId!, dtInicio, dtFim),
        enabled: !!portfolioId,
        staleTime: STALE,
    });
}

export function useCreateSimTrade() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: SimTradeInput) => createSimTrade(payload),
        onSuccess: (_, variables) => {
            qc.invalidateQueries({ queryKey: ['sim', 'trades', variables.ID_PORTFOLIO] });
            qc.invalidateQueries({ queryKey: ['sim', 'positions', variables.ID_PORTFOLIO] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-positions'] });
        },
    });
}

export function useUpdateSimTrade() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ tradeId, payload }: { tradeId: number; payload: SimTradeInput }) =>
            updateSimTrade(tradeId, payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'trades'] });
            qc.invalidateQueries({ queryKey: ['sim', 'positions'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-positions'] });
        },
    });
}

export function useDeleteSimTrade() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (tradeId: number) => deleteSimTrade(tradeId),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'trades'] });
            qc.invalidateQueries({ queryKey: ['sim', 'positions'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-positions'] });
        },
    });
}

export function useSimPositions(portfolioId: number | null) {
    return useQuery({
        queryKey: ['sim', 'positions', portfolioId],
        queryFn: () => getSimPositions(portfolioId!),
        enabled: !!portfolioId,
        staleTime: STALE,
    });
}

export function useSimCarteiraPosicaoSerie(portfolioId: number | null, dtInicio?: string, dtFim?: string) {
    return useQuery({
        queryKey: ['sim', 'carteira-posicao-serie', portfolioId, dtInicio, dtFim],
        queryFn: () => getSimCarteiraPosicaoSerie(portfolioId!, dtInicio, dtFim),
        enabled: !!portfolioId,
        staleTime: STALE,
    });
}

export function useSimFundPositions(fundoId: number | null) {
    return useQuery({
        queryKey: ['sim', 'fund-positions', fundoId],
        queryFn: () => getSimFundPositions(fundoId!),
        enabled: !!fundoId,
        staleTime: STALE,
    });
}

export function useSimFundPnlFechamentoSerie(fundoId: number | null, dtInicio?: string, dtFim?: string) {
    return useQuery({
        queryKey: ['sim', 'fund-pnl-fechamento', fundoId, dtInicio, dtFim],
        queryFn: () => getSimFundPnlFechamentoSerie(fundoId!, dtInicio, dtFim),
        enabled: !!fundoId,
        staleTime: STALE,
    });
}

export function useSimFundDashboard(
    fundoId: number | null,
    dtInicio?: string,
    dtFim?: string,
    dtReferencia?: string,
) {
    return useQuery({
        queryKey: ['sim', 'fund-dashboard', fundoId, dtInicio, dtFim, dtReferencia],
        queryFn: () => getSimFundDashboard(fundoId!, dtInicio, dtFim, dtReferencia),
        enabled: !!fundoId,
        staleTime: STALE,
    });
}

export function useCaptureSimFundPnlLive() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (fundoId: number) => postSimFundPnlLiveCapture(fundoId),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'fund-pnl-fechamento'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-positions'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-dashboard'] });
        },
    });
}

export function useCloseSimFundPnlDia() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ fundoId, dtReferencia }: { fundoId: number; dtReferencia?: string }) =>
            postSimFundPnlFechamento(fundoId, dtReferencia),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'fund-pnl-fechamento'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-positions'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-dashboard'] });
        },
    });
}

export function useBackfillSimFundPnl() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ fundoId, dtInicio, dtFim }: { fundoId: number; dtInicio: string; dtFim: string }) =>
            postSimFundPnlBackfill(fundoId, dtInicio, dtFim),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'fund-pnl-fechamento'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-positions'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-cota-serie'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-dashboard'] });
        },
    });
}

export function useSimFundCotaSerie(fundoId: number | null, dtInicio?: string, dtFim?: string) {
    return useQuery({
        queryKey: ['sim', 'fund-cota-serie', fundoId, dtInicio, dtFim],
        queryFn: () => getSimFundCotaSerie(fundoId!, dtInicio, dtFim),
        enabled: !!fundoId,
        staleTime: STALE,
    });
}

export function useRecalcSimFundCotas() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (fundoId: number) => postSimFundCotaRecalcular(fundoId),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'fund-cota-serie'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-pnl-fechamento'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-dashboard'] });
        },
    });
}

export function usePostSimFundFluxoCapital() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: {
            ID_FUNDO: number;
            ID_TITULAR?: number | null;
            DT_REFERENCIA: string;
            TP_FLUXO: 'APORTE' | 'RESGATE';
            VL_FLUXO: number;
            OBSERVACAO?: string | null;
        }) => postSimFundFluxoCapital(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'fund-cota-serie'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-pnl-fechamento'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-fluxos'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-cotistas-posicao'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-cotistas-posicao-serie'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-dashboard'] });
        },
    });
}

export function useSimFundFluxos(fundoId: number | null, dtInicio?: string, dtFim?: string) {
    return useQuery({
        queryKey: ['sim', 'fund-fluxos', fundoId, dtInicio, dtFim],
        queryFn: () => getSimFundFluxos(fundoId!, dtInicio, dtFim),
        enabled: !!fundoId,
        staleTime: STALE,
    });
}

export function useSimFundCotistasPosicao(fundoId: number | null, dtReferencia?: string) {
    return useQuery({
        queryKey: ['sim', 'fund-cotistas-posicao', fundoId, dtReferencia],
        queryFn: () => getSimFundCotistasPosicao(fundoId!, dtReferencia),
        enabled: !!fundoId,
        staleTime: STALE,
    });
}

export function useSimFundCotistasPosicaoSerie(fundoId: number | null, dtInicio?: string, dtFim?: string) {
    return useQuery({
        queryKey: ['sim', 'fund-cotistas-posicao-serie', fundoId, dtInicio, dtFim],
        queryFn: () => getSimFundCotistasPosicaoSerie(fundoId!, dtInicio, dtFim),
        enabled: !!fundoId,
        staleTime: STALE,
    });
}

export function useSimAtivosLiquidez() {
    return useQuery({
        queryKey: ['sim', 'ativos-liquidez'],
        queryFn: getSimAtivosLiquidez,
        staleTime: STALE,
    });
}

export function usePostSimAtivoLiquidez() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: {
            ID_ATIVO: number;
            NR_DIAS_LIQUIDEZ: number;
            DS_REGRA?: string | null;
            ST_ATIVO?: number;
        }) => postSimAtivoLiquidez(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'ativos-liquidez'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fundo-liquidez-opcoes'] });
        },
    });
}

export function useSimFundoLiquidezOpcoes(fundoId: number | null) {
    return useQuery({
        queryKey: ['sim', 'fundo-liquidez-opcoes', fundoId],
        queryFn: () => getSimFundoLiquidezOpcoes(fundoId!),
        enabled: !!fundoId,
        staleTime: STALE,
    });
}

export function useSimRFTitulos(stAtivo?: number) {
    return useQuery({
        queryKey: ['sim', 'rf-titulos', stAtivo],
        queryFn: () => getSimRFTitulos(stAtivo),
        staleTime: STALE,
    });
}

export function usePostSimRFTitulo() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: {
            CD_TITULO: string;
            NM_TITULO?: string | null;
            ID_ATIVO?: number | null;
            DT_VENCIMENTO: string;
            DT_RESGATE?: string | null;
            VL_TAXA_CONTRATADA?: number | null;
            ST_ATIVO?: number;
        }) => postSimRFTitulo(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'rf-titulos'] });
        },
    });
}

export function usePostSimResgateSolicitacao() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: {
            ID_FUNDO: number;
            ID_TITULAR?: number | null;
            DT_SOLICITACAO: string;
            VL_RESGATE: number;
            DS_OBSERVACAO?: string | null;
        }) => postSimResgateSolicitacao(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'resgates-solicitacoes'] });
        },
    });
}

export function useSimResgateSolicitacoes(fundoId: number | null, stStatus?: string) {
    return useQuery({
        queryKey: ['sim', 'resgates-solicitacoes', fundoId, stStatus],
        queryFn: () => getSimResgateSolicitacoes(fundoId!, stStatus),
        enabled: !!fundoId,
        staleTime: STALE,
    });
}

export function usePostSimResgatePlano() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: {
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
        }) => postSimResgatePlano(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'resgates-planos'] });
            qc.invalidateQueries({ queryKey: ['sim', 'resgates-solicitacoes'] });
        },
    });
}

export function useSimResgatePlanos(solicitacaoId: number | null) {
    return useQuery({
        queryKey: ['sim', 'resgates-planos', solicitacaoId],
        queryFn: () => getSimResgatePlanos(solicitacaoId!),
        enabled: !!solicitacaoId,
        staleTime: STALE,
    });
}

export function usePostSimResgateExecutarPlano() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            planoId,
            payload,
        }: {
            planoId: number;
            payload: {
                DT_REFERENCIA?: string;
                VL_EXECUTADO?: number;
                DS_OBSERVACAO?: string | null;
            };
        }) => postSimResgateExecutarPlano(planoId, payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'resgates-planos'] });
            qc.invalidateQueries({ queryKey: ['sim', 'resgates-solicitacoes'] });
            qc.invalidateQueries({ queryKey: ['sim', 'resgates-eventos-plano'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-fluxos'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-cota-serie'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-cotistas-posicao'] });
        },
    });
}

export function usePostSimResgateOverridePlano() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            planoId,
            payload,
        }: {
            planoId: number;
            payload: {
                DT_REFERENCIA?: string;
                DS_JUSTIFICATIVA: string;
                VL_EVENTO?: number;
            };
        }) => postSimResgateOverridePlano(planoId, payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'resgates-eventos-plano'] });
            qc.invalidateQueries({ queryKey: ['sim', 'resgates-planos'] });
        },
    });
}

export function useSimResgateEventosPlano(planoId: number | null) {
    return useQuery({
        queryKey: ['sim', 'resgates-eventos-plano', planoId],
        queryFn: () => getSimResgateEventosPlano(planoId!),
        enabled: !!planoId,
        staleTime: STALE,
    });
}

export function useSimFundRetorno(fundoId: number | null, dtInicio?: string, dtFim?: string) {
    return useQuery({
        queryKey: ['sim', 'fund-retorno', fundoId, dtInicio, dtFim],
        queryFn: () => getSimFundRetorno(fundoId!, dtInicio, dtFim),
        enabled: !!fundoId,
        staleTime: STALE,
    });
}

export function useSimFxRate(moeda: string | null, dt: string | null) {
    return useQuery({
        queryKey: ['sim', 'fx-rate', moeda, dt],
        queryFn: () => getSimFxRate(moeda!, dt!),
        enabled: !!moeda && moeda !== 'BRL' && !!dt,
        staleTime: 60 * 1000, // 1 min
    });
}
