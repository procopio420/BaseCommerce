# Delivery & Fulfillment Engine

## Visão Geral

O Delivery & Fulfillment Engine é um **módulo horizontal** e **reutilizável** que resolve problemas universais de gestão do ciclo de entrega, independentemente do vertical de negócio. Ele gerencia o ciclo **pedido → entrega → confirmação**.

**Regra de Ouro**: Este engine **apenas executa e registra entregas**. Não vende, não cobra cliente, não define preço do frete, não emite nota, não decide políticas comerciais. Quem define o que entregar e para quem é o **Vertical App**.

---

## Responsabilidade

**Responsabilidade**: Gerenciar o ciclo **pedido → entrega → confirmação**.

O engine recebe pedidos prontos para entrega, planeja rotas, agrupa por região, controla status, registra ocorrências e coleta prova de entrega. O vertical define quais pedidos entregar e para quem, o engine executa a entrega e registra o resultado.

**Permite que qualquer vertical de negócio:**
- Planeje entregas eficientemente (agrupamento por região)
- Rastreie status de entrega em tempo real
- Registre ocorrências durante a entrega
- Colete prova de entrega (foto, assinatura)
- Calcule custo por entrega
- Analise desempenho de entregas

**Regra de Ouro**: O engine **não decide**. Apenas **executa e registra**. O vertical define o que entregar e para quem, o engine executa e registra.

---

## O Que o Engine FAZ

### 1. Planeja Entregas

- Agrupa pedidos por região/área
- Sugere rota otimizada (agrupamento por proximidade)
- Considera capacidade de carga (futuro)
- Considera restrições de horário (futuro)

### 2. Agrupa Pedidos por Rota

- Agrupa pedidos por endereço próximo
- Sugere ordem de entrega (roteirização simples)
- Otimiza distância percorrida
- Considera múltiplas entregas na mesma região

### 3. Controla Status da Entrega

- Status: pendente, em_preparacao, saiu_entrega, chegou, entregue, cancelado
- Atualiza status automaticamente (quando motorista marca)
- Histórico de mudanças de status
- Timestamp de cada mudança de status

### 4. Registra Ocorrências

- Ocorrências durante a entrega (faltou item, item errado, cliente não encontrado, etc.)
- Tipo de ocorrência (genérico)
- Descrição da ocorrência
- Timestamp da ocorrência
- Status resultante (entregue com divergência, não entregue, etc.)

### 5. Coleta Prova de Entrega (Foto, Assinatura)

- Foto dos produtos entregues
- Assinatura do responsável (digital)
- Data/hora da entrega
- Localização (coordenadas GPS - futuro)
- Status: entregue com prova ou entregue sem prova

### 6. Calcula Custo por Entrega

- Distância percorrida (futuro: GPS)
- Tempo gasto (futuro)
- Combustível (futuro: baseado em distância)
- Custo operacional por entrega

### 7. Retorna Dados para Análise Operacional

- Tempo médio de entrega
- Taxa de sucesso de entrega
- Taxa de ocorrências
- Eficiência da rota (distância percorrida vs otimizada)
- Desempenho por motorista (futuro)

---

## O Que o Engine NÃO Faz

### 1. Não Vende

**O que não faz**: Não cria pedido, não faz cotação, não vende para cliente.

**Por quê**: Engine é focado em entrega, não em venda. Vendas são responsabilidade do vertical.

**O que faz**: Recebe pedidos prontos para entrega (criados pelo vertical). Executa entrega.

---

### 2. Não Cobra Cliente

**O que não faz**: Não processa pagamento, não emite cobrança, não gerencia recebimento.

**Por quê**: Engine é focado em entrega, não em financeiro. Cobrança é responsabilidade do vertical ou de outro engine.

**O que faz**: Executa entrega e registra resultado. Vertical ou Financial Engine cobra cliente.

---

### 3. Não Define Preço do Frete

**O que não faz**: Não calcula frete, não sugere preço de frete, não negocia frete com cliente.

**Por quê**: Engine é focado em execução de entrega, não em precificação. Preço de frete é responsabilidade do vertical.

**O que faz**: Calcula custo da entrega (operacional). Vertical define preço de frete e cobra cliente.

---

### 4. Não Emite Nota

**O que não faz**: Não emite nota fiscal, não integra com sistema fiscal, não processa documentos fiscais.

**Por quê**: Engine é focado em entrega, não em fiscal. Fiscal é responsabilidade do vertical ou de sistema externo.

**O que faz**: Registra entrega. Vertical ou sistema fiscal emite nota.

---

### 5. Não Decide Políticas Comerciais

**O que não faz**: Não decide quando entregar, não decide prioridade de entrega, não decide políticas de entrega.

**Por quê**: Engine é focado em execução, não em estratégia comercial. Políticas são responsabilidade do vertical.

**O que faz**: Executa entrega conforme instruções do vertical. Vertical decide políticas.

---

### 6. Não Conhece Regras do Setor

**O que não faz**: Não sabe que "obra" é diferente de "casa", não conhece regras específicas de construção ou mercado.

**Por quê**: Engine é horizontal e genérico. Regras específicas são responsabilidade do vertical.

**O que faz**: Gerencia entrega genérica (endereço, produtos, motorista). Vertical interpreta no contexto do setor.

---

## Inputs Genéricos

### 1. Pedidos Prontos para Entrega

**O que é**: Pedidos com status "pronto para entrega" ou "saiu_entrega".

**Formato genérico**:
- Pedido (identificador)
- Cliente (identificador)
- Endereço de entrega (endereço completo)
- Produtos para entregar (lista de produtos com quantidades)
- Observações (opcional)
- Prioridade (opcional: alta, normal, baixa)

**Obrigatório**: Sim - sem pedidos, engine não funciona.

**Fonte**: Vertical fornece pedidos prontos para entrega.

---

### 2. Endereços das Entregas

**O que é**: Endereços completos dos locais de entrega.

**Formato genérico**:
- Endereço completo (rua, número, bairro, cidade, estado, CEP)
- Coordenadas GPS (opcional, futuro)
- Instruções de acesso (opcional)
- Horário preferencial (opcional)

**Obrigatório**: Sim - sem endereço, não pode entregar.

**Fonte**: Vertical fornece endereços (do pedido ou da obra/cliente).

---

### 3. Motoristas Disponíveis

**O que é**: Lista de motoristas disponíveis para entregar.

**Formato genérico**:
- Motorista (identificador)
- Nome (opcional)
- Status (disponível, ocupado, indisponível)
- Capacidade (futuro: veículo, carga máxima)

**Obrigatório**: Sim - sem motorista, não pode entregar.

**Fonte**: Vertical fornece motoristas disponíveis.

---

### 4. Veículos Disponíveis (Opcional - Futuro)

**O que é**: Lista de veículos disponíveis para entrega.

**Formato genérico**:
- Veículo (identificador)
- Tipo (caminhão, van, etc.)
- Capacidade de carga (peso, volume)
- Status (disponível, em uso, manutenção)

**Obrigatório**: Não - no MVP 3, pode ser manual.

**Fonte**: Vertical fornece veículos disponíveis (futuro).

---

### 5. Parâmetros de Roteirização

**O que é**: Configurações que definem como planejar entregas.

**Parâmetros**:
- **Método de agrupamento**: Por região, por distância, por capacidade (futuro)
- **Raio de agrupamento**: Distância máxima para agrupar (ex: 5 km, 10 km)
- **Capacidade máxima**: Máximo de pedidos por rota (futuro)

**Obrigatório**: Não - engine usa valores padrão se não configurado.

**Fonte**: Vertical configura baseado em seu negócio.

---

## Outputs Genéricos

### 1. Rota de Entrega Sugerida

**O que é**: Sugestão de rota otimizada agrupando pedidos por região.

**Formato genérico**:
- Rota (identificador)
- Lista de pedidos ordenada por ordem de entrega:
  - Pedido (identificador)
  - Endereço
  - Ordem na rota
  - Distância estimada (opcional, futuro)
- Motorista sugerido (opcional)
- Veículo sugerido (opcional, futuro)
- Distância total estimada (futuro)
- Tempo total estimado (futuro)

**Frequência**: Quando vertical solicita planejamento de entregas.

---

### 2. Status da Entrega Atualizado

**O que é**: Status atual de cada pedido na entrega.

**Formato genérico**:
- Pedido (identificador)
- Status atual (pendente, em_preparacao, saiu_entrega, chegou, entregue, cancelado)
- Última atualização (timestamp)
- Motorista responsável (opcional)
- Observações (opcional)

**Frequência**: Em tempo real (quando status muda).

---

### 3. Prova de Entrega

**O que é**: Evidência de que entrega foi realizada (foto, assinatura).

**Formato genérico**:
- Pedido (identificador)
- Foto dos produtos entregues (arquivo de imagem)
- Assinatura do responsável (arquivo de imagem ou texto)
- Data/hora da entrega (timestamp)
- Localização (coordenadas GPS - opcional, futuro)
- Nome do responsável que recebeu (opcional)
- Documento do responsável (opcional)

**Frequência**: Quando entrega é finalizada.

---

### 4. Ocorrências Registradas

**O que é**: Ocorrências durante a entrega (divergências, problemas, etc.).

**Formato genérico**:
- Pedido (identificador)
- Tipo de ocorrência (faltou_item, item_errado, cliente_nao_encontrado, recusa, etc.)
- Descrição da ocorrência
- Data/hora da ocorrência (timestamp)
- Motorista que registrou (opcional)
- Status resultante (entregue_com_divergencia, nao_entregue, etc.)

**Frequência**: Quando ocorrência é registrada (em tempo real).

---

### 5. Custo por Entrega

**O que é**: Custo operacional de cada entrega.

**Formato genérico**:
- Pedido (identificador)
- Distância percorrida (km - futuro)
- Tempo gasto (horas - futuro)
- Combustível (litros - futuro)
- Custo operacional (R$)
- Custo por km (futuro)

**Frequência**: Quando entrega é finalizada.

---

### 6. Dados para Análise Operacional

**O que é**: Métricas e dados para análise de desempenho de entregas.

**Formato genérico**:
- Tempo médio de entrega (horas ou dias)
- Taxa de sucesso de entrega (%)
- Taxa de ocorrências (%)
- Eficiência da rota (distância percorrida vs otimizada - futuro)
- Desempenho por motorista (futuro)

**Frequência**: Diária, semanal ou mensal (conforme vertical solicita).

---

## Como o Engine É Consumido por Verticais

### 1. API Genérica

**Como funciona**: Vertical envia pedidos prontos para entrega e recebe rotas, status e provas de entrega.

**Formato genérico**:
- **POST /delivery-fulfillment/v1/routes/plan**: Planeja rotas agrupando pedidos
- **POST /delivery-fulfillment/v1/deliveries**: Atribui pedido para entrega
- **PUT /delivery-fulfillment/v1/deliveries/{delivery_id}/status**: Atualiza status da entrega
- **POST /delivery-fulfillment/v1/deliveries/{delivery_id}/proof**: Registra prova de entrega
- **POST /delivery-fulfillment/v1/deliveries/{delivery_id}/occurrences**: Registra ocorrência
- **GET /delivery-fulfillment/v1/deliveries/{delivery_id}/cost**: Calcula custo da entrega

**Interface**: REST API genérica, não específica de vertical.

---

### 2. Integração com Outros Engines

**Como funciona**: Outros engines podem consumir dados de entrega para suas análises.

**Exemplo**:
- **Stock Intelligence Engine** pode usar dados de entregas para atualizar estoque (quando pedido é entregue)
- **Financial Intelligence Engine** (futuro) pode usar custo de entrega para análise financeira

**Interface**: API genérica compartilhada entre engines.

---

### 3. Integração Transparente

**Como funciona**: Vertical consome engine como serviço interno, usuário não vê diferença.

**Experiência do usuário**: Usuário vê rotas e status de entrega no contexto do vertical, não sabe que vem de engine horizontal.

**Isolamento**: Engine pode evoluir independentemente sem afetar vertical.

---

## Como o Vertical "Materiais de Construção" Consome o Engine

### 1. Integração no Fluxo do Vertical

**Pontos de consumo**:
- **Gestão de Pedidos**: Planeja rotas quando pedidos estão prontos para entrega
- **Rastreamento**: Atualiza status de entrega em tempo real
- **Confirmação**: Registra prova de entrega (foto, assinatura)
- **Dashboard**: Exibe status de entregas e ocorrências

**Exemplo de fluxo**:
1. Vertical marca pedidos como "prontos para entrega" (status do pedido muda para "saiu_entrega")
2. Vertical consulta engine: `POST /delivery-fulfillment/v1/routes/plan` com lista de pedidos
3. Engine agrupa pedidos por região e retorna rotas sugeridas
4. Vertical exibe rotas no contexto de materiais de construção (ex: "Rota Centro: 3 obras")
5. Usuário atribui motorista para cada rota
6. Motorista executa entrega e atualiza status: `PUT /delivery-fulfillment/v1/deliveries/{id}/status`
7. Engine atualiza status e retorna confirmação
8. Ao finalizar entrega, motorista registra prova: `POST /delivery-fulfillment/v1/deliveries/{id}/proof`
9. Engine armazena foto/assinatura e marca entrega como "entregue"
10. Vertical recebe evento "entrega_finalizada" e atualiza status do pedido para "entregue"

### 2. Dados Enviados pelo Vertical

**Quando planeja rotas**:
- Vertical envia: lista de pedidos com endereços de entrega (obras ou clientes)
- Engine retorna: rotas sugeridas agrupadas por região com ordem de entrega

**Quando atualiza status**:
- Vertical envia: delivery_id, novo_status, observações (opcional)
- Engine retorna: status atualizado com timestamp

**Quando registra prova de entrega**:
- Vertical envia: delivery_id, foto, assinatura, localização (opcional)
- Engine retorna: confirmação de registro de prova

### 3. Outputs Usados pelo Vertical

**Rotas sugeridas**:
- Exibidas na tela de gestão de entregas
- Permitem ação: "Atribuir motorista" ou "Ajustar rota"

**Status de entrega**:
- Exibido no rastreamento de pedidos
- Permite acompanhamento: "Em trânsito", "Chegou no local", "Entregue"

**Prova de entrega**:
- Exibida no histórico do pedido
- Permite resolução: "Ver prova" para resolver conflitos

---

## Eventos/Dados que o Vertical Envia de Volta ao Engine

### 1. Pedidos Prontos para Entrega (Alimentação Contínua)

**Evento**: Pedido com status "saiu_entrega" ou "pronto para entrega"

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "pedido_pronto_entrega",
  "pedido_id": "uuid",
  "cliente_id": "uuid",
  "obra_id": "uuid",
  "endereco_entrega": {
    "rua": "Rua Exemplo, 123",
    "bairro": "Centro",
    "cidade": "Barra Mansa",
    "estado": "RJ",
    "cep": "27300000",
    "coordenadas_gps": null
  },
  "produtos": [
    {
      "produto_id": "uuid",
      "quantidade": 10,
      "peso": 500.0,
      "volume": 0.5
    }
  ],
  "prioridade": "normal",
  "observacoes": "Entregar na obra em horário comercial"
}
```

**Quando**: Quando pedido muda para status "saiu_entrega" ou "pronto para entrega"

**Frequência**: Em tempo real (evento-driven)

**Objetivo**: Permitir planejamento de rotas e agrupamento de entregas

---

### 2. Atualização de Status de Entrega (Alimentação Contínua)

**Evento**: Motorista atualiza status da entrega (em trânsito, chegou, entregue)

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "status_entrega_atualizado",
  "delivery_id": "uuid",
  "pedido_id": "uuid",
  "status_anterior": "saiu_entrega",
  "status_novo": "chegou",
  "motorista_id": "uuid",
  "timestamp": "2026-01-15T10:30:00Z",
  "observacoes": "Chegou no local, aguardando recebedor"
}
```

**Quando**: Sempre que status da entrega muda (atualizado pelo motorista)

**Frequência**: Em tempo real (evento-driven)

**Objetivo**: Rastreamento em tempo real e histórico de mudanças de status

---

### 3. Prova de Entrega (Alimentação Contínua)

**Evento**: Motorista registra prova de entrega (foto, assinatura)

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "prova_entrega_registrada",
  "delivery_id": "uuid",
  "pedido_id": "uuid",
  "foto_produtos": "base64_encoded_image",
  "assinatura_recebedor": "base64_encoded_image",
  "nome_recebedor": "João Silva",
  "documento_recebedor": "12345678900",
  "data_hora_entrega": "2026-01-15T10:30:00Z",
  "coordenadas_gps": {
    "latitude": -22.5431,
    "longitude": -44.1709
  }
}
```

**Quando**: Quando motorista finaliza entrega e registra prova

**Frequência**: Em tempo real (evento-driven)

**Objetivo**: Evidência de entrega para resolver conflitos e garantir confiabilidade

---

### 4. Ocorrência Durante Entrega (Alimentação Contínua)

**Evento**: Problema ou divergência durante entrega

**Dados enviados**:
```json
{
  "tenant_id": "uuid",
  "event_type": "ocorrencia_entrega",
  "delivery_id": "uuid",
  "pedido_id": "uuid",
  "tipo_ocorrencia": "faltou_item|item_errado|cliente_nao_encontrado|recusa|outro",
  "descricao": "Faltou 2 sacos de cimento",
  "motorista_id": "uuid",
  "timestamp": "2026-01-15T10:30:00Z",
  "status_resultante": "entregue_com_divergencia|nao_entregue",
  "produtos_afetados": [
    {
      "produto_id": "uuid",
      "quantidade_esperada": 10,
      "quantidade_entregue": 8,
      "diferenca": 2
    }
  ]
}
```

**Quando**: Quando ocorre problema durante entrega (divergência, problema de acesso, etc.)

**Frequência**: Sob demanda (quando ocorre)

**Objetivo**: Registrar problemas para análise operacional e resolução

---

### 5. Entrega Finalizada (Feedback para Outros Engines)

**Evento**: Entrega concluída com sucesso (status "entregue")

**Dados enviados (para Stock Intelligence Engine)**:
```json
{
  "tenant_id": "uuid",
  "event_type": "entrega_finalizada",
  "pedido_id": "uuid",
  "data_entrega": "2026-01-15T10:30:00Z",
  "itens_entregues": [
    {
      "produto_id": "uuid",
      "quantidade": 10,
      "valor_total": 320.00
    }
  ]
}
```

**Quando**: Quando entrega é finalizada com sucesso

**Frequência**: Em tempo real (evento-driven)

**Objetivo**: Alimentar Stock Intelligence Engine com histórico de vendas (pedido entregue = venda concluída)

---

### Resumo de Integração

**Fluxo principal**:
1. Vertical marca pedidos como "prontos para entrega"
2. Vertical consulta engine para planejar rotas (agrupamento por região)
3. Usuário atribui motorista para cada rota
4. Motorista executa entrega e atualiza status em tempo real
5. Motorista registra prova de entrega ao finalizar
6. Engine retorna confirmação de entrega finalizada
7. Vertical recebe evento e atualiza status do pedido para "entregue"
8. Vertical envia dados de entrega para Stock Intelligence Engine (alimentação)

**Bidirecionalidade**:
- Vertical → Engine: Pedidos prontos, atualizações de status, provas, ocorrências
- Engine → Vertical: Rotas sugeridas, status atualizado, confirmações, custos

**Integração com outros engines**:
- **Stock Intelligence Engine**: Recebe dados de entrega finalizada (pedido entregue = venda concluída)
- **Financial Engine (futuro)**: Pode usar custo de entrega para análise financeira

---

## Limites de Responsabilidade

### Engine É Responsável Por

- ✅ Planejamento de rotas (agrupamento, otimização simples)
- ✅ Controle de status da entrega
- ✅ Registro de ocorrências
- ✅ Coleta de prova de entrega
- ✅ Cálculo de custo operacional da entrega
- ✅ Retorno de dados para análise operacional

### Engine NÃO É Responsável Por

- ❌ Criação de pedidos (vertical cria)
- ❌ Definição de quais pedidos entregar (vertical decide)
- ❌ Definição de prioridade (vertical decide)
- ❌ Definição de preço de frete (vertical decide)
- ❌ Cobrança de cliente (vertical ou Financial Engine)
- ❌ Emissão de nota fiscal (vertical ou sistema externo)
- ❌ Gestão de motoristas (vertical gerencia)

### Vertical É Responsável Por

- ✅ Criar pedidos que serão entregues
- ✅ Definir quais pedidos entregar
- ✅ Definir prioridade de entrega
- ✅ Fornecer endereços e produtos
- ✅ Fornecer motoristas disponíveis
- ✅ Decidir quando usar engine ou fazer manualmente
- ✅ Apresentar rotas e status para usuário
- ✅ Usar prova de entrega para resolver conflitos

---

## Exemplos de Uso

### Exemplo 1: Vertical de Materiais de Construção

**Contexto**: Loja tem 5 pedidos prontos para entrega em obras diferentes.

**Consumo do Engine**:
- Vertical envia 5 pedidos com endereços das obras
- Vertical solicita planejamento de rotas

**Output do Engine**:
- Rota 1: 3 pedidos agrupados (região centro) - ordem de entrega sugerida
- Rota 2: 2 pedidos agrupados (região sul) - ordem de entrega sugerida
- Distância total estimada (futuro)

**Ação do Vertical**:
- Usuário vê rotas sugeridas no contexto de materiais de construção
- Usuário atribui motorista para cada rota
- Motorista executa entrega e registra status no app
- Engine registra prova de entrega (foto, assinatura)

---

### Exemplo 2: Futuro Vertical de Alimentação

**Contexto**: Loja tem 10 pedidos prontos para entrega em endereços residenciais.

**Consumo do Engine**:
- Vertical envia 10 pedidos com endereços residenciais
- Vertical solicita planejamento de rotas

**Output do Engine**:
- Rota 1: 4 pedidos agrupados (bairro A) - ordem de entrega sugerida
- Rota 2: 3 pedidos agrupados (bairro B) - ordem de entrega sugerida
- Rota 3: 3 pedidos agrupados (bairro C) - ordem de entrega sugerida

**Ação do Vertical**:
- Usuário vê rotas sugeridas no contexto de alimentação
- Usuário atribui motorista para cada rota
- Motorista executa entrega e registra status no app
- Engine registra prova de entrega (foto, assinatura)

**Observação**: Mesmo engine, contexto diferente (obras vs residências), outputs ajustados.

---

## Observações Importantes

### 1. Engine É Horizontal, Não Vertical

Engine não sabe que "obra" é diferente de "residência". Ele apenas analisa:
- Identificador de pedido (genérico)
- Endereço (coordenadas ou endereço completo)
- Produtos (lista genérica)
- Status (pendente, entregue, etc.)

### 2. Vertical Interpreta Outputs

Vertical decide como apresentar rotas e status para usuário:
- Materiais de construção: "Rota para obras: Obra A, Obra B, Obra C"
- Alimentação: "Rota residencial: Bairro A (4 pedidos), Bairro B (3 pedidos)"

### 3. Prova de Entrega É Crítica

Prova de entrega (foto, assinatura) é essencial para resolver conflitos. Engine coleta e armazena, vertical usa para resolver reclamações.

### 4. Não Há Decisão Automática

Engine não decide automaticamente quais pedidos entregar ou qual motorista usar. Apenas sugere rotas. Vertical decide.

---

**Última atualização**: Janeiro 2026
**Versão**: 2.0 (MVP 2 - Documentação)

