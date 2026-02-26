# Gráfico de Retorno Consolidado do Fundo

## Conceito

Série de retorno baseada na **cota do fundo**, não em PnL absoluto.
Imune a distorções por aportes/resgates (emissão/queima de cotas mantém o valor da cota).

$$R_t = \frac{cota_t}{cota_0} - 1$$

### Regra de contabilização temporal
- Posições contam **a partir do momento da compra**, não retroativamente.
- Compra → caixa sai, ativo entra ao mesmo preço → retorno naquele tick = 0%.
- Variação subsequente do ativo marca retorno via cota.
- Venda parcial → preço médio recalculado, PnL realizado prévia computado.

### Granularidade
- Presa ao scheduler do yfinance (~30 min).
- Após cada ciclo do yf: captura live → fecha dia provisoriamente → recomputa cotas.
- EOD (19h SP) faz o fechamento definitivo.

---

## Tarefas

### Backend
- [x] Criar endpoint `GET /api/sim/fundos/{id}/retorno?dt_inicio=&dt_fim=`
  - Lê `FAT_FUNDO_COTA_DIARIA`
  - Calcula retorno diário e acumulado
  - Retorna `[{ DT_REFERENCIA, VL_COTA, RETORNO_DIA_PCT, RETORNO_ACUM_PCT }]`
- [x] Integrar no scheduler: após live capture, chamar `close_pnl_day_fundo_sync` + `recompute_fundo_cotas_sync` para manter cota intraday atualizada

### Frontend
- [x] API function `getSimFundRetorno()` em `simulador.ts`
- [x] Hook `useSimFundRetorno()` em `useSimulador.ts`
- [x] Gráfico Plotly em `Fundos.tsx`: linha de retorno acumulado (%)
- [x] Tabela em `Fundos.tsx` com posições consolidadas do fundo (preço médio, preço atual, valor de mercado, exposição %, PnL)

### Dados
- Nenhuma tabela nova. Tudo derivado de `FAT_FUNDO_COTA_DIARIA`.

---

## Fluxo de dados (ponta a ponta)

```
Scheduler yfinance (30 min)
    │
    ├── 1. PricingLiveService().atualizar_todos()
    │       → preços de mercado atualizados
    │
    ├── 2. capture_pnl_live_fundo_sync() (cada fundo ativo)
    │       → snapshot PnL em FAT_FUNDO_PNL_LIVE
    │
    └── 3. close_pnl_day_fundo_sync() + recompute_fundo_cotas_sync()
            → fecha dia provisório + atualiza cota em FAT_FUNDO_COTA_DIARIA
            → série de retorno atualizada automaticamente
```

---

## Critérios de aceite
1. Gráfico mostra retorno acumulado (%) desde a primeira cota.
2. Atualiza automaticamente a cada ciclo do scheduler (~30 min).
3. Aportes/resgates não distorcem a curva de retorno.
4. Tooltip mostra data, cota e retorno acumulado.
