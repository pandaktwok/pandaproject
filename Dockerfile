# PandaProject v1.1 — imagem de producao (Frappe v15 + app crm customizado)
FROM frappe/bench:latest

USER frappe
WORKDIR /home/frappe

RUN bench init --skip-redis-config-generation --skip-assets --version version-15 --frappe-branch version-15 frappe-bench

WORKDIR /home/frappe/frappe-bench
COPY --chown=frappe:frappe . /home/frappe/crm
RUN cd /home/frappe/crm && git init -q && git add -A && git -c user.email=build@local -c user.name=build commit -qm build \
 && cd /home/frappe/frappe-bench && bench get-app /home/frappe/crm --skip-assets \
 && bench build && cp -a sites/assets /home/frappe/assets-build \
 && printf '[client]\nskip-ssl\n' > /home/frappe/.my.cnf \
 && sed -i '/redis/d;/watch/d' Procfile

COPY --chown=frappe:frappe deploy/entrypoint.sh /home/frappe/entrypoint.sh
EXPOSE 8000 9000
ENTRYPOINT ["bash", "/home/frappe/entrypoint.sh"]
