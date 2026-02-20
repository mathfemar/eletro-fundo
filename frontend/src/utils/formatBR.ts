/**
 * Helpers de formatação para o mercado brasileiro.
 */

/** R$ 1.234,56 */
export function formatMoeda(value: number | null | undefined, decimals = 2): string {
    if (value == null || isNaN(value)) return '—';
    return value.toLocaleString('pt-BR', {
        style: 'currency',
        currency: 'BRL',
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

/** 12,34% */
export function formatPct(value: number | null | undefined, decimals = 2): string {
    if (value == null || isNaN(value)) return '—';
    return `${value.toLocaleString('pt-BR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    })}%`;
}

/** 1.234,56 */
export function formatNumero(value: number | null | undefined, decimals = 2): string {
    if (value == null || isNaN(value)) return '—';
    return value.toLocaleString('pt-BR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

/** "2025-01-15" → "15/01/2025" */
export function formatData(dateStr: string | null | undefined): string {
    if (!dateStr) return '—';
    const d = new Date(dateStr + 'T00:00:00');
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('pt-BR');
}

/** Retorna classe CSS para colorir variações (+/-) */
export function variacaoClass(value: number | null | undefined): string {
    if (value == null) return '';
    if (value > 0) return 'positivo';
    if (value < 0) return 'negativo';
    return 'neutro';
}
