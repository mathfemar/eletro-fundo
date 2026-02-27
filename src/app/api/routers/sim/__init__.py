"""
sim/ — Pacote de módulos do simulador de carteiras.

Módulos:
  models.py     — Pydantic models (inputs de API)
  helpers.py    — utilitários de data/hora, entidade, FX e trade
  caixa.py      — saldo de caixa, validação de capital
  positions.py  — motor de posições, MtM, posição diária
  cotas.py      — NAV/cotas, retorno, posição de cotistas
  pnl.py        — captura live, fechamento, backfill, catch-up
"""
