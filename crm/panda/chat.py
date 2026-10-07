"""WhatsApp (Evolution API) e Instagram (API oficial da Meta) - Panda Project, fase 9.

- Caixa de conversas nativa: CRM Chat Conversation / CRM Chat Message.
- V2.0 nao faz disparos: so responde a conversas que o contato iniciou.
- WhatsApp usa o modo de conversa (nao oficial); risco de banimento em envio em massa -> sem disparos.
- Segredos (chaves, tokens) ficam em "Panda Integrations" (Password) e nunca voltam para a tela.
"""
import hashlib
import hmac
import json
import re
import secrets
from urllib.parse import quote

import frappe
import requests
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import get_url as _get_url
from frappe.utils import now_datetime
from frappe.utils.password import get_decrypted_password

DOC = "Panda Integrations"


def get_url() -> str:
	"""Endereco que a Evolution/Meta enxergam: o publico informado em Conexoes, senao o do site."""
	publico = (frappe.db.get_single_value("Panda Integrations", "public_url") or "").strip().rstrip("/")
	return publico or _get_url()

CONV = "CRM Chat Conversation"
MSG = "CRM Chat Message"
PAPEIS = ("System Manager", "Sales Manager", "Sales User")
GRAPH = "https://graph.facebook.com/v21.0"


def _pw(campo: str) -> str | None:
	return get_decrypted_password(DOC, DOC, campo, raise_exception=False)


def _cfg():
	return frappe.get_single(DOC)


def _admin():
	if not (frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()):
		frappe.throw(_("Somente administradores"), frappe.PermissionError)


def _interno():
	if frappe.session.user != "Administrator" and not set(PAPEIS) & set(frappe.get_roles()):
		frappe.throw(_("Sem permissão"), frappe.PermissionError)


def _publicar(conversa: str):
	frappe.publish_realtime("panda_chat", {"conversation": conversa}, after_commit=True)


# ============================================================ conversas (comum)
def _digitos(s: str) -> str:
	return re.sub(r"\D", "", s or "")


def _achar_contato(telefone: str) -> str | None:
	from crm.panda.contatos import achar_contato

	return achar_contato(telefone)


def _conversa(canal: str, ext_id: str, titulo: str | None = None, telefone: str | None = None) -> str:
	nome = frappe.db.get_value(CONV, {"channel": canal, "external_id": ext_id})
	if nome:
		if titulo and not frappe.db.get_value(CONV, nome, "title"):
			frappe.db.set_value(CONV, nome, "title", titulo)
		return nome
	doc = frappe.get_doc(
		{
			"doctype": CONV,
			"channel": canal,
			"external_id": ext_id,
			"title": titulo or telefone or ext_id,
			"contact": _achar_contato(telefone) if telefone else None,
		}
	).insert(ignore_permissions=True)
	return doc.name


def _registrar(conv: str, direcao: str, texto: str, ext_id: str | None = None, status: str | None = None, por=None, quando=None):
	if ext_id and frappe.db.exists(MSG, {"conversation": conv, "external_id": ext_id}):
		return None
	m = frappe.get_doc(
		{
			"doctype": MSG,
			"conversation": conv,
			"direction": direcao,
			"text": texto,
			"sent_at": quando or now_datetime(),
			"status": status or ("Received" if direcao == "In" else "Sent"),
			"external_id": ext_id,
			"sent_by": por,
		}
	).insert(ignore_permissions=True)
	c = frappe.get_doc(CONV, conv)
	c.last_message = (texto or "")[:140]
	c.last_at = m.sent_at
	if direcao == "In":
		c.unread = (c.unread or 0) + 1
	c.save(ignore_permissions=True)
	_publicar(conv)
	return m.name


@frappe.whitelist()
def get_conversations(channel: str):
	_interno()
	rows = frappe.get_all(
		CONV,
		{"channel": channel},
		["name", "title", "contact", "deal", "last_message", "last_at", "unread"],
		order_by="last_at desc",
		limit_page_length=200,
	)
	for r in rows:
		r["contact_name"] = frappe.db.get_value("Contact", r.contact, "full_name") if r.contact else None
		r["deal_name"] = frappe.db.get_value("CRM Deal", r.deal, "project_name") if r.deal else None
	return rows


@frappe.whitelist()
def get_thread(conversation: str):
	_interno()
	frappe.db.set_value(CONV, conversation, "unread", 0, update_modified=False)
	conv = frappe.get_doc(CONV, conversation)
	msgs = frappe.get_all(
		MSG,
		{"conversation": conversation},
		["name", "direction", "text", "sent_at", "status"],
		order_by="sent_at asc",
		limit_page_length=500,
	)
	return {
		"conversation": {
			"name": conv.name,
			"title": conv.title,
			"channel": conv.channel,
			"contact": conv.contact,
			"deal": conv.deal,
		},
		"messages": msgs,
	}


@frappe.whitelist(methods=["POST"])
def open_whatsapp(number: str, title: str = "", deal: str | None = None):
	"""Abre (ou cria) a conversa de WhatsApp com um numero, para o botao 'Conversar no WhatsApp'."""
	_interno()
	from crm.panda.contatos import telefone_normalizado

	n = telefone_normalizado(number)
	if not n:
		frappe.throw(_("Preencha o WhatsApp do fornecedor"))
	conv = _conversa("WhatsApp", n + "@s.whatsapp.net", title or None, n)
	if deal and frappe.has_permission("CRM Deal", "read", deal):
		frappe.db.set_value(CONV, conv, "deal", deal)
	return conv


@frappe.whitelist(methods=["POST"])
def link_conversation(conversation: str, contact: str | None = None, deal: str | None = None):
	_interno()
	if deal and not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Sem permissão neste projeto"), frappe.PermissionError)
	frappe.db.set_value(CONV, conversation, {"contact": contact or None, "deal": deal or None})
	return True


@frappe.whitelist(methods=["POST"])
def create_contact_from(conversation: str):
	_interno()
	conv = frappe.get_doc(CONV, conversation)
	if conv.contact:
		return conv.contact
	c = frappe.new_doc("Contact")
	c.first_name = (conv.title or conv.external_id)[:140]
	c.panda_origem = conv.channel
	if conv.channel == "WhatsApp":
		c.append("phone_nos", {"phone": "+" + _digitos(conv.external_id), "is_primary_mobile_no": 1})
	c.insert(ignore_permissions=True)
	conv.contact = c.name
	conv.save(ignore_permissions=True)
	return c.name


@frappe.whitelist(methods=["POST"])
def send_message(conversation: str, text: str):
	_interno()
	text = (text or "").strip()
	if not text:
		frappe.throw(_("Escreva a mensagem"))
	conv = frappe.get_doc(CONV, conversation)
	try:
		if conv.channel == "WhatsApp":
			ext = _enviar_whatsapp(_digitos(conv.external_id), text)
		else:
			ext = _enviar_instagram(conv.external_id, text)
	except Exception as e:
		_registrar(conversation, "Out", text, status="Failed", por=frappe.session.user)
		frappe.db.commit()
		frappe.throw(str(e))
	_registrar(conversation, "Out", text, ext_id=ext, status="Sent", por=frappe.session.user)
	return True


# ============================================================ WhatsApp / Evolution
def _evo(metodo: str, caminho: str, **kw):
	url, chave = _cfg().evo_url, _pw("evo_key")
	if not url or not chave:
		raise RuntimeError("Preencha o endereço e a chave da Evolution API em Conexões")
	r = requests.request(
		metodo, url.rstrip("/") + caminho, headers={"apikey": chave, "Content-Type": "application/json"}, timeout=30, **kw
	)
	return r


def _inst() -> str:
	return _cfg().evo_instance or "panda"


def _webhook_url() -> str:
	tok = _pw("wa_webhook_token")
	if not tok:
		tok = secrets.token_urlsafe(24)
		c = _cfg()
		c.wa_webhook_token = tok
		c.save(ignore_permissions=True)
	return f"{get_url()}/api/method/crm.panda.chat.webhook_whatsapp?token={quote(tok)}"


@frappe.whitelist(methods=["POST"])
def wa_connect(number: str = ""):
	"""Cria a instancia (se preciso), liga o webhook e devolve o QR Code."""
	_admin()
	nome = _inst()
	hook = _webhook_url()
	eventos = ["MESSAGES_UPSERT", "CONNECTION_UPDATE", "QRCODE_UPDATED", "GROUP_PARTICIPANTS_UPDATE", "GROUPS_UPSERT", "CONTACTS_UPSERT", "CONTACTS_UPDATE"]
	try:
		r = _evo(
			"POST",
			"/instance/create",
			json={
				"instanceName": nome,
				"qrcode": True,
				"integration": "WHATSAPP-BAILEYS",
				"webhookUrl": hook,
				"webhookByEvents": False,
				"webhookEvents": eventos,
			},
		)
		if r.status_code >= 400 and "already" not in r.text.lower() and "in use" not in r.text.lower():
			frappe.throw(_("A Evolution API recusou: {0}").format(r.text[:200]))
		# instancia ja existia: garante o webhook
		_evo("POST", f"/webhook/set/{nome}", json={"webhook": {"enabled": True, "url": hook, "events": eventos, "byEvents": False}})
		num = _digitos(number)
		q = _evo("GET", f"/instance/connect/{nome}", params={"number": num} if num else None)
		dados = q.json() if q.content else {}
	except requests.RequestException as e:
		frappe.throw(_("Não foi possível falar com a Evolution API: {0}").format(str(e)[:160]))
	except RuntimeError as e:
		frappe.throw(str(e))
	qr = dados.get("base64") or (dados.get("qrcode") or {}).get("base64")
	if not qr and (dados.get("instance") or {}).get("state") == "open":
		_set_status("conectado")
		return {"status": "conectado", "qr": None}
	return {"status": "aguardando QR Code", "qr": qr, "pairing": dados.get("pairingCode")}


def _set_status(s: str):
	frappe.db.set_value(DOC, DOC, "wa_status", s)


@frappe.whitelist()
def wa_state():
	_admin()
	if _modo_cloud():
		return {"status": _cloud_verificar(silencioso=True)}
	try:
		r = _evo("GET", f"/instance/connectionState/{_inst()}")
		st = ((r.json() or {}).get("instance") or {}).get("state") or (r.json() or {}).get("state")
	except Exception:
		return {"status": _cfg().wa_status or "desconectado"}
	status = {"open": "conectado", "connecting": "conectando"}.get(st, "desconectado")
	_set_status(status)
	return {"status": status}


@frappe.whitelist(methods=["POST"])
def wa_disconnect():
	_admin()
	if _modo_cloud():
		c = _cfg()
		c.wa_cloud_token = ""
		c.wa_cloud_display = ""
		c.save(ignore_permissions=True)
		_set_status("desconectado")
		return True
	nome = _inst()
	try:
		_evo("DELETE", f"/instance/logout/{nome}")
		_evo("DELETE", f"/instance/delete/{nome}")
	except Exception:
		pass
	_set_status("desconectado")
	return True


def _modo_cloud() -> bool:
	return (_cfg().wa_mode or "Evolution") == "Cloud API"


def _enviar_whatsapp(numero: str, texto: str) -> str | None:
	if _modo_cloud():
		return _enviar_cloud(numero, texto)
	r = _evo("POST", f"/message/sendText/{_inst()}", json={"number": numero, "text": texto})
	if r.status_code >= 400:
		raise RuntimeError(f"WhatsApp não enviou ({r.status_code}). Veja se o número está conectado.")
	return ((r.json() or {}).get("key") or {}).get("id")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=600, seconds=60)
def webhook_whatsapp(token: str | None = None):
	esperado = _pw("wa_webhook_token")
	if not esperado or not token or not hmac.compare_digest(str(token), str(esperado)):
		frappe.throw(_("Token inválido"), frappe.PermissionError)
	corpo = frappe.request.get_json(silent=True) or {}
	evento = str(corpo.get("event", "")).lower().replace("_", ".")
	dados = corpo.get("data")
	if evento == "connection.update":
		st = (dados or {}).get("state")
		_set_status({"open": "conectado", "connecting": "conectando"}.get(st, "desconectado"))
	elif evento == "messages.upsert":
		for item in dados if isinstance(dados, list) else [dados or {}]:
			_processar_whatsapp(item)
	elif evento == "group.participants.update":
		try:
			_participantes_mudaram(dados or {})
		except Exception:
			frappe.log_error(title="Panda: participantes do grupo")
	elif evento in ("contacts.upsert", "contacts.update"):
		try:
			_atualizar_contatos_evolution(dados if isinstance(dados, list) else [dados or {}])
		except Exception:
			frappe.log_error(title="Panda: contatos do WhatsApp")
	frappe.db.commit()
	return "ok"


def _processar_whatsapp(m: dict):
	chave = m.get("key") or {}
	jid = chave.get("remoteJid") or ""
	if jid.endswith("@g.us"):  # grupo: so capta quem escreveu (conversa de grupo nao entra no Chat)
		if not (chave.get("fromMe") or m.get("fromMe")):
			quem = _jid_para_numero(chave.get("participantAlt") or chave.get("participant") or m.get("participant") or "")
			if quem:
				try:
					_capturar_contato(quem, m.get("pushName"), grupo=_nome_grupo(jid), foto_async=True)
				except Exception:
					frappe.log_error(title="Panda: captar contato do grupo")
		return
	if not jid.endswith("@s.whatsapp.net"):  # status e listas de transmissao
		return
	msg = m.get("message") or {}
	texto = (
		msg.get("conversation")
		or (msg.get("extendedTextMessage") or {}).get("text")
		or (msg.get("imageMessage") or {}).get("caption")
		or "[mídia]"
	)
	de_mim = bool(chave.get("fromMe") or m.get("fromMe"))
	numero = jid.split("@")[0]
	if not de_mim:
		try:
			_capturar_contato(numero, m.get("pushName"), foto_async=True)
		except Exception:
			frappe.log_error(title="Panda: captar contato")
	conv = _conversa("WhatsApp", jid, None if de_mim else m.get("pushName"), numero)
	_registrar(conv, "Out" if de_mim else "In", texto, ext_id=chave.get("id"), status="Sent" if de_mim else "Received")


# ------------------------------------------------------------ captacao de contatos (WhatsApp)
def _jid_para_numero(jid: str) -> str:
	"""So aceita numero de telefone de verdade (@s.whatsapp.net). IDs @lid nao dao o numero."""
	if not jid or "@" not in jid:
		return _digitos(jid) if jid and "@" not in jid else ""
	n, dominio = jid.split("@", 1)
	return _digitos(n.split(":")[0]) if dominio.startswith("s.whatsapp.net") else ""


def _nome_grupo(jid: str) -> str:
	chave = f"panda_wa_grupo:{jid}"
	nome = frappe.cache.get_value(chave)
	if nome:
		return nome
	try:
		r = _evo("GET", f"/group/findGroupInfos/{_inst()}", params={"groupJid": jid})
		nome = (r.json() or {}).get("subject") if r.status_code < 400 else None
	except Exception:
		nome = None
	nome = nome or "Grupo"
	frappe.cache.set_value(chave, nome, expires_in_sec=86400)
	return nome


def _eh_placeholder(nome: str | None) -> bool:
	return not nome or not re.search(r"[A-Za-zÀ-ÿ]", nome)


def _salvar_foto_job(contato: str, numero: str):
	_salvar_foto(contato, numero)
	frappe.db.commit()


def _capturar_contato(
	numero: str, nome: str | None = None, grupo: str | None = None, foto_url: str | None = None, foto_async: bool = False
) -> str | None:
	"""Cria o contato (origem WhatsApp) ou atualiza o que ja existe. Nunca troca um nome que a pessoa digitou."""
	from crm.panda import contatos as ct

	n = ct.telefone_normalizado(numero)
	if not n:
		return None
	nome = (nome or "").strip()[:140] or None
	c = ct.achar_contato(n)
	if not c:
		c = ct.criar_contato(nome or ct.telefone_br(n), n, "", "WhatsApp")
	else:
		ct.adicionar_origem(c, "WhatsApp")
		if nome and _eh_placeholder(frappe.db.get_value("Contact", c, "first_name")):
			frappe.db.set_value("Contact", c, {"first_name": nome, "last_name": ""}, update_modified=False)
	if grupo:
		atual = frappe.db.get_value("Contact", c, "panda_grupos") or ""
		lista = [x for x in atual.split("\n") if x]
		if grupo not in lista:
			lista.append(grupo)
			frappe.db.set_value("Contact", c, "panda_grupos", "\n".join(lista)[:2000], update_modified=False)
	if not frappe.db.get_value("Contact", c, "image") and not frappe.db.get_value("Contact", c, "panda_foto_em"):
		if foto_async and not foto_url:
			frappe.enqueue("crm.panda.chat._salvar_foto_job", queue="short", contato=c, numero=n, enqueue_after_commit=True)
		else:
			_salvar_foto(c, n, foto_url)
	return c


def _foto_publica(numero: str) -> str | None:
	try:
		r = _evo("POST", f"/chat/fetchProfilePictureUrl/{_inst()}", json={"number": numero})
		import time

		time.sleep(0.15)
		if r.status_code < 400:
			j = r.json() or {}
			return j.get("profilePictureUrl") or j.get("profilePicUrl")
	except Exception:
		pass
	return None


def _salvar_foto(contato: str, numero: str, url: str | None = None) -> bool:
	"""Baixa a foto publica e guarda no sistema (o link do WhatsApp expira). Sem foto publica: so marca a data."""
	url = url or _foto_publica(numero)
	frappe.db.set_value("Contact", contato, "panda_foto_em", now_datetime(), update_modified=False)
	if not url or not url.startswith("http"):
		return False
	try:
		r = requests.get(url, timeout=15, stream=True)
		if r.status_code != 200 or not (r.headers.get("content-type", "").startswith("image/")):
			return False
		dados = r.raw.read(3 * 1024 * 1024 + 1, decode_content=True)
		if not dados or len(dados) > 3 * 1024 * 1024:
			return False
	except requests.RequestException:
		return False
	for antigo in frappe.get_all(
		"File", {"attached_to_doctype": "Contact", "attached_to_name": contato, "file_name": ["like", "wa-%"]}, pluck="name"
	):
		frappe.delete_doc("File", antigo, ignore_permissions=True, force=True)
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"wa-{numero}.jpg",
			"content": dados,
			"attached_to_doctype": "Contact",
			"attached_to_name": contato,
			"is_private": 0,
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value("Contact", contato, "image", f.file_url, update_modified=False)
	return True


def _participantes_mudaram(dados: dict):
	if str(dados.get("action", "")).lower() not in ("add", "invite", "promote", ""):
		return
	grupo = _nome_grupo(dados.get("id") or dados.get("groupJid") or "")
	for p in dados.get("participants") or []:
		jid = p if isinstance(p, str) else (p.get("phoneNumber") or p.get("id") or "")
		n = _jid_para_numero(jid)
		if n:
			_capturar_contato(n, None if isinstance(p, str) else p.get("name"), grupo=grupo, foto_async=True)


def _atualizar_contatos_evolution(lista: list):
	"""Nome e foto novos de quem ja esta cadastrado (nao cria contato aqui)."""
	from crm.panda import contatos as ct

	for c in lista:
		n = _jid_para_numero(c.get("remoteJid") or c.get("id") or "")
		if not n:
			continue
		existente = ct.achar_contato(n)
		if not existente:
			continue
		nome = (c.get("pushName") or c.get("name") or "").strip()
		if nome and _eh_placeholder(frappe.db.get_value("Contact", existente, "first_name")):
			frappe.db.set_value("Contact", existente, {"first_name": nome[:140], "last_name": ""}, update_modified=False)
		if not frappe.db.get_value("Contact", existente, "image") and c.get("profilePicUrl"):
			_salvar_foto(existente, n, c.get("profilePicUrl"))


# ---- importacao inicial: todos os participantes de todos os grupos
CHAVE_IMPORT = "panda_wa_import"


@frappe.whitelist(methods=["POST"])
def wa_importar_grupos():
	_admin()
	if _modo_cloud():
		frappe.throw(_("A importação de grupos só existe no modo Evolution API"))
	if (_cfg().wa_status or "") != "conectado":
		frappe.throw(_("Conecte o WhatsApp primeiro"))
	atual = frappe.cache.get_value(CHAVE_IMPORT) or {}
	if atual.get("estado") == "rodando":
		return atual
	estado = {"estado": "rodando", "grupos": 0, "grupos_total": 0, "criados": 0, "atualizados": 0, "sem_numero": 0, "fotos": 0}
	frappe.cache.set_value(CHAVE_IMPORT, estado)
	frappe.enqueue("crm.panda.chat._importar_grupos", queue="long", timeout=7200, enqueue_after_commit=True)
	return estado


@frappe.whitelist()
def wa_importar_status():
	_admin()
	return frappe.cache.get_value(CHAVE_IMPORT) or {"estado": "parado"}


def _importar_grupos():
	import time

	from crm.panda import contatos as ct

	est = frappe.cache.get_value(CHAVE_IMPORT) or {}
	try:
		r = _evo("GET", f"/group/fetchAllGroups/{_inst()}", params={"getParticipants": "true"})
		if r.status_code >= 400:
			raise RuntimeError(f"Evolution recusou ({r.status_code}): {r.text[:160]}")
		grupos = r.json() or []
		grupos = grupos if isinstance(grupos, list) else (grupos.get("groups") or [])
		est["grupos_total"] = len(grupos)
		# nomes e fotos que a propria Evolution ja conhece
		conhecidos = {}
		try:
			rc = _evo("POST", f"/chat/findContacts/{_inst()}", json={"where": {}})
			for c in rc.json() if rc.status_code < 400 else []:
				n = _jid_para_numero(c.get("remoteJid") or c.get("id") or "")
				if n:
					conhecidos[ct.telefone_normalizado(n)] = c
		except Exception:
			pass
		for g in grupos:
			assunto = g.get("subject") or "Grupo"
			for p in g.get("participants") or []:
				jid = p.get("phoneNumber") or p.get("id") or p.get("jid") or ""
				n = _jid_para_numero(jid)
				if not n:
					est["sem_numero"] += 1
					continue
				antes = ct.achar_contato(n)
				k = conhecidos.get(ct.telefone_normalizado(n)) or {}
				nome = k.get("pushName") or p.get("name") or p.get("notify")
				c = _capturar_contato(n, nome, grupo=assunto, foto_url=k.get("profilePicUrl"))
				est["atualizados" if antes else "criados"] += 1
			est["grupos"] += 1
			frappe.db.commit()
			frappe.cache.set_value(CHAVE_IMPORT, est)
			time.sleep(0.2)
		est["estado"] = "concluido"
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(title="Panda: importar grupos do WhatsApp")
		est["estado"] = "erro"
		est["erro"] = str(e)[:200]
	frappe.cache.set_value(CHAVE_IMPORT, est)


def atualizar_fotos():
	"""Diario: renova fotos (30+ dias) e tenta de novo quem ainda nao tem. Lote pequeno para nao sobrecarregar."""
	import time
	from datetime import timedelta

	if (_cfg().wa_status or "") != "conectado" or _modo_cloud():
		return
	from crm.panda import contatos as ct

	limite = now_datetime() - timedelta(days=30)
	cands = frappe.get_all(
		"Contact",
		{"panda_origem": ["like", "%WhatsApp%"], "panda_foto_em": ["<", limite]},
		["name"],
		order_by="panda_foto_em asc",
		limit_page_length=80,
	) + frappe.get_all(
		"Contact", {"panda_origem": ["like", "%WhatsApp%"], "panda_foto_em": ["is", "not set"]}, ["name"], limit_page_length=80
	)
	for c in cands[:100]:
		tel = frappe.db.get_value("Contact Phone", {"parent": c.name, "parenttype": "Contact"}, "phone")
		n = ct.telefone_normalizado(tel)
		if n:
			_salvar_foto(c.name, n)
			frappe.db.commit()
			time.sleep(0.5)


def avisar_numeros(texto: str) -> int:
	"""Aviso de reta final por WhatsApp para os numeros cadastrados em Conexoes."""
	numeros = [_digitos(n) for n in re.split(r"[,\n;]", _cfg().wa_notify_numbers or "") if _digitos(n)]
	if not numeros or (_cfg().wa_status or "") != "conectado":
		return 0
	enviados = 0
	for n in numeros:
		try:
			_enviar_whatsapp(n, texto)
			enviados += 1
		except Exception:
			frappe.log_error(title="Panda: aviso por WhatsApp falhou")
	return enviados


# ============================================================ Instagram / Meta
def _redirect_ig() -> str:
	return f"{get_url()}/api/method/crm.panda.chat.ig_callback"


@frappe.whitelist()
def ig_status():
	_admin()
	c = _cfg()
	return {
		"connected": bool(_pw("ig_page_token")),
		"username": c.ig_username or "",
		"redirect_uri": _redirect_ig(),
		"webhook_url": f"{get_url()}/api/method/crm.panda.chat.webhook_instagram",
		"verify_token_set": bool(_pw("meta_verify_token")),
	}


@frappe.whitelist(methods=["POST"])
def ig_save(app_id: str = "", app_secret: str = ""):
	_admin()
	c = _cfg()
	if app_id:
		c.meta_app_id = app_id.strip()
	if app_secret:
		c.meta_app_secret = app_secret.strip()
	if not _pw("meta_verify_token"):
		c.meta_verify_token = secrets.token_urlsafe(16)
	c.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def ig_verify_token():
	_admin()
	return _pw("meta_verify_token") or ""


@frappe.whitelist()
def ig_auth_url():
	_admin()
	c = _cfg()
	if not c.meta_app_id or not _pw("meta_app_secret"):
		frappe.throw(_("Preencha o App ID e o App Secret da Meta primeiro"))
	state = secrets.token_urlsafe(16)
	frappe.cache.set_value(f"panda_ig_state:{state}", frappe.session.user, expires_in_sec=600)
	escopos = "instagram_basic,instagram_manage_messages,pages_show_list,pages_manage_metadata,pages_messaging,business_management"
	return (
		f"https://www.facebook.com/v21.0/dialog/oauth?client_id={quote(c.meta_app_id)}"
		f"&redirect_uri={quote(_redirect_ig())}&state={state}&scope={escopos}&response_type=code"
	)


def _voltar(motivo: str | None = None):
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/crm?instagram=" + ("ok" if not motivo else "erro&motivo=" + quote(motivo))


@frappe.whitelist()
def ig_callback(code: str | None = None, state: str | None = None, error_description: str | None = None):
	_admin()
	if frappe.cache.get_value(f"panda_ig_state:{state}") != frappe.session.user or not code:
		return _voltar(error_description or "A autorização foi cancelada ou expirou.")
	c = _cfg()
	segredo = _pw("meta_app_secret")
	try:
		r = requests.get(
			f"{GRAPH}/oauth/access_token",
			params={"client_id": c.meta_app_id, "client_secret": segredo, "redirect_uri": _redirect_ig(), "code": code},
			timeout=30,
		).json()
		if "access_token" not in r:
			return _voltar((r.get("error") or {}).get("message", "A Meta não devolveu o token."))
		longo = requests.get(
			f"{GRAPH}/oauth/access_token",
			params={"grant_type": "fb_exchange_token", "client_id": c.meta_app_id, "client_secret": segredo, "fb_exchange_token": r["access_token"]},
			timeout=30,
		).json()
		token = longo.get("access_token", r["access_token"])
		paginas = requests.get(
			f"{GRAPH}/me/accounts",
			params={"fields": "name,access_token,instagram_business_account{id,username}", "access_token": token},
			timeout=30,
		).json()
	except requests.RequestException as e:
		return _voltar(f"Falha de rede ao falar com a Meta: {str(e)[:120]}")
	pagina = next((p for p in paginas.get("data", []) if p.get("instagram_business_account")), None)
	if not pagina:
		return _voltar("Nenhuma página do Facebook com conta Instagram Business/Creator foi encontrada. Ligue o Instagram a uma página e tente de novo.")
	try:
		requests.post(
			f"{GRAPH}/{pagina['id']}/subscribed_apps",
			params={"subscribed_fields": "messages", "access_token": pagina["access_token"]},
			timeout=30,
		)
	except requests.RequestException:
		pass
	ig = pagina["instagram_business_account"]
	c.ig_page_token = pagina["access_token"]
	c.ig_user_id = ig["id"]
	c.ig_username = ig.get("username", "")
	c.save(ignore_permissions=True)
	_voltar()


@frappe.whitelist(methods=["POST"])
def ig_disconnect():
	_admin()
	c = _cfg()
	c.ig_page_token = ""
	c.ig_user_id = ""
	c.ig_username = ""
	c.save(ignore_permissions=True)
	return True


def _enviar_instagram(destino: str, texto: str) -> str | None:
	c = _cfg()
	tok = _pw("ig_page_token")
	if not tok or not c.ig_user_id:
		raise RuntimeError("Instagram não conectado")
	r = requests.post(
		f"{GRAPH}/{c.ig_user_id}/messages",
		params={"access_token": tok},
		json={"recipient": {"id": destino}, "message": {"text": texto}},
		timeout=30,
	)
	if r.status_code >= 400:
		msg = ((r.json() or {}).get("error") or {}).get("message", r.text[:120])
		raise RuntimeError(f"Instagram não enviou: {msg}")
	return (r.json() or {}).get("message_id")


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=600, seconds=60)
def webhook_instagram():
	req = frappe.request
	if req.method == "GET":  # verificacao do webhook pela Meta
		esperado = _pw("meta_verify_token")
		if req.args.get("hub.verify_token") and esperado and hmac.compare_digest(req.args["hub.verify_token"], esperado):
			frappe.response["type"] = "download"
			frappe.response["filename"] = "challenge.txt"
			frappe.response["filecontent"] = (req.args.get("hub.challenge") or "").encode()
			frappe.response["display_content_as"] = "inline"
			return
		frappe.throw(_("Token inválido"), frappe.PermissionError)
	bruto = req.get_data()
	segredo = _pw("meta_app_secret") or ""
	assinatura = (req.headers.get("X-Hub-Signature-256") or "").replace("sha256=", "")
	esperado = hmac.new(segredo.encode(), bruto, hashlib.sha256).hexdigest()
	if not segredo or not hmac.compare_digest(assinatura, esperado):
		frappe.throw(_("Assinatura inválida"), frappe.PermissionError)
	corpo = json.loads(bruto or b"{}")
	meu_id = _cfg().ig_user_id
	for entrada in corpo.get("entry", []):
		for ev in entrada.get("messaging", []):
			msg = ev.get("message") or {}
			if not msg:
				continue
			eco = bool(msg.get("is_echo"))
			outro = (ev.get("recipient") or {}).get("id") if eco else (ev.get("sender") or {}).get("id")
			if not outro or outro == meu_id:
				continue
			conv = _conversa("Instagram", outro, f"Instagram {outro[-6:]}")
			_registrar(conv, "Out" if eco else "In", msg.get("text") or "[mídia]", ext_id=msg.get("mid"))
	frappe.db.commit()
	return "ok"


@frappe.whitelist()
def contacts_for_pick():
	"""Opcoes para escolher o WhatsApp de um fornecedor: contatos do programa + contatos do WhatsApp conectado."""
	_interno()
	out, vistos = [], set()
	for p in frappe.get_all("Contact Phone", {"parenttype": "Contact"}, ["parent", "phone"], limit_page_length=0):
		d = _digitos(p.phone)
		if len(d) >= 8 and d not in vistos:
			vistos.add(d)
			out.append({"name": frappe.db.get_value("Contact", p.parent, "full_name") or p.parent, "number": d})
	try:
		if (_cfg().wa_status or "") == "conectado" and not _modo_cloud():
			r = _evo("POST", f"/chat/findContacts/{_inst()}", json={"where": {}})
			for c in r.json() if r.status_code < 400 else []:
				jid = c.get("remoteJid") or c.get("id") or ""
				if jid.endswith("@s.whatsapp.net"):
					d = jid.split("@")[0]
					if d not in vistos:
						vistos.add(d)
						out.append({"name": c.get("pushName") or d, "number": d})
	except Exception:
		pass
	return sorted(out, key=lambda x: (x["name"] or "").lower())


@frappe.whitelist()
def channel_status(channel: str):
	"""Estado simples do canal para a tela de conversas (qualquer usuario interno)."""
	_interno()
	c = _cfg()
	admin = frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()
	if channel == "WhatsApp":
		cloud = _modo_cloud()
		return {
			"connected": (c.wa_status or "") == "conectado",
			"configured": bool(c.wa_cloud_phone_id and _pw("wa_cloud_token")) if cloud else bool(c.evo_url and _pw("evo_key")),
			"is_admin": admin,
			"mode": "cloud" if cloud else "evolution",
		}
	return {"connected": bool(_pw("ig_page_token")), "configured": bool(c.meta_app_id and _pw("meta_app_secret")), "is_admin": admin}


# ============================================================ WhatsApp oficial (Meta Cloud API)
# Alternativa sem QR Code: o numero e registrado na Meta (verificacao por SMS/ligacao) e o
# programa fala direto com a API oficial. Mensagem livre so dentro de 24h apos o contato escrever.
def _cloud_req(metodo: str, caminho: str, **kw):
	tok = _pw("wa_cloud_token")
	if not tok:
		raise RuntimeError("Preencha o token do WhatsApp Cloud em Conexões")
	return requests.request(metodo, f"{GRAPH}{caminho}", headers={"Authorization": f"Bearer {tok}"}, timeout=30, **kw)


def _erro_meta(r) -> str:
	try:
		e = r.json().get("error", {})
	except Exception:
		return r.text[:120]
	if e.get("code") == 131047:
		return "Passaram mais de 24h desde a última mensagem do contato. O WhatsApp só permite mensagem livre dentro de 24h (depois, só modelo aprovado)."
	if e.get("code") in (190, 102):
		return "Token inválido ou vencido. Gere um token permanente (usuário do sistema) na Meta."
	return e.get("message") or r.text[:120]


def _enviar_cloud(numero: str, texto: str) -> str | None:
	pid = _cfg().wa_cloud_phone_id
	if not pid:
		raise RuntimeError("Preencha o ID do número do WhatsApp Cloud em Conexões")
	r = _cloud_req(
		"POST", f"/{pid}/messages", json={"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": texto}}
	)
	if r.status_code >= 400:
		raise RuntimeError(_erro_meta(r))
	return ((r.json() or {}).get("messages") or [{}])[0].get("id")


def _cloud_verificar(silencioso: bool = False) -> str:
	c = _cfg()
	try:
		r = _cloud_req("GET", f"/{c.wa_cloud_phone_id}", params={"fields": "display_phone_number,verified_name"})
	except Exception as e:
		if silencioso:
			return c.wa_status or "desconectado"
		raise
	if r.status_code >= 400:
		_set_status("desconectado")
		if silencioso:
			return "desconectado"
		frappe.throw(_erro_meta(r))
	frappe.db.set_value(DOC, DOC, "wa_cloud_display", (r.json() or {}).get("display_phone_number", ""))
	_set_status("conectado")
	return "conectado"


@frappe.whitelist(methods=["POST"])
def wa_cloud_save(phone_id: str = "", token: str = ""):
	_admin()
	c = _cfg()
	c.wa_mode = "Cloud API"
	if phone_id:
		c.wa_cloud_phone_id = re.sub(r"\D", "", phone_id)
	if token:
		c.wa_cloud_token = token.strip()
	if not _pw("meta_verify_token"):
		c.meta_verify_token = secrets.token_urlsafe(16)
	c.save(ignore_permissions=True)
	return True


@frappe.whitelist(methods=["POST"])
def wa_cloud_connect():
	"""Confere o ID e o token com a Meta e marca o WhatsApp como conectado."""
	_admin()
	if not _cfg().wa_cloud_phone_id:
		frappe.throw(_("Informe o ID do número do WhatsApp Cloud"))
	try:
		return {"status": _cloud_verificar(), "number": _cfg().wa_cloud_display}
	except RuntimeError as e:
		frappe.throw(str(e))
	except requests.RequestException as e:
		frappe.throw(_("Não foi possível falar com a Meta: {0}").format(str(e)[:120]))


@frappe.whitelist()
def wa_cloud_info():
	_admin()
	c = _cfg()
	return {
		"webhook_url": f"{get_url()}/api/method/crm.panda.chat.webhook_whatsapp_cloud",
		"verify_token": _pw("meta_verify_token") or "",
		"display": c.wa_cloud_display or "",
	}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=600, seconds=60)
def webhook_whatsapp_cloud():
	req = frappe.request
	if req.method == "GET":  # verificacao do webhook pela Meta
		esperado = _pw("meta_verify_token")
		tok = req.args.get("hub.verify_token")
		if tok and esperado and hmac.compare_digest(tok, esperado):
			frappe.response["type"] = "download"
			frappe.response["filename"] = "challenge.txt"
			frappe.response["filecontent"] = (req.args.get("hub.challenge") or "").encode()
			frappe.response["display_content_as"] = "inline"
			return
		frappe.throw(_("Token inválido"), frappe.PermissionError)
	bruto = req.get_data()
	segredo = _pw("meta_app_secret") or ""
	assinatura = (req.headers.get("X-Hub-Signature-256") or "").replace("sha256=", "")
	esperado = hmac.new(segredo.encode(), bruto, hashlib.sha256).hexdigest()
	if not segredo or not hmac.compare_digest(assinatura, esperado):
		frappe.throw(_("Assinatura inválida"), frappe.PermissionError)
	corpo = json.loads(bruto or b"{}")
	for ent in corpo.get("entry", []):
		for ch in ent.get("changes", []):
			v = ch.get("value") or {}
			nomes = {c.get("wa_id"): (c.get("profile") or {}).get("name") for c in v.get("contacts", [])}
			for m in v.get("messages", []):
				de = m.get("from")
				if not de:
					continue
				texto = (m.get("text") or {}).get("body") or (m.get("button") or {}).get("text") or "[mídia]"
				conv = _conversa("WhatsApp", f"{de}@s.whatsapp.net", nomes.get(de), de)
				_registrar(conv, "In", texto, ext_id=m.get("id"))
	frappe.db.commit()
	return "ok"


# ============================================================ WhatsApp (Evolution): diagnostico e busca ativa
# O webhook so funciona se a Evolution consegue abrir o endereco do programa. Em ambiente local
# (localhost) isso nao acontece; por isso tambem buscamos as mensagens direto na Evolution.
@frappe.whitelist(methods=["POST"])
def wa_set_webhook():
	_admin()
	hook = _webhook_url()
	try:
		r = _evo(
			"POST",
			f"/webhook/set/{_inst()}",
			json={"webhook": {"enabled": True, "url": hook, "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE", "QRCODE_UPDATED", "GROUP_PARTICIPANTS_UPDATE", "GROUPS_UPSERT", "CONTACTS_UPSERT", "CONTACTS_UPDATE"], "byEvents": False}},
		)
	except RuntimeError as e:
		frappe.throw(str(e))
	except requests.RequestException as e:
		frappe.throw(_("Não foi possível falar com a Evolution API: {0}").format(str(e)[:160]))
	if r.status_code >= 400:
		frappe.throw(_("A Evolution API recusou: {0}").format(r.text[:200]))
	return hook


@frappe.whitelist()
def wa_diagnose():
	_admin()
	esperado = _webhook_url()
	local = any(x in esperado for x in ("localhost", "127.0.0.1", "0.0.0.0", ".local"))
	out = {"expected": esperado, "local": local, "at_evolution": None, "enabled": None}
	try:
		r = _evo("GET", f"/webhook/find/{_inst()}")
		if r.status_code < 400:
			j = r.json() or {}
			out["at_evolution"] = j.get("url") or (j.get("webhook") or {}).get("url")
			out["enabled"] = j.get("enabled") if "enabled" in j else (j.get("webhook") or {}).get("enabled")
	except Exception:
		pass
	return out


def _importar_registros(registros) -> int:
	novos = 0
	for m in registros:
		chave = m.get("key") or {}
		jid = chave.get("remoteJid") or ""
		if not jid.endswith("@s.whatsapp.net") or not chave.get("id"):
			continue
		if frappe.db.exists(MSG, {"external_id": chave["id"]}):
			continue
		msg = m.get("message") or {}
		texto = (
			msg.get("conversation")
			or (msg.get("extendedTextMessage") or {}).get("text")
			or (msg.get("imageMessage") or {}).get("caption")
			or "[mídia]"
		)
		de_mim = bool(chave.get("fromMe"))
		quando = None
		ts = m.get("messageTimestamp")
		try:
			from datetime import datetime

			quando = datetime.fromtimestamp(int(ts)) if ts else None
		except Exception:
			quando = None
		conv = _conversa("WhatsApp", jid, None if de_mim else m.get("pushName"), jid.split("@")[0])
		if _registrar(conv, "Out" if de_mim else "In", texto, ext_id=chave["id"], status="Sent" if de_mim else "Received", quando=quando):
			novos += 1
	return novos


def _buscar_evolution() -> int:
	r = _evo("POST", f"/chat/findMessages/{_inst()}", json={"where": {}, "page": 1, "offset": 100})
	if r.status_code >= 400:
		raise RuntimeError(f"A Evolution não listou as mensagens ({r.status_code})")
	j = r.json()
	if isinstance(j, dict):
		j = (j.get("messages") or {}).get("records") or j.get("records") or j.get("messages") or []
	return _importar_registros(j if isinstance(j, list) else [])


@frappe.whitelist(methods=["POST"])
def wa_sync():
	"""Busca as mensagens recentes direto na Evolution (nao depende do webhook)."""
	_interno()
	if _modo_cloud() or (_cfg().wa_status or "") != "conectado":
		return {"new": 0}
	try:
		novos = _buscar_evolution()
	except RuntimeError as e:
		frappe.throw(str(e))
	except requests.RequestException as e:
		frappe.throw(_("Não foi possível falar com a Evolution API: {0}").format(str(e)[:160]))
	frappe.db.commit()
	return {"new": novos}


def sincronizar_whatsapp():
	"""Agendador: mantem as conversas em dia mesmo sem webhook."""
	try:
		if not _modo_cloud() and (_cfg().wa_status or "") == "conectado" and _cfg().evo_url:
			_buscar_evolution()
			frappe.db.commit()
	except Exception:
		frappe.log_error(title="Panda: sincronizacao do WhatsApp falhou")
