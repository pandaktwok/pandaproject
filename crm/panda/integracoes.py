"""Configuracoes de integracoes (Panda Project): token do site, Google (Calendario/Drive) e E-mail.

So administradores. Segredos nunca voltam para a tela: ela so recebe "configurado: sim/nao".
O fluxo de conexao (OAuth, sincronizacao) entra nas fases 6 e 8; aqui ficam as chaves prontas.
"""
import re
import secrets

import frappe
from frappe import _
from frappe.utils.password import get_decrypted_password

DOC = "Panda Integrations"


def _admin():
	if not (frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()):
		frappe.throw(_("Somente administradores"), frappe.PermissionError)


def token_do_site() -> str | None:
	t = get_decrypted_password(DOC, DOC, "site_token", raise_exception=False)
	return t or frappe.conf.get("panda_site_token")


def _google():
	return frappe.get_single("Google Settings")


@frappe.whitelist()
def _url():
	from crm.panda.chat import get_url

	return get_url()


def get_config():
	_admin()
	cfg = frappe.get_single(DOC)
	g = _google()
	return {
		"site": {
			"configured": bool(token_do_site()),
			"origin": cfg.site_origin or "",
			"endpoint": f"{_url()}/api/method/crm.panda.contatos.cadastro_site",
		},
		"google": {
			"enabled": bool(g.enable),
			"client_id": g.client_id or "",
			"secret_set": bool(get_decrypted_password("Google Settings", "Google Settings", "client_secret", raise_exception=False)),
			"redirect_uris": [
				f"{_url()}?cmd=frappe.integrations.doctype.google_calendar.google_calendar.google_callback",
				f"{_url()}/api/method/crm.panda.drive.callback",
			],
		},
		"calendar": {"enabled": bool(cfg.calendar_enabled)},
		"drive": {"enabled": bool(cfg.drive_enabled), "root_folder": cfg.drive_root_folder or "Panda Project"},
		"email": {"accounts": frappe.db.count("Email Account", {"enable_incoming": 1})},
		"messaging": {
			"wa": {
				"url": cfg.evo_url or "",
				"instance": cfg.evo_instance or "panda",
				"notify": cfg.wa_notify_numbers or "",
				"status": cfg.wa_status or "desconectado",
				"key_set": bool(get_decrypted_password(DOC, DOC, "evo_key", raise_exception=False)),
				"mode": "Cloud API" if cfg.wa_mode == "Cloud API" else "Evolution",
				"public_url": cfg.public_url or "",
				"cloud_phone_id": cfg.wa_cloud_phone_id or "",
				"cloud_token_set": bool(get_decrypted_password(DOC, DOC, "wa_cloud_token", raise_exception=False)),
				"cloud_display": cfg.wa_cloud_display or "",
			},
			"ig": {
				"app_id": cfg.meta_app_id or "",
				"secret_set": bool(get_decrypted_password(DOC, DOC, "meta_app_secret", raise_exception=False)),
			},
		},
	}


@frappe.whitelist(methods=["POST"])
def generate_site_token():
	"""Gera um token novo e o mostra uma unica vez."""
	_admin()
	token = secrets.token_urlsafe(32)
	cfg = frappe.get_single(DOC)
	cfg.site_token = token
	cfg.save(ignore_permissions=True)
	return token


@frappe.whitelist(methods=["POST"])
def save_site(origin: str = ""):
	_admin()
	origin = (origin or "").strip().rstrip("/")
	if origin and not origin.startswith(("http://", "https://")):
		frappe.throw(_("Endereço do site deve começar com https://"))
	cfg = frappe.get_single(DOC)
	cfg.site_origin = origin
	cfg.save(ignore_permissions=True)
	# libera o site para chamar o cadastro (CORS)
	try:
		from frappe.installer import update_site_config

		atuais = [o for o in (frappe.conf.get("allow_cors") or []) if o != "*"] if isinstance(frappe.conf.get("allow_cors"), list) else []
		if origin and origin not in atuais:
			atuais.append(origin)
		update_site_config("allow_cors", atuais)
	except Exception:
		frappe.log_error(title="Panda: falha ao gravar allow_cors")
	return True


@frappe.whitelist(methods=["POST"])
def save_google(client_id: str = "", client_secret: str = "", enabled=1):
	"""Guarda a chave do Google no 'Google Settings' do Frappe (usada por Calendario e Drive)."""
	_admin()
	g = _google()
	if client_id:
		g.client_id = client_id.strip()
	if client_secret:
		g.client_secret = client_secret.strip()
	g.enable = 1 if int(enabled) else 0
	g.save(ignore_permissions=True)
	return True


@frappe.whitelist(methods=["POST"])
def save_services(calendar_enabled=0, drive_enabled=0, drive_root_folder: str = "Panda Project"):
	_admin()
	cfg = frappe.get_single(DOC)
	cfg.calendar_enabled = 1 if int(calendar_enabled) else 0
	cfg.drive_enabled = 1 if int(drive_enabled) else 0
	cfg.drive_root_folder = (drive_root_folder or "Panda Project").strip()
	cfg.save(ignore_permissions=True)
	return True


@frappe.whitelist(methods=["POST"])
def save_messaging(evo_url: str = "", evo_key: str = "", evo_instance: str = "panda", notify: str = "", mode: str = "Evolution", public_url: str = ""):
	_admin()
	url = (evo_url or "").strip().rstrip("/")
	if url and not url.startswith(("http://", "https://")):
		frappe.throw(_("O endereço da Evolution API deve começar com http:// ou https://"))
	cfg = frappe.get_single(DOC)
	cfg.evo_url = url
	cfg.evo_instance = re.sub(r"[^A-Za-z0-9_-]", "", evo_instance or "") or "panda"
	cfg.wa_notify_numbers = notify or ""
	pub = (public_url or "").strip().rstrip("/")
	if pub.startswith(("http://", "https://")):
		from urllib.parse import urlparse

		u = urlparse(pub)
		pub = f"{u.scheme}://{u.netloc}"  # so o dominio: /crm ou outro caminho quebra o webhook
	if pub and not pub.startswith(("http://", "https://")):
		frappe.throw(_("O endereço público deve começar com http:// ou https://"))
	cfg.public_url = pub
	cfg.wa_mode = "Cloud API" if mode == "Cloud API" else "Evolution"
	if evo_key:
		cfg.evo_key = evo_key.strip()
	cfg.save(ignore_permissions=True)
	return True
