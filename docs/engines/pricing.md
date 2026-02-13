# Pricing & Supplier Intelligence Engine

## Visão Geral

O Pricing & Supplier Intelligence Engine é um **módulo horizontal** e **reutilizável** que resolve problemas universais de decisão de fornecedor e custo, independentemente do vertical de negócio. Ele fornece inteligência sobre **DE QUEM comprar e A QUE CUSTO**.

**Regra de Ouro**: Este engine **apenas organiza e compara custos**. Não executa compra, não negocia automaticamente, não fala com cliente final, não define margem. Quem decide e executa é o **Vertical App**.

---

## Responsabilidade

**Responsabilidade**: Ajudar o negócio a decidir **DE QUEM comprar e A QUE CUSTO**.

O engine recebe preços de fornecedores, mantém histórico, compara fornecedores e retorna recomendações claras sobre qual fornecedor escolher e qual custo esperar. O vertical decide qual fornecedor usar e executa a compra.

**Permite que qualquer vertical de negócio:**
- Compare fornecedores objetivamente (preço, histórico, variação)
- Identifique fornecedor mais vantajoso para cada produto
- Acompanhe variação de preços ao longo do tempo
- Mantenha histórico de preços por fornecedor
- Identifique oportunidades de negociação (preço alto, variação grande)

**Regra de Ouro**: O engine **não decide**. Apenas **organiza e compara**. A decisão final de fornecedor é do **Vertical App**.

---

## O Que o Engine FAZ

### 1. Registra Preços de Fornecedores por Produto

- Armazena preço de cada fornecedor para cada produto
- Suporta múltiplos fornecedores por produto
- Suporta múltiplos produtos por fornecedor
- Timestamp de cada registro de preço

### 2. Mantém Histórico de Preços por Fornecedor

- Registra mudanças de preço ao longo do tempo
- Mantém histórico completo de preços
- Permite análise de tendência de preços
- Identifica padrões de variação de preço

### 3. Compara Fornecedores (A vs B)

- Compara preços de diferentes fornecedores para o mesmo produto
- Identifica fornecedor com menor preço
- Calcula diferença percentual entre fornecedores
- Ordena fornecedores por preço (menor para maior)

### 4. Calcula Custo Médio Atualizado

- Calcula custo médio ponderado por produto
- Considera preços de todos os fornecedores disponíveis
- Atualiza automaticamente quando preços mudam
- Pode considerar frequência de compra por fornecedor (futuro)

### 5. Identifica Variações Relevantes de Preço

- Detecta quando preço aumenta significativamente (ex: >10%)
- Detecta quando preço diminui significativamente
- Alertas de variação de preço por fornecedor
- Identifica fornecedores com preços instáveis

### 6. Sugere Fornecedor Mais Vantajoso

- Recomenda fornecedor com menor preço atual
- Considera histórico de preços (não apenas preço atual)
- Considera variação de preço (fornecedor estável vs instável)
- Explicação: "Fornecedor A: R$ 100, Fornecedor B: R$ 95 (5% mais barato)"

### 7. Expõe "Custo Base" para Outros Módulos

- Fornece custo base (preço médio ou preço do fornecedor recomendado) para outros módulos
- Stock Intelligence Engine pode usar custo base para calcular valor de estoque
- Vertical pode usar custo base para calcular margem de venda
- Integração transparente com outros módulos

---

## O Que o Engine NÃO Faz

### 1. Não Executa Compra

**O que não faz**: Não compra produtos, não processa pedido de compra, não processa pagamento.

**Por quê**: Engine é inteligência, não execução. Vertical decide e executa compra.

**O que faz**: Sugere fornecedor e custo. Vertical decide e executa compra.

---

### 2. Não Negocia Automaticamente

**O que não faz**: Não negocia preços com fornecedores, não envia propostas, não fecha negócio.

**Por quê**: Engine é inteligência, não comunicação comercial. Vertical gerencia negociação.

**O que faz**: Identifica oportunidades de negociação (preço alto, variação grande). Vertical negocia.

---

### 3. Não Fala com Cliente Final

**O que não faz**: Não vende para cliente final, não define preço de venda, não gerencia vendas.

**Por quê**: Engine é focado em custo (compra), não em receita (venda). Vendas são responsabilidade do vertical.

**O que faz**: Fornece custo base. Vertical define preço de venda e vende.

---

### 4. Não Define Margem

**O que não faz**: Não calcula margem de venda, não sugere preço de venda, não otimiza margem.

**Por quê**: Engine é focado em custo (compra), não em preço de venda. Margem é responsabilidade do vertical ou de outro engine (Sales Intelligence).

**O que faz**: Fornece custo base. Vertical ou Sales Intelligence Engine calcula margem e preço de venda.

---

### 5. Não Gera Preço de Venda Final

**O que não faz**: Não sugere preço de venda, não calcula preço final, não aplica margem.

**Por quê**: Engine é focado em custo (compra), não em preço de venda. Preço de venda é responsabilidade do vertical ou de outro engine.

**O que faz**: Fornece custo base. Vertical ou Sales Intelligence Engine define preço de venda.

---

### 6. Não Conhece Regras do Setor

**O que não faz**: Não sabe que "cimento" é diferente de "leite", não conhece regras específicas de construção ou mercado.

**Por quê**: Engine é horizontal e genérico. Regras específicas são responsabilidade do vertical.

**O que faz**: Analisa dados genéricos (identificador de produto, preço, fornecedor). Vertical interpreta no contexto do setor.

---

## Inputs Genéricos

### 1. Preços de Fornecedores

**O que é**: Preço de cada fornecedor para cada produto.

**Formato genérico**:
- Produto (identificador)
- Fornecedor (identificador)
- Preço (valor numérico)
- Data do preço
- Unidade de medida (opcional)
- Condições (opcional: prazo, quantidade mínima, etc.)

**Obrigatório**: Sim - sem preços, engine não funciona.

**Fonte**: Vertical fornece preços dos fornecedores.

---

### 2. Histórico de Preços

**O que é**: Histórico de mudanças de preço ao longo do tempo.

**Formato genérico**:
- Produto (identificador)
- Fornecedor (identificador)
- Preço (valor numérico)
- Data da alteração
- Tipo de alteração (novo preço, atualização, etc.)

**Obrigatório**: Não - engine cria histórico automaticamente quando preços são registrados.

**Fonte**: Engine mantém histórico automaticamente.

---

### 3. Parâmetros de Análise

**O que é**: Configurações que definem como analisar preços.

**Parâmetros**:
- **Threshold de variação**: Percentual mínimo para considerar variação relevante (ex: 5%, 10%)
- **Período de análise**: Quantos dias/meses de histórico usar (ex: 90 dias, 12 meses)
- **Peso do histórico**: Quanto considerar preço atual vs histórico (ex: 70% atual, 30% histórico)

**Obrigatório**: Não - engine usa valores padrão se não configurado.

**Fonte**: Vertical configura baseado em seu negócio.

---

## Outputs Genéricos

### 1. Comparação de Fornecedores

**O que é**: Comparação de preços entre fornecedores para o mesmo produto.

**Formato genérico**:
- Produto (identificador)
- Lista de fornecedores ordenada por preço:
  - Fornecedor (identificador)
  - Preço atual
  - Variação percentual vs fornecedor mais barato
  - Preço médio histórico (opcional)
  - Estabilidade de preço (estável, instável)

**Frequência**: Em tempo real (quando vertical solicita) ou diário.

---

### 2. Sugestão de Fornecedor Mais Vantajoso

**O que é**: Recomendação de qual fornecedor escolher para cada produto.

**Formato genérico**:
- Produto (identificador)
- Fornecedor recomendado (identificador)
- Preço recomendado
- Custo base (preço médio ou preço recomendado)
- Explicação simples (ex: "Fornecedor A: R$ 100, Fornecedor B: R$ 95 (5% mais barato). Recomenda Fornecedor B.")
- Alternativas (outros fornecedores com preços próximos)

**Frequência**: Em tempo real (quando vertical solicita) ou diário.

---

### 3. Alerta de Variação de Preço

**O que é**: Alerta quando preço aumenta ou diminui significativamente.

**Formato genérico**:
- Produto (identificador)
- Fornecedor (identificador)
- Preço anterior
- Preço atual
- Variação percentual
- Tipo de alerta (aumento, diminuição)
- Explicação simples (ex: "Preço aumentou 15% em 30 dias")

**Frequência**: Quando preço muda (em tempo real).

---

### 4. Custo Base Atualizado

**O que é**: Custo base por produto (preço médio ou preço do fornecedor recomendado).

**Formato genérico**:
- Produto (identificador)
- Custo base (valor numérico)
- Fornecedor usado no cálculo (opcional)
- Data da última atualização

**Frequência**: Em tempo real (quando vertical solicita).

---

### 5. Histórico de Preços

**O que é**: Histórico completo de preços por produto e fornecedor.

**Formato genérico**:
- Produto (identificador)
- Fornecedor (identificador)
- Lista de preços ao longo do tempo:
  - Preço
  - Data
  - Tipo de alteração

**Frequência**: Quando vertical solicita.

---

### 6. Análise de Tendência de Preço

**O que é**: Análise de tendência de preço ao longo do tempo (aumento, diminuição, estável).

**Formato genérico**:
- Produto (identificador)
- Fornecedor (identificador)
- Tendência (aumento, diminuição, estável)
- Percentual de variação no período
- Previsão simples (ex: "Tendência de aumento: +2% ao mês")

**Frequência**: Mensal ou quando vertical solicita.

---

## Como o Engine É Consumido por Verticais

### 1. API Genérica

**Como funciona**: Vertical envia preços de fornecedores e recebe recomendações.

**Formato genérico**:
- **POST /pricing-supplier/v1/prices**: Registra preço de fornecedor
- **GET /pricing-supplier/v1/comparison/{product_id}**: Compara fornecedores para produto
- **GET /pricing-supplier/v1/suggestion/{product_id}**: Sugestão de fornecedor mais vantajoso
- **GET /pricing-supplier/v1/base-cost/{product_id}**: Custo base do produto
- **GET /pricing-supplier/v1/alerts**: Alertas de variação de preço

**Interface**: REST API genérica, não específica de vertical.

---

### 2. Integração com Outros Engines

**Como funciona**: Outros engines podem consumir custo base para suas análises.

**Exemplo**:
- **Stock Intelligence Engine** consome custo base para calcular valor de estoque
- **Sales Intelligence Engine** pode consumir custo base para calcular margem sugerida

**Interface**: API genérica compartilhada entre engines.

---

### 3. Integração Transparente

**Como funciona**: Vertical consome engine como serviço interno, usuário não vê diferença.

**Experiência do usuário**: Usuário vê comparação de fornecedores e recomendações no contexto do vertical, não sabe que vem de engine horizontal.

**Isolamento**: Engine pode evoluir independentemente sem afetar vertical.

---

## Como o Vertical "Materiais de Construção" Consome o Engine

### 1. Integração no Fluxo do Vertical

**Pontos de consumo**:
- **Gestão de Fornecedores**: Compara preços entre fornecedores ao cadastrar produto
- **Cotação de Compra**: Consulta custo base ao criar pedido de compra
- **Negociação**: Visualiza histórico de preços e tendências antes de negociar
- **Dashboard**: Exibe alertas de variação de preço

**Exemplo de fluxo**:
1. Vertical registra novo preço: `POST /pricing-supplier/v1/prices` com fornecedor A: R$ 32
2. Engine armazena preço e calcula comparação com fornecedores existentes
3. Vertical consulta comparação: `GET /pricing-supplier/v1/comparison?product_id=cimento`
4. Engine retorna: Fornecedor B: R$ 30 (mais barato), Fornecedor A: R$ 32 (+6,7%)
5. Vertical exibe comparação no contexto de materiais de construção
6. Vertical consulta custo base: `GET /pricing-supplier/v1/base-cost?product_id=cimento`
7. Engine retorna: Custo base R$ 30 (preço do fornecedor recomendado)
8. Vertical usa custo base para calcular margem de venda

### 2. Dados Enviados pelo Vertical

**Quando registra preço de fornecedor**:
- Vertical envia: produto_id, fornecedor_id, preço, data, condições (opcional)
- Engine armazena: preço atual e histórico

**Quando consulta comparação**:
- Vertical envia: produto_id (ou lista de produtos)
- Engine retorna: lista de fornecedores ordenada por preço com comparação

**Quando consulta custo base**:
- Vertical envia: produto_id
- Engine retorna: custo base (preço médio ou preço recomendado)

### 3. Outputs Usados pelo Vertical

**Comparação de fornecedores**:
- Exibida na tela de gestão de fornecedores
- Permite decisão: "Escolher fornecedor mais barato" ou "Manter fornecedor atual"

**Custo base**:
- Usado internamente para cálculo de margem de venda
- Usado como referência para definir preço de venda

**Alertas de variação**:
- Exibidos no dashboard
- Permitem ação: "Revisar preço" ou "Renegociar com fornecedor"

---

## Eventos/Dados que o Vertical Envia de Volta ao Engine

### 1. Registro de Preço de Fornecedor (Alimentação Contínua)

**Evento**: Usuário cadastra ou atualiza preço de fornecedor

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "preco_fornecedor_registrado",
  "produto_id": "uuid",
  "fornecedor_id": "uuid",
  "preco": 32.00,
  "unidade": "KG",
  "data_preco": "2026-01-15T10:30:00Z",
  "condicoes": {
    "quantidade_minima": 100,
    "prazo_pagamento": 30,
    "validade_preco": "2026-02-15"
  }
}
```

**Quando**: Sempre que usuário cadastra ou atualiza preço de fornecedor

**Frequência**: Em tempo real (evento-driven)

**Objetivo**: Manter histórico de preços atualizado para comparação e análise

---

### 2. Atualização de Preço (Alimentação Contínua)

**Evento**: Fornecedor informa mudança de preço ou usuário atualiza manualmente

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "preco_atualizado",
  "produto_id": "uuid",
  "fornecedor_id": "uuid",
  "preco_anterior": 32.00,
  "preco_novo": 35.00,
  "variacao_percentual": 9.4,
  "data_atualizacao": "2026-01-15T10:30:00Z",
  "motivo": "reajuste_fornecedor|negociacao|outro"
}
```

**Quando**: Quando preço de fornecedor muda

**Frequência**: Em tempo real (evento-driven)

**Objetivo**: Detectar variações relevantes e gerar alertas

---

### 3. Pedido de Compra Criado (Feedback)

**Evento**: Usuário cria pedido de compra escolhendo fornecedor

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "pedido_compra_criado",
  "pedido_compra_id": "uuid",
  "produto_id": "uuid",
  "fornecedor_id": "uuid",
  "preco_compra": 30.00,
  "quantidade": 100,
  "data_compra": "2026-01-15T10:30:00Z"
}
```

**Quando**: Quando usuário cria pedido de compra (escolhe fornecedor)

**Frequência**: Em tempo real (evento-driven)

**Objetivo**: Feedback para entender qual fornecedor foi escolhido (futuro: melhorar sugestões)

---

### 4. Confirmação de Recebimento (Feedback)

**Evento**: Produto é recebido do fornecedor

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "produto_recebido",
  "pedido_compra_id": "uuid",
  "produto_id": "uuid",
  "fornecedor_id": "uuid",
  "quantidade_recebida": 100,
  "preco_real": 30.00,
  "data_recebimento": "2026-01-20T10:30:00Z",
  "divergencia": false
}
```

**Quando**: Quando produto é recebido do fornecedor (confirmação de entrega)

**Frequência**: Em tempo real (evento-driven)

**Objetivo**: Validar preço real vs preço informado, melhorar precisão do histórico

---

### Resumo de Integração

**Fluxo principal**:
1. Vertical registra preços de fornecedores (alimentação contínua)
2. Engine calcula comparações e custo base automaticamente
3. Vertical consulta engine para comparar fornecedores e obter custo base
4. Vertical usa custo base para calcular margem de venda
5. Vertical envia feedback quando cria pedido de compra (futuro: melhorar sugestões)

**Bidirecionalidade**:
- Vertical → Engine: Preços de fornecedores, atualizações, feedback de escolhas
- Engine → Vertical: Comparações, custo base, alertas de variação, tendências

**Integração com outros engines**:
- **Stock Intelligence Engine**: Consome custo base para calcular valor de estoque
- **Sales Intelligence Engine**: Pode consumir custo base para sugerir margem (futuro)

---

## Limites de Responsabilidade

### Engine É Responsável Por

- ✅ Registro e manutenção de preços de fornecedores
- ✅ Comparação de fornecedores
- ✅ Cálculo de custo base
- ✅ Detecção de variação de preço
- ✅ Sugestão de fornecedor mais vantajoso
- ✅ Análise de tendência de preço
- ✅ Histórico de preços

### Engine NÃO É Responsável Por

- ❌ Decisão de qual fornecedor usar (vertical decide)
- ❌ Execução de compra (vertical executa)
- ❌ Negociação com fornecedores (vertical negocia)
- ❌ Definição de preço de venda (vertical ou Sales Intelligence Engine)
- ❌ Cálculo de margem (vertical ou Sales Intelligence Engine)
- ❌ Gestão de relacionamento com fornecedores (vertical gerencia)

### Vertical É Responsável Por

- ✅ Fornecer preços dos fornecedores
- ✅ Decidir qual fornecedor usar (pode seguir ou ignorar sugestão do engine)
- ✅ Executar compra com fornecedor escolhido
- ✅ Negociar preços com fornecedores
- ✅ Usar custo base para calcular margem e preço de venda
- ✅ Apresentar comparação e recomendações para usuário

---

## Exemplos de Uso

### Exemplo 1: Vertical de Materiais de Construção

**Contexto**: Loja compra cimento de 3 fornecedores diferentes.

**Consumo do Engine**:
- Vertical registra preços: Fornecedor A: R$ 32, Fornecedor B: R$ 30, Fornecedor C: R$ 35
- Vertical solicita comparação para produto "Cimento CP II"

**Output do Engine**:
- Comparação: Fornecedor B: R$ 30 (mais barato), Fornecedor A: R$ 32 (+6,7%), Fornecedor C: R$ 35 (+16,7%)
- Sugestão: "Fornecedor B: R$ 30 (mais barato, 6,7% mais barato que Fornecedor A)"
- Custo base: R$ 30

**Ação do Vertical**:
- Usuário vê comparação no contexto de materiais de construção
- Usuário decide seguir sugestão (Fornecedor B) ou escolher outro
- Vertical executa compra com fornecedor escolhido

---

### Exemplo 2: Futuro Vertical de Alimentação

**Contexto**: Loja compra leite de 2 fornecedores diferentes.

**Consumo do Engine**:
- Vertical registra preços: Fornecedor X: R$ 5,50, Fornecedor Y: R$ 5,30
- Vertical solicita comparação para produto "Leite Integral 1L"

**Output do Engine**:
- Comparação: Fornecedor Y: R$ 5,30 (mais barato), Fornecedor X: R$ 5,50 (+3,8%)
- Sugestão: "Fornecedor Y: R$ 5,30 (mais barato, 3,8% mais barato que Fornecedor X)"
- Custo base: R$ 5,30

**Ação do Vertical**:
- Usuário vê comparação no contexto de alimentação
- Usuário decide seguir sugestão (Fornecedor Y) ou escolher outro
- Vertical executa compra com fornecedor escolhido

**Observação**: Mesmo engine, configurações diferentes, outputs ajustados.

---

## Observações Importantes

### 1. Engine É Horizontal, Não Vertical

Engine não sabe que "cimento" é diferente de "leite". Ele apenas analisa:
- Identificador de produto (genérico)
- Identificador de fornecedor (genérico)
- Preço (número)
- Data (timestamp)

### 2. Vertical Interpreta Outputs

Vertical decide como apresentar comparação e recomendações para usuário:
- Materiais de construção: "Fornecedor B: R$ 30 para cimento CP II"
- Alimentação: "Fornecedor Y: R$ 5,30 para leite integral"

### 3. Custo Base É Compartilhado

Custo base pode ser consumido por outros engines:
- Stock Intelligence Engine: Calcula valor de estoque
- Sales Intelligence Engine: Calcula margem sugerida

### 4. Não Há Decisão Automática

Engine não decide qual fornecedor usar automaticamente. Apenas sugere. Vertical decide.

---

**Última atualização**: Janeiro 2026
**Versão**: 2.0 (MVP 2 - Documentação)

