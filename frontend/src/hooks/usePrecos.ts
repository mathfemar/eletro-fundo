import { useQuery } from '@tanstack/react-query';
import { getPrecosLive, getResumoHistorico, getHistoricoAtivo } from '@/api/precos';

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
