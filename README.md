# Eletro Fundo - Webapp de Acompanhamento de Investimentos

Sistema web para acompanhar investimentos de um fundo, gerenciar cotas, patrimônio líquido e desempenho.

## 🚀 Instalação

### Pré-requisitos
- Python 3.8+
- PostgreSQL 12+ (com schema `eletrofundo` criado)
- Tailscale (para conexão remota em desenvolvimento)

### Setup

1. **Clonar repositório**
```bash
git clone https://github.com/mathfemar/eletro-fundo.git
cd eletro-fundo
```

2. **Criar ambiente virtual**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. **Instalar dependências**
```bash
pip install -r requirements.txt
```

4. **Configurar variáveis de ambiente**
```bash
cp .env.example .env
# Editar .env com suas credenciais
```

5. **Criar tabelas no banco**
```bash
python init_db.py
```

6. **Rodar a aplicação**
```bash
python app.py
```

Acesse: http://0.0.0.0:8527

## 📁 Estrutura do Projeto

```
eletro-fundo/
├── app.py                    # Main Dash application
├── config.py                 # Configurações
├── requirements.txt          # Dependências Python
├── PLANNING.md               # Planejamento detalhado
├── database/
│   ├── connection.py         # Conexão PostgreSQL
│   └── models.py             # Modelos ORM
├── utils/                    # Utilitários
├── components/               # Componentes Dash
├── callbacks/                # Callbacks interativos
├── jobs/                     # Tarefas agendadas
└── logs/                     # Logs de aplicação
```

## 🔧 Tecnologias

- **Frontend**: Dash Plotly
- **Backend**: Python (Flask/Dash)
- **Database**: PostgreSQL
- **Dados de Mercado**: Yahoo Finance
- **Scheduler**: APScheduler

## 📊 Funcionalidades

- ✅ Dashboard com PL, valor de cota e posições
- ✅ Formulários para registrar movimentações
- ✅ Download automático de preços (Yahoo Finance)
- ✅ Cálculo de cotas a cada 5 minutos
- ✅ Conversão USD -> BRL
- ✅ Relatórios e gráficos

## 📞 Contato

Desenvolvido por: Matheus Ferreira
Email: mathfemar@gmail.com

## 📄 Licença

MIT
