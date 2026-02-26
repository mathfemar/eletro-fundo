# Simulador — Fluxo de Dados Alvo (Pente Fino v2)

## 1. Objetivo
Definir um fluxo único e intuitivo para o Simulador, com:
- dados sem redundância;
- regras econômicas claras;
- UI guiada para evitar erro operacional.

Este documento é a referência de produto e implementação para backend + frontend.

---

## 2. Correções de domínio (definitivas)
1. Não haverá aluguel de ações no MVP.
2. Portanto, não usar SHORT/COVER neste ciclo.
3. Derivativos permitidos no escopo: opções (CALL/PUT) em fase própria.
4. Cotista é dono econômico (cotas); titular de carteira é só rastreio operacional.
5. Fundo = agregado das carteiras; PL do fundo deve bater com soma das carteiras.

---

## 3. Modelo conceitual limpo

### 3.1 Pessoas
- DIM_COTISTA
  - cadastro econômico (participa do fundo via cotas)
- DIM_TITULAR_CARTEIRA (opcional; pode ser a própria DIM_COTISTA)
  - metadado de conta/custódia da carteira

Regra:
- toda carteira escolhe titular a partir da lista de cotistas;
- nem todo cotista precisa ter carteira.

### 3.2 Estrutura do fundo
- DIM_FUNDO
- DIM_CARTEIRA
- RL_FUNDO_CARTEIRA

### 3.3 Ledger de eventos
- FAT_FUNDO_FLUXO_COTISTA
  - aporte/resgate de cotista
- FAT_CARTEIRA_MOVIMENTO_CAIXA
  - alocação entre carteiras (inclui carteira caixa)
- FAT_CARTEIRA_TRADE
  - BUY/SELL e, depois, OPTIONS_CALL/OPTIONS_PUT

### 3.4 Read models
- FAT_FUNDO_COTA_DIARIA
- FAT_COTISTA_POSICAO_DIARIA
- FAT_CARTEIRA_POSICAO_DIARIA

### 3.5 Liquidez
- DIM_ATIVO_LIQUIDEZ
  - coluna DTC (days to cover) para ativos negociáveis
- DIM_TITULO_RF
  - data de resgate/vencimento e regras de liquidez de RF

---

## 4. Invariantes obrigatórias

### 4.1 Criação do fundo com PL inicial
- informar PL inicial;
- informar cotistas iniciais + contribuição por cotista;
- validar: soma(contribuições) = PL inicial;
- cota inicial padrão = 1.0;
- cotas por cotista = contribuição / cota inicial;
- cotas totais = soma das cotas dos cotistas.

### 4.2 Ownership econômico
- cotista não recebe ativo na saída, recebe financeiro;
- carteira não representa “propriedade do ativo por pessoa”; apenas operacional.

### 4.3 Agregação
- PL_FUNDO = soma(PL de todas as carteiras do fundo);
- usar carteira caixa obrigatória para capital não alocado.

---

## 5. UX alvo (fácil de usar)

## 5.1 Sessões do Simulador
1. Setup do Fundo
2. Cotistas
3. Carteiras
4. Operações
5. Resgates
6. Visão Consolidada
7. Renda Fixa (nova seção dedicada)

## 5.2 Setup do Fundo (wizard)
Passo 1: dados do fundo
- nome, benchmark, moeda, data início, PL inicial, cota inicial.

Passo 2: cotistas iniciais
- selecionar cotista cadastrado previamente;
- permitir cadastro rápido de cotista nesta etapa;
- grade com valor por cotista e soma dinâmica;
- botão Criar Fundo habilita só quando diferença = 0.

Passo 3: carteiras
- criar carteira caixa automática;
- criar carteiras de estratégia;
- titular da carteira selecionado da lista de cotistas.

Passo 4: alocação inicial
- mover da carteira caixa para carteiras de estratégia.

## 5.3 Tela de Cotistas
Necessária e obrigatória, contendo:
- cadastro/edição de cotistas;
- posição por fundo de cada cotista;
- cotas, PL, PnL e investido líquido;
- indicador se o cotista possui carteira vinculada como titular.

## 5.4 Tela de Operações
Fluxo:
1. gestor escolhe carteira;
2. lança trade;
3. sistema valida caixa e elegibilidade.

Tabela de ativos deve exibir:
- tipo de ativo;
- DTC (> 0) para ativos negociáveis;
- para RF, referência de liquidez pela data de resgate/vencimento do título.

---

## 6. Liquidez para resgate (assistida, não automática)

### 6.1 Regra geral
- decisão é do gestor;
- sistema sugere e valida;
- execução é manual confirmada.

### 6.2 Sugestão no dashboard
- listar ativos com:
  - valor disponível;
  - DTC / D+N;
  - menor data de liquidação;
  - impacto no plano.

### 6.3 Caso especial: Renda Fixa sem liquidez diária
- mostrar explicitamente a data de resgate do título;
- destacar como “sem liquidez diária” quando aplicável;
- bloquear plano que dependa de liquidez antes da data de resgate.

### 6.4 Override de marcação a mercado (ex.: Tesouro)
- permitir opção de override para “venda a mercado” quando instrumento suportar;
- exigir confirmação explícita + justificativa;
- registrar auditoria (quem, quando, motivo, premissas de preço).

---

## 7. APIs mínimas (alvo)

## 7.1 Setup
- POST /sim/fundos/setup
  - cria fundo + cotistas iniciais + carteira caixa + seed de cotas em transação única

## 7.2 Cotistas
- GET /sim/cotistas
- POST /sim/cotistas
- GET /sim/cotistas/{id}/posicao

## 7.3 Carteiras
- POST /sim/fundos/{id}/carteiras
- GET /sim/fundos/{id}/carteiras
- POST /sim/fundos/{id}/alocacoes

## 7.4 Operações
- POST /sim/carteiras/{id}/trades
- GET /sim/carteiras/{id}/posicao

## 7.5 Liquidez e RF
- GET /sim/fundos/{id}/liquidez/opcoes
- POST /sim/ativos/{id}/dtc
- GET /sim/rf/titulos
- POST /sim/rf/titulos

## 7.6 Resgates
- POST /sim/fundos/{id}/resgates/solicitacoes
- POST /sim/resgates/{id}/plano
- POST /sim/resgates/{id}/executar
- POST /sim/resgates/{id}/override-mtm

---

## 8. Critérios de aceite (pente fino)
1. Setup não finaliza se soma dos cotistas != PL inicial.
2. Cotista aparece com posição por fundo mesmo sem carteira própria.
3. Carteira só usa titular da lista de cotistas.
4. Fundo reconcilia 100% com soma das carteiras.
5. Operação inválida por caixa/liquidez mostra motivo claro.
6. Resgate exibe DTC e datas de liquidez por ativo/título.
7. RF sem liquidez diária mostra data de resgate obrigatoriamente.
8. Override MTM fica auditado e rastreável.

---

## 9. Decisões explícitas deste documento
- Sem short/cover neste ciclo.
- Opções (CALL/PUT) entram como trilha específica, separada de aluguel.
- Cotista = ownership econômico.
- Titular de carteira = metadado operacional.
- Resgate = decisão manual do gestor com assistência do sistema.

---

## 10. Roadmap em sprints (do início ao goal final)

Backlog executável detalhado:
- docs/SIMULADOR_BACKLOG_SPRINTS.md

## Sprint 0 — Higiene e alinhamento de base
Objetivo:
- congelar escopo e remover ambiguidades de domínio.

Entregas:
- validar este documento como contrato funcional;
- mapear o que do código atual será reaproveitado, refatorado ou removido;
- criar checklist de reconciliação (PL fundo x soma carteiras).

Pronto quando:
- time concorda com regras de cotista, titular, carteira caixa e resgate manual.

## Sprint 1 — Cadastros e setup transacional do fundo
Objetivo:
- criar onboarding correto do fundo desde o primeiro dia.

Entregas:
- tela de Cotistas (CRUD);
- wizard Setup do Fundo com validação de soma das contribuições;
- endpoint único de setup transacional (fundo + cotistas iniciais + carteira caixa + seed de cotas).

Pronto quando:
- não é possível criar fundo com diferença entre PL inicial e soma dos cotistas;
- cotistas iniciais já saem com cotas emitidas corretamente.

## Sprint 2 — Carteiras, alocação e trilha de caixa
Objetivo:
- organizar toda origem e destino de caixa entre fundo e carteiras.

Entregas:
- criação de carteiras com titular escolhido da lista de cotistas;
- fluxo de alocação inicial e movimentações de caixa entre carteiras;
- validações de saldo para impedir alocação acima do disponível.

Pronto quando:
- todo valor do fundo está em alguma carteira (incluindo carteira caixa);
- não existe caixa órfão fora da estrutura de carteiras.

## Sprint 3 — Operações e posição diária por carteira
Objetivo:
- lançar trades com validação clara e cálculo confiável de posição.

Entregas:
- operações BUY/SELL (sem short/cover);
- read model de posição diária por carteira;
- mensagens de bloqueio objetivas para erros de elegibilidade/caixa.

Pronto quando:
- gestor consegue operar sem ambiguidade e entender por que uma operação foi bloqueada.

## Sprint 4 — Cota do fundo e posição econômica do cotista
Objetivo:
- fechar ciclo contábil do fundo com visibilidade por cotista.

Entregas:
- cálculo de cota diária por fundo;
- posição diária por cotista (cotas, PL, PnL, investido líquido);
- dashboard consolidado fundo x cotistas x carteiras.

Pronto quando:
- posição de cada cotista é reproduzível por histórico de fluxos + cotas;
- reconciliação PL fundo = soma PL carteiras passa em 100% dos dias.

## Sprint 5 — Liquidez e módulo de Renda Fixa
Objetivo:
- tornar a liquidez explícita para decisões de resgate.

Entregas:
- coluna DTC para ativos negociáveis;
- seção dedicada de Renda Fixa com cadastro do título e data de resgate/vencimento;
- regra de identificação de títulos sem liquidez diária.

Pronto quando:
- dashboard distingue claramente D+N versus data fixa de resgate para RF.

## Sprint 6 — Resgate assistido com decisão do gestor
Objetivo:
- permitir resgate seguro e auditável, mantendo poder decisório no gestor.

Entregas:
- solicitação de resgate;
- plano manual de liquidação por ativo/título;
- validação de cronograma e execução parcial/total;
- override de marcação a mercado com justificativa e auditoria.

Pronto quando:
- todo resgate possui trilha: solicitação, plano, execução e evidência de decisão.

## Sprint 7 — UX final, performance e governança
Objetivo:
- fechar produto com experiência intuitiva e operação rápida.

Entregas:
- revisão de navegação e redução de passos desnecessários;
- otimização de queries e invalidação dirigida por evento;
- painéis de status operacional (pendências, reconciliação, inconsistências).

Pronto quando (goal final):
- usuário novo cria fundo completo em até 3 minutos;
- operação diária é objetiva e sem telas confusas;
- resgate é conduzido com segurança, transparência e auditoria completa.
