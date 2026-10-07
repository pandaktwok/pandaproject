#!/bin/bash
# Copia o codigo da pasta do Windows (/repo) para o bench e reconstroi.
# Uso (de fora do container):  docker compose exec frappe bash /workspace/rebuild.sh
set -e
B=/home/frappe/frappe-bench
T=$B/apps/crm
# tar -m: arquivos ficam com a data de agora (assim o build/traducao enxergam a mudanca)
tar -C /repo \
  --exclude=crm/public/frontend --exclude=crm/www/crm.html --exclude='__pycache__' \
  -cf - crm frontend/src frontend/public \
  | tar -C "$T" -xmf -
for f in /repo/frontend/*.js /repo/frontend/*.json /repo/frontend/*.html /repo/frontend/*.ts; do
  [ -f "$f" ] && cp "$f" "$T/frontend/" || true
done
cd $B
bench --site crm.localhost migrate
bench build --app crm
bench --site crm.localhost clear-cache
echo "REBUILD_OK"
