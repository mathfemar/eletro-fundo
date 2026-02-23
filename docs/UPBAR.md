# UPBAR.md - Guia de Criação de Novas Sessões na Upbar

# ESSE ARQUIVO ERA DE OUTRO PROJETO (TRUXT DASH)

## O Que é uma Sessão na Upbar?

A **upbar** (barra superior) é o componente de navegação principal do TRUXT-DASH que permite ao usuário alternar entre as grandes áreas do sistema. Cada botão na upbar representa uma **sessão** completa com sua própria home page e ferramentas.

### Sessões Existentes
- **Middle** - Área de Middle Office (BTC, Liquidez, Análise Gráfica)
- **Comercial** - Área Comercial (Concorrência)
- **Compliance** - Área de Compliance (Diligências)
- **Risco** - Área de Risco (inicialmente vazia, pronta para expansão)

---

## Anatomia de uma Sessão

Cada sessão é composta por **4 componentes fundamentais**:

```
┌─────────────────────────────────────────────┐
│  1. UPBAR (components/upbar.py)             │  ← Link de navegação
├─────────────────────────────────────────────┤
│  Sidebar         │  2. HOME PAGE            │
│  (components/    │  (pages/nome_secao.py)   │  ← Página inicial da seção
│  sidebar.py)     │                          │
│                  │  - Logo Truxt            │
│  3. SIDEBAR      │  - Saudação dinâmica     │  ← Navegação entre ferramentas
│  - Home Global   │  - Relógio               │     (só aparece nas sub-rotas)
│  ───────────     │                          │
│  - Ferramenta 1  │                          │
│  - Ferramenta 2  │                          │
└──────────────────┴──────────────────────────┘
         ↑
    4. ROUTING (index.py) ← Mapeia URLs para layouts
```

---

## Pipeline Completo: Criando uma Nova Sessão

### Passo 0: Planejamento

Antes de começar, defina:
- [ ] **Nome da sessão** (ex: "Jurídico", "Operações", "TI")
- [ ] **Slug da URL** (ex: `/juridico`, `/operacoes`, `/ti`)
- [ ] **Ferramentas iniciais** (pode começar vazio, apenas com home page)
- [ ] **Ícone Font Awesome** (opcional, para futuras ferramentas)

---

### Passo 1: Criar a Página Home da Sessão

**Localização**: `pages/{nome_secao}.py`

**Exemplo**: Para criar a seção "Risco", criamos `pages/risco.py`

#### 1.1. Copiar Template

Use `pages/middle.py` como base. Ele contém o layout padrão completo.

#### 1.2. Adaptar o Código

Faça as seguintes substituições (exemplo com "Risco"):

```python
# ========================================
# pages/risco.py
# ========================================
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
from datetime import datetime
from app import app

# Layout da página Risco - Página inicial da área Risco
layout = dbc.Container(
    [
        # Container centralizado
        html.Div(
            [
                # Título "Risco"
                html.Div([
                    html.H1(
                        "Risco",  # ← NOME DA SEÇÃO
                        style={
                            'fontSize': '3.5rem',
                            'fontWeight': '700',
                            'background': 'linear-gradient(135deg, #1E3A8A, #FF9500)',
                            'WebkitBackgroundClip': 'text',
                            'WebkitTextFillColor': 'transparent',
                            'backgroundClip': 'text',
                            'textAlign': 'center',
                            'marginBottom': '2rem',
                            'letterSpacing': '0.05em'
                        }
                    ),
                ], style={'textAlign': 'center'}),
                
                # Logo da empresa (MANTENHA IGUAL)
                html.Div([
                    html.Img(
                        src='/assets/Logo Truxt Clara.png',
                        style={
                            'maxWidth': '350px',
                            'width': '100%',
                            'height': 'auto',
                            'marginBottom': '3rem',
                            'filter': 'drop-shadow(0 8px 32px rgba(30, 58, 138, 0.6)) drop-shadow(0 0 48px rgba(30, 58, 138, 0.4))',
                        }
                    ),
                ], style={'textAlign': 'center'}),
                
                # Saudação dinâmica
                html.Div(
                    id='greeting-text-risco',  # ← TROCAR SUFIXO
                    style={
                        'fontSize': '2.5rem',
                        'fontWeight': '700',
                        'background': 'linear-gradient(135deg, #1E3A8A, #FF9500)',
                        'WebkitBackgroundClip': 'text',
                        'WebkitTextFillColor': 'transparent',
                        'backgroundClip': 'text',
                        'textAlign': 'center',
                        'marginBottom': '2rem',
                    }
                ),
                
                # Relógio
                html.Div(
                    id='clock-display-risco',  # ← TROCAR SUFIXO
                    style={
                        'fontSize': '3.5rem',
                        'fontWeight': '300',
                        'color': 'white',
                        'textAlign': 'center',
                        'fontFamily': 'monospace',
                        'letterSpacing': '0.1em',
                    }
                ),
                
                # Interval para atualizar o relógio
                dcc.Interval(
                    id='clock-interval-risco',  # ← TROCAR SUFIXO
                    interval=1000,
                    n_intervals=0
                ),
            ],
            style={
                'display': 'flex',
                'flexDirection': 'column',
                'justifyContent': 'center',
                'alignItems': 'center',
                'minHeight': '70vh',
            }
        ),
    ],
    fluid=True,
    style={'padding': '2rem'}
)

# Callback para atualizar saudação e relógio
@app.callback(
    [Output('greeting-text-risco', 'children'),      # ← TROCAR SUFIXO
     Output('clock-display-risco', 'children')],     # ← TROCAR SUFIXO
    Input('clock-interval-risco', 'n_intervals'),    # ← TROCAR SUFIXO
    prevent_initial_call=False
)
def update_greeting_and_clock_risco(n):  # ← TROCAR NOME DA FUNÇÃO
    """Atualiza a saudação baseada no horário e o relógio em tempo real."""
    now = datetime.now()
    hour = now.hour
    
    if 5 <= hour < 12:
        greeting = "Bom dia"
    elif 12 <= hour < 18:
        greeting = "Boa tarde"
    else:
        greeting = "Boa noite"
    
    clock_time = now.strftime("%H:%M:%S")
    return greeting, clock_time
```

#### 1.3. Pontos Críticos de Substituição

| Elemento | Padrão | Exemplo (Risco) |
|----------|--------|-----------------|
| Título H1 | `"Nome da Seção"` | `"Risco"` |
| ID Saudação | `greeting-text-{nome}` | `greeting-text-risco` |
| ID Relógio | `clock-display-{nome}` | `clock-display-risco` |
| ID Interval | `clock-interval-{nome}` | `clock-interval-risco` |
| Nome Callback | `update_greeting_and_clock_{nome}` | `update_greeting_and_clock_risco` |

> **⚠️ IMPORTANTE**: Todos os IDs devem ser únicos! Use sempre o sufixo `-{nome-da-secao}`.

---

### Passo 2: Adicionar Link na Upbar

**Localização**: `components/upbar.py`

#### 2.1. Localizar a Seção Correta

Procure pela lista de `dbc.Col` dentro do primeiro `dbc.Row`. Você verá os botões existentes (Middle, Comercial, Compliance).

#### 2.2. Adicionar Novo `dbc.Col`

Copie um dos blocos existentes e cole **antes** do fechamento da lista `]`:

```python
# Área Risco (novo link na upbar)
dbc.Col(
    [
        html.A(
            [
                html.Span(
                    "Risco",  # ← NOME EXIBIDO
                    style={
                        'fontSize': '1.1rem',
                        'fontWeight': '600',
                        'color': 'white',
                        'letterSpacing': '0.05em',
                        'transition': 'color 0.3s ease'
                    }
                ),
            ],
            href='/risco',  # ← URL DA SEÇÃO
            style={
                'display': 'flex',
                'alignItems': 'center',
                'textDecoration': 'none',
                'padding': '0.5rem 1rem',
                'borderRadius': '8px',
                'transition': 'background 0.3s ease'
            },
            className='upbar-link'
        ),
    ],
    width="auto",
    className="d-flex align-items-center"
),
```

#### 2.3. Posicionamento

O link aparecerá na ordem em que está no código. Coloque ao final da lista para que fique como último botão.

---

### Passo 3: Configurar a Sidebar

**Localização**: `components/sidebar.py`

#### 3.1. Localizar o Callback `update_sidebar_navigation`

Procure pela função decorada com `@app.callback` que retorna `sidebar-navigation`.

#### 3.2. Adicionar Bloco de Detecção de Rota

**Antes** do `return dbc.Nav(...)`, adicione:

```python
# --- RISCO ---
if pathname and pathname.startswith('/risco'):
    nav_items.extend([
        html.Hr(style={'borderColor': 'rgba(255,255,255,0.1)', 'margin': '1rem 1.5rem'}),
        # Futuras ferramentas da seção Risco serão adicionadas aqui
    ])
```

#### 3.3. Adicionando Ferramentas (Opcional - Futuro)

Se a seção tiver sub-páginas/ferramentas, adicione os links:

```python
if pathname and pathname.startswith('/risco'):
    nav_items.extend([
        html.Hr(style={'borderColor': 'rgba(255,255,255,0.1)', 'margin': '1rem 1.5rem'}),
        
        # Ferramenta simples
        dbc.NavLink(
            [html.I(className="fas fa-chart-pie", style={'marginRight': '10px'}), "Análise de Risco"],
            href="/risco/analise",
            active="exact"
        ),
        
        # Submenu colapsável (como BTC)
        html.Div([
            dbc.NavLink([...], id='risco-submenu-toggle', ...),
            html.Div([...], id='risco-submenu-content', ...)
        ])
    ])
```

> **⚠️ REGRA DE OURO**: A home page (`/risco`) **NUNCA** aparece como item clicável na sidebar. Apenas ferramentas/sub-páginas.

#### 3.4. Submenus Colapsáveis (Avançado)

Se precisar de submenu tipo BTC/Diligências, siga o padrão:

1. Adicione `clientside_callback` no topo do arquivo
2. Use estado inicial baseado em `pathname in [lista_de_rotas]`
3. IDs: `{nome}-submenu-toggle`, `{nome}-submenu-icon`, `{nome}-submenu-content`

**Exemplo completo em**: `sidebar.py` linhas 72-106 (BTC) ou 99-106 (Diligências)

---

### Passo 4: Registrar Rota no Index

**Localização**: `index.py`

#### 4.1. Importar o Módulo

No **topo do arquivo**, na linha de imports de `pages`, adicione o novo módulo:

```python
# ANTES:
from pages import home, middle, ..., compliance_sancoes

# DEPOIS:
from pages import home, middle, ..., compliance_sancoes, risco
```

#### 4.2. Adicionar Rota no Callback `display_page`

Dentro da função `display_page(pathname)`, adicione um novo `elif`:

```python
elif p == '/risco':
    return risco.layout
```

**Posicionamento**: Coloque junto com as outras rotas principais (após `/compliance`, antes de `/usuario`).

#### 4.3. Exemplo da Seção Completa

```python
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname'),
    prevent_initial_call=False
)
def display_page(pathname):
    if not pathname:
        pathname = '/'
    p = pathname.rstrip('/') if pathname != '/' else pathname

    if p == '/' or p == '':
        return home.layout
    elif p == '/middle':
        return middle.layout
    # ... outras rotas do middle ...
    elif p == '/comercial':
        return comercial.layout
    # ... outras rotas comercial ...
    elif p == '/compliance':
        return compliance.layout
    # ... outras rotas compliance ...
    elif p == '/risco':           # ← NOVO
        return risco.layout        # ← NOVO
    elif pathname == '/usuario':
        # ... resto do código ...
```

---

### Passo 5: Reiniciar o Servidor

**CRÍTICO**: Quando você adiciona um **novo módulo** (arquivo `.py`), o Dash não recarrega automaticamente.

#### 5.1. Parar o Servidor

No terminal onde o servidor está rodando, pressione `Ctrl+C`.

#### 5.2. Reiniciar

```powershell
.\run.bat
```

#### 5.3. Verificar no Navegador

Acesse: `http://localhost:8527/nome-da-secao`

---

## Checklist de Verificação

Use esta checklist para garantir que tudo foi feito corretamente:

### Arquivos Criados/Modificados
- [ ] **Criado** `pages/{nome_secao}.py` com layout completo
- [ ] **Modificado** `components/upbar.py` (link adicionado)
- [ ] **Modificado** `components/sidebar.py` (bloco de pathname adicionado)
- [ ] **Modificado** `index.py` (import + rota)

### Identidade Visual
- [ ] Título H1 com gradiente `linear-gradient(135deg, #1E3A8A, #FF9500)`
- [ ] Logo Truxt com drop-shadow azul
- [ ] Saudação dinâmica (Bom dia/Boa tarde/Boa noite)
- [ ] Relógio em tempo real (atualiza a cada 1s)
- [ ] Todos os IDs são únicos (sufixo `-{nome}`)

### Navegação
- [ ] Botão aparece na upbar
- [ ] Clicar no botão navega para `/{nome-secao}`
- [ ] Sidebar mostra separador (HR) quando na seção
- [ ] Home page da seção **NÃO** aparece na sidebar
- [ ] URL reflete corretamente (`/nome-secao`)

### Callbacks
- [ ] Callback de saudação/relógio tem nome único
- [ ] IDs de Input/Output batem com os do layout
- [ ] `prevent_initial_call=False` para execução imediata

### Servidor
- [ ] Servidor foi reiniciado após criar novo módulo
- [ ] Sem erros no console/terminal
- [ ] Página carrega sem erro 404

---

## Padrões de Nomenclatura

### Arquivos
- **Página home**: `pages/{nome_minusculo}.py` (ex: `risco.py`, `middle.py`)
- **Ferramentas**: `pages/{secao}_{ferramenta}.py` (ex: `compliance_sancoes.py`)

### URLs
- **Home da seção**: `/{nome-minusculo}` (ex: `/risco`, `/middle`)
- **Ferramentas**: `/{secao}/{ferramenta}` (ex: `/compliance/lista-sancoes`)

### IDs de Componentes
| Tipo | Padrão | Exemplo |
|------|--------|---------|
| Saudação | `greeting-text-{nome}` | `greeting-text-risco` |
| Relógio | `clock-display-{nome}` | `clock-display-risco` |
| Interval | `clock-interval-{nome}` | `clock-interval-risco` |
| Submenu Toggle | `{nome}-submenu-toggle` | `risco-submenu-toggle` |
| Submenu Icon | `{nome}-submenu-icon` | `risco-submenu-icon` |
| Submenu Content | `{nome}-submenu-content` | `risco-submenu-content` |

### Funções de Callback
- **Padrão**: `update_greeting_and_clock_{nome}(n)`
- **Exemplo**: `update_greeting_and_clock_risco(n)`

---

## Identidade Visual: Especificações

### Cores Padrão
```css
/* Gradiente principal (títulos) */
background: linear-gradient(135deg, #1E3A8A, #FF9500);

/* Background da página */
background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);

/* Separadores */
borderColor: rgba(255, 255, 255, 0.1);

/* Texto secundário */
color: rgba(255, 255, 255, 0.7);
```

### Tipografia
| Elemento | Font Size | Font Weight | Font Family |
|----------|-----------|-------------|-------------|
| Título H1 | 3.5rem | 700 | Inter (padrão) |
| Saudação | 2.5rem | 700 | Inter (padrão) |
| Relógio | 3.5rem | 300 | monospace |

### Efeitos Visuais
```css
/* Logo Truxt */
filter: drop-shadow(0 8px 32px rgba(30, 58, 138, 0.6)) 
        drop-shadow(0 0 48px rgba(30, 58, 138, 0.4));

/* Links da upbar (hover) */
transition: background 0.3s ease;
```

---

## Adicionando Ferramentas/Sub-páginas (Futuro)

Após criar a home page da seção, você pode adicionar ferramentas específicas:

### Exemplo: Adicionar "Análise de Risco" em `/risco/analise`

1. **Criar** `pages/risco_analise.py` com o layout da ferramenta
2. **Adicionar na sidebar** (em `sidebar.py`):
   ```python
   if pathname and pathname.startswith('/risco'):
       nav_items.extend([
           html.Hr(...),
           dbc.NavLink([
               html.I(className="fas fa-chart-line", ...),
               "Análise de Risco"
           ], href="/risco/analise", active="exact")
       ])
   ```
3. **Registrar rota** em `index.py`:
   ```python
   elif p == '/risco/analise':
       return risco_analise.layout
   ```

---

## Troubleshooting

### Erro 404 ao acessar a página
- ✅ Verifique se o módulo foi importado em `index.py`
- ✅ Verifique se a rota está no callback `display_page`
- ✅ **Reinicie o servidor** (`Ctrl+C` → `.\run.bat`)

### Link não aparece na upbar
- ✅ Verifique se adicionou o `dbc.Col` em `upbar.py`
- ✅ Verifique se o `href` está correto
- ✅ Limpe o cache do navegador (`Ctrl+Shift+R`)

### Saudação/Relógio não atualizam
- ✅ Verifique se os IDs no layout batem com os do callback
- ✅ Verifique se não há IDs duplicados com outras páginas
- ✅ Abra o console do navegador (F12) para ver erros

### Sidebar não mostra ferramentas
- ✅ Verifique se o bloco `if pathname.startswith(...)` está antes do `return`
- ✅ Verifique se o pathname está correto (ex: `/risco` não `/Risco`)
- ✅ Verifique se não esqueceu o `nav_items.extend([...])`

---

## Exemplos Completos

### Sessões Existentes como Referência

| Sessão | Home Page | Ferramentas | Submenus |
|--------|-----------|-------------|----------|
| **Middle** | `pages/middle.py` | BTC (4), Liquidez (1), Análise (2) | ✅ BTC, Análise |
| **Comercial** | `pages/comercial.py` | Concorrência (2) | ✅ Concorrência |
| **Compliance** | `pages/compliance.py` | Diligências (1) | ✅ Diligências |
| **Risco** | `pages/risco.py` | Nenhuma (ainda) | ❌ (vazio) |

### Para Estudar

- **Seção completa com submenus**: Veja `Middle` (mais complexa)
- **Seção simples**: Veja `Risco` (recém-criada, minimalista)
- **Home page padrão**: Veja `middle.py`, `comercial.py`, `compliance.py`, `risco.py`

---

## Resumo da Pipeline

```
1. Criar pages/{nome}.py (copiar de middle.py, trocar nome/IDs)
   ↓
2. Adicionar link em components/upbar.py (novo dbc.Col)
   ↓
3. Adicionar bloco em components/sidebar.py (if pathname.startswith)
   ↓
4. Importar e rotear em index.py (import + elif p == '/{nome}')
   ↓
5. Reiniciar servidor (Ctrl+C → .\run.bat)
   ↓
6. Testar navegação e funcionalidades
```

**Tempo estimado**: 5-10 minutos por sessão (sem ferramentas).

---

## Notas Finais

- **Sempre use `middle.py` como template** - É o mais completo e atualizado
- **IDs únicos são críticos** - Use sempre sufixo `-{nome-da-secao}`
- **Reinicie o servidor** - Novos módulos não carregam automaticamente
- **Siga a regra de ouro da sidebar** - Home page nunca aparece nela
- **Gradiente é identidade visual** - Mantenha `#1E3A8A → #FF9500`

**Boa sorte! 🚀**
