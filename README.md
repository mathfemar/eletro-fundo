# Analisador de Fundos de Investimentos

Projeto com backend em FastAPI, frontend em React + Vite + TypeScript e banco SQLite.

## Estrutura

- [backend](backend): API, cálculo de cotas, integração com `yfinance` e agendamentos.
- [frontend](frontend): interface React para ativos, preços e simulação do fundo.
- [main.db](main.db): banco SQLite principal, preservando `DIM_ATIVO` e `DIM_ATIVO_MAPPING`.
- [YFinanceConfig.py](YFinanceConfig.py): configuração de proxy/SSL para `yfinance`.

## Regras principais

- `VL_COTA = PL / QTD_COTA`
- aportes e resgates não alteram o valor da cota do instante;
- eventos retroativos disparam reprocessamento completo da linha do tempo do fundo;
- proventos entram em caixa e compensam a queda ex-dividendo;
- preços online usam apenas ativos com `PRECO_ONLINE = 1` e `CD_YF` preenchido.

## Backend

Instalação:

1. criar/ativar ambiente virtual;
2. instalar dependências de [backend/requirements.txt](backend/requirements.txt);
3. subir a API a partir da raiz do projeto com `uvicorn backend.app.main:app --reload`.

Testes:

- `pytest backend/tests -q`

## Frontend

Instalação:

1. entrar em [frontend](frontend);
2. instalar dependências com `npm install`;
3. rodar com `npm run dev`.

Testes:

- `npm run test`
