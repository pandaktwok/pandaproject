"""Painel (dashboard) do Panda Project: numeros, graficos e feed de atividades dos projetos.

Cada funcao get_<nome> e chamada por crm.api.dashboard (mesmo contrato dos graficos originais).
Os numeros sao a "foto" atual (nao dependem do periodo); respeitam o filtro de projeto e as
permissoes do usuario (so projetos que ele pode ver).
"""
import frappe
from frappe import _
from frappe.utils import getdate, nowdate

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
SIMBOLO = "R$"


def _brl(v) -> str:
	s = f"{float(v or 0):,.2f}"
	return SIMBOLO + " " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _dia(d) -> str:
	return getdate(d).strftime("%d/%m/%Y")


def _projetos() -> list[str]:
	"""Projetos que o usuario pode ver (aplica as regras de acesso) e o filtro do painel."""
	nomes = frappe.get_list("CRM Deal", pluck="name", limit_page_length=0)
	alvo = frappe.flags.get("panda_deal")
	if alvo:
		nomes = [n for n in nomes if n == alvo]
	return nomes or [""]


def _tipos(nomes):
	rows = frappe.db.sql(
		"""select d.name, d.deal_value, s.type from `tabCRM Deal` d
		left join `tabCRM Deal Status` s on s.name = d.status where d.name in %(n)s""",
		{"n": tuple(nomes)},
		as_dict=True,
	)
	return rows


def _numero(titulo, tooltip, valor, dinheiro=False):
	out = {"title": titulo, "tooltip": tooltip, "value": valor or 0}
	if dinheiro:
		out["prefix"] = SIMBOLO
	return out


# ------------------------------------------------------------------ numeros
def get_projetos_total(from_date=None, to_date=None, user=None):
	return _numero(_("Total de projetos"), _("Todos os projetos"), len(_tipos(_projetos())) if _projetos() != [""] else 0)


def get_projetos_andamento(from_date=None, to_date=None, user=None):
	rows = _tipos(_projetos())
	return _numero(
		_("Projetos em andamento"), _("Projetos que ainda não foram encerrados"), sum(1 for r in rows if r.type not in ("Won", "Lost"))
	)


def get_projetos_encerrados(from_date=None, to_date=None, user=None):
	rows = _tipos(_projetos())
	return _numero(_("Projetos encerrados"), _("Projetos concluídos ou perdidos"), sum(1 for r in rows if r.type in ("Won", "Lost")))


def get_valor_total_projetos(from_date=None, to_date=None, user=None):
	rows = _tipos(_projetos())
	return _numero(_("Valor total dos projetos"), _("Soma do valor de todos os projetos"), sum(float(r.deal_value or 0) for r in rows), True)


def get_valor_medio_projeto(from_date=None, to_date=None, user=None):
	rows = _tipos(_projetos())
	total = sum(float(r.deal_value or 0) for r in rows)
	return _numero(_("Valor médio por projeto"), _("Valor total dividido pelo número de projetos"), round(total / len(rows), 2) if rows else 0, True)


def _fornecedores(nomes):
	"""Fornecedores distintos (ignora maiusculas e espacos) das linhas e dos pagamentos variaveis."""
	rows = frappe.db.sql(
		"""select lower(trim(l.supplier)) s from `tabCRM Payment Line` l where l.deal in %(n)s
		union select lower(trim(e.supplier)) from `tabCRM Payment Entry` e
		join `tabCRM Payment Line` l on l.name = e.parent where l.deal in %(n)s and e.supplier is not null and e.supplier != ''""",
		{"n": tuple(nomes)},
	)
	return {r[0] for r in rows if r[0]}


def get_qtd_fornecedores(from_date=None, to_date=None, user=None):
	return _numero(_("Fornecedores"), _("Quantidade de fornecedores diferentes nos pagamentos"), len(_fornecedores(_projetos())))


def get_media_por_fornecedor(from_date=None, to_date=None, user=None):
	nomes = _projetos()
	forn = len(_fornecedores(nomes))
	pago = frappe.db.sql("select coalesce(sum(paid_total),0) from `tabCRM Payment Line` where deal in %(n)s", {"n": tuple(nomes)})[0][0]
	return _numero(
		_("Gasto médio por fornecedor"), _("Total pago dividido pelo número de fornecedores"), round(float(pago) / forn, 2) if forn else 0, True
	)


# ------------------------------------------------------------------ graficos
def _ano(to_date) -> int:
	return getdate(to_date or nowdate()).year


def get_projetos_por_tipo_mes(from_date=None, to_date=None, user=None):
	"""Projetos criados em cada mes do ano, uma linha por tipo (etiqueta) de projeto."""
	ano = _ano(to_date)
	nomes = _projetos()
	tipos = frappe.get_all("CRM Project Type", pluck="name", order_by="creation asc")
	rows = frappe.db.sql(
		"""select month(creation) m, coalesce(nullif(project_type,''),'__sem') t, count(*) c from `tabCRM Deal`
		where name in %(n)s and year(creation) = %(a)s group by m, t""",
		{"n": tuple(nomes), "a": ano},
		as_dict=True,
	)
	if any(r.t == "__sem" for r in rows):
		tipos = [*tipos, "__sem"]
	rotulo = lambda t: _("Sem tipo") if t == "__sem" else t  # noqa: E731
	data = []
	for i, mes in enumerate(MESES, start=1):
		linha = {"mes": mes}
		for t in tipos:
			linha[rotulo(t)] = sum(r.c for r in rows if r.m == i and r.t == t)
		data.append(linha)
	return {
		"data": data,
		"title": _("Projetos por tipo"),
		"subtitle": _("Projetos criados em cada mês de {0}, por tipo").format(ano),
		"xAxis": {"title": _("Mês"), "key": "mes", "type": "category"},
		"yAxis": {"title": _("Projetos")},
		"series": [{"name": rotulo(t), "type": "line", "showDataPoints": True} for t in tipos],
	}


def get_pagamentos_por_mes(from_date=None, to_date=None, user=None):
	"""Pagamentos previstos (parcelas por vencimento) e pagos (por data de pagamento) em cada mes."""
	ano = _ano(to_date)
	nomes = tuple(_projetos())
	prev = frappe.db.sql(
		"""select month(i.due_date) m, sum(i.expected_value) v from `tabCRM Payment Installment` i
		join `tabCRM Payment Line` l on l.name = i.parent where l.deal in %(n)s and year(i.due_date) = %(a)s group by m""",
		{"n": nomes, "a": ano},
		as_dict=True,
	)
	pago = frappe.db.sql(
		"""select m, sum(v) v from (
			select month(i.paid_on) m, i.paid_value v from `tabCRM Payment Installment` i
			join `tabCRM Payment Line` l on l.name = i.parent
			where l.deal in %(n)s and i.paid = 1 and l.mode != 'Variable' and year(i.paid_on) = %(a)s
			union all
			select month(e.paid_on), e.value from `tabCRM Payment Entry` e
			join `tabCRM Payment Line` l on l.name = e.parent where l.deal in %(n)s and year(e.paid_on) = %(a)s
		) t group by m""",
		{"n": nomes, "a": ano},
		as_dict=True,
	)
	pv = {r.m: float(r.v or 0) for r in prev}
	pg = {r.m: float(r.v or 0) for r in pago}
	data = [{"mes": mes, "Previsto": pv.get(i, 0), "Pago": pg.get(i, 0)} for i, mes in enumerate(MESES, start=1)]
	return {
		"data": data,
		"title": _("Pagamentos"),
		"subtitle": _("Previsto (vencimento das parcelas) e pago em cada mês de {0}").format(ano),
		"xAxis": {"title": _("Mês"), "key": "mes", "type": "category"},
		"yAxis": {"title": _("Valor") + f" ({SIMBOLO})"},
		"series": [
			{"name": "Previsto", "type": "line", "showDataPoints": True},
			{"name": "Pago", "type": "line", "showDataPoints": True},
		],
	}


# ------------------------------------------------------------------ feed
def get_atividades(from_date=None, to_date=None, user=None):
	"""Feed de tudo que aconteceu nos projetos: pagamentos, tarefas concluidas, avisos e projetos criados."""
	nomes = tuple(_projetos())
	if nomes == ("",):
		return {"items": []}
	nome_projeto = dict(
		frappe.db.sql("select name, coalesce(nullif(project_name,''), name) from `tabCRM Deal` where name in %(n)s", {"n": nomes})
	)
	itens = []

	def add(kind, quando, texto, deal):
		itens.append(
			{"kind": kind, "when": str(quando), "text": texto, "deal": deal, "deal_name": nome_projeto.get(deal, deal)}
		)

	for r in frappe.db.sql(
		"""select i.paid_on, i.paid_value, i.number, l.supplier, l.deal from `tabCRM Payment Installment` i
		join `tabCRM Payment Line` l on l.name = i.parent
		where l.deal in %(n)s and i.paid = 1 and i.paid_on is not null and l.mode != 'Variable'
		order by i.paid_on desc limit 80""",
		{"n": nomes},
		as_dict=True,
	):
		add("payment", r.paid_on, _("{0} — pago em {1} ({2}, parcela {3})").format(r.supplier, _dia(r.paid_on), _brl(r.paid_value), r.number), r.deal)
	for r in frappe.db.sql(
		"""select e.paid_on, e.value, e.installment_number n, coalesce(nullif(e.supplier,''), l.supplier) supplier, l.deal
		from `tabCRM Payment Entry` e join `tabCRM Payment Line` l on l.name = e.parent
		where l.deal in %(n)s and e.paid_on is not null order by e.paid_on desc limit 80""",
		{"n": nomes},
		as_dict=True,
	):
		add("payment", r.paid_on, _("{0} — pago em {1} ({2}, mês {3})").format(r.supplier, _dia(r.paid_on), _brl(r.value), r.n), r.deal)
	for r in frappe.db.sql(
		"""select title, modified, reference_docname deal from `tabCRM Task`
		where status = 'Done' and reference_doctype = 'CRM Deal' and reference_docname in %(n)s
		order by modified desc limit 80""",
		{"n": nomes},
		as_dict=True,
	):
		add("task", r.modified, _("Tarefa “{0}” concluída em {1}").format(r.title or "", _dia(r.modified)), r.deal)
	for r in frappe.db.sql(
		"select deal, sent_on, message from `tabCRM Project Notice` where deal in %(n)s order by sent_on desc limit 40",
		{"n": nomes},
		as_dict=True,
	):
		add("notice", r.sent_on, r.message or _("Aviso do projeto"), r.deal)
	for r in frappe.db.sql(
		"select name deal, creation from `tabCRM Deal` where name in %(n)s order by creation desc limit 40", {"n": nomes}, as_dict=True
	):
		add("project", r.creation, _("Projeto criado em {0}").format(_dia(r.creation)), r.deal)

	itens.sort(key=lambda x: x["when"], reverse=True)
	return {"items": itens[:100]}
