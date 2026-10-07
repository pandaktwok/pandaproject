"""Acesso por projeto (Panda Project, fase 7A).

Regras:
- Sem lista de acesso no projeto: todos os usuarios internos veem e editam.
- Com lista: so entram os listados, o proprietario/responsavel e administradores
  (a lista so RESTRINGE; proprietario e administrador passam por cima).
- Nivel "Ver": le, mas nao edita. Nivel "Editar": le e edita.
- Projeto sem acesso responde "Sem permissão".
- Nunca deixa o sistema sem administrador.
"""
import frappe
from frappe import _

DEAL = "CRM Deal"
SO_LEITURA = ("read", "print", "email", "export", "report")


def _admin(user: str) -> bool:
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def get_deal_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if _admin(user):
		return ""
	u = frappe.db.escape(user)
	t = "`tabCRM Deal`"
	return (
		f"(not exists (select 1 from `tabCRM Deal Access` a where a.parent = {t}.name and a.parenttype = 'CRM Deal')"
		f" or {t}.owner = {u} or {t}.deal_owner = {u}"
		f" or exists (select 1 from `tabCRM Deal Access` a where a.parent = {t}.name"
		f" and a.parenttype = 'CRM Deal' and a.user = {u}))"
	)


def has_deal_permission(doc, ptype, user):
	user = user or frappe.session.user
	if _admin(user) or ptype == "create" or not doc.name:
		return True
	if doc.get("owner") == user or doc.get("deal_owner") == user:
		return True
	linhas = frappe.get_all("CRM Deal Access", {"parent": doc.name, "parenttype": DEAL}, ["user", "access"])
	if not linhas:
		return True
	meu = next((l for l in linhas if l.user == user), None)
	if not meu:
		return False
	return True if meu.access == "Edit" else ptype in SO_LEITURA


def _pode_gerir(deal: str) -> bool:
	u = frappe.session.user
	if _admin(u):
		return True
	dono, resp = frappe.db.get_value(DEAL, deal, ["owner", "deal_owner"])
	return u in (dono, resp)


@frappe.whitelist()
def get_access(deal: str):
	if not frappe.has_permission(DEAL, "read", deal):
		frappe.throw(_("Sem permissão neste projeto"), frappe.PermissionError)
	linhas = frappe.get_all(
		"CRM Deal Access", {"parent": deal, "parenttype": DEAL}, ["user", "access"], order_by="idx asc"
	)
	for l in linhas:
		l["full_name"] = frappe.db.get_value("User", l.user, "full_name") or l.user
	usuarios = frappe.get_all(
		"User",
		{"enabled": 1, "user_type": "System User", "name": ["not in", ("Administrator", "Guest")]},
		["name", "full_name"],
		order_by="full_name asc",
	)
	return {"can_manage": _pode_gerir(deal), "entries": linhas, "users": usuarios}


@frappe.whitelist(methods=["POST"])
def set_access(deal: str, entries):
	"""entries: lista de {user, access}. Lista vazia = projeto aberto a todos os usuarios internos."""
	if not _pode_gerir(deal):
		frappe.throw(_("Só o proprietário ou um administrador altera o acesso"), frappe.PermissionError)
	entries = frappe.parse_json(entries) or []
	doc = frappe.get_doc(DEAL, deal)
	doc.set("access_list", [])
	vistos = set()
	for e in entries:
		u, nivel = e.get("user"), e.get("access") if e.get("access") in ("View", "Edit") else "Edit"
		if not u or u in vistos or not frappe.db.exists("User", u):
			continue
		vistos.add(u)
		doc.append("access_list", {"user": u, "access": nivel})
	doc.flags.ignore_permissions = True
	doc.save()
	return get_access(deal)


# ---- protecao do ultimo administrador --------------------------------------
def _outros_admins(excluir: str) -> int:
	nomes = frappe.get_all("Has Role", {"role": "System Manager", "parenttype": "User"}, pluck="parent")
	return frappe.db.count(
		"User",
		{"name": ["in", [n for n in nomes if n not in (excluir, "Administrator", "Guest")] or [""]], "enabled": 1},
	)


def proteger_ultimo_admin(doc, method=None):
	if doc.is_new() or doc.name in ("Administrator", "Guest"):
		return
	era_admin = frappe.db.exists("Has Role", {"parent": doc.name, "role": "System Manager", "parenttype": "User"})
	if not era_admin:
		return
	continua = doc.enabled and any(r.role == "System Manager" for r in doc.get("roles", []))
	if not continua and _outros_admins(doc.name) == 0:
		frappe.throw(_("Não é possível remover o último administrador"))


def proteger_ultimo_admin_ao_apagar(doc, method=None):
	if doc.name in ("Administrator", "Guest"):
		return
	if frappe.db.exists("Has Role", {"parent": doc.name, "role": "System Manager", "parenttype": "User"}):
		if _outros_admins(doc.name) == 0:
			frappe.throw(_("Não é possível apagar o último administrador"))
