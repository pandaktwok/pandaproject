"""LGPD basica: politica de privacidade, exportar e apagar dados de um contato.

O registro em CRM Privacy Request guarda so o tipo, a referencia (id) e quem fez - nunca dados pessoais.
"""
import frappe
from frappe import _

DOC = "Panda Integrations"
CONV = "CRM Chat Conversation"
MSG = "CRM Chat Message"


def _admin():
	if not (frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()):
		frappe.throw(_("Somente administradores"), frappe.PermissionError)


@frappe.whitelist()
def get_policy():
	_admin()
	return frappe.db.get_single_value(DOC, "privacy_policy") or ""


@frappe.whitelist(methods=["POST"])
def save_policy(text: str = ""):
	_admin()
	frappe.db.set_single_value(DOC, "privacy_policy", text)
	return True


@frappe.whitelist(allow_guest=True)
def public_policy():
	"""Texto da politica de privacidade para o site publicar (so leitura)."""
	return frappe.db.get_single_value(DOC, "privacy_policy") or ""


@frappe.whitelist()
def export_contact(contact: str):
	_admin()
	doc = frappe.get_doc("Contact", contact)
	dados = {
		"contato": doc.as_dict(convert_dates_to_str=True),
		"conversas": [],
		"projetos": frappe.get_all("CRM Deal", {"contact": contact}, ["name", "project_name"]) if frappe.get_meta("CRM Deal").has_field("contact") else [],
	}
	for c in frappe.get_all(CONV, {"contact": contact}, ["name", "channel", "title"]):
		c["mensagens"] = frappe.get_all(MSG, {"conversation": c.name}, ["direction", "text", "sent_at"], order_by="sent_at asc")
		dados["conversas"].append(c)
	_log("Export", contact)
	return dados


@frappe.whitelist(methods=["POST"])
def erase_contact(contact: str):
	"""Apaga o contato e as conversas/mensagens ligadas a ele. Projetos ficam, sem o vinculo."""
	_admin()
	for c in frappe.get_all(CONV, {"contact": contact}, pluck="name"):
		for m in frappe.get_all(MSG, {"conversation": c}, pluck="name"):
			frappe.delete_doc(MSG, m, ignore_permissions=True, force=True)
		frappe.delete_doc(CONV, c, ignore_permissions=True, force=True)
	# desfaz vinculos em projetos
	meta = frappe.get_meta("CRM Deal")
	if meta.has_field("contact"):
		frappe.db.sql("update `tabCRM Deal` set contact=null where contact=%s", contact)
	frappe.db.sql("delete from `tabCRM Contacts` where contact=%s", contact)
	frappe.delete_doc("Contact", contact, ignore_permissions=True, force=True)
	_log("Erase", contact)
	return True


def _log(tipo: str, ref: str):
	frappe.get_doc(
		{"doctype": "CRM Privacy Request", "request_type": tipo, "subject_ref": ref, "performed_by": frappe.session.user}
	).insert(ignore_permissions=True)
