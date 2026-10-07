"""Log simplificado do projeto (aba Atividades) e resumo (aba Dados)."""
import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, nowdate

from crm.panda import calc

DIAS_AVISO = 10


def _brl(v) -> str:
	return "R$ " + f"{float(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _check(deal):
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Sem permissão neste projeto"), frappe.PermissionError)


@frappe.whitelist()
def get_project_log(deal: str):
	_check(deal)
	doc = frappe.get_doc("CRM Deal", deal)
	hoje = getdate(nowdate())
	itens = []

	itens.append({"date": str(doc.creation), "kind": "project", "severity": "info", "text": _("Projeto criado")})

	for row in doc.status_change_log or []:
		if row.to:
			itens.append(
				{
					"date": str(row.to_date or row.creation),
					"kind": "stage",
					"severity": "info",
					"text": _("Etapa alterada para {0}").format(row.to),
				}
			)

	for t in frappe.get_all(
		"CRM Task",
		{"reference_doctype": "CRM Deal", "reference_docname": deal},
		["name", "title", "status", "due_date", "creation", "modified"],
	):
		itens.append(
			{"date": str(t.creation), "kind": "task", "severity": "info", "text": _("Nova tarefa: {0}").format(t.title)}
		)
		if t.status == "Done":
			itens.append(
				{
					"date": str(t.modified),
					"kind": "task",
					"severity": "success",
					"text": _("Tarefa concluída: {0}").format(t.title),
				}
			)
		elif t.status not in ("Canceled",) and t.due_date and getdate(t.due_date) < hoje:
			itens.append(
				{
					"date": str(t.due_date),
					"kind": "task",
					"severity": "danger",
					"text": _("Tarefa pendente (atrasada): {0}").format(t.title),
				}
			)

	limite = add_days(hoje, DIAS_AVISO)
	for ln in frappe.get_all("CRM Payment Line", {"deal": deal}, pluck="name"):
		line = frappe.get_doc("CRM Payment Line", ln)
		for p in line.installments:
			if p.paid:
				itens.append(
					{
						"date": str(p.paid_on or line.modified),
						"kind": "payment",
						"severity": "success",
						"text": _("Pagamento realizado: {0}, parcela {1} ({2})").format(
							line.supplier, p.number, _brl(p.paid_value)
						),
					}
				)
			elif p.due_date and getdate(p.due_date) <= limite:
				dias = date_diff(p.due_date, hoje)
				quando = (
					_("atrasado há {0} dia(s)").format(-dias)
					if dias < 0
					else _("vence hoje")
					if dias == 0
					else _("vence em {0} dia(s)").format(dias)
				)
				itens.append(
					{
						"date": str(p.due_date),
						"kind": "payment",
						"severity": "danger" if dias < 0 else "warning",
						"text": _("Pagamento pendente: {0}, parcela {1} ({2}) {3}").format(
							line.supplier, p.number, _brl(p.expected_value), quando
						),
					}
				)

	itens.sort(key=lambda i: i["date"], reverse=True)
	return itens[:200]


@frappe.whitelist()
def get_project_summary(deal: str):
	"""Mini dashboard do projeto."""
	_check(deal)
	doc = frappe.get_doc("CRM Deal", deal)
	hoje = getdate(nowdate())

	linhas = frappe.get_all("CRM Payment Line", {"deal": deal}, ["total", "paid_total", "remaining"])
	total = sum(calc.to_cents(l.total) for l in linhas)
	pago = sum(calc.to_cents(l.paid_total) for l in linhas)
	restante = sum(calc.to_cents(l.remaining) for l in linhas)
	if not linhas:
		total = restante = calc.to_cents(doc.deal_value)

	tarefas = {}
	for t in frappe.get_all("CRM Task", {"reference_doctype": "CRM Deal", "reference_docname": deal}, ["status"]):
		tarefas[t.status] = tarefas.get(t.status, 0) + 1

	proximas = []
	for ln in frappe.get_all("CRM Payment Line", {"deal": deal}, pluck="name"):
		line = frappe.get_doc("CRM Payment Line", ln)
		for p in line.installments:
			if not p.paid and p.due_date:
				proximas.append(
					{
						"supplier": line.supplier,
						"number": p.number,
						"due_date": str(p.due_date),
						"value": p.expected_value,
						"late": getdate(p.due_date) < hoje,
					}
				)
	proximas.sort(key=lambda x: x["due_date"])

	por_tag = []
	for t in frappe.get_all("CRM Finance Tag", {"deal": deal}, ["name", "tag_name", "value", "color"]):
		usado = sum(
			calc.to_cents(l.total)
			for l in frappe.get_all("CRM Payment Line", {"deal": deal, "finance_tag": t.name}, ["total"])
		)
		por_tag.append({**t, "used": calc.from_cents(usado)})

	fim = doc.expected_closure_date
	return {
		"status": doc.status,
		"project_type": doc.project_type,
		"organization": doc.organization,
		"days_to_end": date_diff(fim, hoje) if fim else None,
		"last_notice": frappe.db.get_value(
			"CRM Project Notice",
			{"deal": deal},
			["reference", "sent_on", "message"],
			order_by="sent_on desc",
			as_dict=True,
		),
		"expected_closure_date": str(fim) if fim else None,
		"total": calc.from_cents(total),
		"paid": calc.from_cents(pago),
		"remaining": calc.from_cents(restante),
		"percent_paid": round(pago * 100 / total, 1) if total else 0,
		"tasks": tarefas,
		"next_payments": proximas[:5],
		"tags": por_tag,
	}
