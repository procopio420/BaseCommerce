# Stock Intelligence Engine

## Visão Geral

O Stock Intelligence Engine é um **módulo horizontal** e **reutilizável** que resolve problemas universais de decisão de compra de estoque, independentemente do vertical de negócio. Ele fornece inteligência sobre **O QUE comprar, QUANDO comprar e QUANTO comprar**.

**Regra de Ouro**: Este engine **apenas informa e recomenda**. Não compra produtos, não fala com fornecedores, não gera pedidos, não define preços. Quem decide e executa é o **Vertical App**.

---

## Objetivo do Engine

**Responsabilidade**: Ajudar o negócio a decidir **O QUE comprar, QUANDO comprar e QUANTO comprar**.

O engine recebe dados históricos de vendas e estoque atual, processa informações considerando lead time e sazonalidade, e retorna recomendações claras com explicações. O vertical decide se segue ou ignora as recomendações.

**Permite que qualquer vertical de negócio:**

- **O QUE comprar**: Identifique produtos que precisam ser comprados (risco de ruptura ou abaixo do mínimo)
- **QUANDO comprar**: Identifique o momento certo para comprar (baseado em lead time e estoque atual)
- **QUANTO comprar**: Sugira quantidade ideal de compra (baseada em vendas históricas e estoque mínimo/máximo)
- Classifique produtos por importância (análise ABC)
- Compreenda padrões de venda ao longo do tempo (sazonalidade)

**Regra de Ouro**: O engine **não decide**. Apenas **informa e recomenda**. A decisão final de compra é do **Vertical App**.

---

## O Que o Engine FAZ

### 1. Analisa Histórico de Vendas

- Calcula média de vendas por período (semana, mês)
- Identifica padrões de venda ao longo do tempo
- Detecta sazonalidade simples
- Calcula desvio padrão (variação)

### 2. Analisa Estoque Atual

- Compara estoque atual com vendas históricas
- Identifica produtos abaixo do mínimo sugerido
- Identifica produtos acima do máximo sugerido

### 3. Considera Lead Time de Fornecedor

- Usa tempo de reposição (lead time) fornecido pelo vertical
- Calcula estoque mínimo baseado em lead time
- Sugere compra antecipada considerando lead time

### 4. Considera Sazonalidade (Tempo)

- Detecta padrões sazonais simples (ex: vendas aumentam em dezembro)
- Ajusta previsões baseadas em sazonalidade
- Permite configuração manual de sazonalidade pelo vertical

### 5. Classifica Produtos (Ex: ABC)

- Classifica produtos em curva ABC (análise de Pareto)
- **Classe A**: Alto giro (20% dos produtos = 80% das vendas)
- **Classe B**: Médio giro
- **Classe C**: Baixo giro (80% dos produtos = 20% das vendas)

### 6. Gera Alertas de Risco de Ruptura

- Detecta produtos com risco de ficar sem estoque em X dias
- Calcula dias até ruptura baseado em vendas e estoque atual
- Nível de risco (Alto, Médio, Baixo)

### 7. Gera Alertas de Excesso de Estoque

- Identifica produtos com estoque acima do ideal
- Calcula capital parado em estoque
- Sugere redução de estoque para produtos com excesso

### 8. Sugere Quantidades de Reposição

- Sugere quantidade ideal de compra baseada em:
  - Vendas históricas
  - Estoque atual
  - Lead time
  - Estoque mínimo/máximo calculado
- Prioridade baseada em classificação ABC

### 9. Explica o Motivo da Sugestão (Transparência)

- Explicações em linguagem natural de por que sugere algo
- Exemplos: "Vende 10 unidades/dia, tem 20 unidades, lead time 7 dias. Ruptura em 2 dias se não comprar."
- Transparência: Usuário entende o raciocínio por trás da sugestão

---

---

## Problemas Universais Que Resolve

### 1. Ruptura de Estoque

**Problema**: Item fica sem estoque e vendas são perdidas.

**Solução**: Detecta risco de ruptura baseado em histórico de vendas e tempo de reposição.

**Universal**: Aplica-se a qualquer negócio que venda produtos físicos.

---

### 2. Excesso de Estoque

**Problema**: Capital investido em produtos que não vendem ou vendem pouco.

**Solução**: Identifica produtos com estoque acima do ideal e sugere redução.

**Universal**: Aplica-se a qualquer negócio com múltiplos produtos em estoque.

---

### 3. Decisão de Reposição Baseada em Intuição

**Problema**: Decisão de o que comprar e quanto comprar baseada em "feeling", não em dados.

**Solução**: Sugere reposição baseada em vendas históricas, não intuição.

**Universal**: Aplica-se a qualquer negócio que precise decidir o que comprar.

---

### 4. Desconhecimento de Itens Mais Importantes

**Problema**: Não sabe quais produtos são mais importantes para o negócio (classe A, B, C).

**Solução**: Classifica produtos em curva ABC (análise de Pareto).

**Universal**: Aplica-se a qualquer negócio com múltiplos produtos.

---

### 5. Desconhecimento de Padrões de Venda

**Problema**: Não identifica sazonalidade, tendências ou padrões de venda ao longo do tempo.

**Solução**: Analisa padrões históricos e detecta sazonalidade simples.

**Universal**: Aplica-se a qualquer negócio com histórico de vendas.

---

## Inputs Genéricos

### 1. Histórico de Vendas

**O que é**: Dados históricos de vendas por produto ao longo do tempo.

**Formato genérico**:
- Produto (identificador)
- Data da venda
- Quantidade vendida
- Valor da venda (opcional)

**Obrigatório**: Sim - sem histórico, engine não funciona.

**Fonte**: Vertical fornece dados de vendas históricas.

---

### 2. Estoque Atual

**O que é**: Quantidade atual disponível de cada produto.

**Formato genérico**:
- Produto (identificador)
- Quantidade atual
- Última atualização

**Obrigatório**: Sim - sem estoque atual, não pode calcular risco.

**Fonte**: Vertical fornece estado atual do estoque.

---

### 3. Parâmetros de Reposição

**O que é**: Configurações que definem como calcular sugestões.

**Parâmetros**:
- **Tempo de reposição (lead time)**: Tempo médio para receber produto após compra (em dias)
- **Estoque de segurança**: Margem de segurança para variações (percentual ou quantidade fixa)
- **Período de análise**: Quantos dias/meses de histórico usar (ex: 90 dias)
- **Estoque mínimo percentual**: Percentual do estoque máximo para considerar alerta

**Obrigatório**: Sim - define comportamento do engine.

**Fonte**: Vertical configura baseado em seu negócio.

---

### 4. Sazonalidade (Opcional)

**O que é**: Padrões de sazonalidade conhecidos (ex: vendas aumentam em dezembro).

**Formato genérico**:
- Produto (identificador)
- Período (ex: "dezembro", "primeiro trimestre")
- Fator de ajuste (ex: 1.5 = 50% a mais)

**Obrigatório**: Não - engine pode detectar automaticamente (simples).

**Fonte**: Vertical pode fornecer ou engine detecta automaticamente.

---

### 5. Classificação de Produtos (Opcional)

**O que é**: Classificação manual de produtos (se vertical já tem).

**Formato genérico**:
- Produto (identificador)
- Classe (A, B, C) ou Categoria

**Obrigatório**: Não - engine calcula automaticamente via curva ABC.

**Fonte**: Vertical pode fornecer ou engine calcula automaticamente.

---

## Outputs Genéricos

### 1. Alertas de Risco de Ruptura

**O que é**: Lista de produtos com risco de ficar sem estoque em X dias.

**Formato genérico**:
- Produto (identificador)
- Estoque atual
- Estoque mínimo calculado
- Dias até ruptura estimada
- Nível de risco (Alto, Médio, Baixo)
- Explicação simples (ex: "Vende 10 unidades/dia, tem 20 unidades, lead time 7 dias")

**Frequência**: Em tempo real (quando estoque muda) ou diário.

---

### 2. Sugestões de Reposição

**O que é**: Lista de produtos sugeridos para comprar com quantidades sugeridas.

**Formato genérico**:
- Produto (identificador)
- Quantidade sugerida
- Estoque atual
- Estoque mínimo calculado
- Estoque máximo sugerido
- Prioridade (Alta, Média, Baixa)
- Explicação simples (ex: "Vende 10 unidades/dia, lead time 7 dias, sugere 100 unidades para 10 dias de estoque")

**Frequência**: Diária ou sob demanda.

---

### 3. Análise ABC (Curva ABC)

**O que é**: Classificação de produtos em três classes (A, B, C) baseada em importância para o negócio.

**Formato genérico**:
- Produto (identificador)
- Classe (A, B, C)
- Percentual de vendas acumulado
- Percentual de produtos acumulado
- Explicação simples (ex: "Classe A: 20% dos produtos = 80% das vendas")

**Frequência**: Mensal (ou quando vertical solicita).

---

### 4. Identificação de Excesso de Estoque

**O que é**: Lista de produtos com estoque acima do ideal (capital parado).

**Formato genérico**:
- Produto (identificador)
- Estoque atual
- Estoque máximo sugerido
- Excesso (quantidade ou valor)
- Explicação simples (ex: "Tem 200 unidades, mas vende 5 unidades/dia, sugere máximo 100 unidades")

**Frequência**: Semanal ou mensal.

---

### 5. Explicações Simples

**O que é**: Explicações em linguagem natural de por que o engine sugere algo.

**Formato genérico**:
- Título da recomendação
- Explicação (1-2 frases)
- Dados de apoio (vendas médias, lead time, etc.)

**Exemplos**:
- "Risco de ruptura: Produto X vende 10 unidades/dia, tem 20 unidades, e lead time é 7 dias. Ruptura em 2 dias se não comprar."
- "Excesso de estoque: Produto Y tem 200 unidades, mas vende apenas 5 unidades/dia. Sugestão: reduzir para 100 unidades."

**Frequência**: Sempre que há alerta ou sugestão.

---

## O Que o Engine NÃO Faz

### 1. Não Compra Produtos

**O que não faz**: Não compra produtos, não executa compra, não processa pagamento.

**Por quê**: Engine é inteligência, não execução. Vertical decide e executa compra.

**O que faz**: Sugere o que comprar e quanto comprar. Vertical decide e executa.

---

### 2. Não Fala com Fornecedores

**O que não faz**: Não integra com fornecedores, não cria ordem de compra, não negocia com fornecedores.

**Por quê**: Engine é inteligência, não comunicação comercial. Vertical gerencia relacionamento com fornecedores.

**O que faz**: Sugere produtos e quantidades. Vertical gerencia fornecedores e executa compra.

---

### 3. Não Gera Pedidos

**O que não faz**: Não cria pedido de compra, não processa pedido, não atualiza status de pedido.

**Por quê**: Engine é inteligência, não execução operacional. Vertical cria e gerencia pedidos.

**O que faz**: Sugere o que comprar. Vertical cria pedido de compra se decidir seguir sugestão.

---

### 4. Não Define Preço de Venda

**O que não faz**: Não sugere preço de venda, não analisa margem, não otimiza preços.

**Por quê**: Engine é focado em estoque (quantidade), não em preços. Preços são responsabilidade de outro engine (Pricing Engine) ou do vertical.

**O que faz**: Analisa quantidade vendida e estoque. Não analisa preços.

---

### 5. Não Conhece Regras do Setor

**O que não faz**: Não sabe que "cimento" é diferente de "leite", não conhece regras específicas de construção ou mercado.

**Por quê**: Engine é horizontal e genérico. Regras específicas são responsabilidade do vertical.

**O que faz**: Analisa dados genéricos (identificador de produto, quantidade, data). Vertical interpreta no contexto do setor.

---

### 6. Não Gerencia Estoque Físico

**O que não faz**: Não atualiza estoque físico, não registra entradas/saídas, não faz inventário.

**Por quê**: Engine é inteligência, não gestão operacional. Vertical gerencia estoque físico.

**O que faz**: Lê estoque atual (fornecido pelo vertical) e fornece sugestões.

---

### 2. Não Compra Produtos

**O que não faz**: Não cria ordem de compra, não integra com fornecedores, não processa pagamentos.

**Por quê**: Engine é inteligência, não execução. Vertical decide e executa compras.

**O que faz**: Sugere o que comprar e quanto comprar.

---

### 3. Não Faz Previsão Complexa (Machine Learning)

**O que não faz**: Não usa machine learning avançado, não faz previsão de longo prazo, não analisa múltiplas variáveis complexas.

**Por quê**: Engine foca em simplicidade e interpretabilidade. Previsão complexa é futuro.

**O que faz**: Análise simples baseada em média histórica e padrões detectáveis.

---

### 4. Não Gerenciar Múltiplos Depósitos

**O que não faz**: Não gerencia estoque em múltiplos locais, não sugere transferência entre depósitos, não otimiza localização.

**Por quê**: Engine foca em estoque único inicialmente. Multi-depósito é futuro.

**O que faz**: Analisa estoque de um depósito (tenant/location).

---

### 5. Não Define Preços

**O que não faz**: Não sugere preços de venda, não analisa margem, não otimiza preços.

**Por quê**: Engine é focado em estoque, não em preços. Preços são responsabilidade do vertical.

**O que faz**: Analisa quantidade vendida e valor vendido (se disponível), mas não sugere preços.

---

## Como o Engine É Consumido por Verticais

### 1. API Genérica

**Como funciona**: Vertical envia dados (vendas, estoque) e recebe outputs (alertas, sugestões).

**Formato genérico**:
- **POST /stock-intelligence/v1/suggestions**: Envia vendas e estoque, recebe sugestões
- **GET /stock-intelligence/v1/alerts**: Recebe alertas de risco
- **GET /stock-intelligence/v1/abc-analysis**: Recebe análise ABC

**Interface**: REST API genérica, não específica de vertical.

---

### 2. Configuração por Vertical

**Como funciona**: Cada vertical configura parâmetros de reposição baseados em seu negócio.

**Exemplos**:
- Materiais de construção: Lead time 7-14 dias, estoque de segurança 20%
- Alimentação: Lead time 1-3 dias, estoque de segurança 10%
- Eletrônicos: Lead time 15-30 dias, estoque de segurança 30%

**Flexibilidade**: Engine aceita configurações diferentes por vertical ou por tenant.

---

### 3. Integração Transparente

**Como funciona**: Vertical consome engine como serviço interno, usuário não vê diferença.

**Experiência do usuário**: Usuário vê sugestões e alertas no contexto do vertical, não sabe que vem de engine horizontal.

**Isolamento**: Engine pode evoluir independentemente sem afetar vertical.

---

## Como o Vertical "Materiais de Construção" Consome o Engine

### 1. Integração no Fluxo do Vertical

**Pontos de consumo**:
- **Dashboard**: Exibe alertas de risco de ruptura e sugestões de reposição
- **Gestão de Estoque**: Visualiza análise ABC e estoque ideal por produto
- **Compra de Reposição**: Consulta sugestões antes de criar pedido de compra

**Exemplo de fluxo**:
1. Vertical consulta `GET /stock-intelligence/v1/alerts` periodicamente
2. Engine retorna alertas de risco de ruptura (ex: "Cimento: risco alto, ruptura em 5 dias")
3. Vertical exibe alertas no dashboard para o usuário
4. Usuário clica em "Ver sugestões de reposição"
5. Vertical consulta `GET /stock-intelligence/v1/suggestions?product_id=cimento`
6. Engine retorna sugestão: "Comprar 100 sacos, estoque mínimo 50, máximo 150"
7. Vertical exibe sugestão no contexto de materiais de construção
8. Usuário decide criar pedido de compra seguindo ou ajustando a sugestão

### 2. Dados Enviados pelo Vertical

**Quando cria/atualiza produto**:
- Vertical envia: identificador do produto, lead time configurado, estoque de segurança
- Engine armazena: configurações de reposição por produto

**Quando consulta sugestões**:
- Vertical envia: identificador do produto (ou lista de produtos)
- Engine retorna: sugestões específicas com explicações

**Quando consulta alertas**:
- Vertical envia: filtros opcionais (risco alto, produto específico)
- Engine retorna: lista de alertas ordenados por prioridade

### 3. Outputs Usados pelo Vertical

**Alertas de risco**:
- Exibidos no dashboard principal
- Permitem ação rápida: "Ver sugestões" ou "Ignorar"

**Sugestões de reposição**:
- Exibidas na tela de gestão de estoque
- Permitem ação: "Criar pedido de compra" com sugestão pré-preenchida

**Análise ABC**:
- Exibida em relatório de classificação de produtos
- Permite estratégia: foco em produtos classe A, reduzir classe C

---

## Eventos/Dados que o Vertical Envia de Volta ao Engine

### 1. Histórico de Vendas (Alimentação Contínua)

**Evento**: Pedido entregue com status "entregue"

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "pedido_entregue",
  "pedido_id": "uuid",
  "data_entrega": "2026-01-15T10:30:00Z",
  "itens": [
    {
      "produto_id": "uuid",
      "quantidade": 10,
      "valor_total": 320.00
    }
  ]
}
```

**Quando**: Sempre que um pedido é marcado como "entregue"

**Frequência**: Em tempo real (evento-driven) ou batched diário

**Objetivo**: Atualizar histórico de vendas para análise futura

---

### 2. Estoque Atual (Sincronização Periódica)

**Evento**: Atualização de estoque (entrada ou saída manual)

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "estoque_atualizado",
  "produto_id": "uuid",
  "quantidade_atual": 50,
  "data_atualizacao": "2026-01-15T10:30:00Z",
  "tipo_movimento": "entrada|saida|ajuste"
}
```

**Quando**: 
- Quando estoque é atualizado manualmente (inventário, ajuste)
- Quando produto é recebido de fornecedor
- Quando produto sai para venda (opcional - pode ser inferido de vendas)

**Frequência**: Em tempo real (evento-driven) ou sincronização diária

**Objetivo**: Manter estoque atualizado para cálculo de risco de ruptura

---

### 3. Parâmetros de Reposição Configurados

**Evento**: Configuração de parâmetros de reposição por produto

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "parametros_reposicao_configurados",
  "produto_id": "uuid",
  "lead_time_dias": 7,
  "estoque_seguranca_percentual": 20,
  "estoque_minimo_manual": null,
  "estoque_maximo_manual": null
}
```

**Quando**: Quando usuário configura parâmetros de reposição para um produto

**Frequência**: Sob demanda (quando configurado)

**Objetivo**: Personalizar cálculo de sugestões por produto

---

### 4. Confirmação de Compra (Feedback)

**Evento**: Pedido de compra criado seguindo sugestão do engine

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "sugestao_seguida",
  "sugestao_id": "uuid",
  "produto_id": "uuid",
  "quantidade_sugerida": 100,
  "quantidade_comprada": 100,
  "data_compra": "2026-01-15T10:30:00Z"
}
```

**Quando**: Quando usuário cria pedido de compra baseado em sugestão

**Frequência**: Sob demanda (quando usuário segue sugestão)

**Objetivo**: Feedback para melhorar algoritmos de sugestão (futuro)

---

### 5. Ignorar Sugestão (Feedback)

**Evento**: Usuário ignora sugestão de reposição

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "sugestao_ignorada",
  "sugestao_id": "uuid",
  "produto_id": "uuid",
  "motivo": "estoque_suficiente|preco_alto|outro"
}
```

**Quando**: Quando usuário descarta sugestão de reposição

**Frequência**: Sob demanda (quando usuário ignora)

**Objetivo**: Feedback para entender por que sugestões não são seguidas (futuro)

---

### Resumo de Integração

**Fluxo principal**:
1. Vertical alimenta engine com histórico de vendas (pedidos entregues)
2. Vertical alimenta engine com estoque atual (periódico)
3. Vertical configura parâmetros de reposição (quando necessário)
4. Engine calcula alertas e sugestões baseado nos dados
5. Vertical consulta engine para exibir alertas/sugestões
6. Vertical envia feedback quando segue/ignora sugestões (futuro)

**Bidirecionalidade**:
- Vertical → Engine: Dados de vendas, estoque, configurações, feedback
- Engine → Vertical: Alertas, sugestões, análise ABC, explicações

---

## Limites de Responsabilidade

### Engine É Responsável Por

- ✅ Análise de dados históricos de vendas
- ✅ Cálculo de estoque mínimo/máximo sugerido
- ✅ Detecção de risco de ruptura
- ✅ Sugestão de reposição
- ✅ Análise ABC
- ✅ Detecção de sazonalidade simples
- ✅ Explicações em linguagem natural

### Engine NÃO É Responsável Por

- ❌ Gestão de estoque físico (entradas/saídas)
- ❌ Decisão de compra (vertical decide)
- ❌ Integração com fornecedores
- ❌ Processamento de pagamentos
- ❌ Emissão de ordens de compra
- ❌ Gestão de preços
- ❌ Gestão de múltiplos depósitos

### Vertical É Responsável Por

- ✅ Fornecer dados históricos de vendas
- ✅ Fornecer estoque atual
- ✅ Configurar parâmetros de reposição
- ✅ Decidir se segue sugestões ou não
- ✅ Executar compras
- ✅ Atualizar estoque físico
- ✅ Apresentar alertas/sugestões para usuário

---

## Arquitetura Conceitual

```
┌─────────────────────────────────────────┐
│   Stock Intelligence Engine (Core)      │
│                                         │
│   ┌─────────────────────────────────┐  │
│   │   Análise de Vendas             │  │
│   │   - Histórico                   │  │
│   │   - Padrões                     │  │
│   │   - Sazonalidade                │  │
│   └─────────────────────────────────┘  │
│                                         │
│   ┌─────────────────────────────────┐  │
│   │   Cálculo de Reposição          │  │
│   │   - Estoque mínimo              │  │
│   │   - Estoque máximo              │  │
│   │   - Sugestões                   │  │
│   └─────────────────────────────────┘  │
│                                         │
│   ┌─────────────────────────────────┐  │
│   │   Alertas e Explicações         │  │
│   │   - Risco de ruptura            │  │
│   │   - Excesso                     │  │
│   │   - Linguagem natural           │  │
│   └─────────────────────────────────┘  │
└─────────────────────────────────────────┘
           ▲                    │
           │                    ▼
┌──────────┴──────────┐  ┌──────────────┐
│  Vertical Materials │  │ Future       │
│  (Construction)     │  │ Verticals    │
│                     │  │ - Food       │
│  Consome Engine     │  │ - Retail     │
│  para obter:        │  │ - etc.       │
│  - Alertas          │  │              │
│  - Sugestões        │  │ Consome      │
│  - Análise ABC      │  │ Engine       │
└─────────────────────┘  └──────────────┘
```

---

## Estratégia de Expansão Futura

### Fase 1: Vertical Inicial (Materiais de Construção)

- Engine é consumido apenas por vertical de materiais de construção
- Interface e outputs são genéricos, mas implementação inicial é focada em validar o engine

### Fase 2: Validação e Refinamento

- Engine é refinado baseado em feedback do vertical inicial
- Interface genérica é estabilizada
- Documentação de consumo é completa

### Fase 3: Expansão para Outros Verticais

- Engine é oferecido para outros verticais (ex: alimentação, eletrônicos, varejo)
- Configurações por vertical são suportadas
- Engine evolui baseado em necessidades de múltiplos verticais

### Princípios de Expansão

- ✅ Engine permanece horizontal (não vira vertical)
- ✅ Verticais evoluem independentemente
- ✅ Interface genérica não muda (backward compatible)
- ✅ Novos verticais podem consumir sem modificar engine

---

## Exemplos de Uso

### Exemplo 1: Vertical de Materiais de Construção

**Contexto**: Loja vende cimento, areia, tijolos, etc.

**Consumo do Engine**:
- Envia histórico de vendas (ex: vendeu 100 sacos de cimento no mês passado)
- Envia estoque atual (ex: tem 50 sacos de cimento)
- Configura parâmetros (lead time: 7 dias, estoque segurança: 20%)

**Output do Engine**:
- Alerta: "Risco de ruptura: Cimento vende 3 sacos/dia, tem 50 sacos, lead time 7 dias. Ruptura em ~16 dias."
- Sugestão: "Sugestão de reposição: Cimento - comprar 100 sacos (estoque máximo sugerido: 150 sacos)"

---

### Exemplo 2: Futuro Vertical de Alimentação

**Contexto**: Loja vende alimentos perecíveis.

**Consumo do Engine**:
- Envia histórico de vendas (ex: vendeu 200 unidades de leite no mês passado)
- Envia estoque atual (ex: tem 30 unidades de leite)
- Configura parâmetros (lead time: 2 dias, estoque segurança: 10%)

**Output do Engine**:
- Alerta: "Risco de ruptura: Leite vende 7 unidades/dia, tem 30 unidades, lead time 2 dias. Ruptura em ~4 dias."
- Sugestão: "Sugestão de reposição: Leite - comprar 50 unidades (estoque máximo sugerido: 70 unidades)"

**Observação**: Mesmo engine, configurações diferentes, outputs ajustados.

---

## Observações Importantes

### 1. Engine É Horizontal, Não Vertical

Engine não sabe que "cimento" é diferente de "leite". Ele apenas analisa:
- Identificador de produto (genérico)
- Quantidade vendida (número)
- Período (data)
- Parâmetros de reposição (configurável)

### 2. Vertical Interpreta Outputs

Vertical decide como apresentar sugestões para usuário:
- Materiais de construção: "Comprar cimento para obra X"
- Alimentação: "Comprar leite para reposição diária"

### 3. Simplicidade sobre Complexidade

Engine foca em simplicidade e interpretabilidade:
- Análise baseada em média histórica (simples)
- Não usa machine learning complexo (por enquanto)
- Explicações em linguagem natural

### 4. Evolução Independente

Engine pode evoluir sem afetar vertical:
- Novos algoritmos podem ser adicionados
- Interface permanece compatível
- Vertical continua funcionando

---

**Última atualização**: Janeiro 2026
**Versão**: 2.0 (MVP 2 - Documentação)

