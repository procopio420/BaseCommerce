# Frontend HTMX - Design System e Guia de Desenvolvimento

## Visão Geral

O frontend do BaseCommerce é construído usando **HTMX** (server-rendered) com um **Design System** customizado (HTML + CSS), seguindo uma arquitetura multi-tenant com branding server-side.

**Princípios:**
- Desktop-first (foco em balcão/PC)
- Pouca dependência de JS (apenas micro-interações)
- HTMX para partials e ações
- Estados loading/empty/error sempre tratados
- Multi-tenant via template context (server-side)

## Estrutura de Arquivos

```
apps/verticals/construction/src/construction_app/web/
├── models/
│   └── tenant_branding.py      # Modelo de branding (compartilhado com auth)
├── deps.py                      # Dependências (get_current_tenant_context)
├── router.py                    # Rotas SSR
├── static/
│   ├── app.css                  # Design System (tokens + components)
│   └── app.js                   # JavaScript mínimo (toast, drawer, helpers)
└── templates/
    ├── layout.html              # Layout base (TopBar + SideNav + Main + Footer)
    ├── pages/                   # Páginas principais
    │   ├── dashboard.html
    │   ├── cotacoes_list.html
    │   ├── cotacoes_new.html
    │   ├── pedidos_list.html
    │   ├── stock.html
    │   ├── suppliers.html
    │   ├── customers.html
    │   └── customer_details.html
    └── partials/               # Componentes HTMX reutilizáveis
        ├── table_cotacoes.html
        ├── table_pedidos.html
        ├── stock_table.html
        ├── suppliers_table.html
        ├── dashboard_alerts.html
        └── ...
```

## Multi-Tenant Server-Side

### Como Funciona

O tenant branding é resolvido **server-side** via template context:

1. **Middleware** (`TenantResolutionMiddleware`): Extrai `tenant_slug` do header `X-Tenant-Slug` ou Host
2. **Dependência** (`get_current_tenant_context`): Busca `Tenant` e `TenantBranding` do banco usando `user.tenant_id`
3. **Template Context**: Injetado em todas as rotas via `get_template_context()`

### CSS Variables Aplicadas

```html
<!-- Em layout.html -->
<style>
    :root {
        --primary-color: {{ tenant_context.primary_color }};
        --secondary-color: {{ tenant_context.secondary_color }};
        --primary-hover: color-mix(in srgb, var(--primary-color) 85%, black);
        --primary-light: color-mix(in srgb, var(--primary-color) 15%, white);
    }
</style>
```

### Usar no Template

```html
<!-- Logo do tenant -->
{% if tenant_context and tenant_context.logo_url %}
<img src="{{ tenant_context.logo_url }}" alt="{{ tenant_name }}">
{% else %}
<span>{{ tenant_name }}</span>
{% endif %}

<!-- Nome do tenant -->
{{ tenant_name }}  <!-- ou tenant_context.name -->
```

## Design System

### Tokens CSS

O design system define tokens em `app.css`:

#### Spacing
- `--spacing-1` a `--spacing-8` (4px a 32px base)

#### Colors
- `--color-primary`, `--color-secondary` (do tenant)
- `--color-bg`, `--color-surface`, `--color-text`, `--color-text-muted`, `--color-border`
- `--color-success`, `--color-warning`, `--color-danger`, `--color-info` (semantic)

#### Typography
- `--font-size-xs` a `--font-size-3xl`
- `--font-weight-normal`, `--font-weight-medium`, `--font-weight-semibold`, `--font-weight-bold`
- `--line-height-tight`, `--line-height-normal`, `--line-height-relaxed`

#### Radius & Shadows
- `--radius-sm` a `--radius-full`
- `--shadow-sm` a `--shadow-xl`

### Componentes Disponíveis

#### TopBar
```html
<nav class="topbar">
    <div class="topbar-content">
        <a href="/web/dashboard" class="topbar-brand">Logo/Nome</a>
        <div class="topbar-nav">
            <a href="/web/path" class="topbar-link active">Link</a>
        </div>
        <div class="topbar-user">User Menu</div>
    </div>
</nav>
```

#### SideNav
```html
<aside class="sidenav">
    <ul class="sidenav-list">
        <li class="sidenav-item">
            <a href="/web/path" class="sidenav-link active">
                <svg class="sidenav-icon">...</svg>
                Label
            </a>
        </li>
    </ul>
</aside>
```

#### Card
```html
<div class="card">
    <div class="card-header">
        <h2 class="card-title">Título</h2>
    </div>
    <div class="card-body">
        Conteúdo
    </div>
    <div class="card-footer">
        Footer (opcional)
    </div>
</div>
```

#### StatCard
```html
<div class="stat-card">
    <div class="stat-card-icon">...</div>
    <div class="stat-card-value">R$ 1.000,00</div>
    <div class="stat-card-label">Label</div>
    <div class="stat-card-change">Contexto adicional</div>
</div>
```

#### AlertCard
```html
<div class="alert-card alert-warning">
    <div class="alert-icon">...</div>
    <div class="alert-content">
        <div class="alert-title">Título</div>
        <div class="alert-message">Mensagem</div>
        <div class="alert-actions">
            <a href="/path" class="btn btn-sm">Ação</a>
        </div>
    </div>
</div>
```

Variantes: `alert-warning`, `alert-danger`, `alert-success`, `alert-info`

#### Badge
```html
<span class="badge badge-aprovada">Aprovada</span>
```

Variantes: `badge-rascunho`, `badge-enviada`, `badge-aprovada`, `badge-pendente`, `badge-entregue`, `badge-cancelada`, etc.

#### Button
```html
<a href="/path" class="btn btn-primary">Texto</a>
<button class="btn btn-outline btn-sm">Texto</button>
```

Variantes: `btn-primary`, `btn-secondary`, `btn-success`, `btn-danger`, `btn-outline`
Tamanhos: `btn-sm`, `btn-lg`
Modificadores: `btn-full`

#### Table
```html
<div class="table-container">
    <table class="table">
        <thead>
            <tr>
                <th>Coluna</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dado</td>
            </tr>
        </tbody>
    </table>
</div>
```

#### EmptyState
```html
<div class="empty-state">
    <div class="empty-state-title">Título</div>
    <div class="empty-state-message">Mensagem</div>
    <div class="empty-state-action">
        <a href="/path" class="btn btn-primary">Ação</a>
    </div>
</div>
```

#### Toast/Flash
```html
<!-- Container (já existe em layout.html) -->
<div id="flash-container" class="flash-container"></div>

<!-- Flash message (via partial ou HTMX swap-oob) -->
<div class="flash flash-success">
    Mensagem
    <button onclick="this.parentElement.remove()" class="flash-close">&times;</button>
</div>
```

Variantes: `flash-success`, `flash-error`, `flash-warning`, `flash-info`

## Padrões HTMX

### Carregar Partial em Container

```html
<div id="target" 
     hx-get="/web/endpoint" 
     hx-trigger="load, eventName from:body"
     hx-swap="innerHTML">
    <div class="htmx-indicator">Carregando...</div>
</div>
```

### Ação com Confirmação

```html
<button hx-post="/web/action" 
        hx-target="#container" 
        hx-swap="innerHTML"
        hx-confirm="Tem certeza?">
    Ação
</button>
```

### Filtros com Delay

```html
<form hx-get="/web/filter" 
      hx-target="#results"
      hx-trigger="change delay:300ms">
    <select name="status" class="form-input">
        <option value="">Todos</option>
    </select>
</form>
```

### Swap OOB (Out of Band)

```html
<!-- No partial retornado -->
<div class="flash flash-success" hx-swap-oob="beforeend:#flash-container">
    Mensagem
    <button onclick="this.parentElement.remove()" class="flash-close">&times;</button>
</div>
```

### Atualizar Múltiplos Elementos

```html
<!-- Trigger event após swap -->
<div hx-post="/web/action" 
     hx-target="#container"
     hx-swap="innerHTML"
     hx-headers='{"HX-Trigger": "itemUpdated"}'>
    Ação
</div>

<!-- Outro elemento escuta o evento -->
<div id="other" hx-get="/web/refresh" hx-trigger="itemUpdated from:body">
    ...
</div>
```

### HTMX Indicator Global

O CSS define `.htmx-indicator` que aparece durante requisições:

```html
<div class="htmx-indicator">Carregando...</div>
```

Por padrão, elementos com `.htmx-indicator` são ocultos e aparecem durante `htmx-request`.

## Como Criar uma Nova Tela

### 1. Criar Template

```html
{% extends "layout.html" %}

{% block title %}Minha Tela - {{ tenant_name }}{% endblock %}

{% block content %}
<div class="page-header">
    <h1 class="page-title">Minha Tela</h1>
    <p class="page-subtitle">Descrição</p>
</div>

<div class="card">
    <div class="card-header">
        <h2 class="card-title">Seção</h2>
    </div>
    <div class="card-body">
        <!-- Conteúdo -->
    </div>
</div>
{% endblock %}
```

### 2. Criar Rota

```python
@web_router.get("/minha-tela", response_class=HTMLResponse)
async def minha_tela_page(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    # Buscar dados
    items = db.query(Item).filter(Item.tenant_id == user.tenant_id).all()
    
    context = get_template_context(request, user=user, db=db, items=items)
    return templates.TemplateResponse("pages/minha_tela.html", context)
```

### 3. Criar Partial HTMX (se necessário)

```html
<!-- partials/items_table.html -->
{% if items %}
<div class="table-container">
    <table class="table">
        ...
    </table>
</div>
{% else %}
<div class="empty-state">
    <div class="empty-state-title">Nenhum item encontrado</div>
    <div class="empty-state-message">Comece adicionando itens.</div>
</div>
{% endif %}
```

### 4. Rota para Partial

```python
@web_router.get("/minha-tela/table", response_class=HTMLResponse)
async def minha_tela_table_partial(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    db: Session = Depends(get_db),
    status: str = Query(None),
):
    items = db.query(Item).filter(Item.tenant_id == user.tenant_id)
    if status:
        items = items.filter(Item.status == status)
    items = items.all()
    
    context = get_template_context(request, user=user, db=db, items=items)
    return templates.TemplateResponse("partials/items_table.html", context)
```

## JavaScript Helpers

### Toast Notifications

```javascript
window.BaseCommerce.showToast("Mensagem", "success|error|warning|info", duration);
```

### Formatação

```javascript
window.BaseCommerce.formatCurrency(1000); // "R$ 1.000,00"
window.BaseCommerce.formatDate(new Date()); // "01/01/2024"
```

### Drawer

```javascript
window.BaseCommerce.openDrawer('drawer-id');
window.BaseCommerce.closeDrawer('drawer-id');
```

## Responsividade

O design system é **desktop-first** com breakpoint em `768px`:

```css
@media (max-width: 768px) {
    .sidenav {
        transform: translateX(-100%);
    }
    .main-content {
        margin-left: 0;
    }
}
```

## Estados de UI

### Loading

```html
<div hx-get="/web/data" hx-trigger="load">
    <div class="htmx-indicator">Carregando...</div>
</div>
```

### Empty

```html
{% if items %}
<!-- Lista -->
{% else %}
<div class="empty-state">
    <div class="empty-state-title">Nenhum item</div>
    <div class="empty-state-message">Mensagem</div>
    <div class="empty-state-action">
        <a href="/path" class="btn btn-primary">Ação</a>
    </div>
</div>
{% endif %}
```

### Error

```html
<!-- Via flash message -->
<div class="flash flash-error">
    Erro ao processar
    <button onclick="this.parentElement.remove()" class="flash-close">&times;</button>
</div>
```

## Boas Práticas

1. **Sempre use `get_template_context()`** com `db=db` para ter tenant context
2. **Empty states claros**: Quando endpoint não existir, mostrar empty state com mensagem
3. **HTMX para interações**: Use HTMX ao invés de JS quando possível
4. **Acessibilidade**: Contraste adequado, foco visível, labels
5. **Performance**: Use `hx-trigger="load"` para lazy loading, `delay` em filtros
6. **Consistência**: Use componentes do design system, não invente classes
7. **Desktop-first**: Foco em balcão/PC, responsivo mínimo

## Troubleshooting

### HTMX não funciona
1. Verifique se HTMX está carregado: `<script src="https://unpkg.com/htmx.org@2.0.4"></script>`
2. Verifique se `hx-boost="true"` está no `<body>`
3. Verifique console do navegador

### Tenant branding não aparece
1. Verifique se `get_template_context()` recebe `db=db`
2. Verifique se `tenant_context` está no template context
3. Verifique se CSS variables estão sendo aplicadas

### Componentes não estilizam
1. Verifique se `app.css` está carregado
2. Verifique se classes estão corretas (sem typos)
3. Verifique se CSS variables do tenant estão definidas

## Referências

- [HTMX Documentation](https://htmx.org/docs/)
- [Design System Tokens](apps/verticals/construction/src/construction_app/web/static/app.css)
- [Jinja2 Template Documentation](https://jinja.palletsprojects.com/)
