-- ============================================================
-- SCRIPT COMPLETO: RECONSTRUIR BANCO DO ZERO
-- Database: eletrofundo
-- Schemas: financeiro, mercado, operacional
-- ============================================================

-- ============================================================
-- 1. CRIAR SCHEMAS
-- ============================================================

CREATE SCHEMA IF NOT EXISTS financeiro;
CREATE SCHEMA IF NOT EXISTS mercado;
CREATE SCHEMA IF NOT EXISTS operacional;

-- ============================================================
-- 2. MIGRAR TABELAS DO PUBLIC PARA MERCADO
-- ============================================================

-- Copiar tipoativo para mercado
CREATE TABLE mercado.tipoativo AS
SELECT * FROM public.tipoativo;

-- Copiar ativo para mercado (renomear para ativos)
CREATE TABLE mercado.ativos AS
SELECT 
    idativo,
    codigo,
    ticker_yf,
    idtipoativo,
    moeda
FROM public.ativo;

-- Adicionar constraints nas tabelas migradas
ALTER TABLE mercado.tipoativo
ADD CONSTRAINT tipoativo_pkey PRIMARY KEY (idtipoativo);

ALTER TABLE mercado.ativos
ADD CONSTRAINT ativos_pkey PRIMARY KEY (idativo);

ALTER TABLE mercado.ativos
ADD CONSTRAINT ativos_idtipoativo_fk 
FOREIGN KEY (idtipoativo) REFERENCES mercado.tipoativo(idtipoativo);

-- Criar índices
CREATE UNIQUE INDEX idx_ativos_codigo ON mercado.ativos(codigo);
CREATE UNIQUE INDEX idx_ativos_ticker_yf ON mercado.ativos(ticker_yf);
CREATE INDEX idx_ativos_tipoativo ON mercado.ativos(idtipoativo);

-- ============================================================
-- 3. CRIAR TABELAS DE FINANCEIRO
-- ============================================================

-- Tabela: fundo (informações do fundo)
CREATE TABLE financeiro.fundo (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    data_criacao DATE NOT NULL,
    valor_cota_inicial NUMERIC(10, 2),
    pl_atual NUMERIC(15, 2),
    cotas_emitidas NUMERIC(15, 4),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabela: posicoes (posição atual de cada ativo)
CREATE TABLE financeiro.posicoes (
    id SERIAL PRIMARY KEY,
    fundo_id INT NOT NULL REFERENCES financeiro.fundo(id) ON DELETE CASCADE,
    idativo INT NOT NULL REFERENCES mercado.ativos(idativo) ON DELETE CASCADE,
    quantidade NUMERIC(15, 4),
    preco_medio_entrada NUMERIC(10, 4),
    data_ultima_atualizacao DATE,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_posicoes_fundo ON financeiro.posicoes(fundo_id);
CREATE INDEX idx_posicoes_ativo ON financeiro.posicoes(idativo);

-- Tabela: cotas_historico (histórico de cotas)
CREATE TABLE financeiro.cotas_historico (
    id SERIAL PRIMARY KEY,
    valor_cota NUMERIC(10, 2),
    pl NUMERIC(15, 2),
    data_calculo DATE,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cotas_data ON financeiro.cotas_historico(data_calculo);

-- ============================================================
-- 4. CRIAR TABELAS DE MERCADO
-- ============================================================

-- Tabela: precos_historicos (preços do Yahoo Finance)
CREATE TABLE mercado.precos_historicos (
    id SERIAL PRIMARY KEY,
    idativo INT NOT NULL REFERENCES mercado.ativos(idativo) ON DELETE CASCADE,
    data DATE NOT NULL,
    preco_moeda_local NUMERIC(10, 4),
    preco_real NUMERIC(10, 4),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(idativo, data)
);

CREATE INDEX idx_precos_ativo_data ON mercado.precos_historicos(idativo, data);

-- Tabela: taxa_cambio (taxa USD/BRL)
CREATE TABLE mercado.taxa_cambio (
    id SERIAL PRIMARY KEY,
    data DATE UNIQUE,
    usd_brl NUMERIC(10, 4),
    criado_em TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- 5. CRIAR TABELAS DE OPERACIONAL
-- ============================================================

-- Tabela: movimentacoes_ativos (compras/vendas)
CREATE TABLE operacional.movimentacoes_ativos (
    id SERIAL PRIMARY KEY,
    idativo INT NOT NULL REFERENCES mercado.ativos(idativo) ON DELETE CASCADE,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('COMPRA', 'VENDA')),
    quantidade NUMERIC(15, 4),
    preco_unitario NUMERIC(10, 4),
    data_operacao DATE NOT NULL,
    comissao NUMERIC(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_movimentacoes_data ON operacional.movimentacoes_ativos(data_operacao);
CREATE INDEX idx_movimentacoes_ativo ON operacional.movimentacoes_ativos(idativo);

-- Tabela: operacoes_cota (aportes/resgates)
CREATE TABLE operacional.operacoes_cota (
    id SERIAL PRIMARY KEY,
    fundo_id INT NOT NULL REFERENCES financeiro.fundo(id) ON DELETE CASCADE,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('APORTE', 'RESGATE')),
    quantidade_cotas NUMERIC(15, 4),
    valor_total NUMERIC(15, 2),
    valor_cota_na_operacao NUMERIC(10, 2),
    data_operacao DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_operacoes_fundo ON operacional.operacoes_cota(fundo_id);
CREATE INDEX idx_operacoes_data ON operacional.operacoes_cota(data_operacao);

-- ============================================================
-- 6. VERIFICAÇÃO FINAL
-- ============================================================

-- Contar tabelas por schema
SELECT 'Financeiro' as schema, COUNT(*) as tabelas
FROM information_schema.tables 
WHERE table_schema = 'financeiro'
UNION ALL
SELECT 'Mercado', COUNT(*)
FROM information_schema.tables 
WHERE table_schema = 'mercado'
UNION ALL
SELECT 'Operacional', COUNT(*)
FROM information_schema.tables 
WHERE table_schema = 'operacional';

-- Contar registros nas tabelas migradas
SELECT 'tipoativo' as tabela, COUNT(*) as total FROM mercado.tipoativo
UNION ALL
SELECT 'ativos', COUNT(*) FROM mercado.ativos;

-- Listar todas as tabelas
SELECT table_schema, table_name 
FROM information_schema.tables 
WHERE table_schema IN ('financeiro', 'mercado', 'operacional')
ORDER BY table_schema, table_name;
