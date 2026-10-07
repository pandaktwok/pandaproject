import frappe
from frappe import _


@frappe.whitelist()
def get_invitation_link(name: str) -> str:
	"""Devolve o link de aceite de um convite pendente (para copiar e enviar por qualquer canal)."""
	frappe.only_for(["System Manager", "Sales Manager"])
	doc = frappe.get_doc("CRM Invitation", name)
	if doc.status != "Pending" or not doc.key:
		frappe.throw(_("Invalid or expired key"))
	return frappe.utils.get_url(f"/api/method/crm.api.accept_invitation?key={doc.key}")
