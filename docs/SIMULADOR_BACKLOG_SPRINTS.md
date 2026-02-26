# Simulador — Backlog Executável por Sprint

## Como usar
- Cada sprint tem tarefas separadas por trilha: Dados, Backend, Frontend e QA.
- Status sugerido: TODO, DOING, DONE.
- Critério: só avançar quando o "Gate da Sprint" estiver cumprido.

---

## Sprint 0 — Higiene e baseline

### Dados
- [ ] Inventariar tabelas atuais do simulador e marcar: manter/refatorar/remover.
- [ ] Definir dicionário canônico de entidades (fundo, cotista, carteira, fluxo, cota).

### Backend
- [ ] Congelar endpoints legados com tag de depreciação.
- [ ] Criar endpoint de health do módulo simulador com versão de esquema.

### Frontend
- [ ] Marcar telas legadas como "fluxo antigo" (banner temporário).
- [x] Definir menu final alvo do simulador.

### QA
- [ ] Criar checklist de reconciliação: PL fundo x soma carteiras.
- [ ] Criar checklist de usabilidade (onboarding em até 3 min).

### Gate da Sprint
- [ ] Documento de fluxo aprovado pelo time (produto + técnico).

---

## Sprint 1 — Cotistas + Setup transacional

### Dados
- [x] Criar estrutura de cotista econômico.
- [x] Criar estrutura de seed inicial (cotas e PL inicial).

### Backend
- [x] Implementar POST /sim/fundos/setup transacional.
- [x] Implementar CRUD de cotistas.
- [x] Validar soma contribuições == PL inicial (hard fail).

### Frontend
- [x] Criar tela Cotistas (CRUD).
- [x] Criar wizard Setup do Fundo (passos + validação de diferença).

### QA
- [ ] Cenário: 3 cotistas, soma correta, criação bem-sucedida.
- [ ] Cenário: soma divergente, bloqueio de criação.

### Gate da Sprint
- [x] Fundo só nasce com seed válido e cotistas emitidos.

---

## Sprint 2 — Carteiras + caixa + alocação

### Dados
- [x] Criar/ajustar carteira caixa obrigatória por fundo.
- [x] Criar ledger de movimentos de caixa entre carteiras.

### Backend
- [x] Implementar criação de carteiras por fundo.
- [x] Titular da carteira deve ser selecionado da lista de cotistas.
- [x] Implementar alocação inicial e transferências com validação de saldo.

### Frontend
- [x] Tela de Carteiras com criação e vínculo de titular.
- [x] Tela de Alocação (origem/destino/valor, saldo disponível em tempo real).

### QA
- [ ] Cenário: não permitir alocação acima do saldo da carteira caixa.
- [ ] Cenário: total em carteiras reconcilia com PL do fundo.

### Gate da Sprint
- [ ] Nenhum valor do fundo fica fora de carteira.

---

## Sprint 3 — Operações (BUY/SELL) e posição diária

### Dados
- [x] Consolidar FAT_CARTEIRA_TRADE sem SHORT/COVER no ciclo atual.
- [x] Criar read model de posição diária por carteira.

### Backend
- [x] Implementar regras de lançamento de trade (caixa/elegibilidade).
- [x] Implementar cálculo incremental de posição diária.

### Frontend
- [x] Tela Operações simplificada (carteira -> ativo -> ordem).
- [x] Mensagens de bloqueio objetivas e acionáveis.

### QA
- [ ] Cenário: BUY e SELL com atualização de posição.
- [ ] Cenário: tentativa inválida bloqueada com motivo claro.

### Gate da Sprint
- [ ] Gestor consegue operar sem ambiguidade.

---

## Sprint 4 — Cota diária e posição econômica por cotista

### Dados
- [x] Criar/ajustar read model de posição diária do cotista.
- [x] Padronizar snapshots de cota diária por fundo.

### Backend
- [x] Regras de emissão/queima de cotas para aporte/resgate.
- [x] Cálculo de PL/PnL por cotista por data.

### Frontend
- [x] Dashboard consolidado: fundo, carteiras e cotistas.
- [x] Tela de posição do cotista por fundo.

### QA
- [ ] Teste de reprodutibilidade por histórico de fluxos.
- [ ] Reconciliação diária de PL fundo x soma carteiras.

### Gate da Sprint
- [ ] Reconciliação 100% no período testado.

---

## Sprint 5 — Liquidez e módulo de Renda Fixa

### Dados
- [x] Adicionar DTC para ativos negociáveis.
- [x] Criar cadastro de título RF com data de resgate/vencimento.

### Backend
- [x] Expor endpoints de liquidez por ativo/título.
- [x] Regras específicas para RF sem liquidez diária.

### Frontend
- [x] Nova seção Renda Fixa na navegação.
- [x] Exibir liquidez como D+N ou data fixa de resgate.

### QA
- [ ] Cenário: título RF sem liquidez diária identificado corretamente.
- [ ] Cenário: ativo com DTC refletido no dashboard.

### Gate da Sprint
- [ ] Gestor enxerga claramente liquidez real por instrumento.

---

## Sprint 6 — Resgate assistido (decisão do gestor)

### Dados
- [x] Estruturar solicitação, plano e itens de plano com versionamento.
- [x] Estruturar trilha de auditoria para override.

### Backend
- [x] Implementar criação de solicitação de resgate.
- [x] Implementar plano manual por ativo/título com validação de cronograma.
- [x] Implementar execução parcial/total.
- [x] Implementar override de MTM com justificativa obrigatória.

### Frontend
- [x] Tela Resgates com assistente de plano manual.
- [x] Timeline de liquidação por item.
- [x] Fluxo de confirmação forte para override.

### QA
- [ ] Cenário: resgate parcial com pendência.
- [ ] Cenário: override registrado e auditável.

### Gate da Sprint
- [ ] Resgate completo com trilha ponta a ponta.

---

## Sprint 7 — UX final, performance e governança

### Dados
- [x] Revisar índices e consultas críticas dos read models.

### Backend
- [x] Otimizar endpoints consolidados para uso em dashboard.
- [ ] Fechar métricas de consistência e monitoramento.

### Frontend
- [ ] Revisão final de fluxo e simplificação de navegação.
- [ ] Estados vazios e mensagens de erro padronizados.

### QA
- [ ] Teste de jornada completa de usuário novo (meta <= 3 min no setup).
- [ ] Teste de regressão do simulador completo.

### Gate da Sprint (Goal Final)
- [ ] Onboarding rápido, operação clara, resgates auditáveis e reconciliação íntegra.

---

## Quadro de dependências críticas
- Sprint 1 depende de aprovação do modelo de cotista e setup transacional.
- Sprint 2 depende da carteira caixa definida no setup.
- Sprint 4 depende de eventos confiáveis de Sprint 1-3.
- Sprint 6 depende da camada de liquidez de Sprint 5.

---

## Definição de pronto global
- [ ] Fluxo principal sem bloqueios manuais fora do sistema.
- [ ] Nenhum cálculo econômico dependente de planilha externa.
- [ ] Logs e auditoria suficientes para explicar qualquer número no dashboard.
