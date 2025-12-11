# 🎨 Design & UX - Eletro Fundo Webapp

## 1. Paleta de Cores

**Inspiração:** Dashboard financeiro profissional (Bloomberg, Robinhood, Nubank)

### Core Colors
- **Primary:** `#1F77B4` (Azul profissional – headers, buttons principais)
- **Secondary:** `#2CA02C` (Verde – ganhos/positivo)
- **Alert:** `#D62728` (Vermelho – perdas/negativo)
- **Neutral Dark:** `#2C3E50` (Fundo principal, texto)
- **Neutral Light:** `#ECF0F1` (Backgrounds secundários)
- **Accent Gold:** `#F39C12` (Destaque – cotas, valores importantes)

### Aplicação
- **Navbar:** `#2C3E50` (escuro) com logo em branco
- **Cards:** Branco (`#FFF`) com border sutil `#BDC3C7`
- **Buttons:** Primary `#1F77B4`, Secondary `#95A5A6`
- **Positivo:** `#27AE60` (texto/ícones)
- **Negativo:** `#E74C3C` (texto/ícones)

---

## 2. Layout & Seções

```
┌─────────────────────────────────────────┐
│  Eletro Fundo | Home | Posições | ... ▼ │ (Navbar fixo, #2C3E50)
├─────────────────────────────────────────┤
│                                         │
│  📊 DASHBOARD (Hero Section)            │
│  ┌────────────┬────────────┬────────────┐
│  │ PL Atual   │ Cota Hoje  │ Variação % │ (Cards grandes, #1F77B4 icons)
│  │ R$ 45.2K   │ R$ 1.052   │ +2.15%     │
│  └────────────┴────────────┴────────────┘
│                                         │
│  📈 GRÁFICO (Curva de cotas últimos 90d)│
│  ┌─────────────────────────────────────┐
│  │ [Plotly Chart – linha com area]     │
│  └─────────────────────────────────────┘
│                                         │
│  📋 POSIÇÕES (Tabela interativa)        │
│  ┌─────────────────────────────────────┐
│  │ Ativo  | Qtd | P. Médio | P. Atual  │
│  │ PETR4  | 100 | R$ 24.50 | R$ 25.10  │
│  │ VALE3  |  50 | R$ 61.20 | R$ 62.80  │
│  └─────────────────────────────────────┘
│                                         │
└─────────────────────────────────────────┘
```

---

## 3. Estrutura de Páginas

### **Página: HOME / DASHBOARD** 
**Path:** `/`

**Componentes:**
1. **Hero Cards** (3 cards grandes lado a lado)
   - PL Atual (big number, cor conforme negativo/positivo)
   - Valor Cota Hoje (com variação diária)
   - Total Investido vs Resgatado

2. **Gráfico Principal** (Curva de cotas)
   - Últimos 90 dias (ou customizável)
   - Hover mostra data e valor
   - Botões: 1W, 1M, 3M, 6M, 1Y

3. **Tabela de Posições** (com search/filter)
   - Ativo | Qty | Preço Médio | Preço Atual | Ganho/Perda | % Ganho
   - Linhas com cores: verde (ganho) / vermelho (perda)

4. **Resumo de Operações** (últimas 5)
   - Data | Tipo (COMPRA/VENDA/APORTE/RESGATE) | Ativo | Valor | Status

---

### **Página: OPERAÇÕES**
**Path:** `/operacoes`

**Abas/Tabs:**

#### **Tab 1: Nova Movimentação** (COMPRA/VENDA)
Form 2-col:
```
[Ativo Dropdown v]        [Tipo: ◉ COMPRA ○ VENDA]
[Data picker]             [Quantidade]
[Preço Unitário]          [Comissão]
[Observações (opcional)]  [ Inserir Operação ]
```

#### **Tab 2: Aporte/Resgate**
Form simples:
```
[Tipo: ◉ APORTE ○ RESGATE]
[Data]
[Quantidade de Cotas]
[Valor da Cota (auto-filled)]
[Valor Total (auto-calc)]
[ Confirmar Operação ]
```

#### **Tab 3: Histórico de Operações** (Tabela filtrada)
- Data | Tipo | Ativo | Qtd | Preço | Comissão | Total
- Paginação + search

---

### **Página: POSIÇÕES**
**Path:** `/posicoes`

**Componentes:**

1. **Resumo** (cards pequenos)
   - Total de ativos: 15
   - Posição maior: PETR4 (35%)
   - Maior ganho: VALE3 (+8.5%)

2. **Tabela Detalhada**
   - Ativo | Tipo | Qtd | Preço Médio | Preço Atual | Ganho $ | Ganho % | Ações
   - Ações: Ver histórico de operações, gráfico do ativo

3. **Gráfico Pizza** (Composição da carteira)
   - % de cada ativo
   - Click para expandir detalhes

---

### **Página: PREÇOS & ANÁLISE**
**Path:** `/precos`

**Componentes:**

1. **Seletor de Ativo** + **Gráfico de Preço**
   - Dropdown com search
   - Candlestick ou linha (últimos 252 dias)
   - Volume abaixo

2. **Estatísticas do Ativo**
   - Preço Atual | Variação Hoje | Máx (52W) | Mín (52W) | Média (200d)

3. **Tabela de Preços Históricos**
   - Data | Abertura | Máximo | Mínimo | Fechamento | Volume | Variação %

---

### **Página: CONFIGURAÇÕES** (futura)
**Path:** `/config`
- Nome do fundo
- Cota inicial
- Ativos para monitorar
- Frequência de atualização

---

## 4. Componentes Reutilizáveis

### **Card Grande (Hero)**
```
┌─────────────────┐
│ 📊 PL Atual     │
│ R$ 45.200,00    │
│ +2,15% (hoje)   │
└─────────────────┘
```
Altura: 120px | Cores: fundo light, texto bold

### **Card Pequeno (Resumo)**
```
┌──────────────────┐
│ Total Posições   │
│ 15 ativos        │
└──────────────────┘
```

### **Botão Primário**
```
[ + Novo Ativo ]  → Azul (#1F77B4), padding 10px 20px
```

### **Badge (Status)**
```
🟢 COMPRA  🔴 VENDA  🟡 APORTE  🔵 RESGATE
```

---

## 5. Tipografia & Spacing

**Fonts:**
- Headings (H1-H3): `Segoe UI`, Roboto, sans-serif | Bold
- Body text: `Segoe UI`, Roboto, sans-serif | Regular
- Mono (valores): `Monaco`, `Courier New` para números

**Tamanhos:**
- H1 (Títulos principais): 28px
- H2 (Seções): 20px
- H3 (Subseções): 16px
- Body: 14px
- Small (footer): 12px

**Spacing:**
- Navbar height: 64px
- Container padding: 24px
- Card padding: 16px
- Gap between cards: 16px

---

## 6. Interatividade

### **Navbar**
- Logo/Home (left)
- Links: Home | Posições | Operações | Preços (center)
- Ícone de menu (mobile)
- Info badge (ex: "Última atualização: 14h30")

### **Modals & Alerts**
- ✅ Sucesso (verde): "Operação inserida com sucesso!"
- ⚠️ Aviso (amarelo): "Ativo não encontrado"
- ❌ Erro (vermelho): "Erro ao conectar ao banco"

### **Tables**
- Hover row → Background light
- Click row → Expande detalhes
- Sort by column header
- Search/filter em tempo real

### **Gráficos (Plotly)**
- Hover mostra valor exato
- Botões para mudar período (1W, 1M, 3M, etc)
- Download como PNG

---

## 7. Responsividade

**Breakpoints:**
- **Desktop** (≥1200px): 3 colunas, tabelas completas
- **Tablet** (768-1199px): 2 colunas, tabelas scrolláveis
- **Mobile** (<768px): 1 coluna, stacked cards, abas em lugar de abas horizontais

---

## 8. Exemplos Visuais (Pseudocódigo Dash)

```python
# Core structure
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(navbar_component(), width=12)
    ], class_name="g-0"),
    dbc.Row([
        dbc.Col([
            dbc.Row([hero_cards()]),
            dbc.Row([grafico_cotas()]),
            dbc.Row([tabela_posicoes()]),
            dbc.Row([historico_operacoes()]),
        ], width=12)
    ], class_name="p-24 mt-4")
])
```

---

## 9. Checklist de Implementação

- [ ] Navbar com logo + links
- [ ] 3 Hero Cards (PL, Cota, Investido)
- [ ] Gráfico Plotly (curva de cotas)
- [ ] Tabela de Posições (DataTable)
- [ ] Forms (Compra/Venda, Aporte/Resgate)
- [ ] Gráfico de Preços individual
- [ ] Pie chart (composição carteira)
- [ ] Responsividade mobile
- [ ] Toasts/Alerts de feedback
- [ ] Tema escuro (opcional, futura)

---

**Próximos passos:** Revisar este design, aprovar paleta e estrutura, depois começar a codificar componentes.
