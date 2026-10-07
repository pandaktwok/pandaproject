"""Entrada de contatos pelo site (newsletter) - Panda Project.

O formulario do site envia POST para /api/method/crm.panda.contatos.cadastro_site
com o token configurado em site_config.json (chave "panda_site_token").
Cria (ou atualiza) um Contato; nao cria lead.
"""
import hmac

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=60)
def cadastro_site(email: str, nome: str | None = None, telefone: str | None = None, token: str | None = None, origem: str | None = None):
	from crm.panda.integracoes import token_do_site

	esperado = token_do_site()
	if not esperado:
		frappe.throw(_("Cadastro pelo site não está ativado"), frappe.PermissionError)
	if not token or not hmac.compare_digest(str(token), str(esperado)):
		frappe.throw(_("Token inválido"), frappe.PermissionError)

	email = (email or "").strip().lower()
	if not email or not validate_email_address(email):
		frappe.throw(_("E-mail inválido"))
	origem = (origem or "Newsletter do site").strip()[:80]
	nome = (nome or "").strip()[:140] or email.split("@")[0]

	existente = frappe.db.get_value("Contact Email", {"email_id": email, "parenttype": "Contact"}, "parent")
	if existente:
		if not frappe.db.get_value("Contact", existente, "panda_origem"):
			frappe.db.set_value("Contact", existente, "panda_origem", origem, update_modified=False)
		return {"ok": True, "criado": False}

	contato = frappe.new_doc("Contact")
	contato.first_name = nome
	contato.panda_origem = origem
	contato.append("email_ids", {"email_id": email, "is_primary": 1})
	if telefone:
		contato.append("phone_nos", {"phone": str(telefone)[:30], "is_primary_mobile_no": 1})
	contato.insert(ignore_permissions=True)
	return {"ok": True, "criado": True}
