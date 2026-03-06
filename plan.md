## Plan: Analisador de Fundos

Rascunho: estruturar o projeto do zero com backend em FastAPI, frontend em React + Vite + TypeScript e SQLite, reaproveitando [YFinanceConfig.py](YFinanceConfig.py) como utilitário de infraestrutura para `yfinance`. O banco será redesenhado, mas preservando o papel funcional de `DIM_ATIVO` e `DIM_ATIVO_MAPPING` descrito por você, incluindo a flag `preco_online`. O núcleo da solução será orientado a eventos, para suportar trades, aportes, resgates e proventos retroativos com reprocessamento completo da linha do tempo a partir do evento afetado, mantendo a regra `VL_COTA = PL / QTD_COTA` e sem alterar valor da cota por aportes/resgates. Também entram duas frentes de preço: histórico `adj_close` e intraday `price_live` 1D com atualização a cada 30 minutos e deduplicação de pontos repetidos.

**Steps**
1. Estruturar o monorepo com dois apps principais: backend FastAPI e frontend React/Vite/TypeScript, mantendo [YFinanceConfig.py](YFinanceConfig.py) como módulo compartilhável do backend, porque a função `configure_yfinance_for_corporate_proxy()` já resolve o cenário de proxy/SSL antes do import de `yfinance` em [YFinanceConfig.py](YFinanceConfig.py#L64-L122).

2. Definir o schema SQLite novo com separação clara entre cadastro, eventos e dados derivados:
   - `DIM_ATIVO`: cadastro mestre do ativo, incluindo status, tipo/classe e `preco_online`.
   - `DIM_ATIVO_MAPPING`: vínculo do `id_ativo` com ticker Yahoo.
   - tabelas de domínio para `fundo`, `cotista`, relacionamento fundo-cotista, operações de caixa, trades, proventos e posições.
   - tabelas derivadas para séries de NAV/cota, histórico `adj_close`, snapshots intraday e retorno histórico de ativos.
   Como [main.db](main.db) não pôde ser inspecionado por schema textual, o plano assume migração conceitual, não cópia cega da estrutura antiga.

3. Modelar o motor de cálculo do fundo em backend como replay transacional:
   - início do fundo em data-base com caixa inicial de um ou mais cotistas;
   - aportes e resgates emitem/movimentam cotas sem mudar o valor da cota do instante;
   - trades alteram caixa e posição;
   - proventos entram como caixa do fundo e compensam a queda ex-dividendo, sem distorcer a série de retorno;
   - qualquer evento retroativo dispara reprocessamento completo desde o evento mais antigo impactado até a data atual.

4. Separar o backend em camadas simples e legíveis:
   - API FastAPI;
   - serviços de domínio para `ativos`, `precos`, `proventos`, `fundos`, `cotistas` e `simulacao`;
   - repositórios SQLite;
   - motor de replay/cálculo;
   - jobs agendados.
   O uso do Yahoo deve ficar encapsulado em um client próprio, que aplica [YFinanceConfig.py](YFinanceConfig.py#L64-L122) e usa as URLs listadas em [YFinanceConfig.py](YFinanceConfig.py#L183-L198) apenas indiretamente via `yfinance`.

5. Planejar a ingestão de mercado em dois fluxos:
   - histórico `adj_close`: carga por ativo mapeado com `preco_online = true`, persistindo série diária e tabela de retorno histórico;
   - `price_live` 1D: job agendado a cada 30 minutos, buscando intraday e gravando apenas pontos novos cujo preço difira do último snapshot persistido.
   O filtro por `preco_online` evita chamadas desnecessárias e mantém aderência ao cadastro do ativo.

6. Incluir importação automática de proventos quando o Yahoo disponibilizar o dado:
   - registrar evento de provento por ativo e data ex/pagamento;
   - refletir o recebimento em caixa;
   - manter a consistência da marcação a mercado e da série do fundo.
   Se houver limitação de cobertura por ativo, o plano prevê status de sincronização e fallback de conferência manual.

7. Expor endpoints REST enxutos para:
   - cadastro e consulta de ativos/mappings;
   - sincronização de preços históricos, live e proventos;
   - criação de fundo e cotistas;
   - lançamento de aportes, resgates e trades retroativos;
   - consulta de posições, caixa, PL, quantidade de cotas, valor da cota e série histórica;
   - consulta analítica de retorno por ativo e do fundo.

8. Projetar o frontend com páginas focadas em operação e leitura:
   - visão geral do fundo;
   - página de ativos com `adj_close`, retorno e metadados;
   - página exclusiva de `price_live` 1D com gráfico intraday;
   - tela de operações retroativas;
   - tela de cotistas/aportes/resgates;
   - tela de evolução de PL, cotas e valor da cota.
   O frontend consome APIs prontas e evita lógica financeira duplicada.

9. Definir a UX para retroatividade:
   - qualquer inclusão/edição/exclusão de evento antigo mostra que haverá recálculo;
   - o backend reprocessa e devolve novo estado consolidado;
   - o frontend atualiza timeline, posições e série histórica com transparência do impacto.

10. Organizar testes desde o início, com pasta `tests` em cada app:
    - backend: unitários para regras de cotas, trades, proventos e replay; integração para repositórios SQLite; testes de API para fluxos completos;
    - frontend: testes de componentes, hooks, páginas e integração de chamadas;
    - cenários obrigatórios: inicialização do fundo, múltiplos cotistas, aporte sem mudar `VL_COTA`, resgate sem distorção de cota, trade retroativo, aporte retroativo, provento automático, ativo sem `preco_online`, ativo sem mapping, snapshot intraday duplicado, mercado fechado sem hardcode de horário.

11. Prever observabilidade mínima:
    - logs de sincronização Yahoo;
    - status de jobs;
    - rastreio de eventos reprocessados;
    - flags de erro por ativo.
    Isso é especialmente importante porque a cobertura do Yahoo pode variar por ticker e por tipo de ativo.

12. Fechar o handoff com uma ordem de execução prática:
    - primeiro backend e schema;
    - depois motor de cálculo e ingestão de preços/proventos;
    - então APIs;
    - depois frontend;
    - por fim testes integrados e ajuste fino de performance.

**Verification**
- Backend: suíte automatizada cobrindo cálculo de cotas, replay retroativo, trades, proventos, sincronização `adj_close` e snapshots `price_live`.
- Frontend: testes de renderização, estados de carregamento/erro, gráficos e fluxos de operação retroativa.
- Integração: cenário ponta a ponta com fundo iniciado em data fixa, mais de um cotista, compra de ativos, provento, aporte retroativo e recálculo completo.
- Banco: validação de integridade entre `DIM_ATIVO`, `DIM_ATIVO_MAPPING`, flag `preco_online`, histórico diário e snapshots intraday.
- Scheduler: confirmar execução a cada 30 minutos e não persistência de pontos com preço idêntico ao último.

**Decisions**
- Banco novo em SQLite, preservando apenas o papel funcional de `DIM_ATIVO` e `DIM_ATIVO_MAPPING`.
- Frontend em React + Vite + TypeScript.
- Escopo inicial inclui simulador do fundo e análise.
- Preço online só para ativos mapeados e com `preco_online` habilitado.
- Histórico diário em `adj_close`.
- Página separada para `price_live` 1D.
- Proventos com importação automática e entrada em caixa, sem alterar a lógica de retorno/cota.
- Reprocessamento completo para qualquer evento retroativo.

**Ponto crítico já identificado**
- O schema interno de [main.db](main.db) não ficou legível nas ferramentas disponíveis. O plano acima continua válido porque você decidiu redesenhar o banco, mas a execução deverá começar com uma inspeção real do SQLite para extrair o significado exato das colunas úteis de `DIM_ATIVO` e `DIM_ATIVO_MAPPING` antes da migração/importação.
