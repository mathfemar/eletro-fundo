import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getPrecosLive,
    getResumoHistorico,
    getHistoricoAtivo,
    atualizarPrecosLive,
    getPrecosLiveSerieAtivo,
} from '@/api/precos';

const TRINTA_MINUTOS = 30 * 60 * 1000;

export function usePrecosLive() {
    return useQuery({
        queryKey: ['precos', 'live'],
        queryFn: getPrecosLive,
        staleTime: TRINTA_MINUTOS,
        refetchInterval: TRINTA_MINUTOS,
        refetchOnWindowFocus: false,
    });
}

export function useResumoHistorico() {
    return useQuery({
        queryKey: ['precos', 'historico', 'resumo'],
        queryFn: getResumoHistorico,
        staleTime: TRINTA_MINUTOS,
    });
}

export function useRefreshCache() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: atualizarPrecosLive,
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['ativos'] });
            qc.invalidateQueries({ queryKey: ['ativos', 'online'] });
            qc.invalidateQueries({ queryKey: ['ativos-meta'] });
            qc.invalidateQueries({ queryKey: ['precos', 'live'] });
            qc.invalidateQueries({ queryKey: ['precos', 'live', 'serie'] });
            qc.invalidateQueries({ queryKey: ['precos', 'historico', 'resumo'] });
        },
    });
}

export function useHistoricoAtivo(
    cdAtivo: string | null,
    dtInicio?: string,
    dtFim?: string,
) {
    return useQuery({
        queryKey: ['precos', 'historico', cdAtivo, dtInicio, dtFim],
        queryFn: () => getHistoricoAtivo(cdAtivo!, dtInicio, dtFim),
        enabled: !!cdAtivo,
        staleTime: TRINTA_MINUTOS,
    });
}

export function usePrecosLiveSerie(cdAtivo: string | null, horas = 24) {
    return useQuery({
        queryKey: ['precos', 'live', 'serie', cdAtivo, horas],
        queryFn: () => getPrecosLiveSerieAtivo(cdAtivo!, horas),
        enabled: !!cdAtivo,
        staleTime: TRINTA_MINUTOS,
        refetchInterval: TRINTA_MINUTOS,
        refetchOnWindowFocus: false,
    });
}
