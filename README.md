# PandaProject

**Gestão de projetos com cronograma de pagamentos**, feita em português (pt-BR) para organizações e equipes que precisam acompanhar, em um só lugar, o andamento dos projetos, o dinheiro que entra e sai e a conversa com fornecedores e clientes.

> **Versão 1.1** · fork de código aberto do [Frappe CRM](https://github.com/frappe/crm) · licença AGPL-3.0

## Sobre este projeto

O PandaProject é um **fork do [Frappe CRM](https://github.com/frappe/crm)** (v1.86), da Frappe Technologies. Aproveitamos a base sólida dele (framework Frappe, Vue 3, permissões, kanban, listas, e-mail, tarefas) e adaptamos o produto: onde o CRM trata *negócios* (deals), o PandaProject trata **projetos**, cada um com seu cronograma financeiro.

O primeiro cliente é a Sociedade Cultural Cruzeiro do Sul (SCCS), de Criciúma/SC. A meta é oferecê-lo como SaaS pago para outras organizações.

## O que o PandaProject acrescenta ao Frappe CRM

- **Projetos com cronograma de pagamentos:** linhas por fornecedor, parcelas com vencimento e valor previsto/pago, modos de cálculo (total da linha, por parcela, variável), descrição e telefone do fornecedor.
- **Painel financeiro do projeto:** próximo pagamento, copiar o pedido de nota, **enviar pedido de nota por WhatsApp** direto do programa, e-mail de recebimento da nota por projeto.
- **Dashboard de gestão:** totais de projetos (andamento/encerrados), valor total e médio, fornecedores, gráfico de projetos por tipo/mês, previsto × pago, feed de atividades e relatório para imprimir.
- **Chat (WhatsApp e Instagram):** WhatsApp via [Evolution API](https://github.com/EvolutionAPI/evolution-api) (conexão por QR ou código de pareamento) e Instagram via Meta; histórico vinculado a contatos e projetos.
- **Caixa de entrada de e-mail** integrada (Gmail, Outlook, Hostinger e outros).
- **Google Drive:** arquivos e notas dos pagamentos organizados automaticamente.
- **Calendário e tarefas** ligados aos projetos, com avisos de pagamentos pendentes.
- **Agente de ajuda com IA** (OpenAI-compatível, Claude ou Gemini) que só responde dúvidas de uso do programa, além de um endpoint MCP.
- **LGPD:** origem do contato, base legal, data de consentimento e política de privacidade configurável.
- **Interface 100% em português do Brasil** e moeda real (BRL) por padrão.

Os documentos de ajuda ficam em `crm/panda/ajuda/`; o código específico do PandaProject fica em `crm/panda/` e no frontend em `frontend/src`.

## Como rodar

**Produção (VPS com Docker):** veja [DEPLOY.md](DEPLOY.md). Resumo:

```bash
cp .env.example .env     # edite domínio e senhas
docker compose up -d --build
```

**Desenvolvimento local (Windows/Linux):** a pasta [`dev/`](dev) tem o ambiente Docker usado no desenvolvimento (`docker compose up`, depois `rebuild.sh` a cada alteração).

## Estado do projeto

As funcionalidades acima estão implementadas, mas as integrações que dependem de chaves externas (Google, Meta/Instagram, e-mail, WhatsApp/Evolution, IA) ainda estão em fase de testes. Use com cuidado em produção e faça backup (`bench backup`).

## Créditos e licença

- Base: [Frappe CRM](https://github.com/frappe/crm) © Frappe Technologies Pvt. Ltd., sob [GNU AGPL-3.0](LICENSE). Todo o crédito do núcleo vai para a equipe e a comunidade do Frappe.
- Como este é um derivado, o PandaProject também é distribuído sob **AGPL-3.0**: quem oferecer o programa pela rede deve disponibilizar o código-fonte, incluindo as modificações.
- Mantido por [@pandaktwok](https://github.com/pandaktwok).
