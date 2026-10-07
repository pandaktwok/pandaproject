# PandaProject v1.1 — imagem de producao (Frappe v15 + app crm customizado)
FROM frappe/bench:latest

USER frappe
WORKDIR /home/frappe

RUN bench init --skip-redis-config-generation --skip-assets --version version-15 --frappe-branch version-15 frappe-bench

WORKDIR /home/frappe/frappe-bench
COPY --chown=frappe:frappe . /home/frappe/crm-src
RUN bench get-app crm /home/frappe/crm-src --skip-assets \
 && bench build --app crm \
 && printf '[client]\nskip-ssl\n' > /home/frappe/.my.cnf \
 && sed -i '/redis/d;/watch/d' Procfile

COPY --chown=frappe:frappe deploy/entrypoint.sh /home/frappe/entrypoint.sh
EXPOSE 8000 9000
ENTRYPOINT ["bash", "/home/frappe/entrypoint.sh"]
