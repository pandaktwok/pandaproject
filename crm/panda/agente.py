"""Agente de IA do Panda Project (Fase 10) - assistente SO DE AJUDA.

Regras (nao negociaveis na V2.0):
- Nao le NENHUM dado do programa (projetos, contatos, pagamentos...). Recebe apenas a pergunta,
  o historico da conversa e trechos dos documentos de ajuda em crm/panda/ajuda/*.md.
- Nenhuma ferramenta (nem do MCP) devolve dados do programa.
- Niveis de permissao: ajuda = ligado; ler dados = desligado; agir = V2.1.
"""
import hmac
import json
import re
from pathlib import Path

import frappe
import requests
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils.password import get_decrypted_password

DOC = "Panda Integrations"
MSGS = "CRM AI Message"
AJUDA = Path(__file__).parent / "ajuda"
PROVEDORES = ("OpenAI", "Claude", "Gemini")

PROMPT = """Você é o Agente de IA do Panda Project, um assistente SOMENTE DE AJUDA.
Responda sempre em português do Brasil, de forma curta e prática.
Você NÃO tem acesso a nenhum dado do programa (projetos, contatos, valores, e-mails). Se a pessoa pedir isso,
explique que só pode ensinar a usar o programa.
Use APENAS os trechos de ajuda abaixo. Se não houver resposta neles, diga que não sabe e sugira a pessoa procurar o administrador.
Quando indicar uma tela, escreva o caminho (ex.: Configurações > Conexões) e acrescente, em linha própria, o marcador
[[abrir:/caminho|Texto do botão]] usando só os caminhos listados nos trechos.
Quando entregar um texto pronto para copiar (mensagem, e-mail), coloque-o entre <<<texto e >>> para o programa mostrar o botão Copiar.

TRECHOS DE AJUDA:
{docs}
"""


def _pw(c):
	return get_decrypted_password(DOC, DOC, c, raise_exception=False)


def _interno():
	if frappe.session.user == "Guest":
		frappe.throw(_("Sem permissão"), frappe.PermissionError)


def _admin():
	if not (frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()):
		frappe.throw(_("Somente administradores"), frappe.PermissionError)


# ---------------------------------------------------------------- ajuda (base de consulta)
def _docs():
	out = []
	for f in sorted(AJUDA.glob("*.md")):
		txt = f.read_text(encoding="utf-8")
		titulo = (re.match(r"#\s*(.+)", txt) or [None, f.stem])[1]
		out.append({"id": f.stem, "titulo": titulo.strip(), "texto": txt})
	return out


def _tokens(s: str):
	return {w for w in re.findall(r"\w{3,}", (s or "").lower())}


def buscar_ajuda(pergunta: str, n: int = 3):
	q = _tokens(pergunta)
	pont = []
	for d in _docs():
		alvo = _tokens(d["titulo"]) | _tokens(d["texto"])
		peso = len(q & _tokens(d["titulo"])) * 3 + len(q & alvo)
		if peso:
			pont.append((peso, d))
	pont.sort(key=lambda x: -x[0])
	return [d for _p, d in pont[:n]]


# ---------------------------------------------------------------- configuracao
@frappe.whitelist()
def get_config():
	_admin()
	c = frappe.get_single(DOC)
	return {
		"provider": c.ai_provider or "OpenAI",
		"base_url": c.ai_base_url or "",
		"model": c.ai_model or "",
		"key_set": bool(_pw("ai_api_key")),
		"mcp_token_set": bool(_pw("mcp_token")),
		"mcp_url": f"{frappe.utils.get_url()}/api/method/crm.panda.agente.mcp",
		"levels": {"help": True, "read_data": False, "actions": False},
	}


@frappe.whitelist(methods=["POST"])
def save_config(provider: str, base_url: str = "", model: str = "", api_key: str = ""):
	_admin()
	if provider not in PROVEDORES:
		frappe.throw(_("Provedor inválido"))
	c = frappe.get_single(DOC)
	c.ai_provider, c.ai_base_url, c.ai_model = provider, base_url.strip(), model.strip()
	if api_key:
		c.ai_api_key = api_key.strip()
	c.save(ignore_permissions=True)
	return True


@frappe.whitelist(methods=["POST"])
def generate_mcp_token():
	_admin()
	import secrets

	t = secrets.token_urlsafe(32)
	c = frappe.get_single(DOC)
	c.mcp_token = t
	c.save(ignore_permissions=True)
	return t  # mostrado uma unica vez


@frappe.whitelist()
def available():
	_interno()
	return bool(_pw("ai_api_key"))


# ---------------------------------------------------------------- provedores
def _chamar(sistema: str, historico: list[dict]) -> str:
	c = frappe.get_single(DOC)
	chave = _pw("ai_api_key")
	if not chave:
		frappe.throw(_("O Agente de IA ainda não foi configurado (Configurações > Agente de IA)"))
	prov, modelo = c.ai_provider or "OpenAI", c.ai_model
	if not modelo:
		frappe.throw(_("Informe o modelo em Configurações > Agente de IA"))
	try:
		if prov == "Claude":
			r = requests.post(
				(c.ai_base_url or "https://api.anthropic.com").rstrip("/") + "/v1/messages",
				headers={"x-api-key": chave, "anthropic-version": "2023-06-01"},
				json={"model": modelo, "max_tokens": 1024, "system": sistema, "messages": historico},
				timeout=60,
			)
			_ok(r)
			return "".join(b.get("text", "") for b in r.json().get("content", []))
		if prov == "Gemini":
			base = (c.ai_base_url or "https://generativelanguage.googleapis.com").rstrip("/")
			r = requests.post(
				f"{base}/v1beta/models/{modelo}:generateContent",
				headers={"x-goog-api-key": chave},
				json={
					"systemInstruction": {"parts": [{"text": sistema}]},
					"contents": [
						{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in historico
					],
				},
				timeout=60,
			)
			_ok(r)
			return "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])
		base = (c.ai_base_url or "https://api.openai.com/v1").rstrip("/")  # compativel com OpenAI
		r = requests.post(
			base + "/chat/completions",
			headers={"Authorization": f"Bearer {chave}"},
			json={"model": modelo, "messages": [{"role": "system", "content": sistema}, *historico]},
			timeout=60,
		)
		_ok(r)
		return r.json()["choices"][0]["message"]["content"]
	except requests.RequestException as e:
		frappe.throw(_("Não consegui falar com o provedor de IA: {0}").format(str(e)[:140]))


def _ok(r):
	if r.status_code >= 400:
		frappe.throw(_("O provedor de IA recusou o pedido ({0}). Confira a chave, o modelo e o endereço.").format(r.status_code))


@frappe.whitelist(methods=["POST"])
def test_connection():
	_admin()
	return _chamar("Responda apenas: ok", [{"role": "user", "content": "teste"}])[:60]


# ---------------------------------------------------------------- conversa
@frappe.whitelist()
@rate_limit(limit=30, seconds=60)
def history():
	_interno()
	return frappe.get_all(
		MSGS, {"user": frappe.session.user}, ["name", "role", "content", "creation"], order_by="creation asc", limit_page_length=100
	)


@frappe.whitelist(methods=["POST"])
def clear_history():
	_interno()
	for n in frappe.get_all(MSGS, {"user": frappe.session.user}, pluck="name"):
		frappe.delete_doc(MSGS, n, ignore_permissions=True, force=True)
	return True


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=20, seconds=60)
def ask(question: str):
	_interno()
	question = (question or "").strip()[:2000]
	if not question:
		frappe.throw(_("Escreva sua pergunta"))
	prev = frappe.get_all(
		MSGS, {"user": frappe.session.user}, ["role", "content"], order_by="creation desc", limit_page_length=8
	)[::-1]
	trechos = buscar_ajuda(question + " " + " ".join(p.content for p in prev[-2:] if p.role == "user"))
	docs = "\n\n---\n\n".join(d["texto"] for d in trechos) or "(nenhum trecho encontrado)"
	hist = [{"role": p.role, "content": p.content} for p in prev] + [{"role": "user", "content": question}]
	resposta = _chamar(PROMPT.format(docs=docs), hist)
	for papel, txt in (("user", question), ("assistant", resposta)):
		frappe.get_doc({"doctype": MSGS, "user": frappe.session.user, "role": papel, "content": txt}).insert(ignore_permissions=True)
	return resposta


# ---------------------------------------------------------------- MCP (so ajuda)
FERRAMENTAS = [
	{
		"name": "buscar_ajuda",
		"description": "Procura nos documentos de ajuda do Panda Project. Não devolve dados do programa.",
		"inputSchema": {"type": "object", "properties": {"pergunta": {"type": "string"}}, "required": ["pergunta"]},
	},
	{
		"name": "listar_ajuda",
		"description": "Lista os temas de ajuda disponíveis.",
		"inputSchema": {"type": "object", "properties": {}},
	},
]


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=120, seconds=60)
def mcp():
	"""MCP minimo sobre HTTP (JSON-RPC). Autenticado por 'Authorization: Bearer <mcp_token>'."""
	esperado = _pw("mcp_token")
	enviado = (frappe.request.headers.get("Authorization") or "").replace("Bearer ", "")
	if not esperado or not hmac.compare_digest(enviado, esperado):
		frappe.throw(_("Token inválido"), frappe.PermissionError)
	req = frappe.request.get_json(silent=True) or {}
	metodo, rid, p = req.get("method"), req.get("id"), req.get("params") or {}
	if rid is None:  # notificacao
		return
	if metodo == "initialize":
		res = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "panda-ajuda", "version": "2.0"}}
	elif metodo == "tools/list":
		res = {"tools": FERRAMENTAS}
	elif metodo == "tools/call":
		nome, args = p.get("name"), p.get("arguments") or {}
		if nome == "buscar_ajuda":
			txt = "\n\n---\n\n".join(d["texto"] for d in buscar_ajuda(args.get("pergunta", ""))) or "Nada encontrado."
		elif nome == "listar_ajuda":
			txt = "\n".join(f"- {d['titulo']}" for d in _docs())
		else:
			frappe.local.response.update({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "ferramenta desconhecida"}})
			return
		res = {"content": [{"type": "text", "text": txt}]}
	else:
		frappe.local.response.update({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "método desconhecido"}})
		return
	frappe.local.response.update({"jsonrpc": "2.0", "id": rid, "result": res})
