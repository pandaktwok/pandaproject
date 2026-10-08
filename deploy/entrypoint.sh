#!/bin/bash
set -e
cd /home/frappe/frappe-bench
SITE="${SITE_NAME:?defina SITE_NAME no .env}"
echo "Aguardando MariaDB..."; until (echo > /dev/tcp/${DB_HOST:-mariadb}/3306) 2>/dev/null; do sleep 2; done; sleep 3

bench set-mariadb-host "${DB_HOST:-mariadb}"
bench set-redis-cache-host "redis://${REDIS_HOST:-redis}:6379"
bench set-redis-queue-host "redis://${REDIS_HOST:-redis}:6379"
bench set-redis-socketio-host "redis://${REDIS_HOST:-redis}:6379"
printf '[client]\nskip-ssl\n' > ~/.my.cnf

# pastas de volume podem chegar vazias/sem dono
mkdir -p sites/assets && cp -a /home/frappe/assets-build/. sites/assets/
echo "$SITE" > sites/currentsite.txt

if [ ! -d "sites/$SITE" ]; then
  echo "Criando o site $SITE (primeira execucao)..."
  bench new-site "$SITE" --force \
    --mariadb-root-password "${DB_ROOT_PASSWORD:?defina DB_ROOT_PASSWORD}" \
    --admin-password "${ADMIN_PASSWORD:?defina ADMIN_PASSWORD}" \
    --no-mariadb-socket
  bench --site "$SITE" install-app crm
fi

bench --site "$SITE" migrate
bench --site "$SITE" set-config host_name "https://${SITE}"
# sem isso o Frappe gruda ":8000" nos links (OAuth do Google, webhooks)
bench set-config -g restart_supervisor_on_update 1
bench --site "$SITE" set-config server_script_enabled 0
bench use "$SITE"
exec bench start
