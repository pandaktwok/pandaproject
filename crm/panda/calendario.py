"""Calendario unificado (Panda Project, fase 8).

- Compromissos: doctype "Event" do Frappe. A sincronizacao com o Google nos dois sentidos e do proprio
  Frappe (doctype "Google Calendar", uma conexao por usuario); aqui so conectamos, mostramos e criamos.
- Camadas internas (so no programa): tarefas com prazo, parcelas nao pagas e fim (reta final) dos projetos.
- Regras de conflito (calculadas ao vivo; o alerta some sozinho quando o conflito some):
  1. mesmo nome e mesmo horario em calendarios diferentes -> mostra uma vez so
  2. mesmo horario, nome diferente -> dia inteiro em vermelho + alerta nos compromissos
  3. mesmo nome, horario diferente (no mesmo dia) -> faixa amarela + triangulo
  4. apenas sobrepostos -> nada
  Compromissos de dia inteiro nao entram nas regras 2 e 3.
"""
from datetime import datetime

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate


def _s(dt) -> str:
	return get_datetime(dt).strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def _norm(t: str) -> str:
	return " ".join((t or "").lower().split())


def _google_ok() -> bool:
	return bool(frappe.db.get_single_value("Google Settings", "enable"))


@frappe.whitelist()
def get_state():
	cals = frappe.get_all(
		"Google Calendar",
		{"user": frappe.session.user},
		["name", "calendar_name", "enable", "pull_from_google_calendar", "push_to_google_calendar", "google_calendar_id"],
	)
	return {
		"google_enabled": _google_ok(),
		"calendars": [{**c, "authorized": bool(c.google_calendar_id)} for c in cals],
	}


@frappe.whitelist(methods=["POST"])
def connect(calendar_name: str):
	"""Cria a conexao do usuario com o Google Calendar e devolve o link de autorizacao."""
	if not _google_ok():
		frappe.throw(_("Peça a um administrador para configurar a chave do Google em Conexões"))
	calendar_name = (calendar_name or "").strip() or frappe.session.user
	doc = frappe.get_doc(
		{
			"doctype": "Google Calendar",
			"calendar_name": calendar_name,
			"user": frappe.session.user,
			"enable": 1,
			"pull_from_google_calendar": 1,
			"push_to_google_calendar": 1,
		}
	).insert(ignore_permissions=True)
	from frappe.integrations.doctype.google_calendar.google_calendar import authorize_access

	res = authorize_access(doc.name)
	url = res.get("url") if isinstance(res, dict) else res
	return {"name": doc.name, "url": url}


@frappe.whitelist(methods=["POST"])
def reauthorize(name: str):
	_dono(name)
	from frappe.integrations.doctype.google_calendar.google_calendar import authorize_access

	res = authorize_access(name, reauthorize=True)
	return {"url": res.get("url") if isinstance(res, dict) else res}


def _dono(name: str):
	if frappe.db.get_value("Google Calendar", name, "user") != frappe.session.user:
		frappe.throw(_("Sem permissão"), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def disconnect(name: str):
	_dono(name)
	frappe.delete_doc("Google Calendar", name, ignore_permissions=True)
	return True


@frappe.whitelist(methods=["POST"])
def sync_now():
	from frappe.integrations.doctype.google_calendar.google_calendar import sync

	for c in frappe.get_all("Google Calendar", {"user": frappe.session.user, "enable": 1}, pluck="name"):
		sync(c)
	return True


@frappe.whitelist()
def get_events(start: str, end: str):
	"""Tudo que aparece na tela, no intervalo [start, end] (AAAA-MM-DD)."""
	from frappe.desk.doctype.event.event import get_events as frappe_get_events

	ini, fim = str(getdate(start)), str(getdate(end))
	itens = []

	# ---- compromissos (Google + programa)
	brutos = frappe_get_events(ini, fim + " 23:59:59", frappe.session.user) or []
	nomes = list({e["name"] for e in brutos})
	meta = {
		r.name: r
		for r in frappe.get_all("Event", {"name": ["in", nomes or [""]]}, ["name", "google_calendar"])
	}
	cal_nome = {
		c.name: c.calendar_name for c in frappe.get_all("Google Calendar", fields=["name", "calendar_name"])
	}
	vistos = {}
	for e in brutos:
		origem = cal_nome.get(getattr(meta.get(e["name"]), "google_calendar", None), "Programa")
		item = {
			"id": e["name"],
			"kind": "event",
			"title": e.get("subject") or "",
			"start": _s(e["starts_on"]),
			"end": _s(e.get("ends_on")),
			"all_day": bool(e.get("all_day")),
			"origins": [origem],
			"conflict": "",
		}
		chave = (_norm(item["title"]), item["start"], item["end"])
		if chave in vistos and not item["all_day"]:  # regra 1: mesmo nome e horario -> uma vez so
			if origem not in vistos[chave]["origins"]:
				vistos[chave]["origins"].append(origem)
			continue
		vistos[chave] = item
		itens.append(item)

	dias = {}
	por_dia = {}
	for it in itens:
		if not it["all_day"]:
			por_dia.setdefault(it["start"][:10], []).append(it)
	for dia, lista in por_dia.items():
		for a in lista:
			for b in lista:
				if a is b:
					continue
				mesmo_horario = a["start"] == b["start"] and a["end"] == b["end"]
				mesmo_nome = _norm(a["title"]) == _norm(b["title"])
				if mesmo_horario and not mesmo_nome:  # regra 2
					a["conflict"] = "time"
					dias[dia] = "red"
				elif mesmo_nome and not mesmo_horario and a["conflict"] != "time":  # regra 3
					a["conflict"] = "name"
					dias.setdefault(dia, "yellow")

	# ---- camadas internas
	visiveis = set(frappe.get_list("CRM Deal", pluck="name", limit_page_length=0))
	nome_deal = {
		d.name: d.project_name or d.organization or d.name
		for d in frappe.get_all(
			"CRM Deal", {"name": ["in", list(visiveis) or [""]]}, ["name", "project_name", "organization"]
		)
	}
	for t in frappe.get_list(
		"CRM Task",
		filters={"status": ["not in", ["Done", "Canceled"]], "due_date": ["between", [ini, fim + " 23:59:59"]]},
		fields=["name", "title", "due_date", "reference_docname", "reference_doctype"],
		limit_page_length=0,
	):
		itens.append(
			{
				"id": t.name,
				"kind": "task",
				"title": t.title,
				"start": _s(t.due_date),
				"end": "",
				"all_day": False,
				"origins": ["Tarefa"],
				"conflict": "",
				"deal": t.reference_docname if t.reference_doctype == "CRM Deal" else None,
			}
		)
	parcelas = frappe.get_all(
		"CRM Payment Installment",
		{"paid": 0, "parenttype": "CRM Payment Line", "due_date": ["between", [ini, fim]]},
		["parent", "number", "due_date", "expected_value"],
	)
	linhas = {
		l.name: l
		for l in frappe.get_all(
			"CRM Payment Line", {"name": ["in", list({p.parent for p in parcelas}) or [""]]}, ["name", "deal", "supplier"]
		)
	}
	for p in parcelas:
		l = linhas.get(p.parent)
		if not l or l.deal not in visiveis:
			continue
		itens.append(
			{
				"id": f"{p.parent}:{p.number}",
				"kind": "payment",
				"title": f"{l.supplier} — parcela {p.number} (R$ {p.expected_value:,.2f})",
				"start": _s(p.due_date)[:10] + " 00:00:00",
				"end": "",
				"all_day": True,
				"origins": ["Pagamento"],
				"conflict": "",
				"deal": l.deal,
			}
		)
	abertos = frappe.get_all("CRM Deal Status", {"type": ["not in", ["Won", "Lost"]]}, pluck="name")
	for d in frappe.get_all(
		"CRM Deal",
		{"name": ["in", list(visiveis) or [""]], "status": ["in", abertos], "expected_closure_date": ["between", [ini, fim]]},
		["name", "expected_closure_date"],
	):
		itens.append(
			{
				"id": d.name,
				"kind": "end",
				"title": f"Fim do projeto: {nome_deal.get(d.name, d.name)}",
				"start": _s(d.expected_closure_date)[:10] + " 00:00:00",
				"end": "",
				"all_day": True,
				"origins": ["Reta final"],
				"conflict": "",
				"deal": d.name,
			}
		)
	itens.sort(key=lambda i: i["start"])
	return {"items": itens, "days": dias}


@frappe.whitelist(methods=["POST"])
def create_event(
	title: str,
	starts_on: str,
	ends_on: str | None = None,
	all_day=0,
	calendar: str | None = None,
	meet=0,
	description: str | None = None,
):
	"""calendar vazio = so no programa; senao o nome da conexao Google Calendar do usuario."""
	title = (title or "").strip()
	if not title:
		frappe.throw(_("O título é obrigatório"))
	if calendar:
		_dono(calendar)
	doc = frappe.get_doc(
		{
			"doctype": "Event",
			"subject": title,
			"starts_on": starts_on,
			"ends_on": ends_on or starts_on,
			"all_day": 1 if int(all_day) else 0,
			"event_type": "Private",
			"description": description or "",
			"sync_with_google_calendar": 1 if calendar else 0,
			"google_calendar": calendar or None,
			"add_video_conferencing": 1 if (calendar and int(meet)) else 0,
		}
	)
	doc.insert()
	return doc.name


@frappe.whitelist(methods=["POST"])
def delete_event(name: str):
	doc = frappe.get_doc("Event", name)
	if not doc.has_permission("delete"):
		frappe.throw(_("Sem permissão"), frappe.PermissionError)
	frappe.delete_doc("Event", name)
	return True
