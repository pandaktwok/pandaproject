# PandaProject v1.1 — Deploy na VPS

1. Aponte o DNS do seu dominio (registro A) para o IP da VPS. Portas 80 e 443 abertas.
2. Instale Docker + Docker Compose na VPS.
3. `git clone <este-repositorio> && cd <pasta>`
4. `cp .env.example .env` e edite: `SITE_NAME` (dominio), senhas.
5. `docker compose up -d --build` (o 1o build demora varios minutos).
6. Acesse `https://SEU-DOMINIO/crm` — usuario `Administrator`, senha = `ADMIN_PASSWORD`.
7. Em Configuracoes > Conexoes, preencha a Evolution API e o "Endereco publico" = `https://SEU-DOMINIO` (o webhook do WhatsApp passa a funcionar).

Atualizar: `git pull && docker compose up -d --build`.
Backup: `docker compose exec app bench --site SEU-DOMINIO backup --with-files`.
A pasta `dev/` e o ambiente local de desenvolvimento (Windows).
