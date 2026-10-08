"""Espelho no Google Drive (Panda Project, fase 6 / 7C).

- Escopo minimo: drive.file (o programa so enxerga o que ele mesmo criou).
- Estrutura: <pasta raiz> / <Projeto> / Financeiro / Parcela N - MM-AAAA / arquivo.pdf
- Fila (CRM Drive Copy): ate 8 tentativas, espera crescente, botao "Tentar de novo".
- Pastas e arquivos nao duplicam: pastas sao buscadas por nome antes de criar e cada arquivo
  guarda o id do Drive depois de copiado.
- Segredos: o refresh token fica criptografado em "Panda Integrations" e nunca vai para a tela.
"""
import json
import secrets
from datetime import timedelta

import frappe
import requests
from frappe import _
from frappe.utils import add_to_date, now_datetime

from crm.panda.chat import get_url
from frappe.utils.password import get_decrypted_password

DOC = "Panda Integrations"
SCOPE = "https://www.googleapis.com/auth/drive.file"
AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
MAX_TENTATIVAS = 8
PASTA = "application/vnd.google-apps.folder"


def _admin():
	if not (frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()):
		frappe.throw(_("Somente administradores"), frappe.PermissionError)


def redirect_uri() -> str:
	return f"{get_url()}/api/method/crm.panda.drive.callback"


def _cliente():
	cid = frappe.db.get_single_value("Google Settings", "client_id")
	secret = get_decrypted_password("Google Settings", "Google Settings", "client_secret", raise_exception=False)
	if not cid or not secret:
		frappe.throw(_("Cole o Client ID e o Client Secret do Google em Conexões primeiro"))
	return cid, secret


# ---------------------------------------------------------------- autorizacao
@frappe.whitelist()
def get_auth_url():
	_admin()
	cid, _s = _cliente()
	state = secrets.token_urlsafe(24)
	frappe.cache.set_value(f"panda_drive_state:{state}", frappe.session.user, expires_in_sec=600)
	q = requests.Request(
		"GET",
		AUTH,
		params={
			"client_id": cid,
			"redirect_uri": redirect_uri(),
			"response_type": "code",
			"scope": SCOPE,
			"access_type": "offline",
			"prompt": "consent",
			"state": state,
		},
	).prepare()
	return q.url


@frappe.whitelist()
def callback(code: str | None = None, state: str | None = None, error: str | None = None):
	_admin()
	dono = frappe.cache.get_value(f"panda_drive_state:{state}") if state else None
	if error or not code or dono != frappe.session.user:
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/crm?drive=erro"
		return
	cid, secret = _cliente()
	r = requests.post(
		TOKEN,
		data={
			"code": code,
			"client_id": cid,
			"client_secret": secret,
			"redirect_uri": redirect_uri(),
			"grant_type": "authorization_code",
		},
		timeout=30,
	)
	dados = r.json() if r.content else {}
	refresh = dados.get("refresh_token")
	if not refresh:
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/crm?drive=erro"
		return
	cfg = frappe.get_single(DOC)
	cfg.drive_refresh_token = refresh
	cfg.drive_enabled = 1
	try:
		cfg.drive_account = _sobre(dados["access_token"]).get("emailAddress") or ""
	except Exception:
		cfg.drive_account = ""
	cfg.save(ignore_permissions=True)
	from urllib.parse import urlencode

	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/assets/crm/conectado.html?" + urlencode(
		{"s": "drive", "conta": cfg.drive_account or "", "volta": "/crm"}
	)


def _sobre(token: str) -> dict:
	r = requests.get(f"{API}/about", params={"fields": "user(emailAddress)"}, headers={"Authorization": f"Bearer {token}"}, timeout=20)
	return (r.json() or {}).get("user", {})


def _access_token() -> str:
	refresh = get_decrypted_password(DOC, DOC, "drive_refresh_token", raise_exception=False)
	if not refresh:
		raise RuntimeError("Drive não conectado")
	cid, secret = _cliente()
	r = requests.post(
		TOKEN,
		data={"client_id": cid, "client_secret": secret, "refresh_token": refresh, "grant_type": "refresh_token"},
		timeout=30,
	)
	if r.status_code != 200:
		raise RuntimeError(f"Google recusou o token ({r.status_code}). Reconecte o Drive.")
	return r.json()["access_token"]


@frappe.whitelist()
def get_status():
	_admin()
	refresh = get_decrypted_password(DOC, DOC, "drive_refresh_token", raise_exception=False)
	cfg = frappe.get_single(DOC)
	cont = {s: frappe.db.count("CRM Drive Copy", {"status": s}) for s in ("Pending", "Copied", "Failed")}
	return {"connected": bool(refresh), "account": cfg.drive_account or "", "redirect_uri": redirect_uri(), "counts": cont}


@frappe.whitelist(methods=["POST"])
def test():
	_admin()
	try:
		tok = _access_token()
		return {"ok": True, "account": _sobre(tok).get("emailAddress", "")}
	except Exception as e:
		return {"ok": False, "error": str(e)}


@frappe.whitelist(methods=["POST"])
def disconnect():
	_admin()
	refresh = get_decrypted_password(DOC, DOC, "drive_refresh_token", raise_exception=False)
	if refresh:
		try:
			requests.post("https://oauth2.googleapis.com/revoke", params={"token": refresh}, timeout=20)
		except Exception:
			pass
	cfg = frappe.get_single(DOC)
	cfg.drive_refresh_token = ""
	cfg.drive_account = ""
	cfg.drive_enabled = 0
	cfg.save(ignore_permissions=True)
	return True


# ---------------------------------------------------------------- fila
def _ativo() -> bool:
	return bool(
		frappe.db.get_single_value(DOC, "drive_enabled")
		and get_decrypted_password(DOC, DOC, "drive_refresh_token", raise_exception=False)
	)


def enfileirar(file_name: str, deal: str):
	"""Chamado quando um PDF de pagamento e criado."""
	if not _ativo() or frappe.db.exists("CRM Drive Copy", {"file": file_name}):
		return
	c = frappe.get_doc({"doctype": "CRM Drive Copy", "file": file_name, "deal": deal, "status": "Pending"}).insert(
		ignore_permissions=True
	)
	frappe.enqueue("crm.panda.drive.processar", copy=c.name, enqueue_after_commit=True, queue="short")


@frappe.whitelist(methods=["POST"])
def copy_old():
	"""Copia pagamentos antigos (arquivos que ainda nao entraram na fila)."""
	_admin()
	if not _ativo():
		frappe.throw(_("Conecte o Drive primeiro"))
	n = 0
	for f in frappe.get_all(
		"File", {"attached_to_doctype": "CRM Deal", "panda_key": ["like", "%parcela:%"]}, ["name", "attached_to_name"]
	):
		if not frappe.db.exists("CRM Drive Copy", {"file": f.name}):
			enfileirar(f.name, f.attached_to_name)
			n += 1
	return n


@frappe.whitelist(methods=["POST"])
def retry(name: str | None = None):
	"""Tentar de novo: uma copia ou todas as que falharam."""
	_admin()
	filtros = {"status": "Failed"}
	if name:
		filtros = {"name": name}
	for c in frappe.get_all("CRM Drive Copy", filtros, pluck="name"):
		frappe.db.set_value("CRM Drive Copy", c, {"status": "Pending", "attempts": 0, "next_try": None, "last_error": ""})
		frappe.enqueue("crm.panda.drive.processar", copy=c, enqueue_after_commit=True, queue="short")
	return True


def reprocessar_pendentes():
	"""Tarefa agendada (a cada hora): tenta de novo o que esta pendente e ja pode ser tentado."""
	if not _ativo():
		return
	agora = now_datetime()
	for c in frappe.get_all("CRM Drive Copy", {"status": "Pending"}, ["name", "next_try"]):
		if not c.next_try or c.next_try <= agora:
			processar(c.name)


def processar(copy: str):
	doc = frappe.get_doc("CRM Drive Copy", copy)
	if doc.status == "Copied":
		return
	try:
		if not _ativo():
			raise RuntimeError("Drive desligado ou não conectado")
		tok = _access_token()
		doc.drive_path, doc.drive_file_id = _copiar(doc, tok)
		doc.status, doc.last_error, doc.next_try = "Copied", "", None
	except Exception as e:
		doc.attempts = (doc.attempts or 0) + 1
		doc.last_error = str(e)[:500]
		if doc.attempts >= MAX_TENTATIVAS:
			doc.status = "Failed"
			doc.next_try = None
		else:
			espera = min(5 * 2 ** (doc.attempts - 1), 360)  # 5, 10, 20... ate 6 h
			doc.next_try = add_to_date(now_datetime(), minutes=espera)
	doc.save(ignore_permissions=True)
	frappe.db.commit()


# ---------------------------------------------------------------- Drive
def _h(tok):
	return {"Authorization": f"Bearer {tok}"}


def _q(s: str) -> str:
	return s.replace("\\", "\\\\").replace("'", "\\'")


def _pasta(tok, nome: str, pai: str) -> str:
	"""Acha a pasta pelo nome dentro do pai; cria so se nao existir (sem duplicar)."""
	r = requests.get(
		f"{API}/files",
		params={
			"q": f"name='{_q(nome)}' and mimeType='{PASTA}' and '{pai}' in parents and trashed=false",
			"fields": "files(id)",
			"pageSize": 1,
		},
		headers=_h(tok),
		timeout=30,
	)
	r.raise_for_status()
	achados = r.json().get("files", [])
	if achados:
		return achados[0]["id"]
	r = requests.post(
		f"{API}/files", json={"name": nome, "mimeType": PASTA, "parents": [pai]}, headers=_h(tok), timeout=30
	)
	r.raise_for_status()
	return r.json()["id"]


def _limpo(s: str) -> str:
	return " ".join((s or "").replace("/", "-").replace("\\", "-").split()) or "Sem nome"


def _copiar(doc, tok) -> tuple[str, str]:
	from crm.panda.files import _chave  # noqa: F401

	f = frappe.get_doc("File", doc.file)
	chave = (f.panda_key or "").replace("desfeito:", "")
	_, line, n = chave.split(":")
	due = frappe.db.get_value("CRM Payment Installment", {"parent": line, "number": int(n)}, "due_date")
	pasta_parcela = f"Parcela {n} - {due.strftime('%m-%Y')}" if due else f"Parcela {n}"
	nome_proj = frappe.db.get_value("CRM Deal", doc.deal, "project_name") or doc.deal
	raiz = frappe.db.get_single_value(DOC, "drive_root_folder") or "Panda Project"

	pai = "root"
	for nome in (raiz, _limpo(nome_proj), "Financeiro", pasta_parcela):
		pai = _pasta(tok, _limpo(nome), pai)
	caminho = f"{raiz}/{_limpo(nome_proj)}/Financeiro/{pasta_parcela}/{f.file_name}"

	# nao duplica: ja existe um arquivo com esse nome nessa pasta?
	r = requests.get(
		f"{API}/files",
		params={"q": f"name='{_q(f.file_name)}' and '{pai}' in parents and trashed=false", "fields": "files(id)", "pageSize": 1},
		headers=_h(tok),
		timeout=30,
	)
	r.raise_for_status()
	if r.json().get("files"):
		return caminho, r.json()["files"][0]["id"]

	meta = json.dumps({"name": f.file_name, "parents": [pai]})
	limite = "panda" + secrets.token_hex(8)
	corpo = (
		f"--{limite}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
		f"--{limite}\r\nContent-Type: application/pdf\r\n\r\n"
	).encode() + f.get_content() + f"\r\n--{limite}--".encode()
	r = requests.post(
		UPLOAD,
		params={"uploadType": "multipart", "fields": "id"},
		headers={**_h(tok), "Content-Type": f"multipart/related; boundary={limite}"},
		data=corpo,
		timeout=120,
	)
	r.raise_for_status()
	return caminho, r.json()["id"]


@frappe.whitelist()
def pasta_projeto(deal: str):
	"""Link da pasta raiz do projeto no Google Drive (cria se ainda nao existir)."""
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Sem permissão neste projeto"), frappe.PermissionError)
	if not frappe.db.get_single_value(DOC, "drive_enabled") or not _ativo():
		frappe.throw(_("O Google Drive não está conectado. Conecte em Configurações → Conexões."))
	try:
		tok = _access_token()
		nome_proj = frappe.db.get_value("CRM Deal", deal, "project_name") or deal
		raiz = frappe.db.get_single_value(DOC, "drive_root_folder") or "Panda Project"
		pai = "root"
		for nome in (raiz, _limpo(nome_proj)):
			pai = _pasta(tok, _limpo(nome), pai)
	except Exception as e:
		frappe.throw(_("Não consegui abrir a pasta no Drive: {0}").format(str(e)[:200]))
	return {"url": f"https://drive.google.com/drive/folders/{pai}"}


# ---------------------------------------------------------------- selo no card de arquivos
@frappe.whitelist()
def get_badges(deal: str):
	"""{ nome_do_file: {status, copy, error} } para o selo Copiado / Pendente / Falhou."""
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Sem permissão neste projeto"), frappe.PermissionError)
	if not frappe.db.get_single_value(DOC, "drive_enabled"):
		return {}
	return {
		c.file: {"status": c.status, "copy": c.name, "error": c.last_error if _eh_admin() else ""}
		for c in frappe.get_all("CRM Drive Copy", {"deal": deal}, ["name", "file", "status", "last_error"])
	}


def _eh_admin() -> bool:
	return frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()
