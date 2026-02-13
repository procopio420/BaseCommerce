# Sales Intelligence Engine

## Visão Geral

O Sales Intelligence Engine é um **módulo horizontal** e **reutilizável** que resolve problemas universais de aumento de valor de venda, independentemente do vertical de negócio. Ele ajuda a **AUMENTAR o valor da venda** com sugestões lógicas.

**Regra de Ouro**: Este engine **apenas sugere oportunidades de venda**. Não cria cotação, não fecha venda, não conversa com cliente, não define preços, não altera pedidos sozinha. Quem decide e executa é o **Vertical App**.

---

## Responsabilidade

**Responsabilidade**: Ajudar o negócio a **AUMENTAR o valor da venda** com sugestões lógicas.

O engine recebe dados de histórico de vendas e contexto atual (produtos no carrinho/cotação), analisa padrões e retorna sugestões de produtos complementares, substitutos ou bundles. O vertical decide se usa ou ignora as sugestões.

**Permite que qualquer vertical de negócio:**
- Sugira produtos complementares (quem compra X também compra Y)
- Sugira produtos substitutos (X não tem? Sugere Y similar)
- Identifique padrões de compra (cliente sempre compra A, B e C juntos)
- Recomende bundles (combinações de produtos que vendem bem juntos)
- Aumente ticket médio através de sugestões inteligentes

**Regra de Ouro**: O engine **não decide**. Apenas **sugere**. A decisão final de adicionar produtos é do **Vertical App**.

---

## O Que o Engine FAZ

### 1. Sugere Produtos Complementares

- Identifica produtos que são frequentemente comprados juntos
- Analisa padrões de compra (ex: quem compra cimento também compra areia)
- Sugere produtos relacionados ao que está no carrinho/cotação
- Explicação: "Clientes que compram X também compram Y (80% das vezes)"

### 2. Sugere Produtos Substitutos

- Identifica produtos similares quando produto desejado não está disponível
- Analisa características de produtos (categoria, preço similar, uso similar)
- Sugere alternativas quando produto está em falta
- Explicação: "X não disponível? Y é similar (mesma categoria, preço próximo)"

### 3. Identifica Padrões de Compra

- Identifica padrões de compra por cliente (ex: cliente sempre compra A, B e C juntos)
- Identifica padrões de compra por período (ex: em dezembro, clientes compram mais X)
- Identifica padrões de compra por contexto (ex: para obras, sempre inclui Y e Z)

### 4. Recomenda Bundles

- Identifica combinações de produtos que vendem bem juntos
- Sugere bundles baseados em vendas históricas (ex: "Pacote Construção: Cimento + Areia + Brita")
- Calcula desconto sugerido para bundle (futuro)
- Explicação: "Estes 3 produtos são frequentemente comprados juntos (70% das vezes)"

### 5. Usa Regras Simples (Não IA Pesada Inicialmente)

- Análise baseada em frequência (não machine learning complexo)
- Regras simples de associação (produto A + produto B = frequente)
- Análise de padrões detectáveis (não previsão complexa)
- Explicações simples e interpretáveis

### 6. Retorna Sugestões Explicáveis

- Cada sugestão vem com explicação em linguagem natural
- Explicação inclui: por que sugere, frequência do padrão, contexto
- Transparência: Usuário entende o raciocínio por trás da sugestão
- Exemplos: "80% dos clientes que compram cimento também compram areia"

---

## O Que o Engine NÃO Faz

### 1. Não Cria Cotação

**O que não faz**: Não cria cotação, não adiciona produtos à cotação, não modifica cotação.

**Por quê**: Engine é inteligência, não execução operacional. Vertical cria e gerencia cotações.

**O que faz**: Sugere produtos para adicionar. Vertical adiciona à cotação se decidir seguir sugestão.

---

### 2. Não Fecha Venda

**O que não faz**: Não finaliza venda, não aprova pedido, não processa pagamento.

**Por quê**: Engine é inteligência, não execução comercial. Vendas são responsabilidade do vertical.

**O que faz**: Sugere produtos para aumentar valor da venda. Vertical finaliza venda.

---

### 3. Não Conversa com Cliente

**O que não faz**: Não interage com cliente, não explica produtos, não negocia preço.

**Por quê**: Engine é inteligência, não comunicação. Interação com cliente é responsabilidade do vertical.

**O que faz**: Fornece sugestões. Vertical apresenta sugestões para cliente e interage.

---

### 4. Não Define Preços

**O que não faz**: Não sugere preço de venda, não calcula margem, não otimiza preços.

**Por quê**: Engine é focado em produtos (o que vender), não em preços (a que preço vender). Preços são responsabilidade do vertical ou de outro engine (Pricing Engine).

**O que faz**: Sugere produtos. Vertical ou Pricing Engine define preços.

---

### 5. Não Altera Pedidos Sozinha

**O que não faz**: Não adiciona produtos a pedidos existentes automaticamente, não modifica pedidos sem aprovação.

**Por quê**: Engine é inteligência, não execução. Alterações de pedidos requerem aprovação do usuário.

**O que faz**: Sugere produtos para adicionar. Vertical decide se adiciona e executa.

---

### 6. Não Conhece Regras do Setor

**O que não faz**: Não sabe que "cimento" é diferente de "leite", não conhece regras específicas de construção ou mercado.

**Por quê**: Engine é horizontal e genérico. Regras específicas são responsabilidade do vertical.

**O que faz**: Analisa padrões genéricos (produto A + produto B = frequente). Vertical interpreta no contexto do setor.

---

## Inputs Genéricos

### 1. Histórico de Vendas

**O que é**: Dados históricos de vendas (pedidos/cotações finalizadas) com produtos vendidos juntos.

**Formato genérico**:
- Venda (identificador de pedido/cotação)
- Data da venda
- Cliente (identificador - opcional)
- Produtos vendidos (lista de identificadores de produtos)
- Quantidades (opcional)

**Obrigatório**: Sim - sem histórico, engine não funciona.

**Fonte**: Vertical fornece histórico de vendas.

---

### 2. Contexto Atual (Carrinho/Cotação)

**O que é**: Produtos que estão atualmente no carrinho ou cotação sendo criada.

**Formato genérico**:
- Produtos no carrinho (lista de identificadores de produtos)
- Quantidades (opcional)
- Cliente (identificador - opcional)
- Contexto (ex: "criando_cotacao", "finalizando_pedido")

**Obrigatório**: Sim - sem contexto, engine não pode sugerir.

**Fonte**: Vertical fornece produtos no carrinho/cotação atual.

---

### 3. Catálogo de Produtos

**O que é**: Informações sobre produtos disponíveis para venda.

**Formato genérico**:
- Produto (identificador)
- Nome (opcional)
- Categoria (opcional)
- Preço (opcional - para análise)
- Status (ativo/inativo)

**Obrigatório**: Sim - sem catálogo, engine não pode sugerir produtos.

**Fonte**: Vertical fornece catálogo de produtos.

---

### 4. Parâmetros de Análise

**O que é**: Configurações que definem como analisar padrões e gerar sugestões.

**Parâmetros**:
- **Frequência mínima**: Frequência mínima para considerar padrão relevante (ex: 20%, 30%)
- **Período de análise**: Quantos dias/meses de histórico usar (ex: 90 dias, 12 meses)
- **Limite de sugestões**: Máximo de produtos para sugerir (ex: 3, 5)

**Obrigatório**: Não - engine usa valores padrão se não configurado.

**Fonte**: Vertical configura baseado em seu negócio.

---

## Outputs Genéricos

### 1. Sugestões de Produtos Complementares

**O que é**: Lista de produtos que são frequentemente comprados junto com produtos no carrinho.

**Formato genérico**:
- Produto sugerido (identificador)
- Tipo: complementar
- Frequência (% de vezes que é comprado junto)
- Explicação simples (ex: "80% dos clientes que compram X também compram Y")
- Prioridade (alta, média, baixa)

**Frequência**: Em tempo real (quando vertical solicita durante criação de cotação/carrinho).

---

### 2. Sugestões de Produtos Substitutos

**O que é**: Lista de produtos similares quando produto desejado não está disponível ou carrinho vazio.

**Formato genérico**:
- Produto sugerido (identificador)
- Tipo: substituto
- Produto original (se aplicável)
- Motivo (similar, mesma categoria, preço próximo)
- Explicação simples (ex: "Y é similar a X (mesma categoria, preço 5% mais barato)")

**Frequência**: Quando produto não está disponível ou vertical solicita.

---

### 3. Recomendações de Bundles

**O que é**: Combinações de produtos que são frequentemente vendidos juntos.

**Formato genérico**:
- Bundle (nome sugerido - opcional)
- Lista de produtos (identificadores)
- Frequência (% de vezes que são vendidos juntos)
- Desconto sugerido (opcional, futuro)
- Explicação simples (ex: "Estes 3 produtos são vendidos juntos em 70% das vendas")

**Frequência**: Quando vertical solicita ou quando contexto sugere bundle relevante.

---

### 4. Padrões de Compra Identificados

**O que é**: Padrões detectados no histórico de vendas (produtos que frequentemente aparecem juntos).

**Formato genérico**:
- Padrão (identificador)
- Lista de produtos que formam o padrão
- Frequência (% de vezes que padrão ocorre)
- Contexto (opcional: por cliente, por período, etc.)
- Explicação simples (ex: "Padrão: 60% dos clientes compram A, B e C juntos")

**Frequência**: Mensal ou quando vertical solicita análise de padrões.

---

### 5. Sugestões Contextuais

**O que é**: Sugestões específicas para o contexto atual (produtos no carrinho, cliente, etc.).

**Formato genérico**:
- Produto sugerido (identificador)
- Tipo (complementar, substituto, bundle)
- Contexto (por que sugere neste contexto)
- Explicação simples (ex: "Para cliente X: sugere Y (comprou Y nas últimas 3 compras)")

**Frequência**: Em tempo real (durante criação de cotação/carrinho).

---

## Como o Engine É Consumido por Verticais

### 1. API Genérica

**Como funciona**: Vertical envia contexto atual (produtos no carrinho) e recebe sugestões.

**Formato genérico**:
- **POST /sales-intelligence/v1/suggestions**: Solicita sugestões baseadas em contexto atual
- **GET /sales-intelligence/v1/complementary/{product_id}**: Produtos complementares de um produto
- **GET /sales-intelligence/v1/substitutes/{product_id}**: Produtos substitutos de um produto
- **GET /sales-intelligence/v1/bundles**: Lista de bundles sugeridos
- **GET /sales-intelligence/v1/patterns**: Padrões de compra identificados

**Interface**: REST API genérica, não específica de vertical.

---

### 2. Integração com Outros Engines

**Como funciona**: Pode consumir dados de outros engines para melhorar sugestões.

**Exemplo**:
- **Stock Intelligence Engine**: Pode sugerir produtos substitutos quando produto está em falta
- **Pricing Engine**: Pode usar preços para sugerir produtos com melhor margem (futuro)

**Interface**: API genérica compartilhada entre engines.

---

### 3. Integração Transparente

**Como funciona**: Vertical consome engine como serviço interno, usuário não vê diferença.

**Experiência do usuário**: Usuário vê sugestões de produtos no contexto do vertical (ex: "Quem viu isso também comprou..."), não sabe que vem de engine horizontal.

**Isolamento**: Engine pode evoluir independentemente sem afetar vertical.

---

## Como o Vertical "Materiais de Construção" Consome o Engine

### 1. Integração no Fluxo do Vertical

**Pontos de consumo**:
- **Criação de Cotação**: Exibe sugestões de produtos complementares enquanto vendedor adiciona itens
- **Finalização de Pedido**: Sugere produtos adicionais antes de finalizar
- **Produto Indisponível**: Sugere substitutos quando produto está em falta
- **Dashboard**: Exibe padrões de compra identificados para estratégia

**Exemplo de fluxo**:
1. Vendedor está criando cotação e adiciona "Cimento CP II"
2. Vertical consulta engine: `POST /sales-intelligence/v1/suggestions` com contexto: [Cimento]
3. Engine analisa histórico e retorna: "Areia" (80% dos clientes compram junto)
4. Vertical exibe sugestão no contexto: "Também recomendamos: Areia (80% dos clientes compram junto)"
5. Vendedor decide adicionar "Areia" à cotação
6. Vertical atualiza contexto e consulta novamente: [Cimento, Areia]
7. Engine retorna: "Brita" (70% dos clientes compram os 3 juntos)
8. Vertical exibe sugestão adicional
9. Vendedor finaliza cotação (pode seguir ou ignorar sugestões)
10. Vertical envia feedback quando vendedor segue sugestão (futuro)

### 2. Dados Enviados pelo Vertical

**Quando solicita sugestões**:
- Vertical envia: lista de produtos no carrinho/cotação, cliente_id (opcional), contexto
- Engine retorna: lista de sugestões (complementares, substitutos, bundles) com explicações

**Quando consulta produtos complementares**:
- Vertical envia: produto_id
- Engine retorna: lista de produtos frequentemente comprados junto

**Quando consulta substitutos**:
- Vertical envia: produto_id (produto indisponível)
- Engine retorna: lista de produtos similares

### 3. Outputs Usados pelo Vertical

**Sugestões de produtos complementares**:
- Exibidas durante criação de cotação/pedido
- Permitem ação: "Adicionar ao carrinho" ou "Ignorar"

**Sugestões de produtos substitutos**:
- Exibidas quando produto está indisponível
- Permitem ação: "Ver substituto" ou "Aguardar disponibilidade"

**Recomendações de bundles**:
- Exibidas como "Pacotes recomendados"
- Permitem ação: "Adicionar pacote completo" ou "Adicionar produtos separadamente"

---

## Eventos/Dados que o Vertical Envia de Volta ao Engine

### 1. Histórico de Vendas (Alimentação Contínua)

**Evento**: Cotação aprovada e convertida em pedido, ou pedido finalizado

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "venda_concluida",
  "pedido_id": "uuid",
  "cotacao_id": "uuid",
  "cliente_id": "uuid",
  "data_venda": "2026-01-15T10:30:00Z",
  "produtos_vendidos": [
    {
      "produto_id": "uuid",
      "quantidade": 10,
      "preco_unitario": 32.00,
      "valor_total": 320.00
    },
    {
      "produto_id": "uuid",
      "quantidade": 20,
      "preco_unitario": 15.00,
      "valor_total": 300.00
    }
  ],
  "valor_total_pedido": 620.00
}
```

**Quando**: 
- Quando cotação é convertida em pedido (venda confirmada)
- Quando pedido é finalizado (futuro: também quando cotação é aprovada)

**Frequência**: Em tempo real (evento-driven) ou batched diário

**Objetivo**: Atualizar histórico de vendas para análise de padrões e sugestões futuras

---

### 2. Contexto de Cotação/Pedido em Criação (Solicitação de Sugestões)

**Evento**: Vendedor está criando cotação/pedido e solicita sugestões

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "solicitacao_sugestoes",
  "contexto": "criando_cotacao|finalizando_pedido",
  "cliente_id": "uuid",
  "produtos_carrinho": [
    {
      "produto_id": "uuid",
      "quantidade": 10
    }
  ],
  "categoria_contexto": "obra|cliente_recorrente|nova_obra"
}
```

**Quando**: Durante criação de cotação/pedido, quando vendedor adiciona produto

**Frequência**: Em tempo real (quando solicitado)

**Objetivo**: Obter sugestões contextualizadas baseadas no que está no carrinho

---

### 3. Produto Indisponível (Solicitação de Substitutos)

**Evento**: Produto desejado não está disponível em estoque

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "produto_indisponivel",
  "produto_id": "uuid",
  "quantidade_desejada": 10,
  "motivo": "sem_estoque|produto_inativo",
  "contexto_carrinho": [
    {
      "produto_id": "uuid",
      "quantidade": 10
    }
  ]
}
```

**Quando**: Quando vendedor tenta adicionar produto que não está disponível

**Frequência**: Sob demanda (quando ocorre)

**Objetivo**: Obter sugestão de produto substituto para manter venda

---

### 4. Sugestão Seguida (Feedback)

**Evento**: Vendedor adiciona produto sugerido ao carrinho/cotação

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "sugestao_seguida",
  "sugestao_id": "uuid",
  "tipo_sugestao": "complementar|substituto|bundle",
  "produto_sugerido_id": "uuid",
  "produto_original_id": "uuid",
  "contexto_carrinho": [
    {
      "produto_id": "uuid",
      "quantidade": 10
    }
  ],
  "timestamp": "2026-01-15T10:30:00Z"
}
```

**Quando**: Quando vendedor adiciona produto sugerido pelo engine

**Frequência**: Sob demanda (quando vendedor segue sugestão)

**Objetivo**: Feedback para melhorar algoritmos de sugestão (futuro: validar se sugestões são úteis)

---

### 5. Sugestão Ignorada (Feedback)

**Evento**: Vendedor ignora sugestão de produto

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "sugestao_ignorada",
  "sugestao_id": "uuid",
  "tipo_sugestao": "complementar|substituto|bundle",
  "produto_sugerido_id": "uuid",
  "contexto_carrinho": [
    {
      "produto_id": "uuid",
      "quantidade": 10
    }
  ],
  "timestamp": "2026-01-15T10:30:00Z"
}
```

**Quando**: Quando vendedor descarta sugestão de produto

**Frequência**: Sob demanda (quando vendedor ignora)

**Objetivo**: Feedback para entender por que sugestões não são seguidas (futuro: melhorar relevância)

---

### 6. Venda Finalizada (Feedback Completo)

**Evento**: Cotação convertida em pedido ou pedido finalizado

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "venda_finalizada",
  "pedido_id": "uuid",
  "cliente_id": "uuid",
  "produtos_finais": [
    {
      "produto_id": "uuid",
      "quantidade": 10,
      "foi_sugerido": true,
      "sugestao_id": "uuid"
    },
    {
      "produto_id": "uuid",
      "quantidade": 20,
      "foi_sugerido": false
    }
  ],
  "valor_total": 620.00,
  "ticket_medio": 620.00,
  "data_venda": "2026-01-15T10:30:00Z"
}
```

**Quando**: Quando venda é finalizada (cotação convertida ou pedido finalizado)

**Frequência**: Em tempo real (evento-driven)

**Objetivo**: Feedback completo para validar se sugestões aumentaram ticket médio (futuro: métricas de sucesso)

---

### Resumo de Integração

**Fluxo principal**:
1. Vertical alimenta engine com histórico de vendas (cotações convertidas, pedidos finalizados)
2. Vendedor está criando cotação e adiciona produto
3. Vertical consulta engine para obter sugestões baseadas no carrinho atual
4. Engine retorna sugestões de produtos complementares, substitutos ou bundles
5. Vertical exibe sugestões no contexto de materiais de construção
6. Vendedor decide seguir ou ignorar sugestões
7. Vertical envia feedback quando sugere ou ignora (futuro: melhorar algoritmos)
8. Quando venda é finalizada, vertical alimenta engine com dados completos

**Bidirecionalidade**:
- Vertical → Engine: Histórico de vendas, contexto de criação, feedback de sugestões
- Engine → Vertical: Sugestões de produtos, padrões de compra, explicações

**Integração com outros engines**:
- **Stock Intelligence Engine**: Pode consultar disponibilidade antes de sugerir (futuro: não sugerir produtos em falta)
- **Pricing Engine**: Pode usar custo base para sugerir produtos com melhor margem (futuro)

---

## Limites de Responsabilidade

### Engine É Responsável Por

- ✅ Análise de padrões de compra
- ✅ Sugestão de produtos complementares
- ✅ Sugestão de produtos substitutos
- ✅ Recomendação de bundles
- ✅ Identificação de padrões de compra
- ✅ Explicações em linguagem natural

### Engine NÃO É Responsável Por

- ❌ Criação de cotações (vertical cria)
- ❌ Finalização de vendas (vertical finaliza)
- ❌ Interação com cliente (vertical interage)
- ❌ Definição de preços (vertical ou Pricing Engine)
- ❌ Alteração de pedidos (vertical altera com aprovação)

### Vertical É Responsável Por

- ✅ Fornecer histórico de vendas
- ✅ Fornecer contexto atual (produtos no carrinho)
- ✅ Decidir se usa ou ignora sugestões
- ✅ Apresentar sugestões para usuário (ex: "Também recomendamos...")
- ✅ Adicionar produtos sugeridos ao carrinho se usuário aprovar

---

## Exemplos de Uso

### Exemplo 1: Vertical de Materiais de Construção

**Contexto**: Vendedor está criando cotação com cimento e areia.

**Consumo do Engine**:
- Vertical envia contexto: produtos no carrinho = [Cimento, Areia]
- Vertical solicita sugestões

**Output do Engine**:
- Sugestão complementar: "Brita" (80% dos clientes que compram cimento e areia também compram brita)
- Sugestão bundle: "Pacote Básico: Cimento + Areia + Brita" (vendido junto em 70% das vezes)

**Ação do Vertical**:
- Interface mostra: "Também recomendamos: Brita (80% dos clientes compram junto)"
- Vendedor decide adicionar ou não
- Se adicionar, aumenta valor da venda

---

### Exemplo 2: Futuro Vertical de Alimentação

**Contexto**: Cliente está finalizando pedido com leite e açúcar.

**Consumo do Engine**:
- Vertical envia contexto: produtos no carrinho = [Leite, Açúcar]
- Vertical solicita sugestões

**Output do Engine**:
- Sugestão complementar: "Café" (75% dos clientes que compram leite e açúcar também compram café)
- Sugestão bundle: "Café da Manhã: Leite + Açúcar + Café" (vendido junto em 60% das vezes)

**Ação do Vertical**:
- Interface mostra: "Também recomendamos: Café (75% dos clientes compram junto)"
- Cliente decide adicionar ou não
- Se adicionar, aumenta ticket médio

**Observação**: Mesmo engine, contexto diferente (construção vs alimentação), outputs ajustados.

---

## Observações Importantes

### 1. Engine É Horizontal, Não Vertical

Engine não sabe que "cimento" é diferente de "leite". Ele apenas analisa:
- Identificador de produto (genérico)
- Padrões de associação (produto A + produto B = frequente)
- Frequência (número ou percentual)

### 2. Vertical Interpreta Outputs

Vertical decide como apresentar sugestões para usuário:
- Materiais de construção: "Também recomendamos: Brita (80% dos clientes compram junto)"
- Alimentação: "Também recomendamos: Café (75% dos clientes compram junto)"

### 3. Não Há Decisão Automática

Engine não adiciona produtos automaticamente ao carrinho. Apenas sugere. Vertical ou usuário decide.

### 4. Regras Simples Inicialmente

Engine usa análise simples (frequência, associação), não machine learning complexo inicialmente. Pode evoluir no futuro.

---

**Última atualização**: Janeiro 2026
**Versão**: 2.0 (MVP 2 - Documentação)

