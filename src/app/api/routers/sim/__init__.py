"""
sim/ — Pacote que organiza os endpoints do simulador em módulos separados.

Módulos:
  - common:     Helpers, Pydantic models, utilitários compartilhados
  - fundos:     CRUD de fundos, setup, exclusão, fluxos
  - carteiras:  CRUD de carteiras, alocação de caixa, portfolios legados
  - trades:     CRUD de trades, posições por carteira e fundo
  - pnl:        PnL live/fechamento, cotas, retorno, dashboard
  - cotistas:   Titulares, corretoras, cotistas, posição diária
  - resgates:   Solicitações, planos, itens, execução, override MTM
  - renda_fixa: RF títulos, liquidez por ativo
"""
