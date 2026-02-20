# Guia de Clonagem de Arquitetura — TRUXT-DASH

> **Público-alvo**: Agentes de IA que precisam criar um novo projeto baseado nesta mesma arquitetura.
>
> Este documento descreve a arquitetura **React + FastAPI** usada no TRUXT-DASH e fornece instruções passo a passo para replicá-la em outro projeto com outro domínio. **Não há Dash/Flask** — isso era legado do projeto original e não faz parte desta arquitetura.

---

## 1. Visão Geral da Arquitetura

Dois processos independentes:

```
┌──────────────────────┐     ┌───────────────────┐
│   FastAPI (REST API) │◄───►│  React/Vite       │
│   porta 8528         │     │  porta 3000       │
│   /api/*             │     │  (frontend)       │
└──────────┬───────────┘     └───────────────────┘
           │
           ▼
┌──────────────────┐
│   services/      │  Lógica de negócios (Python)
│   (ETL, Pandas)  │  chamada pelos endpoints
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   SQLite         │  banco local, arquivo .db na raiz
└──────────────────┘
```

| Processo | Tech | Porta | Função |
|---|---|---|---|
| **Backend API** | FastAPI + Uvicorn | 8528 | REST API JSON, lógica de negócios, cache |
| **Frontend** | React + Vite + TypeScript | 3000 | SPA com TanStack Query, React Router, Plotly |

---

## 2. Estrutura de Diretórios (Template para novo projeto)

```text
MEU-PROJETO/
├── .env                         # Variáveis de ambiente (gitignored)
├── .env.example                 # Template commitável
├── .gitignore
├── database.db                  # Arquivo SQLite (gitignored)
├── requirements.txt             # Deps Python (FastAPI + Pandas — SQLite é built-in)
├── run_api.bat                  # Script de inicialização do backend
│
├── src/meu_projeto/             # BACKEND PYTHON (package Python)
│   ├── __init__.py
│   ├── config.py                # Constantes globais (cores, config servidor, etc.)
│   │
│   ├── api/                     # ★ FASTAPI
│   │   ├── __init__.py
│   │   ├── main.py              # App FastAPI, CORS, lifespan, registro de routers
│   │   ├── config.py            # APISettings (pydantic-settings, carrega .env)
│   │   ├── dependencies.py      # Injeção de dependências (@lru_cache singletons)
│   │   ├── models/              # Pydantic models compartilhados
│   │   │   ├── __init__.py
│   │   │   └── common.py        # APIResponse, ErrorResponse, PaginationParams
│   │   └── routers/             # Endpoints REST agrupados por domínio
│   │       ├── __init__.py
│   │       ├── dominio_a.py     # APIRouter(prefix="/api/dominio-a", tags=["DominioA"])
│   │       └── dominio_b.py
│   │
│   └── services/                # ★ LÓGICA DE NEGÓCIOS
│       ├── __init__.py
│       ├── db_connection.py     # Conexão SQLite (sqlite3 built-in)
│       ├── cache_manager.py     # Sistema de cache em background (threads)
│       ├── df_mailer.py         # Envio de emails (opcional)
│       └── dominio_a/           # Serviços por domínio
│           ├── __init__.py
│           ├── service.py       # Classe principal do domínio
│           └── cache.py         # Cache específico do domínio
│
├── frontend/                    # ★ FRONTEND REACT
│   ├── package.json
│   ├── vite.config.ts           # Proxy /api → localhost:8528
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx             # Entrypoint React
│       ├── App.tsx              # Router principal + QueryClientProvider
│       ├── App.css
│       ├── styles/
│       │   └── globals.css      # Reset + variáveis CSS globais + dark theme
│       ├── api/                 # Clientes HTTP tipados
│       │   ├── client.ts        # Axios instance centralizada
│       │   └── dominioA.ts      # Funções fetch + interfaces TypeScript
│       ├── hooks/               # TanStack Query hooks
│       │   └── useDominioA.ts   # useQuery/useMutation wrappers
│       ├── components/          # Componentes React
│       │   ├── layout/          # Sidebar, Upbar (fixos)
│       │   └── dominio_a/       # Componentes específicos do domínio
│       ├── pages/               # Páginas (uma por rota)
│       │   ├── Home/
│       │   │   ├── Home.tsx
│       │   │   └── Home.css
│       │   └── DominioA/
│       │       ├── Pagina.tsx
│       │       └── Pagina.css
│       ├── config/
│       │   └── navigation.ts    # Estrutura de navegação (seções + itens)
│       └── utils/
│           └── formatBR.ts      # Utilitários de formatação
│
├── cache/                       # Arquivos .pkl de cache (gitignored)
└── docs/                        # Documentação
```

---

## 3. Backend — Camada por Camada

### 3.1 `api/config.py` — Configurações centralizadas

Usa `pydantic-settings` para carregar variáveis de ambiente com tipagem e defaults:

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class APISettings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8528
    debug: bool = True

    cors_origins: list[str] = [
        "http://localhost:3000",      # Vite dev
        "http://localhost:5173",      # Vite default
    ]

    # JWT (se necessário, futuro)
    jwt_secret: str = "change-in-production"
    jwt_algorithm: str = "HS256"

    cache_dir: str = "cache"

    class Config:
        env_prefix = "MEU_API_"     # ← prefixo das variáveis de ambiente
        env_file = ".env"

@lru_cache()
def get_settings() -> APISettings:
    return APISettings()
```

**Regra**: todas as configurações sensíveis (emails, secrets, URLs) vêm do `.env`.

---

### 3.2 `api/main.py` — App FastAPI

Responsável por: criar a instância FastAPI, configurar CORS, registrar routers e gerenciar o ciclo de vida (lifespan) para threads de background.

```python
import time, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from meu_projeto.api.config import get_settings
from meu_projeto.api.routers import dominio_a, dominio_b

logger = logging.getLogger("api")
_start_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 API starting...")
    # Inicializar caches em background thread se necessário
    import threading
    from meu_projeto.services.cache_manager import initialize_caches
    threading.Thread(target=initialize_caches, daemon=True).start()
    yield
    logger.info("🛑 API shutting down...")

settings = get_settings()

app = FastAPI(
    title="Meu Projeto API",
    description="REST API para ...",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(dominio_a.router)
app.include_router(dominio_b.router)

@app.get("/", tags=["System"])
async def root():
    return {"app": "Meu Projeto API", "docs": "/docs", "health": "/health"}

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "uptime_seconds": round(time.time() - _start_time, 1)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("meu_projeto.api.main:app", host=settings.api_host, port=settings.api_port, reload=settings.debug)
```

---

### 3.3 `api/models/common.py` — Response wrapper padrão

**Todas** as respostas da API usam o mesmo envelope:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

class APIResponse(BaseModel):
    success: bool = True
    data: Any = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
```

Isso garante que o frontend sempre receba `{ success, data, error, timestamp }`.

---

### 3.4 `api/routers/<dominio>.py` — Endpoints REST

Cada domínio tem seu próprio router com **prefix**. O padrão:

```python
import logging
from fastapi import APIRouter, HTTPException, Query
from meu_projeto.api.models.common import APIResponse

logger = logging.getLogger("api.dominio_a")
router = APIRouter(prefix="/api/dominio-a", tags=["Domínio A"])

@router.get("/dados", response_model=APIResponse)
async def get_dados():
    try:
        # Import lazy (dentro do endpoint) para evitar circular imports
        from meu_projeto.services.dominio_a.service import MeuService
        service = MeuService()
        data = service.get_dados()  # Retorna dict/list, NUNCA DataFrame
        return APIResponse(data=data)
    except Exception as e:
        logger.exception("Error in /dominio-a/dados")
        raise HTTPException(status_code=500, detail=str(e))
```

**Regras críticas do router**:
1. O `prefix` sempre começa com `/api/`
2. Os imports dos services são **lazy** (dentro da função) para evitar circular imports
3. **NUNCA** retorna DataFrames — converta com `.to_dict('records')` antes
4. Sempre envolve em `try/except` com logging
5. Usa `response_model=APIResponse` para documentação automática no Swagger

---

### 3.5 `api/dependencies.py` — Injeção de serviços

Usa `@lru_cache` para criar singletons dos services:

```python
from functools import lru_cache

@lru_cache()
def get_meu_service():
    from meu_projeto.services.dominio_a.service import MeuService
    return MeuService()
```

Pode ser injetado nos endpoints com `Depends()`:

```python
from fastapi import Depends
from meu_projeto.api.dependencies import get_meu_service

@router.get("/dados")
async def get_dados(service=Depends(get_meu_service)):
    return APIResponse(data=service.get_dados())
```

---

### 3.6 `services/` — Lógica de Negócios

A **regra de ouro**: toda lógica pesada (SQL, Pandas, cálculos, ETL) fica nos services. Endpoints e componentes de UI apenas consomem.

```
services/
├── db_connection.py       # Conexão SQLite — retorna sqlite3.Connection
├── cache_manager.py       # Thread background que verifica mudanças no DB
├── df_mailer.py           # Classe para enviar emails (opcional)
└── dominio_a/
    ├── service.py         # Classe com métodos get_ que retornam dict/list
    └── cache.py           # start_background_cache() para thread do domínio
```

**Conexão SQLite** (`db_connection.py`):
```python
import sqlite3
import os

DB_PATH = os.getenv("DATABASE_PATH", "database.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # permite acessar colunas por nome
    return conn
```

**Padrão do service**:
```python
import pandas as pd
from meu_projeto.services.db_connection import get_connection

class MeuService:
    def get_dados(self) -> dict:
        """Retorna dados prontos para JSON."""
        df = self._query_db()       # SQL → DataFrame
        return {
            "items": df.to_dict('records'),
            "total": len(df),
        }

    def _query_db(self) -> pd.DataFrame:
        conn = get_connection()
        return pd.read_sql("SELECT * FROM minha_tabela", conn)
```

---

### 3.7 Sistema de Cache em Background

O cache usa **threads daemon** que verificam mudanças no banco a cada N minutos:

```python
# cache_manager.py
import threading, time, pickle, os

class CacheManager:
    def __init__(self, cache_dir='cache', update_interval=900):
        self.cache_dir = cache_dir
        self.update_interval = update_interval  # 15 min
        os.makedirs(cache_dir, exist_ok=True)

    def check_needs_update(self) -> bool:
        # Compara metadados do cache com o banco
        ...

    def update_cache(self):
        # Query no banco → grava .pkl por item
        ...

    def start_background_updates(self):
        def loop():
            while True:
                time.sleep(self.update_interval)
                if self.check_needs_update():
                    self.update_cache()
        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
```

**Pontos-chave**:
- Armazenamento em pickle (`.pkl`), um arquivo por item/ticker
- `daemon=True` para morrer junto com o processo principal
- Verificação leve (SELECT COUNT/MAX) antes de atualizar
- Graceful: se o cache falhar, o sistema busca direto no banco

---

### 3.8 `run_api.bat` — Script de Execução

```batch
@echo off
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

set PYTHONPATH=%~dp0src;%PYTHONPATH%

python -m uvicorn meu_projeto.api.main:app --host 0.0.0.0 --port 8528 --reload
pause
```

**Importante**: `PYTHONPATH` aponta para `src/` para que imports como `from meu_projeto.services...` funcionem.

---

### 3.9 Dependências Python

**`requirements.txt`** (tudo em um arquivo):
```text
# API
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-multipart>=0.0.9
python-dotenv>=1.0.0

# Data
pandas
numpy
openpyxl
requests

# SQLite já vem embutido no Python — sem dependência extra
```

> **SQLite é built-in**: o módulo `sqlite3` já vem com o Python. Nenhuma dependência extra é necessária para o banco de dados.

---

## 4. Frontend — Camada por Camada

### 4.1 Inicialização (`vite.config.ts`)

O proxy é o coração da integração — redireciona `/api` para o backend Python:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: { '@': path.resolve(__dirname, './src') },
    },
    server: {
        port: 3000,
        host: true,
        proxy: {
            '/api': {
                target: 'http://localhost:8528',
                changeOrigin: true,
            },
        },
    },
});
```

---

### 4.2 Entrypoint (`main.tsx`)

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/globals.css';

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <App />
    </StrictMode>,
);
```

---

### 4.3 App Shell (`App.tsx`)

Monta: `QueryClientProvider` → `BrowserRouter` → Layout (Sidebar + Upbar + Routes).

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Sidebar from './components/layout/Sidebar';
import Upbar from './components/layout/Upbar';
import HomePage from './pages/Home/Home';
import SectionHome from './pages/SectionHome/SectionHome';
import MinhaPage from './pages/DominioA/MinhaPage';
import './App.css';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 60000,        // 1 min antes de considerar "velho"
            retry: 2,
            refetchOnWindowFocus: false,
        },
    },
});

function AppLayout() {
    return (
        <div className="app-layout">
            <Sidebar />
            <Upbar />
            <main className="main-content">
                <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/secao-a" element={<SectionHome title="Seção A" />} />
                    <Route path="/secao-a/minha-page" element={<MinhaPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </main>
        </div>
    );
}

export default function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <BrowserRouter>
                <AppLayout />
            </BrowserRouter>
        </QueryClientProvider>
    );
}
```

---

### 4.4 API Client (`api/client.ts`)

Instância Axios centralizada com interceptor de erro:

```typescript
import axios from 'axios';

// Em dev, Vite proxeia /api para localhost:8528
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export const apiClient = axios.create({
    baseURL: API_BASE,
    timeout: 0,
    headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('[API Error]', error.response?.data || error.message);
        return Promise.reject(error);
    }
);

export interface APIResponse<T = unknown> {
    success: boolean;
    data: T;
    error: string | null;
    timestamp: string;
}

export default apiClient;
```

---

### 4.5 API Client por Domínio (`api/dominioA.ts`)

Cada domínio tem seu arquivo com interfaces TypeScript + funções fetch:

```typescript
import { apiClient } from './client';

// ---- Types ----
export interface MeuDado {
    id: number;
    nome: string;
    valor: number;
}

export interface DadosResponse {
    items: MeuDado[];
    total: number;
}

// ---- API Functions ----
export async function getDados(): Promise<MeuDado[]> {
    const response = await apiClient.get<{ data: DadosResponse }>('/api/dominio-a/dados');
    return response.data.data.items;
}
```

**Padrão**: `response.data` vem do Axios, `.data` vem do envelope `APIResponse`, e `.items` é a chave específica.

---

### 4.6 Hooks TanStack Query (`hooks/useDominioA.ts`)

Cada hook encapsula um `useQuery` ou `useMutation`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { getDados } from '../api/dominioA';

export function useDados() {
    return useQuery({
        queryKey: ['dominio-a', 'dados'],
        queryFn: getDados,
        staleTime: 60_000,              // 1 min
        refetchOnWindowFocus: true,
    });
}
```

**Benefícios**: cache automático, loading/error states, invalidation após mutations.

---

### 4.7 Componentes de Layout

#### Sidebar (`components/layout/Sidebar.tsx`)
- Fixa à esquerda, **280px** de largura
- Lê `navigation.ts` para montar os itens de menu
- Submenus colapsáveis (toggle com estado local)
- Destaca item ativo baseado no `pathname` atual

#### Upbar (`components/layout/Upbar.tsx`)
- Barra superior fixa, **70px** de altura
- Links de navegação entre seções (Middle, Comercial, etc.)
- Margem esquerda de 280px (alinha com a sidebar)

#### CSS do layout (`App.css`)
```css
.app-layout {
    display: flex;
    min-height: 100vh;
    background: #000;
}
.main-content {
    margin-left: 280px;
    margin-top: 70px;
    padding: 2rem;
    flex: 1;
    min-height: calc(100vh - 70px);
    background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
}
```

---

### 4.8 Navegação (`config/navigation.ts`)

Define toda a estrutura de menu em um único lugar:

```typescript
export interface NavItem {
    label: string;
    href: string;
    icon: string;           // classe Font Awesome
    children?: NavItem[];    // submenus
}

export interface Section {
    id: string;
    label: string;
    basePath: string;
    navItems: NavItem[];
}

export const sections: Section[] = [
    {
        id: 'secao-a',
        label: 'Seção A',
        basePath: '/secao-a',
        navItems: [
            {
                label: 'Dashboard',
                href: '#',
                icon: 'fas fa-chart-line',
                children: [
                    { label: 'Visão Geral', href: '/secao-a/visao-geral', icon: 'fas fa-eye' },
                    { label: 'Detalhes', href: '/secao-a/detalhes', icon: 'fas fa-list' },
                ],
            },
        ],
    },
];
```

A **Sidebar** e a **Upbar** consomem esse array. Para adicionar uma seção ou página, basta editar este arquivo + registrar a rota no `App.tsx`.

---

### 4.9 Páginas (`pages/`)

Cada página tem seu `.tsx` + `.css`, e segue o padrão:

```tsx
import { useDados } from '../../hooks/useDominioA';
import './MinhaPage.css';

export default function MinhaPage() {
    const { data, isLoading, error } = useDados();

    if (isLoading) return <div className="loading">Carregando...</div>;
    if (error) return <div className="error">Erro: {(error as Error).message}</div>;

    return (
        <div className="minha-page">
            <h1>Título da Página</h1>
            {/* Renderizar data aqui */}
        </div>
    );
}
```

---

### 4.10 Gráficos com Plotly

Usa `react-plotly.js` com `plotly.js-dist-min` para fidelidade visual:

```tsx
import Plot from 'react-plotly.js';

const darkLayout = {
    template: 'plotly_dark',
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: 'white', family: 'Inter' },
};

<Plot
    data={[{ x: datas, y: valores, type: 'scatter' }]}
    layout={{ ...darkLayout, title: 'Meu Gráfico' } as Record<string, unknown>}
    config={{ displayModeBar: false, responsive: true }}
    style={{ width: '100%', height: 400 }}
/>
```

> **Dica**: use `as Record<string, unknown>` no `layout` para evitar conflitos de tipo entre `plotly.js` e `react-plotly.js`.

---

### 4.11 Dependências Frontend (`package.json`)

```json
{
    "dependencies": {
        "@tanstack/react-query": "^5.62.0",
        "axios": "^1.7.0",
        "date-fns": "^4.1.0",
        "plotly.js-dist-min": "^3.3.1",
        "react": "^19.0.0",
        "react-dom": "^19.0.0",
        "react-plotly.js": "^2.6.0",
        "react-router-dom": "^7.1.0"
    },
    "devDependencies": {
        "@types/react": "^19.0.0",
        "@types/react-dom": "^19.0.0",
        "@types/react-plotly.js": "^2.6.0",
        "@vitejs/plugin-react": "^4.3.0",
        "typescript": "~5.7.0",
        "vite": "^6.0.0",
        "eslint": "^9.17.0"
    }
}
```

---

## 5. Fluxo de Dados Completo (Ponta a Ponta)

```
Usuário clica em uma página
       │
       ▼
React Router renderiza o componente da página
       │
       ▼
Componente chama hook (ex: useDados())
       │
       ▼
TanStack Query verifica cache client-side
       │
       ├── Cache válido? → Retorna dados imediatamente
       │
       └── Cache expirado? → Chama API client
                                    │
                                    ▼
                            fetch('/api/dominio/dados')
                                    │
                                    ▼
                           Vite Proxy (dev) redireciona
                                    │
                                    ▼
                            FastAPI endpoint recebe request
                                    │
                                    ▼
                            Import lazy do Service
                                    │
                                    ▼
                            Service consulta Cache (.pkl)
                                    │
                            ├── Cache .pkl existe? → Lê pickle
                            └── Não? → Query SQL Server → Retorna
                                    │
                                    ▼
                            Service retorna dict/list
                                    │
                                    ▼
                            FastAPI envelopa em APIResponse(data=...)
                                    │
                                    ▼
                            JSON response → Axios → TanStack → React re-render
```

---

## 6. Pipeline para Criar uma Nova Página

### Backend
1. Se necessário, crie o service em `services/dominio/service.py` com método que retorna dict/list
2. Crie o router em `api/routers/dominio.py` com endpoint GET/POST
3. Registre o router em `api/main.py`: `app.include_router(dominio.router)`

### Frontend
4. Crie o API client em `frontend/src/api/dominio.ts` — interfaces + função fetch
5. Crie o hook em `frontend/src/hooks/useDominio.ts` — wrapper useQuery
6. Crie componentes em `frontend/src/components/dominio/` — cards, tabelas, charts
7. Crie a página em `frontend/src/pages/Dominio/MinhaPage.tsx` + `.css`
8. Registre a rota em `App.tsx`: `<Route path="/secao/minha-page" element={...} />`
9. Adicione à navegação em `config/navigation.ts`

### Verificação
10. `npm run build` sem erros
11. Teste visual no browser com backend rodando

---

## 7. Identidade Visual (Dark Theme)

### Cores base
```css
:root {
    --color-primary: #1E3A8A;         /* Azul escuro */
    --color-secondary: #FF9500;       /* Laranja */
    --color-success: #10b981;         /* Verde */
    --color-danger: #ef4444;          /* Vermelho */
    --color-bg-dark: #000000;         /* Fundo principal */
    --color-bg-card: #1a1a1a;         /* Fundo de cards */
    --color-text: #ffffff;
    --color-text-muted: rgba(255,255,255,0.7);
    --color-border: rgba(255,255,255,0.1);
}
```

### Tipografia
- Fonte principal: **Inter** (Google Fonts)
- Ícones: **Font Awesome 6.4**

### Gradiente principal (títulos, destaques)
```css
background: linear-gradient(135deg, #1E3A8A, #FF9500);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
```

---

## 8. Padrões e Convenções

### Nomenclatura
| Tipo | Padrão | Exemplo |
|---|---|---|
| Router Python | `api/routers/<dominio>.py` | `routers/vendas.py` |
| Service Python | `services/<dominio>/service.py` | `services/vendas/service.py` |
| API Client TS | `src/api/<dominio>.ts` | `src/api/vendas.ts` |
| Hook TS | `src/hooks/use<Dominio>.ts` | `src/hooks/useVendas.ts` |
| Página React | `src/pages/<Dominio>/<Pagina>.tsx` | `src/pages/Vendas/Dashboard.tsx` |
| CSS par | `src/pages/<Dominio>/<Pagina>.css` | `src/pages/Vendas/Dashboard.css` |

### Imports Python
Sempre **absolutos**:
```python
from meu_projeto.services.vendas.service import VendasService
```

### Imports TypeScript
Path alias `@` para `src/`:
```typescript
import { useDados } from '@/hooks/useDados';
```

### Variáveis de Ambiente
- Sempre via `.env` na raiz, carregado por `python-dotenv`
- Acesso: `os.getenv('CHAVE', 'fallback')`
- Template em `.env.example` (commitado no git)

### Windows
- Use `;` para encadear comandos (não `&&`)
- `PYTHONPATH` sempre definido nos scripts `.bat`
- `.venv` na raiz do projeto

---

## 9. Checklist Completo para Criar o Projeto Clone

```markdown
## Infraestrutura
- [ ] Criar diretório raiz do projeto
- [ ] `python -m venv .venv`
- [ ] Criar `requirements.txt` (FastAPI + Pandas + Pydantic — SQLite é built-in)
- [ ] `pip install -r requirements.txt`
- [ ] Criar `.env` e `.env.example` (incluir DATABASE_PATH=database.db)
- [ ] Criar `.gitignore` (incluir .venv, cache/, __pycache__, .env, database.db*)
- [ ] Criar `run_api.bat` (com PYTHONPATH=src)

## Backend
- [ ] Criar `src/meu_projeto/__init__.py`
- [ ] Criar `src/meu_projeto/config.py` (constantes visuais, server config)
- [ ] Criar `src/meu_projeto/api/__init__.py`
- [ ] Criar `src/meu_projeto/api/config.py` (APISettings com pydantic-settings)
- [ ] Criar `src/meu_projeto/api/main.py` (FastAPI app, CORS, lifespan, routers)
- [ ] Criar `src/meu_projeto/api/models/common.py` (APIResponse, ErrorResponse)
- [ ] Criar `src/meu_projeto/api/dependencies.py` (singletons @lru_cache)
- [ ] Criar `src/meu_projeto/api/routers/__init__.py`
- [ ] Criar primeiro router de domínio
- [ ] Criar `src/meu_projeto/services/__init__.py`
- [ ] Criar `src/meu_projeto/services/db_connection.py`
- [ ] Criar primeiro service de domínio
- [ ] Testar: `run_api.bat` → acessar http://localhost:8528/docs

## Frontend
- [ ] `npx -y create-vite@latest frontend -- --template react-ts`
- [ ] `cd frontend && npm install`
- [ ] Instalar deps: `npm install @tanstack/react-query axios react-router-dom date-fns plotly.js-dist-min react-plotly.js`
- [ ] Instalar dev deps: `npm install -D @types/react-plotly.js`
- [ ] Configurar `vite.config.ts` com proxy `/api → localhost:8528`
- [ ] Criar `src/styles/globals.css` (reset + dark theme + variáveis)
- [ ] Criar `src/api/client.ts` (Axios instance)
- [ ] Criar `src/config/navigation.ts` (estrutura de navegação)
- [ ] Criar `src/components/layout/Sidebar.tsx` + `.css`
- [ ] Criar `src/components/layout/Upbar.tsx` + `.css`
- [ ] Criar `src/pages/Home/Home.tsx` + `.css`
- [ ] Configurar `src/App.tsx` (QueryClient + Router + Layout)
- [ ] Configurar `src/main.tsx` (entrypoint)
- [ ] Criar primeiro API client de domínio
- [ ] Criar primeiro hook
- [ ] Criar primeira página de domínio
- [ ] Testar: `npm run dev` → acessar http://localhost:3000
- [ ] Verificar: `npm run build` sem erros

## Validação
- [ ] Backend responde em /docs com Swagger
- [ ] Frontend abre no browser
- [ ] Proxy /api funciona (dados chegam no React)
- [ ] Dark theme consistente
- [ ] Navegação entre seções funcional
```

---

## 10. Diferenças em Relação ao TRUXT-DASH Original

| Aspecto | TRUXT-DASH (original) | Projeto clone |
|---|---|---|
| **Frontend legado** | Dash/Flask (porta 8527) | ❌ Não existe — só React |
| **Banco de dados** | SQL Server (pyodbc) | SQLite (built-in Python) |
| **Requirements** | `requirements.txt` + `requirements-api.txt` | Um único `requirements.txt` |
| **Scripts** | `run.bat` + `run_api.bat` | Apenas `run_api.bat` |
| **Conexão DB** | `pyodbc.connect(...)` com driver ODBC | `sqlite3.connect('database.db')` |

> O TRUXT-DASH carrega Dash por legado histórico. Projetos novos usam **apenas FastAPI + React**.
