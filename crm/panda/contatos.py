"""Entrada de contatos pelo site (newsletter) - Panda Project.

O formulario do site envia POST para /api/method/crm.panda.contatos.cadastro_site
com o token configurado em site_config.json (chave "panda_site_token").
Cria (ou atualiza) um Contato; nao cria lead.
"""
import hmac
import re

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
		adicionar_origem(existente, origem)
		return {"ok": True, "criado": False}

	contato = frappe.new_doc("Contact")
	contato.first_name = nome
	contato.panda_origem = origem
	contato.append("email_ids", {"email_id": email, "is_primary": 1})
	if telefone:
		contato.append("phone_nos", {"phone": str(telefone)[:30], "is_primary_mobile_no": 1})
	contato.insert(ignore_permissions=True)
	return {"ok": True, "criado": True}


# ============================================================ Origens, telefone e listagem
ORIGENS = ["WhatsApp", "Instagram", "Fornecedor", "Newsletter", "E-mail", "Manual"]


def normalizar_origem(valor: str) -> str:
	v = (valor or "").strip()
	b = v.lower()
	if "newsletter" in b:
		return "Newsletter"
	if "whats" in b:
		return "WhatsApp"
	if "insta" in b:
		return "Instagram"
	if "fornecedor" in b:
		return "Fornecedor"
	if "mail" in b:
		return "E-mail"
	if b in ("manual", ""):
		return "Manual"
	return v[:40]


def origens_de(valor: str | None) -> list[str]:
	"""'Newsletter do site, WhatsApp' -> ['Newsletter', 'WhatsApp']. Vazio = Manual."""
	out: list[str] = []
	for parte in re.split(r"[,;]", valor or ""):
		o = normalizar_origem(parte)
		if parte.strip() and o not in out:
			out.append(o)
	return out or ["Manual"]


def adicionar_origem(contato: str, origem: str):
	atual = frappe.db.get_value("Contact", contato, "panda_origem")
	lista = origens_de(atual) if atual else []
	nova = normalizar_origem(origem)
	if nova not in lista:
		lista.append(nova)
	if lista != origens_de(atual) or not atual:
		frappe.db.set_value("Contact", contato, "panda_origem", ", ".join(lista), update_modified=False)


def telefone_normalizado(s: str | None) -> str:
	"""So digitos, com prefixo 55 (Brasil). Vazio se nao parecer um telefone."""
	d = re.sub(r"\D", "", s or "")
	d = d.lstrip("0") if len(d) > 11 and not d.startswith("55") else d
	if len(d) in (10, 11):
		d = "55" + d
	return d if len(d) >= 12 else (d if len(d) >= 8 else "")


def telefone_br(s: str | None) -> str:
	"""Formato de tela: (48) 99654-5728."""
	d = telefone_normalizado(s)
	if d.startswith("55") and len(d) in (12, 13):
		ddd, resto = d[2:4], d[4:]
		return f"({ddd}) {resto[:-4]}-{resto[-4:]}"
	return s or ""


def mesmo_telefone(a: str | None, b: str | None) -> bool:
	da, db = telefone_normalizado(a), telefone_normalizado(b)
	if not da or not db:
		return False
	if da == db:
		return True
	# numeros antigos sem o 9: mesmo DDD e mesmos 8 ultimos digitos
	return da.startswith("55") and db.startswith("55") and da[2:4] == db[2:4] and da[-8:] == db[-8:]


def achar_contato(telefone: str | None = None, email: str | None = None) -> str | None:
	email = (email or "").strip().lower()
	if email:
		nome = frappe.db.get_value("Contact Email", {"email_id": email, "parenttype": "Contact"}, "parent")
		if nome:
			return nome
	alvo = telefone_normalizado(telefone)
	if alvo:
		fim = alvo[-8:]
		for p in frappe.get_all(
			"Contact Phone", {"parenttype": "Contact", "phone": ["like", f"%{fim[-4:]}%"]}, ["parent", "phone"], limit_page_length=0
		):
			if mesmo_telefone(p.phone, alvo):
				return p.parent
	return None


def criar_contato(nome: str, telefone: str = "", email: str = "", origem: str = "Manual", documento: str = "") -> str:
	c = frappe.new_doc("Contact")
	c.first_name = (nome or "").strip()[:140] or telefone_br(telefone) or email
	c.panda_origem = normalizar_origem(origem)
	if documento:
		c.panda_documento = documento[:30]
	if email:
		c.append("email_ids", {"email_id": email.strip().lower(), "is_primary": 1})
	tel = telefone_normalizado(telefone)
	if tel:
		c.append("phone_nos", {"phone": tel, "is_primary_mobile_no": 1})
	c.insert(ignore_permissions=True)
	return c.name


def _dados_basicos(nomes: list[str]) -> dict:
	tel, mail = {}, {}
	if not nomes:
		return {}
	for p in frappe.get_all("Contact Phone", {"parenttype": "Contact", "parent": ["in", nomes]}, ["parent", "phone", "is_primary_mobile_no"], order_by="is_primary_mobile_no desc", limit_page_length=0):
		tel.setdefault(p.parent, p.phone)
	for e in frappe.get_all("Contact Email", {"parenttype": "Contact", "parent": ["in", nomes]}, ["parent", "email_id", "is_primary"], order_by="is_primary desc", limit_page_length=0):
		mail.setdefault(e.parent, e.email_id)
	return {"tel": tel, "mail": mail}


@frappe.whitelist()
def listar(q: str = "", origem: str = ""):
	"""Pagina Contatos: 'contatos' (qualquer origem que nao seja so newsletter) e 'newsletters' (so newsletter).
	A mesma pessoa nunca aparece nas duas listas."""
	frappe.has_permission("Contact", "read", throw=True)
	campos = ["name", "full_name", "first_name", "image", "panda_origem", "panda_grupos", "creation"]
	rows = frappe.get_list("Contact", fields=campos, order_by="creation desc", limit_page_length=5000)
	d = _dados_basicos([r.name for r in rows])
	busca = (q or "").strip().lower()
	busca_d = re.sub(r"\D", "", busca)
	contatos, news = [], []
	for r in rows:
		origens = origens_de(r.panda_origem)
		if origem and origem not in origens:
			continue
		tel, mail = d["tel"].get(r.name, ""), d["mail"].get(r.name, "")
		if busca:
			achou = busca in (r.full_name or "").lower() or busca in (mail or "").lower() or (
				busca_d and busca_d in re.sub(r"\D", "", tel or "")
			)
			if not achou:
				continue
		item = {
			"name": r.name,
			"full_name": r.full_name or r.first_name,
			"image": r.image,
			"phone": telefone_br(tel),
			"email": mail,
			"origens": origens,
			"grupos": r.panda_grupos or "",
			"creation": str(r.creation),
		}
		(news if origens == ["Newsletter"] else contatos).append(item)
	return {"contatos": contatos, "newsletters": news, "origens": ORIGENS}


@frappe.whitelist()
def buscar(q: str = ""):
	"""Lista para escolher um contato (busca por nome, numero ou e-mail)."""
	frappe.has_permission("Contact", "read", throw=True)
	q = (q or "").strip()
	filtros = {}
	rows = frappe.get_list("Contact", fields=["name", "full_name", "first_name", "image"], order_by="modified desc", limit_page_length=3000)
	d = _dados_basicos([r.name for r in rows])
	busca, busca_d, out = q.lower(), re.sub(r"\D", "", q), []
	for r in rows:
		tel, mail = d["tel"].get(r.name, ""), d["mail"].get(r.name, "")
		if busca and not (
			busca in (r.full_name or "").lower()
			or busca in (mail or "").lower()
			or (busca_d and busca_d in re.sub(r"\D", "", tel or ""))
		):
			continue
		out.append({"name": r.name, "full_name": r.full_name or r.first_name, "image": r.image,
			"phone": telefone_normalizado(tel), "phone_br": telefone_br(tel), "email": mail})
		if len(out) >= 30:
			break
	return out


@frappe.whitelist(methods=["POST"])
def vincular_fornecedor(nome: str, whatsapp: str = "", email: str = "", documento: str = "", contato: str = ""):
	"""Liga o fornecedor a um contato. Se vier um contato escolhido, usa esse; senao procura por numero/e-mail;
	se nao achar e houver numero ou e-mail, cria com origem Fornecedor."""
	nome = (nome or "").strip()
	if not nome:
		frappe.throw(_("O nome do fornecedor é obrigatório"))
	if email and not validate_email_address(email):
		frappe.throw(_("E-mail inválido"))
	tel = telefone_normalizado(whatsapp)
	if whatsapp and not tel:
		frappe.throw(_("WhatsApp inválido"))
	existente = contato if contato and frappe.db.exists("Contact", contato) else achar_contato(tel, email)
	if existente:
		adicionar_origem(existente, "Fornecedor")
		return {"contact": existente, "linked": True, "created": False}
	if not tel and not email:
		return {"contact": None, "linked": False, "created": False}
	novo = criar_contato(nome, tel, email, "Fornecedor", documento)
	return {"contact": novo, "linked": False, "created": True}
