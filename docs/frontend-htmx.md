# Frontend HTMX - Guia de Desenvolvimento

## Visão Geral

O frontend do BaseCommerce é construído usando **HTMX** (server-rendered) + **Tailwind CSS** (via CDN), seguindo uma arquitetura multi-tenant com design system mínimo e componentes reutilizáveis.

## Estrutura de Arquivos

```
apps/verticals/construction/src/construction_app/web/
├── templates/
│   ├── layout.html              # Layout base
│   ├── pages/                   # Páginas principais
│   │   ├── dashboard.html
│   │   ├── cotacoes_list.html
│   │   ├── cotacoes_new.html
│   │   ├── pedidos_list.html
│   │   ├── insights.html
│   │   └── ui_kit.html
│   └── partials/               # Componentes reutilizáveis
│       ├── button.html
│       ├── card.html
│       ├── badge.html
│       ├── alert_item.html
│       └── ...
├── static/
│   ├── app.css                 # Estilos custom (compatibilidade)
│   └── app.js                  # JavaScript mínimo
└── router.py                   # Rotas SSR
```

## Como Criar uma Nova Tela

### 1. Criar Template

Crie um arquivo em `templates/pages/`:

```html
{% extends "layout.html" %}

{% block title %}Minha Tela - {{ tenant_name }}{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <h1 class="text-3xl font-bold text-gray-900">Minha Tela</h1>
    <!-- Conteúdo aqui -->
</div>
{% endblock %}
```

### 2. Criar Rota no Router

Em `router.py`:

```python
@web_router.get("/minha-tela", response_class=HTMLResponse)
async def minha_tela_page(
    request: Request,
    user: UserClaims = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    context = get_template_context(request, user=user)
    return templates.TemplateResponse("pages/minha_tela.html", context)
```

### 3. Usar Partials

Inclua componentes reutilizáveis:

```html
{% include "partials/section_header.html" with title="Seção", subtitle="Descrição" %}
{% include "partials/button.html" with variant="primary", text="Clique", href="/path" %}
{% include "partials/card.html" with title="Título", content="Conteúdo" %}
```

## Design System

### Componentes Disponíveis

#### Button (`partials/button.html`)
```html
{% include "partials/button.html" with 
    variant="primary|secondary|outline|danger|ghost",
    size="sm|md|lg",
    text="Texto",
    href="/path" %}
```

#### Card (`partials/card.html`)
```html
{% include "partials/card.html" with 
    title="Título",
    content="Conteúdo HTML",
    footer="Footer HTML" %}
```

#### Badge (`partials/badge.html`)
```html
{% include "partials/badge.html" with 
    text="Status",
    variant="success|warning|danger|info|primary",
    size="sm|md|lg" %}
```

#### Stat Card (`partials/stat_card.html`)
```html
{% include "partials/stat_card.html" with 
    label="Métrica",
    value="R$ 1.000",
    trend="+12%",
    description="Descrição",
    icon="<svg>...</svg>" %}
```

#### Empty State (`partials/empty_state.html`)
```html
{% include "partials/empty_state.html" with 
    title="Título",
    message="Mensagem",
    cta_text="Ação",
    cta_href="/path",
    icon="<svg>...</svg>" %}
```

#### Alert Item (`partials/alert_item.html`)
```html
{% set alert = {
    "severity": "warning|danger|success|info",
    "title": "Título",
    "message": "Mensagem",
    "actions": [{"label": "Ação", "href": "/path"}]
} %}
{% include "partials/alert_item.html" with alert=alert %}
```

## Padrões HTMX

### Carregar Conteúdo Assíncrono

```html
<div hx-get="/web/endpoint" hx-trigger="load" hx-target="#target">
    Carregando...
</div>
```

### Atualizar após Ação

```html
<button hx-post="/web/action" 
        hx-target="#container" 
        hx-swap="innerHTML">
    Ação
</button>
```

### Filtros com Delay

```html
<select hx-get="/web/filter" 
        hx-target="#results"
        hx-trigger="change delay:300ms">
    <option>...</option>
</select>
```

### Swap OOB (Out of Band)

```html
<!-- No partial retornado -->
<div hx-swap-oob="beforeend:#flash-container">
    Mensagem
</div>
```

## Tenant Theming

### Carregar Tema

O tema é carregado automaticamente via `app.js` que busca `/tenant.json` e aplica CSS variables:

```javascript
// app.js faz isso automaticamente
loadTenantTheme(); // Aplica --primary-color, --secondary-color, etc.
```

### Usar Cores do Tenant

```html
<div class="bg-primary text-white">Usa cor primária do tenant</div>
<div class="text-primary">Texto na cor primária</div>
```

### CSS Variables Disponíveis

- `--primary-color`: Cor primária do tenant
- `--secondary-color`: Cor secundária
- `--primary-hover`: Cor primária escurecida
- `--primary-light`: Cor primária clareada

## JavaScript Helpers

### Toast Notifications

```javascript
window.BaseCommerce.showToast("Mensagem", "success|error|warning|info");
```

### Formatação

```javascript
window.BaseCommerce.formatCurrency(1000); // "R$ 1.000,00"
window.BaseCommerce.formatDate(new Date()); // "01/01/2024"
```

## Responsividade

### Breakpoints Tailwind

- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px

### Exemplo

```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <!-- Responsivo -->
</div>
```

## Troubleshooting

### HTMX não funciona

1. Verifique se HTMX está carregado: `<script src="https://unpkg.com/htmx.org@2.0.4"></script>`
2. Verifique se `hx-boost="true"` está no `<body>`
3. Verifique console do navegador para erros

### Tailwind não aplica estilos

1. Verifique se Tailwind CDN está carregado
2. Verifique se classes estão corretas (sem typos)
3. Use `!important` se necessário: `!bg-primary`

### Tenant theme não carrega

1. Verifique se `/tenant.json` está acessível
2. Verifique console para erros de fetch
3. Verifique se `app.js` está carregado

### Partials não renderizam

1. Verifique se caminho está correto: `partials/nome.html`
2. Verifique se variáveis estão sendo passadas
3. Verifique sintaxe Jinja2

## Boas Práticas

1. **Sempre use partials** para componentes reutilizáveis
2. **Mobile-first**: Comece com mobile, depois adicione breakpoints
3. **HTMX para interações**: Use HTMX ao invés de JS quando possível
4. **Acessibilidade**: Use `aria-label`, contraste adequado, foco visível
5. **Performance**: Evite carregar dados desnecessários, use `hx-trigger="load"` para lazy loading

## Exemplos Completos

### Lista com Filtros

```html
<!-- Filtros -->
<form hx-get="/web/items" hx-target="#results" hx-trigger="change delay:300ms">
    <select name="status">
        <option value="">Todos</option>
    </select>
</form>

<!-- Resultados -->
<div id="results" hx-get="/web/items" hx-trigger="load">
    {% include "partials/items_list.html" %}
</div>
```

### Modal/Drawer HTMX

```html
<!-- Trigger -->
<button hx-get="/web/item/123/details" hx-target="#modal">Ver Detalhes</button>

<!-- Modal -->
<div id="modal" class="hidden">
    <!-- Conteúdo carregado via HTMX -->
</div>
```

## Referências

- [HTMX Documentation](https://htmx.org/docs/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Jinja2 Template Documentation](https://jinja.palletsprojects.com/)


