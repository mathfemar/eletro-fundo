# Planejamento - Webapp Eletro Fundo

## 📊 Visão Geral
Sistema web para acompanhar investimentos de um fundo (gestão de ativos, cotas, patrimônio líquido) usando Dash Plotly, PostgreSQL e Yahoo Finance.

**Tecnologias:**
- Frontend: Dash Plotly
- Backend: Python (Flask/Dash)
- Database: PostgreSQL
- Preços de Mercado: Yahoo Finance
- Agendador: APScheduler
- Conexão: Tailscale (dev) / Localhost (produção)

---

## 🗄️ Banco de Dados

### Conexão
```
Host: 100.116.199.25 (dev via Tailscale) / 127.0.0.1 (prod)
Port: 5432
Database: eletrofundo
Schemas: financeiro, mercado, operacional
User: postgres
Password: (sem senha - conexão trust)
```

### Tabelas a Criar (Database: eletrofundo)

#### 1. `fundo` (Schema: financeiro)
```sql
CREATE TABLE financeiro.fundo (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    data_criacao DATE NOT NULL,
    valor_cota_inicial DECIMAL(10, 2),
    pl_atual DECIMAL(15, 2),
    cotas_emitidas DECIMAL(15, 4),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. `ativos` (Schema: mercado)
```sql
CREATE TABLE mercado.ativos (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) UNIQUE NOT NULL,
    nome VARCHAR(255),
    tipo VARCHAR(50), -- 'ação', 'cripto', 'renda_fixa', etc
    moeda_local VARCHAR(10) DEFAULT 'BRL', -- BRL, USD
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 3. `precos_historicos` (Schema: mercado)
```sql
CREATE TABLE mercado.precos_historicos (
    id SERIAL PRIMARY KEY,
    ativo_id INT REFERENCES mercado.ativos(id) ON DELETE CASCADE,
    data DATE NOT NULL,
    preco_moeda_local DECIMAL(10, 4),
    preco_real DECIMAL(10, 4), -- Convertido para BRL
    volume BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ativo_id, data)
);

CREATE INDEX idx_precos_ativo_data ON mercado.precos_historicos(ativo_id, data);
```

#### 4. `posicoes` (Schema: financeiro)
```sql
CREATE TABLE financeiro.posicoes (
    id SERIAL PRIMARY KEY,
    fundo_id INT REFERENCES financeiro.fundo(id) ON DELETE CASCADE,
    ativo_id INT REFERENCES mercado.ativos(id) ON DELETE CASCADE,
    quantidade DECIMAL(15, 4),
    preco_medio_entrada DECIMAL(10, 4),
    data_ultima_atualizacao DATE,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 5. `movimentacoes_ativos` (Schema: operacional)
```sql
CREATE TABLE operacional.movimentacoes_ativos (
    id SERIAL PRIMARY KEY,
    ativo_id INT REFERENCES mercado.ativos(id) ON DELETE CASCADE,
    tipo VARCHAR(10) NOT NULL, -- 'COMPRA', 'VENDA'
    quantidade DECIMAL(15, 4),
    preco_unitario DECIMAL(10, 4),
    data_operacao DATE NOT NULL,
    comissao DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_movimentacoes_data ON operacional.movimentacoes_ativos(data_operacao);
```

#### 6. `operacoes_cota` (Schema: operacional)
```sql
CREATE TABLE operacional.operacoes_cota (
    id SERIAL PRIMARY KEY,
    fundo_id INT REFERENCES financeiro.fundo(id) ON DELETE CASCADE,
    tipo VARCHAR(10) NOT NULL, -- 'APORTE', 'RESGATE'
    quantidade_cotas DECIMAL(15, 4),
    valor_total DECIMAL(15, 2),
    valor_cota_na_operacao DECIMAL(10, 2),
    data_operacao DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 7. `cotas_historico` (Schema: financeiro)
```sql
CREATE TABLE financeiro.cotas_historico (
    id SERIAL PRIMARY KEY,
    valor_cota DECIMAL(10, 2),
    pl DECIMAL(15, 2),
    data_calculo DATE,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cotas_data ON financeiro.cotas_historico(data_calculo);
```

#### 8. `taxa_cambio` (Schema: mercado)
```sql
CREATE TABLE mercado.taxa_cambio (
    id SERIAL PRIMARY KEY,
    data DATE UNIQUE,
    usd_brl DECIMAL(10, 4), -- Taxa USD -> BRL
    criado_em TIMESTAMP DEFAULT NOW()
);
```

---

## 📁 Estrutura do Projeto

```
eletro-fundo/
├── app.py                          # Main Dash app
├── config.py                       # Configurações (DB, credenciais, URLs)
├── requirements.txt                # Dependências Python
├── .env.example                    # Template de variáveis de ambiente
├── README.md                       # Documentação
├── PLANNING.md                     # Este arquivo
│
├── database/
│   ├── __init__.py
│   ├── connection.py               # Conexão PostgreSQL (SQLAlchemy)
│   ├── models.py                   # Modelos ORM (Fundo, Ativo, etc)
│   └── migrations.sql              # Script para criar tabelas
│
├── utils/
│   ├── __init__.py
│   ├── yahoo_finance.py            # Download de dados Yahoo Finance (adaptado funcao_yf.py)
│   ├── calculations.py             # Cálculos financeiros (PL, cota, etc)
│   ├── exchange_rates.py           # Conversão USD -> BRL
│   └── validators.py               # Validações de entrada
│
├── components/
│   ├── __init__.py
│   ├── forms.py                    # Formulários Dash (compra, venda, aporte, etc)
│   └── charts.py                   # Gráficos e visualizações Plotly
│
├── callbacks/
│   ├── __init__.py
│   └── operations.py               # Callbacks interativos do Dash
│
├── jobs/
│   ├── __init__.py
│   └── scheduled_tasks.py          # Tarefas agendadas (APScheduler)
│       ├── Atualizar preços (diário - 16h)
│       ├── Calcular cotas (a cada 5 min ou via input)
│       └── Buscar taxa cambio
│
├── logs/
│   └── app.log                     # Log de execução
│
└── .gitignore                      # Git ignore (venv, .env, logs)
```

---

## 🔄 Fluxo de Dados

### 1. **Input de Dados (Manual via Formulário)**
```
Usuário inputa:
  - Compra/Venda de ativo (ticker, quantidade, preço, comissão, data)
  - Aporte/Resgate (valor total, data)
  - Novo ativo (ticker, nome, tipo, moeda)

↓ Validação (validators.py)

↓ Inserção no PostgreSQL (models.py)

↓ Recálculo automático (calculations.py)
  - Atualiza posição do ativo
  - Recalcula PL total
  - Recalcula valor da cota
  - Gera entrada em cotas_historico

↓ Dashboard atualiza em tempo real
```

### 2. **Atualização de Preços (Job Agendado)**
```
Diariamente às 16h (ou manual):

1. Buscar todos os tickers cadastrados
2. Baixar preços Yahoo Finance desde 2020-01-01
3. Inserir/atualizar em precos_historicos
4. Converter USD -> BRL (se aplicável)
5. Triggar recalculamento de cotas
```

### 3. **Cálculo de Cotas (A cada 5 min ou via input)**
```
Fórmula:
  PL = Σ (quantidade_ativo × preco_atual_moeda_local_convertido_brl)
  
  Cotas Emitidas = Total aportes / valor_cota_inicial
  
  Valor Cota = PL / Cotas Emitidas
  
  Rentabilidade Diária = (Cota Hoje - Cota Ontem) / Cota Ontem
```

---

## 🎯 Funcionalidades MVP (Fase 1)

### Frontend (Dash)
1. **Dashboard Principal**
   - Card: Valor PL atual
   - Card: Valor da cota atual
   - Card: Total de cotas emitidas
   - Gráfico: Evolução do PL (linha) - últimos 12 meses
   - Gráfico: Evolução da cota (linha) - últimos 12 meses
   - Tabela: Posição atual de cada ativo (ticker, qtd, preço médio, valor atual, % do PL)
   - Tabela: Últimas 10 movimentações

2. **Formulários (Abas)**
   - **Aba 1: Movimentação de Ativo**
     - Dropdown: Selecionar ativo (ou criar novo)
     - Radio: Compra / Venda
     - Input: Quantidade
     - Input: Preço unitário
     - Input: Comissão (opcional)
     - Input: Data (default hoje)
     - Button: Registrar
   
   - **Aba 2: Aporte/Resgate**
     - Radio: Aporte / Resgate
     - Input: Valor total
     - Input: Data (default hoje)
     - Display: Valor da cota no dia
     - Display: Cotas que serão emitidas/canceladas
     - Button: Registrar
   
   - **Aba 3: Novo Ativo**
     - Input: Ticker (ex: PETR4.SA, BTC-USD)
     - Input: Nome (ex: Petrobras, Bitcoin)
     - Dropdown: Tipo (ação, cripto, renda_fixa)
     - Dropdown: Moeda (BRL, USD)
     - Button: Criar + Baixar histórico Yahoo Finance

3. **Menu de Opções**
   - Atualizar preços manualmente
   - Recalcular cotas
   - Exportar relatório (CSV)

### Backend (Cálculos)
- ✅ Conexão PostgreSQL (SQLAlchemy)
- ✅ Modelos ORM
- ✅ Cálculos de PL e Cota
- ✅ Download Yahoo Finance (adaptado funcao_yf.py)
- ✅ Conversão USD -> BRL
- ✅ Jobs agendados (APScheduler)

---

## 🚀 Fases de Implementação

### **Fase 1: Setup Base (ATUAL)**
- [ ] Criar estrutura de pastas
- [ ] Configurar requirements.txt
- [ ] Criar config.py (DB, URLs, etc)
- [ ] Criar database/connection.py (SQLAlchemy + PostgreSQL)
- [ ] Criar database/models.py (Modelos ORM)
- [ ] Executar migrations.sql (criar tabelas no DB)
- [ ] Testar conexão PostgreSQL

### **Fase 2: Yahoo Finance**
- [ ] Adaptar funcao_yf.py → utils/yahoo_finance.py
- [ ] Criar utils/exchange_rates.py (buscar cotação USD/BRL)
- [ ] Criar job para baixar histórico desde 2020-01-01
- [ ] Criar job para atualizar preços diariamente
- [ ] Testar download de dados

### **Fase 3: Cálculos Financeiros**
- [ ] Criar utils/calculations.py
  - [ ] calcular_pl()
  - [ ] calcular_valor_cota()
  - [ ] calcular_preco_medio()
  - [ ] registrar_movimentacao()
  - [ ] registrar_aporte_resgate()
- [ ] Testar cálculos com dados fictícios

### **Fase 4: Interface Dash**
- [ ] Criar app.py (estrutura básica Dash)
- [ ] Criar components/forms.py (formulários)
- [ ] Criar components/charts.py (gráficos)
- [ ] Criar callbacks/operations.py (interações)
- [ ] Testar interface

### **Fase 5: Jobs Agendados**
- [ ] Criar jobs/scheduled_tasks.py (APScheduler)
- [ ] Job: Atualizar preços (diário 16h)
- [ ] Job: Calcular cotas (a cada 5 min)
- [ ] Job: Sincronizar taxa cambio
- [ ] Testar agendamentos

### **Fase 6: Deploy**
- [ ] Testes de integração
- [ ] Documentação
- [ ] Deploy no servidor (produção)
- [ ] Monitoramento de logs

---

## 🔧 Dependências Python (requirements.txt)

```
dash==2.14.1
plotly==5.17.0
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
pandas==2.1.3
numpy==1.26.2
yfinance==0.2.32
requests==2.31.0
python-dotenv==1.0.0
apscheduler==3.10.4
```

---

## 🌐 Configuração Host/Porta

```
Host: 0.0.0.0
Port: 8527
URL Desenvolvimento: http://127.0.0.1:8527
URL Produção (via Tailscale): http://100.116.199.25:8527
```

---

## 📝 Variáveis de Ambiente (.env)

```
ENVIRONMENT=development  # development ou production
DB_HOST=100.116.199.25   # Dev: Tailscale | Prod: 127.0.0.1
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=              # Vazio (conexão trust)
DB_SCHEMA=eletrofundo
DASH_HOST=0.0.0.0
DASH_PORT=8527
DASH_DEBUG=True
LOG_LEVEL=INFO
```

---

## 🔐 Segurança

- [ ] Validação de entrada em todos os formulários
- [ ] Proteção contra SQL Injection (SQLAlchemy ORM)
- [ ] Variáveis de ambiente para credenciais
- [ ] Logs estruturados para auditoria
- [ ] (Futuro) Autenticação de usuários

---

## 📊 Relatórios Futuros (Fase 2+)

- Performance acumulada (anual, desde início)
- Comparação com benchmarks (Ibovespa, S&P 500)
- Drawdown máximo
- Sharpe Ratio, Sortino Ratio
- Gráfico de alocação por tipo de ativo
- Gráfico de alocação por moeda (BRL vs USD)
- Histórico de rentabilidade mensal

---

## 🎯 Próximos Passos

1. ✅ Confirmar conexão PostgreSQL
2. ✅ Confirmar schema `eletrofundo` existe
3. ✅ Confirmar credenciais (sem senha)
4. ➜ **PRÓXIMO: Criar estrutura de pastas e requirements.txt**
5. ➜ Implementar database/connection.py
6. ➜ Criar database/models.py
7. ➜ Executar migrations.sql

---

## 📞 Perguntas Resolvidas

| Questão | Resposta |
|---------|----------|
| Cota inicial? | Definir via DB depois, não via site ainda |
| Frequência cálculo? | 5 minutos automático + input do usuário |
| Preços? | Yahoo Finance (adaptado funcao_yf.py) |
| Moedas? | BRL e USD com conversão |
| Período dados? | Desde 2020-01-01 |
| BD já existe? | Sim, schema `eletrofundo` no PostgreSQL |
| Credenciais? | User: postgres, sem senha (trust) |
| Host/Porta? | 0.0.0.0:8527 (Tailscale dev, localhost prod) |
| Conversão USD? | Buscar cotação externa + armazenar em DB |

---

*Última atualização: 10/12/2025*
