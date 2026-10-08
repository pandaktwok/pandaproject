"""API do financeiro do projeto (Panda Project): etiquetas, linhas e parcelas."""
import frappe
from frappe import _
from frappe.utils import getdate

from crm.panda import calc


def _check(deal: str, perm: str = "write"):
	if not frappe.has_permission("CRM Deal", perm, deal):
		frappe.throw(_("Sem permissão neste projeto"), frappe.PermissionError)


def _linha_para_parcelas(line) -> list[dict]:
	return [
		{
			"number": p.number,
			"due_date": p.due_date,
			"expected_cents": calc.to_cents(p.expected_value),
			"paid": bool(p.paid),
			"paid_cents": calc.to_cents(p.paid_value) if p.paid else 0,
			"paid_on": p.paid_on,
		}
		for p in line.installments
	]


def _gravar_parcelas(line, parcelas: list[dict], total_cents: int):
	por_numero = {p["number"]: p for p in parcelas}
	for row in line.installments:
		p = por_numero[row.number]
		row.expected_value = calc.from_cents(p["expected_cents"])
		row.paid = 1 if p["paid"] else 0
		row.paid_value = calc.from_cents(p["paid_cents"]) if p["paid"] else 0
		row.paid_on = p.get("paid_on") if p["paid"] else None
	s = calc.summary(parcelas)
	line.total = calc.from_cents(total_cents)
	line.paid_total = calc.from_cents(s["paid"])
	line.remaining = calc.from_cents(s["remaining"])


def atualizar_totais_do_projeto(deal: str):
	linhas = frappe.get_all("CRM Payment Line", {"deal": deal}, ["total", "remaining"])
	if linhas:
		total = sum(calc.to_cents(l.total) for l in linhas)
		restante = sum(calc.to_cents(l.remaining) for l in linhas)
		frappe.db.set_value(
			"CRM Deal",
			deal,
			{"finance_total": calc.from_cents(total), "finance_remaining": calc.from_cents(restante)},
			update_modified=False,
		)
	else:
		valor = frappe.db.get_value("CRM Deal", deal, "deal_value") or 0
		frappe.db.set_value(
			"CRM Deal", deal, {"finance_total": valor, "finance_remaining": valor}, update_modified=False
		)


def _dados_fornecedor(nome, telefone, email, documento, contato) -> dict:
	"""Liga o fornecedor a Contatos (acha ou cria com origem Fornecedor) e devolve os campos da linha."""
	from crm.panda.contatos import telefone_normalizado, vincular_fornecedor

	email = (email or "").strip().lower()
	documento = (documento or "").strip()[:30]
	tel = telefone_normalizado(telefone)
	v = vincular_fornecedor(nome, tel, email, documento, contato or "")
	if v["contact"] and documento and not frappe.db.get_value("Contact", v["contact"], "panda_documento"):
		frappe.db.set_value("Contact", v["contact"], "panda_documento", documento, update_modified=False)
	return {"supplier_phone": tel, "supplier_email": email, "supplier_document": documento, "supplier_contact": v["contact"]}


def _serializar_linha(line) -> dict:
	from crm.panda.contatos import telefone_br

	return {
		"name": line.name,
		"supplier": line.supplier,
		"description": line.description or "",
		"supplier_phone": line.supplier_phone or "",
		"supplier_phone_br": telefone_br(line.supplier_phone) if line.supplier_phone else "",
		"supplier_email": line.supplier_email or "",
		"supplier_document": line.supplier_document or "",
		"supplier_contact": line.supplier_contact or "",
		"finance_tag": line.finance_tag,
		"tag_name": frappe.db.get_value("CRM Finance Tag", line.finance_tag, "tag_name")
		if line.finance_tag
		else None,
		"mode": line.mode,
		"amount": line.amount,
		"installments_count": line.installments_count,
		"first_due_date": str(line.first_due_date) if line.first_due_date else None,
		"total": line.total,
		"paid_total": line.paid_total,
		"remaining": line.remaining,
		"entries": [
			{
				"name": e.name,
				"number": e.installment_number,
				"supplier": e.supplier,
				"value": e.value,
				"paid_on": str(e.paid_on) if e.paid_on else None,
				"file": e.file,
			}
			for e in line.entries
		],
		"installments": [
			{
				"number": p.number,
				"due_date": str(p.due_date) if p.due_date else None,
				"expected_value": p.expected_value,
				"paid": bool(p.paid),
				"paid_value": p.paid_value,
				"paid_on": str(p.paid_on) if p.paid_on else None,
			}
			for p in line.installments
		],
	}


@frappe.whitelist()
def get_finance(deal: str):
	_check(deal, "read")
	linhas = [
		_serializar_linha(frappe.get_doc("CRM Payment Line", n))
		for n in frappe.get_all("CRM Payment Line", {"deal": deal}, pluck="name", order_by="creation asc")
	]
	tags = frappe.get_all(
		"CRM Finance Tag", {"deal": deal}, ["name", "tag_name", "value", "color"], order_by="creation asc"
	)
	for t in tags:
		t["used"] = sum(l["total"] for l in linhas if l["finance_tag"] == t["name"])
	total = sum(calc.to_cents(l["total"]) for l in linhas)
	pago = sum(calc.to_cents(l["paid_total"]) for l in linhas)
	restante = sum(calc.to_cents(l["remaining"]) for l in linhas)
	return {
		"deal_name": frappe.db.get_value("CRM Deal", deal, "project_name") or deal,
		"invoice_email": frappe.db.get_value("CRM Deal", deal, "invoice_email") or "",
		"summary": {
			"project_value": frappe.db.get_value("CRM Deal", deal, "deal_value") or 0,
			"total": calc.from_cents(total),
			"paid": calc.from_cents(pago),
			"remaining": calc.from_cents(restante),
			"end_date": str(frappe.db.get_value("CRM Deal", deal, "expected_closure_date") or "") or None,
			"start_date": str(frappe.db.get_value("CRM Deal", deal, "creation") or "")[:10] or None,
		},
		"tags": tags,
		"lines": linhas,
	}


@frappe.whitelist()
def save_tag(deal: str, tag_name: str, value=0, color: str = "gray", name: str | None = None):
	_check(deal)
	tag_name = (tag_name or "").strip()
	if not tag_name:
		frappe.throw(_("O nome da etiqueta é obrigatório"))
	if name:
		doc = frappe.get_doc("CRM Finance Tag", name)
		if doc.deal != deal:
			frappe.throw(_("Etiqueta de outro projeto"))
	else:
		doc = frappe.new_doc("CRM Finance Tag")
		doc.deal = deal
	if frappe.db.exists("CRM Finance Tag", {"deal": deal, "tag_name": tag_name, "name": ["!=", doc.name or ""]}):
		frappe.throw(_("Já existe uma etiqueta com esse nome neste projeto"))
	# vermelho e reservado ao aviso de valor ultrapassado
	if color == "red":
		color = "gray"
	doc.tag_name, doc.value, doc.color = tag_name, value or 0, color or "gray"
	doc.save()
	return doc.name


@frappe.whitelist()
def delete_tag(name: str):
	tag = frappe.get_doc("CRM Finance Tag", name)
	_check(tag.deal)
	if frappe.db.exists("CRM Payment Line", {"finance_tag": name}):
		frappe.throw(_("Há linhas de pagamento usando esta etiqueta"))
	frappe.delete_doc("CRM Finance Tag", name)
	return True


def _n_parcelas(deal, mode, n, first_due, atual: int = 0):
	"""Valor variavel: uma parcela por mes ate o fim do projeto.
	Demais modos: no maximo uma parcela por mes ate o fim do projeto (se o fim estiver definido)."""
	fim = frappe.db.get_value("CRM Deal", deal, "expected_closure_date") if deal else None
	if mode != calc.VARIAVEL:
		if fim and first_due:
			limite = calc.months_between(getdate(first_due), getdate(fim))
			if limite < 1:
				frappe.throw(_("O primeiro vencimento é depois do fim do projeto"))
			if int(n or 0) > max(limite, int(atual or 0)):  # linha antiga ja maior: nao trava a edicao
				frappe.throw(
					_("O projeto termina em {0}: no máximo {1} parcela(s) a partir deste primeiro vencimento").format(
						getdate(fim).strftime("%m/%Y"), limite
					)
				)
		return n
	if not fim:
		frappe.throw(_("Defina a data de fim do projeto para usar o valor variável"))
	meses = calc.months_between(getdate(first_due), getdate(fim))
	if meses < 1:
		frappe.throw(_("O primeiro vencimento é depois do fim do projeto"))
	return meses


def _montar(amount, mode, n, first_due):
	try:
		return calc.build_installments(amount, mode, int(n), getdate(first_due))
	except ValueError as e:
		frappe.throw(_(str(e)))


@frappe.whitelist()
def preview_line(amount, mode: str, installments_count, first_due_date, deal: str | None = None):
	installments_count = _n_parcelas(deal, mode, installments_count, first_due_date)
	total, parcelas = _montar(amount, mode, installments_count, first_due_date)
	return {
		"total": calc.from_cents(total),
		"installments": [
			{
				"number": p["number"],
				"due_date": str(p["due_date"]),
				"expected_value": calc.from_cents(p["expected_cents"]),
			}
			for p in parcelas
		],
	}


@frappe.whitelist()
def create_line(
	deal: str,
	supplier: str,
	mode: str,
	amount,
	installments_count,
	first_due_date,
	finance_tag: str | None = None,
	description: str = "",
	supplier_phone: str = "",
	supplier_email: str = "",
	supplier_document: str = "",
	supplier_contact: str = "",
):
	_check(deal)
	supplier = (supplier or "").strip()
	if not supplier:
		frappe.throw(_("O fornecedor é obrigatório"))
	if finance_tag and frappe.db.get_value("CRM Finance Tag", finance_tag, "deal") != deal:
		frappe.throw(_("Etiqueta de outro projeto"))
	installments_count = _n_parcelas(deal, mode, installments_count, first_due_date)
	total, parcelas = _montar(amount, mode, installments_count, first_due_date)
	line = frappe.new_doc("CRM Payment Line")
	forn = _dados_fornecedor(supplier, supplier_phone, supplier_email, supplier_document, supplier_contact)
	line.update(
		{
			"deal": deal,
			"supplier": supplier,
			"description": (description or "").strip(),
			**forn,
			"finance_tag": finance_tag,
			"mode": mode,
			"amount": amount,
			"installments_count": int(installments_count),
			"first_due_date": getdate(first_due_date),
		}
	)
	for p in parcelas:
		line.append("installments", {"number": p["number"], "due_date": p["due_date"]})
	_gravar_parcelas(line, parcelas, total)
	line.insert()
	atualizar_totais_do_projeto(deal)
	return line.name


@frappe.whitelist()
def update_line(name: str, supplier: str, finance_tag: str | None = None):
	"""Edita o fornecedor e a etiqueta da linha (os valores e parcelas nao mudam)."""
	line = frappe.get_doc("CRM Payment Line", name)
	_check(line.deal)
	supplier = (supplier or "").strip()
	if not supplier:
		frappe.throw(_("O fornecedor é obrigatório"))
	if finance_tag and frappe.db.get_value("CRM Finance Tag", finance_tag, "deal") != line.deal:
		frappe.throw(_("Etiqueta de outro projeto"))
	line.supplier = supplier
	line.finance_tag = finance_tag
	line.save()
	return _serializar_linha(line)


@frappe.whitelist()
def update_line_full(
	name: str,
	supplier: str,
	mode: str,
	amount,
	installments_count,
	first_due_date,
	finance_tag: str | None = None,
	description: str = "",
	supplier_phone: str = "",
	supplier_email: str = "",
	supplier_document: str = "",
	supplier_contact: str = "",
):
	"""Edicao completa da linha. Parcelas pagas sao mantidas; as pendentes sao refeitas."""
	line = frappe.get_doc("CRM Payment Line", name)
	_check(line.deal)
	supplier = (supplier or "").strip()
	if not supplier:
		frappe.throw(_("O fornecedor é obrigatório"))
	if finance_tag and frappe.db.get_value("CRM Finance Tag", finance_tag, "deal") != line.deal:
		frappe.throw(_("Etiqueta de outro projeto"))
	installments_count = _n_parcelas(line.deal, mode, installments_count, first_due_date, line.installments_count)
	try:
		total, parcelas = calc.rebuild(
			_linha_para_parcelas(line), amount, mode, int(installments_count), getdate(first_due_date)
		)
	except ValueError as e:
		frappe.throw(_(str(e)))
	line.supplier = supplier
	line.description = (description or "").strip()
	line.update(_dados_fornecedor(supplier, supplier_phone, supplier_email, supplier_document, supplier_contact))
	line.finance_tag = finance_tag
	line.mode = mode
	line.amount = amount
	line.installments_count = int(installments_count)
	line.first_due_date = getdate(first_due_date)
	line.set("installments", [])
	for p in parcelas:
		line.append("installments", {"number": p["number"], "due_date": p["due_date"]})
	_gravar_parcelas(line, parcelas, total)
	line.save()
	atualizar_totais_do_projeto(line.deal)
	return _serializar_linha(line)


@frappe.whitelist()
def delete_line(name: str):
	line = frappe.get_doc("CRM Payment Line", name)
	_check(line.deal)
	if any(p.paid for p in line.installments):
		frappe.throw(_("Desfaça os pagamentos antes de apagar a linha"))
	frappe.delete_doc("CRM Payment Line", name)
	atualizar_totais_do_projeto(line.deal)
	return True


@frappe.whitelist()
def preview_payment(line: str, number, paid_value):
	doc = frappe.get_doc("CRM Payment Line", line)
	_check(doc.deal, "read")
	parcelas = _linha_para_parcelas(doc)
	try:
		total, novas = calc.register_payment(
			parcelas, calc.to_cents(doc.total), int(number), calc.to_cents(paid_value)
		)
	except ValueError as e:
		frappe.throw(_(str(e)))
	antes = {p.number: p.expected_value for p in doc.installments}
	return {
		"total": calc.from_cents(total),
		"installments": [
			{
				"number": p["number"],
				"due_date": str(p["due_date"]) if p["due_date"] else None,
				"before": antes[p["number"]],
				"after": calc.from_cents(p["paid_cents"] if p["paid"] else p["expected_cents"]),
				"paid": p["paid"],
			}
			for p in novas
		],
	}


@frappe.whitelist()
def register_payment(line: str, number, paid_value, paid_on=None):
	doc = frappe.get_doc("CRM Payment Line", line)
	_check(doc.deal)
	parcelas = _linha_para_parcelas(doc)
	try:
		total, novas = calc.register_payment(
			parcelas, calc.to_cents(doc.total), int(number), calc.to_cents(paid_value)
		)
	except ValueError as e:
		frappe.throw(_(str(e)))
	for p in novas:
		if p["number"] == int(number):
			p["paid_on"] = getdate(paid_on) if paid_on else getdate()
	_gravar_parcelas(doc, novas, total)
	doc.save()
	atualizar_totais_do_projeto(doc.deal)
	from crm.panda.events import pagamento_registrado

	pagamento_registrado(doc.deal, doc.supplier, int(number), f"R$ {float(paid_value):,.2f}")
	return _serializar_linha(doc)


@frappe.whitelist()
def undo_payment(line: str, number):
	doc = frappe.get_doc("CRM Payment Line", line)
	_check(doc.deal)
	parcelas = _linha_para_parcelas(doc)
	# o total "comprometido" da linha e o valor original: reconstruir a partir dos parametros da linha
	original = calc.line_total_cents(calc.to_cents(doc.amount), doc.mode, int(doc.installments_count))
	try:
		total, novas = calc.undo_payment(parcelas, original, int(number))
	except ValueError as e:
		frappe.throw(_(str(e)))
	_gravar_parcelas(doc, novas, total)
	doc.save()
	atualizar_totais_do_projeto(doc.deal)
	from crm.panda.events import pagamento_desfeito

	pagamento_desfeito(doc.deal, doc.supplier, int(number))
	if doc.mode != calc.VARIAVEL:
		from crm.panda.files import marcar_desfeito

		marcar_desfeito(doc.name, number)
	return _serializar_linha(doc)


@frappe.whitelist()
def get_send_options(deal: str):
	"""E-mails para o envio de nota: o salvo no projeto + contas de e-mail ja cadastradas."""
	_check(deal, "read")
	contas = frappe.get_all("Email Account", {"enable_incoming": 1}, pluck="email_id")
	return {"saved": frappe.db.get_value("CRM Deal", deal, "invoice_email") or "", "accounts": contas}


@frappe.whitelist(methods=["POST"])
def set_invoice_email(deal: str, email: str):
	_check(deal)
	email = (email or "").strip()
	if email and not frappe.utils.validate_email_address(email):
		frappe.throw(_("E-mail inválido"))
	frappe.db.set_value("CRM Deal", deal, "invoice_email", email)
	return True


@frappe.whitelist(methods=["POST"])
def send_whatsapp(deal: str, phone: str, text: str, email: str = ""):
	"""Envia o pedido de nota pelo WhatsApp conectado no proprio programa (Evolution), sem abrir o WhatsApp Web."""
	_check(deal)
	from crm.panda import chat

	text = (text or "").strip()
	numero = chat._digitos(phone)
	if len(numero) < 10:
		frappe.throw(_("Preencha o WhatsApp do fornecedor"))
	if len(numero) <= 11:
		numero = "55" + numero
	if not text:
		frappe.throw(_("Escreva a mensagem"))
	email = (email or "").strip()
	if email:
		if not frappe.utils.validate_email_address(email):
			frappe.throw(_("E-mail inválido"))
		frappe.db.set_value("CRM Deal", deal, "invoice_email", email)
	conv = chat._conversa("WhatsApp", numero + "@s.whatsapp.net", None, numero)
	try:
		ext = chat._enviar_whatsapp(numero, text)
	except Exception as e:
		chat._registrar(conv, "Out", text, status="Failed", por=frappe.session.user)
		frappe.db.commit()
		frappe.throw(str(e))
	frappe.db.set_value(chat.CONV, conv, "deal", deal)
	chat._registrar(conv, "Out", text, ext_id=ext, status="Sent", por=frappe.session.user)
	chat._publicar(conv)
	return True
