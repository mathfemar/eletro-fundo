# 🔄 Migração: Tabela Ativos

## Mudança Realizada

Substituímos a tabela simples `mercado.ativos` pela sua tabela mais completa e profissional que você criou em `public`.

---

## 📋 Novo Modelo de Dados

### Schema: `mercado`

#### Tabela 1: `tipoativo`
```sql
idtipoativo  (PK)
descricao
```

**Propósito:** Categorizar ativos (ação, cripto, renda fixa, etc)

#### Tabela 2: `ativos`
```sql
idativo      (PK)
codigo       (UNIQUE) - Alias: NVDA, PETR4, BTC
ticker_yf    (UNIQUE) - Yahoo Finance: NVDA, PETR4.SA, BTC-USD
idtipoativo  (FK) - Referencia tipoativo
moeda        - BRL, USD, etc
created_at
```

**Propósito:** Catálogo central de todos os ativos

**Campos mantidos:** `codigo`, `ticker_yf`, `moeda`
**Campos removidos:** idsetorpai, idsetorfilho, idemissor, etc (não necessários)

---

## 🔄 Processo de Migração

### 1. Deletar tabela antiga
```sql
DROP TABLE IF EXISTS mercado.ativos CASCADE;
```

### 2. Executar o script de migração
```bash
# Arquivo: database/migration_ativos.sql
psql -h 100.116.199.25 -U postgres -d eletrofundo -f database/migration_ativos.sql
```

O script vai:
- ✅ Criar `mercado.tipoativo`
- ✅ Criar `mercado.ativos`
- ✅ Copiar dados de `public.tipoativo`
- ✅ Copiar dados de `public.ativos`
- ✅ Criar índices

### 3. Deletar tabelas de public (opcional)
```sql
DROP TABLE public.ativos;
DROP TABLE public.tipoativo;
```

---

## 📊 Estrutura Atualizada

```
Database: eletrofundo
├── Schema: financeiro
│   ├── fundo
│   ├── posicoes (FK: idativo)
│   └── cotas_historico
├── Schema: mercado
│   ├── tipoativo
│   ├── ativos (FK: idtipoativo)
│   ├── precos_historicos (FK: idativo)
│   └── taxa_cambio
└── Schema: operacional
    ├── movimentacoes_ativos (FK: idativo)
    └── operacoes_cota
```

---

## 🐍 Modelos ORM Atualizados

### TipoAtivo
```python
class TipoAtivo(Base):
    idtipoativo = Column(Integer, primary_key=True)
    descricao = Column(String(255))
    ativos = relationship("Ativo", back_populates="tipo_ativo")
```

### Ativo
```python
class Ativo(Base):
    idativo = Column(Integer, primary_key=True)
    codigo = Column(String(55), unique=True)        # NVDA, PETR4
    ticker_yf = Column(String(55), unique=True)     # NVDA, PETR4.SA
    idtipoativo = Column(Integer, FK)
    moeda = Column(String(10), default='BRL')
    tipo_ativo = relationship("TipoAtivo")
    precos = relationship("PrecoHistorico")
    posicoes = relationship("Posicao")
    movimentacoes = relationship("MovimentacaoAtivo")
```

---

## 🔗 Relacionamentos Atualizados

**Antes:**
```
movimentacoes_ativos.ativo_id → ativos.id
posicoes.ativo_id → ativos.id
precos_historicos.ativo_id → ativos.id
```

**Depois:**
```
movimentacoes_ativos.idativo → ativos.idativo
posicoes.idativo → ativos.idativo
precos_historicos.idativo → ativos.idativo
```

---

## ✅ Benefícios

1. **Dados Reais** - Usar ativos realmente cadastrados
2. **Mais Completo** - Sua tabela tem muito mais informação
3. **Profissional** - Estrutura pronta para produção
4. **Integrado** - Tipoativo categoriza os ativos
5. **Escalável** - Pronto para crescer

---

## 📝 Próximos Passos

1. ✅ Executar `migration_ativos.sql` no PostgreSQL
2. ✅ Testar conexão e dados
3. ➜ Implementar Yahoo Finance (usar `ticker_yf`)
4. ➜ Criar dashboard com dados reais
5. ➜ Popular `precos_historicos`

---

*Migração preparada: 10/12/2025*
*Status: Pronto para executar ✅*
