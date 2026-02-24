import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    getSimPortfolios,
    createSimPortfolio,
    getSimFundos,
    createSimFundo,
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
    getSimFundPositions,
    getSimFundPnlFechamentoSerie,
    postSimFundPnlLiveCapture,
    postSimFundPnlFechamento,
    postSimFundPnlBackfill,
    getSimFundCotaSerie,
    postSimFundCotaRecalcular,
    type SimPortfolioInput,
    type SimFundoInput,
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

export function useCaptureSimFundPnlLive() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (fundoId: number) => postSimFundPnlLiveCapture(fundoId),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['sim', 'fund-pnl-fechamento'] });
            qc.invalidateQueries({ queryKey: ['sim', 'fund-positions'] });
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
        },
    });
}
