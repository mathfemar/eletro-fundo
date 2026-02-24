import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAtivos, getAtivosOnline, getAtivosMeta, criarAtivo, atualizarAtivo } from '@/api/ativos';
import type { AtivoInput } from '@/api/ativos';

export function useAtivos() {
    return useQuery({
        queryKey: ['ativos'],
        queryFn: getAtivos,
        staleTime: 5 * 60 * 1000,
    });
}

/** Apenas ativos com PRECO_ONLINE=1 — usado nos seletores de Preços e Histórico. */
export function useAtivosOnline() {
    return useQuery({
        queryKey: ['ativos', 'online'],
        queryFn: getAtivosOnline,
        staleTime: 5 * 60 * 1000,
    });
}

export function useAtivosMeta() {
    return useQuery({
        queryKey: ['ativos-meta'],
        queryFn: getAtivosMeta,
        staleTime: 30 * 60 * 1000, // dimensiões mudam raramente
    });
}

export function useCriarAtivo() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (payload: AtivoInput) => criarAtivo(payload),
        onSuccess: () => qc.invalidateQueries({ queryKey: ['ativos'] }),
    });
}

export function useAtualizarAtivo() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ cdAtivo, payload }: { cdAtivo: string; payload: AtivoInput }) =>
            atualizarAtivo(cdAtivo, payload),
        onSuccess: () => qc.invalidateQueries({ queryKey: ['ativos'] }),
    });
}
