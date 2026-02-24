# Simulador de Fundos — Proposta de Produto e Implementação

## 1) Objetivo
Criar um **simulador de carteira** (sem posições reais) para testar estratégias com:
- Renda Variável (long/short)
- Renda Fixa (prefixado, CDI+, IPCA+)
- Opções (fase 2)

Foco inicial: **MVP simples, confiável e auditável**.

---

## 2) Escopo MVP (recomendado)

### MVP v1 (entrega rápida)
1. Criar carteiras simuladas
2. Inserir operações manuais:
   - Compra/Venda de ações/ETFs
  - Short (sem modelagem de aluguel no MVP)
   - RF por título (com taxa e vencimento)
3. Calcular posição atual e PnL diário
4. Dashboard com:
   - PL da carteira
   - Exposição por classe
   - Rentabilidade acumulada
   - Série histórica de PL

### MVP v1.1
1. Curva de RF diária (marcação a mercado)
2. Cenários (alta/queda juros, bolsa, câmbio)
3. Rebalanceamento simulado

### MVP v2
1. Opções (gregas simplificadas)
2. Estratégias combinadas (travas, covered call)
3. Stress test e VaR

---

## 3) Como modelar posições (dados)

## 3.1 Entidades principais
- `SIM_PORTFOLIO`
  - `ID_PORTFOLIO`, `NM_PORTFOLIO`, `DT_INICIO`, `BENCHMARK`, `MOEDA_BASE`
- `SIM_TRADE`
  - `ID_TRADE`, `ID_PORTFOLIO`, `ID_ATIVO`, `DT_TRADE`, `SIDE` (BUY/SELL/SHORT/COVER), `QTD`, `PU`, `CUSTO`
- `SIM_POSITION_DAILY`
  - snapshot diário por ativo/carteira (quantidade, preço MTM, valor de mercado, PnL)
- `SIM_RF_POSITION`
  - RF com campos específicos: `TIPO_TAXA` (PRE, CDI, IPCA), `TAXA_CONTRATADA`, `VENCIMENTO`, `VALOR_APLICADO`, `INDEXADOR`
- `SIM_NAV_DAILY`
  - PL diário da carteira

## 3.2 Convenções
- Long: quantidade positiva
- Short: quantidade negativa
- PnL separado em:
  - `PnL_preco`
  - `PnL_carry` (juros/custo aluguel)
  - `PnL_total`

---

## 4) Regras de cálculo

## 4.1 Renda Variável
- **Valor de mercado**: `QTD * PRECO_ATUAL`
- **Preço médio**: média ponderada por compras (ou FIFO, se quiser contábil)
- **PnL não realizado**: `(PRECO_ATUAL - PRECO_MEDIO) * QTD`
- Short: sinal naturalmente invertido via `QTD < 0`

## 4.2 Short (simplificado para MVP)
- Tratar como posição negativa
- Sem custo de aluguel no MVP (apenas efeito de preço)
- Custos operacionais opcionais via campo `CUSTO` da operação

## 4.3 Renda Fixa futura (simulação)

### A) Prefixado
- Contratado por taxa anual `r`
- Preço teórico no tempo: desconto pelo prazo remanescente
- Para gráfico de carteira: usar valor presente diário

### B) CDI+
- Acumular CDI diário + spread contratado
- Atualização diária por fator

### C) IPCA+
- Atualizar inflação acumulada + taxa real
- Para simulação simples: usar série mensal de inflação projetada/interpolada

### D) Marcação a mercado (quando houver curva)
- Se tiver curva de juros por vértice:
  - descontar fluxo por taxa do prazo
- Se não tiver:
  - usar aproximação por duration

Resumo prático: no MVP, começar por **accrual diário**; depois evoluir para **MTM por curva**.

---

## 5) Visualização no site (UX)

## 5.1 Nova sessão: "Simulador"
Menu principal com 4 páginas:
1. **Carteiras**
   - criar/duplicar/arquivar carteira
2. **Operações**
   - tabela + formulário de trade
3. **Posições**
   - posição atual por ativo/classe
4. **Performance**
   - PL, retorno, drawdown, benchmark

## 5.2 Componentes principais
- Filtros: carteira, período, classe, estratégia
- KPIs topo:
  - PL atual
  - Retorno MTD/YTD
  - Volatilidade
  - Exposição long, short, líquida
- Gráficos:
  - Linha de PL
  - Barra de exposição por classe
  - Waterfall de contribuição de PnL
  - Pizza de alocação

## 5.3 Tela de posição detalhada
Ao clicar no ativo:
- Quantidade, preço médio, preço atual
- PnL aberto e realizado
- Histórico de trades
- Para RF: taxa contratada, duration, vencimento, accrual

---

## 6) Opções (como encaixar depois)

Modelo mínimo:
- `SIM_OPTION_POSITION`
  - strike, vencimento, tipo (CALL/PUT), lado (long/short), quantidade, prêmio

Cálculo MVP:
- usar preço de mercado da opção se disponível
- fallback: Black-Scholes simplificado

Métricas úteis:
- Delta por carteira
- Exposição direcional líquida
- Theta diário estimado

---

## 7) APIs sugeridas

- `POST /api/sim/portfolios`
- `GET /api/sim/portfolios`
- `POST /api/sim/trades`
- `GET /api/sim/trades?portfolio_id=&dt_inicio=&dt_fim=`
- `GET /api/sim/positions?portfolio_id=`
- `GET /api/sim/nav?portfolio_id=&dt_inicio=&dt_fim=`
- `POST /api/sim/recalculate?portfolio_id=`

---

## 8) Jobs e atualização

- Job de mercado (já existente): atualiza preços live/hist
- Job simulador (novo):
  1. recalcula posições por trade
  2. marca mercado por preço do dia
  3. grava `SIM_NAV_DAILY`

Periodicidade:
- intraday: a cada 30 min (junto do live)
- fechamento: cálculo consolidado EOD

---

## 9) Roadmap prático (4 sprints)

### Sprint 1
- Estruturas SQL do simulador
- CRUD de carteiras
- Cadastro de operações de RV/short (sem aluguel)

### Sprint 2
- Motor de posições + PnL
- Página de posições
- Série de PL da carteira

### Sprint 3
- RF (accrual diário)
- Exposição por classe e risco
- Cenários simples (choque de juros/bolsa)

### Sprint 4
- Opções (MVP)
- Stress e relatórios
- Export CSV / snapshot de carteira

---

## 10) Recomendações objetivas

1. **Começar sem opções** (deixar para v2)
2. Em RF, começar por **accrual diário**, depois MTM por curva
3. Separar claramente:
   - dados de mercado
   - dados simulados
4. Implementar trilha de auditoria:
   - toda operação com timestamp e usuário
5. Evitar complexidade precoce:
   - primeiro acertar posição e PnL

---

## 11) Definição de sucesso do MVP

- Criar carteira simulada em menos de 2 minutos
- Inserir operações e ver impacto no PL no mesmo fluxo
- Visualizar long/short/rf com transparência de cálculo
- Reproduzir carteira em qualquer data (histórico consistente)

---

## 12) Próximo passo sugerido

Implementar primeiro os schemas e endpoints de:
- carteiras
- trades
- posições consolidadas

Depois conectar uma página única de "Performance" com:
- PL diário
- alocação
- contribuição por ativo/classe
