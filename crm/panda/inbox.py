"""Caixa de entrada unificada (Panda Project, fase 7).

Modelo A: o Frappe baixa os e-mails (Email Account) e guarda como Communication; aqui so listamos,
lemos, respondemos escolhendo a conta, e ligamos a contato / projeto / tarefa.
Nenhum lead e criado sozinho (ver setup._desligar_lead_automatico).
"""
import re

import frappe
from frappe import _
from frappe.utils import cint, strip_html

COMM = "Communication"


def _admin() -> bool:
	return frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()


def _contas():
	"""Contas visiveis: administradores veem todas; os demais, as ligadas ao proprio usuario."""
	filtros = {"enable_incoming": 1}
	contas = frappe.get_all("Email Account", filtros, ["name", "email_id", "email_account_name", "service"])
	if _admin():
		return contas
	minhas = set(frappe.get_all("User Email", {"parent": frappe.session.user}, pluck="email_account"))
	return [c for c in contas if c.name in minhas]


def _nomes(contas):
	return [c.name for c in contas] or [""]


@frappe.whitelist()
def get_accounts():
	contas = _contas()
	for c in contas:
		c["unread"] = frappe.db.count(
			COMM,
			{"email_account": c.name, "sent_or_received": "Received", "seen": 0, "communication_medium": "Email"},
		)
	return {
		"accounts": contas,
		"total_unread": sum(c["unread"] for c in contas),
		"can_send": [
			c for c in frappe.get_all("Email Account", {"enable_outgoing": 1}, ["name", "email_id", "email_account_name"])
			if _admin() or c.name in {x.name for x in contas}
		],
	}


def _previa(html: str) -> str:
	return re.sub(r"\s+", " ", strip_html(html or "")).strip()[:140]


@frappe.whitelist()
def get_messages(account: str | None = None, folder: str = "Received", search: str | None = None, start: int = 0):
	contas = _contas()
	nomes = _nomes(contas)
	if account:
		if account not in nomes:
			frappe.throw(_("Sem permissão nesta conta"), frappe.PermissionError)
		nomes = [account]
	filtros = {
		"communication_medium": "Email",
		"email_account": ["in", nomes],
		"sent_or_received": "Sent" if folder == "Sent" else "Received",
	}
	or_filtros = None
	if search:
		like = f"%{search.strip()}%"
		or_filtros = [["subject", "like", like], ["sender", "like", like], ["recipients", "like", like]]
	rows = frappe.get_all(
		COMM,
		filtros,
		["name", "subject", "content", "sender", "sender_full_name", "recipients", "communication_date", "seen", "email_account", "reference_doctype", "reference_name"],
		or_filters=or_filtros,
		order_by="communication_date desc",
		start=cint(start),
		page_length=50,
	)
	anexos = set(
		frappe.get_all(
			"File", {"attached_to_doctype": COMM, "attached_to_name": ["in", [r.name for r in rows] or [""]]}, pluck="attached_to_name"
		)
	)
	contas_nome = {c.name: c.email_account_name or c.email_id for c in contas}
	out = []
	for r in rows:
		out.append(
			{
				"name": r.name,
				"subject": r.subject or _("(sem assunto)"),
				"preview": _previa(r.content),
				"from": r.sender_full_name or r.sender,
				"sender": r.sender,
				"to": r.recipients,
				"date": str(r.communication_date),
				"seen": bool(r.seen) or folder == "Sent",
				"account": r.email_account,
				"account_name": contas_nome.get(r.email_account, r.email_account),
				"has_attachment": r.name in anexos,
				"deal": r.reference_name if r.reference_doctype == "CRM Deal" else None,
			}
		)
	return out


def _comm(name: str):
	c = frappe.get_doc(COMM, name)
	if c.email_account not in _nomes(_contas()):
		frappe.throw(_("Sem permissão nesta mensagem"), frappe.PermissionError)
	return c


@frappe.whitelist()
def get_message(name: str):
	from frappe.utils.html_utils import clean_email_html

	c = _comm(name)
	if not c.seen and c.sent_or_received == "Received":
		frappe.db.set_value(COMM, name, "seen", 1, update_modified=False)
	anexos = frappe.get_all(
		"File",
		{"attached_to_doctype": COMM, "attached_to_name": name},
		["name", "file_name", "file_url", "is_private"],
	)
	contatos = [l.link_name for l in c.get("timeline_links", []) if l.link_doctype == "Contact"]
	return {
		"name": c.name,
		"subject": c.subject,
		"content": clean_email_html(c.content or ""),
		"from": c.sender_full_name or c.sender,
		"sender": c.sender,
		"to": c.recipients,
		"cc": c.cc,
		"date": str(c.communication_date),
		"account": c.email_account,
		"sent_or_received": c.sent_or_received,
		"attachments": anexos,
		"deal": c.reference_name if c.reference_doctype == "CRM Deal" else None,
		"deal_name": frappe.db.get_value("CRM Deal", c.reference_name, "project_name")
		if c.reference_doctype == "CRM Deal"
		else None,
		"contacts": contatos,
	}


@frappe.whitelist(methods=["POST"])
def mark_unread(name: str):
	_comm(name)
	frappe.db.set_value(COMM, name, "seen", 0, update_modified=False)
	return True


@frappe.whitelist(methods=["POST"])
def send(from_account: str, to: str, subject: str, content: str, cc: str | None = None, reply_to: str | None = None):
	"""Envia pela conta escolhida em 'De:'. O Frappe usa a conta cujo e-mail e o remetente."""
	conta = frappe.get_doc("Email Account", from_account)
	if not conta.enable_outgoing:
		frappe.throw(_("Esta conta não está habilitada para envio"))
	if not _admin() and from_account not in {c.name for c in _contas()}:
		frappe.throw(_("Sem permissão nesta conta"), frappe.PermissionError)
	to = (to or "").strip()
	if not to:
		frappe.throw(_("Informe o destinatário"))
	dados = {
		"doctype": COMM,
		"communication_type": "Communication",
		"communication_medium": "Email",
		"sent_or_received": "Sent",
		"subject": subject or "",
		"content": content or "",
		"sender": conta.email_id,
		"sender_full_name": frappe.db.get_value("User", frappe.session.user, "full_name"),
		"recipients": to,
		"cc": cc or "",
		"email_account": conta.name,
		"communication_date": frappe.utils.now_datetime(),
		"seen": 1,
	}
	if reply_to:
		original = _comm(reply_to)
		dados["in_reply_to"] = original.name
		if original.reference_doctype and original.reference_name:
			dados["reference_doctype"] = original.reference_doctype
			dados["reference_name"] = original.reference_name
	comm = frappe.get_doc(dados).insert(ignore_permissions=True)
	frappe.sendmail(
		recipients=[x.strip() for x in to.replace(";", ",").split(",") if x.strip()],
		cc=[x.strip() for x in (cc or "").replace(";", ",").split(",") if x.strip()],
		sender=conta.email_id,
		subject=subject,
		message=content,
		communication=comm.name,
		reference_doctype=dados.get("reference_doctype"),
		reference_name=dados.get("reference_name"),
	)
	return comm.name


@frappe.whitelist(methods=["POST"])
def link_deal(name: str, deal: str | None = None):
	c = _comm(name)
	if deal and not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Sem permissão neste projeto"), frappe.PermissionError)
	frappe.db.set_value(
		COMM,
		name,
		{"reference_doctype": "CRM Deal" if deal else None, "reference_name": deal or None},
		update_modified=False,
	)
	return True


def _email_do_remetente(c) -> str:
	m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", c.sender or "")
	return m.group(0).lower() if m else ""


@frappe.whitelist(methods=["POST"])
def create_contact(name: str):
	"""Botao manual 'Criar contato' (no lugar da criacao automatica de lead)."""
	c = _comm(name)
	email = _email_do_remetente(c) if c.sent_or_received == "Received" else (c.recipients or "").split(",")[0].strip().lower()
	if not email:
		frappe.throw(_("Sem e-mail para criar o contato"))
	existente = frappe.db.get_value("Contact Email", {"email_id": email, "parenttype": "Contact"}, "parent")
	if existente:
		contato = existente
	else:
		doc = frappe.new_doc("Contact")
		doc.first_name = (c.sender_full_name or email.split("@")[0])[:140]
		doc.panda_origem = "E-mail"
		doc.append("email_ids", {"email_id": email, "is_primary": 1})
		doc.insert(ignore_permissions=True)
		contato = doc.name
	c.reload()
	if not any(l.link_doctype == "Contact" and l.link_name == contato for l in c.get("timeline_links", [])):
		c.append("timeline_links", {"link_doctype": "Contact", "link_name": contato})
		c.save(ignore_permissions=True)
	return contato


@frappe.whitelist(methods=["POST"])
def create_task(name: str, deal: str | None = None, due_date: str | None = None):
	c = _comm(name)
	t = frappe.get_doc(
		{
			"doctype": "CRM Task",
			"title": (c.subject or _("E-mail"))[:140],
			"description": f"<p>{frappe.utils.escape_html(_('E-mail de'))} {frappe.utils.escape_html(c.sender or '')}</p>",
			"status": "Todo",
			"priority": "Medium",
			"due_date": due_date or None,
			"reference_doctype": "CRM Deal" if deal else None,
			"reference_docname": deal or None,
		}
	)
	t.insert()
	return t.name


@frappe.whitelist(methods=["POST"])
def sync(account: str | None = None):
	"""Busca e-mails novos agora (sem esperar o agendador do Frappe, que roda de tempos em tempos)."""
	contas = _contas()
	if account:
		contas = [c for c in contas if c.name == account]
	erros = []
	for c in contas:
		try:
			frappe.get_doc("Email Account", c.name).receive()
		except Exception as e:
			erros.append(f"{c.email_id}: {str(e)[:160]}")
			frappe.log_error(title="Panda: falha ao buscar e-mails")
	frappe.db.commit()
	return {"errors": erros, "accounts": len(contas)}
