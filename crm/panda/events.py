"""Notificacoes do Panda Project: todos os eventos de todos os projetos.

Cada evento vira uma CRM Notification para todos os usuarios internos
(menos para quem fez a acao). Aparece no menu Notificacoes.
"""
import frappe
from frappe import _
from frappe.utils import add_days, date_diff, escape_html, getdate, nowdate

DIAS_AVISO = 10
PAPEIS = ("System Manager", "Sales Manager", "Sales User")


def _destinatarios(excluir: str | None = None) -> list[str]:
	usuarios = set(
		frappe.get_all("Has Role", {"role": ["in", PAPEIS], "parenttype": "User"}, pluck="parent")
	)
	ativos = set(frappe.get_all("User", {"enabled": 1, "user_type": "System User"}, pluck="name"))
	return [u for u in usuarios & ativos if u not in ("Guest", excluir)]


def _nome(deal: str) -> str:
	nome, org = frappe.db.get_value("CRM Deal", deal, ["project_name", "organization"]) or (None, None)
	return nome or org or deal


def notificar(deal: str, texto: str, autor: str | None = None, dedupe: bool = False):
	"""Cria a notificacao para todos. texto ja deve estar escapado/limpo."""
	autor = autor or frappe.session.user
	html = f'<div class="mb-2 leading-5 text-ink-gray-5">{texto}</div>'
	for u in _destinatarios(excluir=autor if autor != "Administrator" else None):
		if dedupe and frappe.db.exists(
			"CRM Notification", {"to_user": u, "notification_type_doc": deal, "notification_text": html}
		):
			continue
		frappe.get_doc(
			{
				"doctype": "CRM Notification",
				"from_user": autor,
				"to_user": u,
				"type": "Project",
				"message": frappe.utils.strip_html(texto),
				"notification_text": html,
				"notification_type_doctype": "CRM Deal",
				"notification_type_doc": deal,
				"reference_doctype": "CRM Deal",
				"reference_name": deal,
			}
		).insert(ignore_permissions=True)


def _b(s) -> str:
	return f'<span class="font-medium text-ink-gray-9">{escape_html(str(s))}</span>'


# ---- ganchos de documentos ------------------------------------------------
def deal_criado(doc, method=None):
	notificar(doc.name, _("Novo projeto: {0}").format(_b(_nome(doc.name))))


def deal_atualizado(doc, method=None):
	if doc.flags.in_insert or not doc.has_value_changed("status"):
		return
	notificar(doc.name, _("{0} mudou para {1}").format(_b(_nome(doc.name)), _b(doc.status)))


def tarefa_criada(doc, method=None):
	if doc.reference_doctype == "CRM Deal" and doc.reference_docname:
		notificar(
			doc.reference_docname,
			_("Nova tarefa em {0}: {1}").format(_b(_nome(doc.reference_docname)), _b(doc.title)),
		)


def tarefa_atualizada(doc, method=None):
	if doc.reference_doctype != "CRM Deal" or not doc.reference_docname:
		return
	if doc.has_value_changed("status") and doc.status == "Done":
		notificar(
			doc.reference_docname,
			_("Tarefa concluída em {0}: {1}").format(_b(_nome(doc.reference_docname)), _b(doc.title)),
		)


def pagamento_registrado(deal: str, fornecedor: str, numero: int, valor: str):
	notificar(
		deal,
		_("Pagamento realizado em {0}: {1}, parcela {2} ({3})").format(
			_b(_nome(deal)), _b(fornecedor), numero, valor
		),
	)


def pagamento_desfeito(deal: str, fornecedor: str, numero: int):
	notificar(
		deal,
		_("Pagamento desfeito em {0}: {1}, parcela {2}").format(_b(_nome(deal)), _b(fornecedor), numero),
	)


# ---- tarefa agendada (diaria) ---------------------------------------------
def avisar_pagamentos_pendentes():
	"""Parcelas nao pagas que vencem em ate 10 dias (ou ja venceram). Uma vez por parcela e por dia."""
	hoje = getdate(nowdate())
	limite = add_days(hoje, DIAS_AVISO)
	for p in frappe.get_all(
		"CRM Payment Installment",
		{"paid": 0, "due_date": ["<=", limite], "parenttype": "CRM Payment Line"},
		["parent", "number", "due_date", "expected_value"],
	):
		line = frappe.db.get_value("CRM Payment Line", p.parent, ["deal", "supplier"], as_dict=True)
		if not line:
			continue
		dias = date_diff(p.due_date, hoje)
		quando = (
			_("atrasado há {0} dia(s)").format(-dias)
			if dias < 0
			else _("vence hoje")
			if dias == 0
			else _("vence em {0} dia(s)").format(dias)
		)
		notificar(
			line.deal,
			_("Pagamento pendente em {0}: {1}, parcela {2} {3}").format(
				_b(_nome(line.deal)), _b(line.supplier), p.number, quando
			),
			autor="Administrator",
			dedupe=True,
		)


def avisar_reta_final():
	"""Projeto nos ultimos 3 meses (contando o mes atual): aviso interno, 1 por projeto por mes.

	O historico fica em CRM Project Notice (referencia AAAA-MM + ultimo aviso).
	WhatsApp/webhook entram depois da Fase 9 (campo 'channel' ja previsto).
	"""
	from crm.panda import calc

	hoje = getdate(nowdate())
	referencia = hoje.strftime("%Y-%m")
	abertos = frappe.get_all("CRM Deal Status", {"type": ["not in", ["Won", "Lost"]]}, pluck="name")
	for d in frappe.get_all(
		"CRM Deal",
		{"status": ["in", abertos], "expected_closure_date": ["is", "set"]},
		["name", "expected_closure_date"],
	):
		fim = getdate(d.expected_closure_date)
		if fim < hoje or calc.months_between(hoje, fim) > 3:
			continue
		if frappe.db.exists("CRM Project Notice", {"deal": d.name, "reference": referencia}):
			continue
		dias = date_diff(fim, hoje)
		texto = _("Reta final: {0} termina em {1} ({2} dia(s))").format(
			_b(_nome(d.name)), fim.strftime("%d/%m/%Y"), dias
		)
		notificar(d.name, texto, autor="Administrator")
		canal = "Internal"
		try:
			from crm.panda import chat

			if chat.avisar_numeros(frappe.utils.strip_html(texto)):
				canal = "WhatsApp"
		except Exception:
			frappe.log_error(title="Panda: reta final por WhatsApp")
		frappe.get_doc(
			{
				"doctype": "CRM Project Notice",
				"deal": d.name,
				"reference": referencia,
				"channel": canal,
				"sent_on": frappe.utils.now_datetime(),
				"message": frappe.utils.strip_html(texto),
			}
		).insert(ignore_permissions=True)
