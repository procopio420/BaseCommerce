# WhatsApp Messaging Engine

## Visao Geral

A WhatsApp Messaging Engine e um modulo horizontal que integra o BaseCommerce com WhatsApp atraves de multiplos providers. Ela e completamente independente das verticais e se comunica apenas via Redis Streams.

### Providers Suportados

A engine suporta multiplos providers de WhatsApp:

1. **Meta Cloud API** (Oficial): API oficial do WhatsApp Business
2. **Evolution API** (Open-source): Solucao baseada em Baileys/WhatsApp Web
3. **Stub Provider**: Para desenvolvimento e testes

Cada tenant pode escolher qual provider usar baseado em suas necessidades.

### Capacidades

1. **Inbound**: Receber mensagens de clientes via webhook
2. **Outbound**: Enviar mensagens para clientes (texto, templates, botoes)
3. **Routing**: Resolver tenant e contexto de conversa
4. **Automacao**: Detectar intencoes, respostas automaticas, opt-out
5. **Auditoria**: Historico de mensagens, status de entrega, erros

## Arquitetura

```
    ┌─────────────────┐         ┌─────────────────┐
    │   Meta Cloud    │         │  Evolution API  │
    │   WhatsApp API  │         │  (Baileys/Web)   │
    └────────┬────────┘         └────────┬────────┘
             │                           │
             └───────────┬───────────────┘
                         │
                ┌────────▼────────┐
                │ whatsapp-webhook│
                │   (FastAPI)     │
                │  Auto-detecta   │
                │    provider     │
                └────────┬────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
┌─────────▼───────┐     │     ┌────────▼────────┐
│bc:whatsapp:     │     │     │ events:materials│
│   inbound       │     │     │ (verticais)     │
└─────────┬───────┘     │     └────────┬────────┘
          │             │              │
          │    ┌────────▼────────┐     │
          │    │ whatsapp-worker │     │
          │    │   (consumer)    │◄────┘
          │    └────────┬────────┘
          │             │
┌─────────▼───────┐     │
│bc:whatsapp:     │◄────┘
│   outbound      │
└─────────────────┘
          │
┌─────────▼───────┐
│   PostgreSQL    │
│ (whatsapp_*)    │
└─────────────────┘
```

## Escolhendo um Provider

### Comparacao: Meta Cloud API vs Evolution API

| Caracteristica | Meta Cloud API | Evolution API |
|----------------|----------------|---------------|
| **Custo** | Pago (por mensagem) | Gratuito |
| **Requisitos** | WhatsApp Business aprovado | Nenhum (WhatsApp pessoal OK) |
| **Estabilidade** | Alta (API oficial) | Media (depende de sessao Web) |
| **Templates** | Suportado (aprovados) | Nao suportado |
| **Rate Limits** | 1000 msg/seg | Limitado por WhatsApp Web |
| **Risco de Banimento** | Baixo | Medio/Alto |
| **Setup** | Complexo (aprovacao Meta) | Simples (QR code) |
| **Self-hosted** | Nao | Sim (opcional) |

### Quando Usar Cada Provider

**Use Meta Cloud API se:**
- Voce tem WhatsApp Business aprovado
- Precisa de templates oficiais
- Volume alto de mensagens
- Prioriza estabilidade e conformidade

**Use Evolution API se:**
- Nao tem ou nao quer WhatsApp Business
- Volume baixo/medio
- Precisa de solucao rapida
- Aceita risco de banimento
- Quer evitar custos por mensagem

## Configuracao de Tenant

### 1. Registrar Binding - Meta Cloud API

```bash
python -m messaging_whatsapp.cli bind-tenant \
  --tenant-id "uuid-do-tenant" \
  --provider "meta" \
  --phone-number-id "ID_DO_NUMERO" \
  --waba-id "ID_DA_CONTA_WABA" \
  --display-number "+5511999999999" \
  --access-token "TOKEN_DE_ACESSO" \
  --verify-token "TOKEN_DE_VERIFICACAO"
```

### 2. Registrar Binding - Evolution API

```bash
# Primeiro, crie a instancia no Evolution API
python -m messaging_whatsapp.cli evolution-create-instance \
  --tenant-id "uuid-do-tenant" \
  --instance-name "tenant_123" \
  --api-url "https://evolution-api.example.com" \
  --api-key "SUA_API_KEY" \
  --display-number "+5511999999999"

# Depois, conecte o WhatsApp (gera QR code)
python -m messaging_whatsapp.cli evolution-connect \
  --instance-name "tenant_123" \
  --show-qr
```

### 3. Configurar Webhook

**Para Meta Cloud API:**

No Meta Business Manager:

1. Va para **WhatsApp > Configuracao > Webhooks**
2. Configure a URL: `https://seu-dominio.com/webhook`
3. Use o verify token: valor de `WHATSAPP_VERIFY_TOKEN`
4. Inscreva-se nos campos: `messages`

**Para Evolution API:**

Configure o webhook na Evolution API (via API ou painel):

```bash
# Via Evolution API
curl -X POST "https://evolution-api.example.com/webhook/instance/tenant_123" \
  -H "apikey: SUA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://seu-dominio.com/webhook",
    "webhook_by_events": false,
    "events": ["MESSAGES_UPSERT", "MESSAGES_UPDATE"]
  }'
```

### 4. Variaveis de Ambiente

```bash
# Webhook Service
WHATSAPP_VERIFY_TOKEN=seu_token_de_verificacao  # Para Meta
WHATSAPP_APP_SECRET=seu_app_secret_do_facebook   # Para Meta
EVOLUTION_API_KEY=chave_global_evolution         # Opcional (validacao global)

# Worker Service
WHATSAPP_PROVIDER=stub  # Provider padrao (meta, evolution, stub)
WHATSAPP_ENCRYPTION_KEY=chave_fernet_para_tokens

# Evolution API (opcional - se usar provider padrao)
EVOLUTION_API_URL=https://evolution-api.example.com
EVOLUTION_INSTANCE_NAME=default_instance

# Comum
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

## Eventos

### Eventos Publicados pela Engine

| Evento | Quando | Payload |
|--------|--------|---------|
| `whatsapp_inbound_received` | Cliente envia mensagem | from_phone, text, message_type |
| `whatsapp_action_requested` | Cliente clica botao/keyword | intent, from_phone, context |
| `whatsapp_customer_opted_out` | Cliente opta por sair | phone, reason |
| `whatsapp_delivery_failed` | Falha na entrega | message_id, error |
| `whatsapp_delivery_confirmed` | Mensagem entregue | message_id, status |

### Eventos Consumidos (de Verticais)

| Evento | Acao | Template |
|--------|------|----------|
| `quote_created` | Notifica cliente | quote_created_template |
| `order_status_changed` | Notifica status | order_status_template |
| `delivery_started` | Notifica saida | delivery_started_template |
| `delivery_completed` | Notifica entrega | delivery_completed_template |

Para ativar notificacoes WhatsApp, inclua no payload do evento:

```python
publish_event(
    event_type="quote_created",
    tenant_id=tenant_id,
    payload={
        "quote_id": "...",
        "customer_phone": "+5511888888888",  # Obrigatorio
        "notify_whatsapp": True,  # Opcional, mas recomendado
        "customer_name": "Joao Silva",
    }
)
```

## Automacao

### Keywords de Opt-Out

- `STOP`, `SAIR`, `CANCELAR`, `REMOVER`, `PARAR`

### Deteccao de Intencoes

| Intent | Keywords |
|--------|----------|
| `create_quote` | cotacao, orcamento, preco, valor |
| `order_status` | status, pedido, entrega, rastrear |
| `talk_to_human` | atendente, humano, ajuda, suporte |

### Botoes Padrao

```
[Fazer cotacao] [Status do pedido] [Falar com atendente]
```

## Templates

Templates devem ser aprovados no Meta Business Manager antes do uso.

### Registro de Templates

```python
from messaging_whatsapp.providers.meta_cloud.templates import template_registry, MessageTemplate

template_registry.register(MessageTemplate(
    name="meu_template",
    language="pt_BR",
    category="UTILITY",
    components=[
        TemplateComponent(
            type="body",
            parameters=[
                TemplateParameter(name="customer_name"),
                TemplateParameter(name="order_number"),
            ],
        ),
    ],
))
```

## CLI

### Comandos Gerais

```bash
# Listar bindings
python -m messaging_whatsapp.cli list-bindings

# Listar conversas
python -m messaging_whatsapp.cli list-conversations --tenant-id UUID

# Enviar mensagem teste
python -m messaging_whatsapp.cli send-test --to +5511999999999 --text "Ola!"

# Ver informacoes do stream
python -m messaging_whatsapp.cli stream-info --stream bc:whatsapp:inbound

# Replay DLQ
python -m messaging_whatsapp.cli replay-dlq --limit 10
```

### Comandos Evolution API

```bash
# Criar instancia Evolution
python -m messaging_whatsapp.cli evolution-create-instance \
  --tenant-id UUID \
  --instance-name "tenant_123" \
  --api-url "https://evolution-api.example.com" \
  --api-key "SUA_API_KEY"

# Conectar WhatsApp (gera QR code)
python -m messaging_whatsapp.cli evolution-connect \
  --instance-name "tenant_123" \
  --show-qr

# Listar instancias Evolution
python -m messaging_whatsapp.cli evolution-list-instances \
  --api-url "https://evolution-api.example.com" \
  --api-key "SUA_API_KEY"

# Ver status de uma instancia
python -m messaging_whatsapp.cli evolution-instance-status \
  --instance-name "tenant_123"
```

## Troubleshooting

### Webhook nao recebe mensagens

1. Verifique se o binding existe: `list-bindings`
2. Verifique o verify token no Meta Business Manager
3. Verifique logs do whatsapp-webhook
4. Verifique se a URL e acessivel publicamente (HTTPS)

### Mensagens nao sao enviadas

1. Verifique se o tenant tem binding ativo
2. Verifique se o access_token esta configurado
3. Verifique se o cliente nao esta opted-out
4. Verifique logs do whatsapp-worker
5. Verifique mensagens na DLQ: `stream-info --stream bc:whatsapp:dlq`

### Consultar mensagens no banco

```sql
-- Ultimas mensagens
SELECT * FROM whatsapp_messages 
ORDER BY created_at DESC LIMIT 10;

-- Conversas ativas
SELECT * FROM whatsapp_conversations 
WHERE status = 'active' 
ORDER BY last_message_at DESC;

-- Clientes que optaram por sair
SELECT * FROM whatsapp_optouts WHERE is_active = true;
```

### Consultar streams no Redis

```bash
# Via redis-cli
XINFO STREAM bc:whatsapp:inbound
XINFO GROUPS bc:whatsapp:inbound
XLEN bc:whatsapp:outbound
XRANGE bc:whatsapp:dlq - + COUNT 10
```

## Rate Limits

- Meta API: 1000 mensagens/segundo por numero
- Engine: Rate limit por tenant/customer via Redis (configuravel)

## Seguranca

1. **Tokens Criptografados**: Access tokens sao criptografados com Fernet
2. **Validacao de Assinatura**: Webhooks sao validados com HMAC-SHA256
3. **Multi-tenant**: Isolamento por tenant_id em todas as tabelas
4. **Opt-out**: Respeito automatico a pedidos de opt-out

## Tabelas do Banco

| Tabela | Descricao |
|--------|-----------|
| `whatsapp_tenant_bindings` | Mapeamento tenant <-> numero WhatsApp |
| `whatsapp_conversations` | Estado das conversas |
| `whatsapp_messages` | Historico de mensagens |
| `whatsapp_optouts` | Clientes que optaram por sair |
| `whatsapp_processed_events` | Idempotencia de eventos |

## Desenvolvimento

### Modo Stub

Para desenvolvimento local sem chamar APIs reais:

```bash
export WHATSAPP_PROVIDER=stub
```

O stub provider:
- Loga todas as mensagens
- Aceita qualquer assinatura de webhook
- Retorna IDs ficticios

### Evolution API Local

Para testar Evolution API localmente:

```bash
# Rodar Evolution API via Docker
docker run -d \
  --name evolution_api \
  -p 8080:8080 \
  -e AUTHENTICATION_API_KEY=test-key \
  atendai/evolution-api:latest

# Configurar binding
python -m messaging_whatsapp.cli evolution-create-instance \
  --tenant-id UUID \
  --instance-name "test_instance" \
  --api-url "http://localhost:8080" \
  --api-key "test-key"
```

## Riscos e Consideracoes

### Evolution API

**Riscos:**
- Uso de Evolution API pode violar termos de servico do WhatsApp
- Risco de banimento do numero WhatsApp
- Dependencia de manter sessao Web ativa
- Menos estavel que API oficial

**Mitigacoes:**
- Use apenas para desenvolvimento/testes ou volumes baixos
- Monitore desconexoes e reconecte automaticamente
- Considere Meta Cloud API para producao

### Meta Cloud API

**Riscos:**
- Custo por mensagem
- Requer aprovacao do Meta
- Processo de setup mais complexo

**Mitigacoes:**
- Templates aprovados reduzem custos
- API oficial e mais estavel
- Suporte oficial do Meta

### Testes

```bash
cd packages/messaging_whatsapp
pytest tests/ -v
```

