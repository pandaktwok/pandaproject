"""Arquivos dos pagamentos (Panda Project): comprovante + nota fiscal em um unico PDF.

Regras (herdadas da V1):
- Comprovante e NF sao unidos num PDF so (comprovante primeiro).
- Pastas virtuais: Financeiro > "Parcela N - MM-AAAA" (calculadas, nao existem no disco).
- Nome do arquivo: "Fornecedor - Parcela N.pdf" (" (2)" se repetir).
- WebP/HEIC sao recusados com mensagem clara.
- PDFs de pagamentos desfeitos so aparecem para administradores.
- Downloads sempre como anexo (nunca abrem no navegador).
"""
import io
import re
import zipfile

import frappe
from frappe import _

from crm.panda import finance

RECUSADOS = (".webp", ".heic", ".heif")
IMAGENS = (".jpg", ".jpeg", ".png")
MAX_MB = 20


def _eh_admin() -> bool:
	return frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()


def _limpar(nome: str) -> str:
	nome = re.sub(r'[\\/:*?"<>|\r\n]+', " ", nome or "").strip()
	return re.sub(r"\s+", " ", nome) or "Fornecedor"


def _ler(arquivo) -> tuple[str, bytes]:
	nome = (arquivo.filename or "").lower()
	dados = arquivo.read()
	cab = dados[:16]
	if nome.endswith(RECUSADOS) or cab[8:12] in (b"heic", b"heix", b"mif1", b"msf1") or (
		cab[:4] == b"RIFF" and cab[8:12] == b"WEBP"
	):
		frappe.throw(_("Formato não aceito (WebP/HEIC). Envie PDF, JPG ou PNG."))
	if len(dados) > MAX_MB * 1024 * 1024:
		frappe.throw(_("Arquivo maior que {0} MB").format(MAX_MB))
	if dados[:4] == b"%PDF":
		return "pdf", dados
	if dados[:3] == b"\xff\xd8\xff" or dados[:8] == b"\x89PNG\r\n\x1a\n":
		return "img", dados
	frappe.throw(_("Formato não aceito. Envie PDF, JPG ou PNG."))


def _para_pdf(tipo: str, dados: bytes):
	from pypdf import PdfReader

	if tipo == "pdf":
		try:
			return PdfReader(io.BytesIO(dados))
		except Exception:
			frappe.throw(_("PDF inválido ou protegido por senha"))
	from PIL import Image

	img = Image.open(io.BytesIO(dados)).convert("RGB")
	buf = io.BytesIO()
	img.save(buf, format="PDF")
	buf.seek(0)
	return PdfReader(buf)


def _unir(arquivos: list) -> bytes:
	from pypdf import PdfWriter

	w = PdfWriter()
	for tipo, dados in arquivos:
		for pagina in _para_pdf(tipo, dados).pages:
			w.add_page(pagina)
	out = io.BytesIO()
	w.write(out)
	return out.getvalue()


def _chave(line: str, number) -> str:
	return f"parcela:{line}:{int(number)}"


def _nome_unico(deal: str, base: str) -> str:
	existentes = set(
		frappe.get_all(
			"File", {"attached_to_doctype": "CRM Deal", "attached_to_name": deal}, pluck="file_name"
		)
	)
	nome, i = f"{base}.pdf", 2
	while nome in existentes:
		nome = f"{base} ({i}).pdf"
		i += 1
	return nome


@frappe.whitelist(methods=["POST"])
def register_with_files(line: str, number, paid_value, paid_on=None):
	"""Valida os arquivos, registra o pagamento e guarda o PDF unido."""
	doc = frappe.get_doc("CRM Payment Line", line)
	finance._check(doc.deal)
	enviados = []
	for campo in ("comprovante", "nota_fiscal"):
		f = frappe.request.files.get(campo)
		if f and f.filename:
			enviados.append(_ler(f))
	pdf = _unir(enviados) if enviados else None  # valida antes de mexer no financeiro
	resultado = finance.register_payment(line, number, paid_value, paid_on)
	if pdf:
		_guardar_pdf(doc, number, doc.supplier, pdf)
	return resultado


def _guardar_pdf(doc, number, fornecedor: str, pdf: bytes) -> str:
	nome = _nome_unico(doc.deal, f"{_limpar(fornecedor)} - Parcela {int(number)}")
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": nome,
			"attached_to_doctype": "CRM Deal",
			"attached_to_name": doc.deal,
			"panda_key": _chave(doc.name, number),
			"is_private": 1,
			"content": pdf,
		}
	).insert(ignore_permissions=True)
	from crm.panda.drive import enfileirar

	enfileirar(f.name, doc.deal)
	return f.name


def _receber_pdf():
	enviados = []
	for campo in ("comprovante", "nota_fiscal"):
		f = frappe.request.files.get(campo)
		if f and f.filename:
			enviados.append(_ler(f))
	return _unir(enviados) if enviados else None


def _linha_variavel(line: str, number):
	doc = frappe.get_doc("CRM Payment Line", line)
	finance._check(doc.deal)
	if doc.mode != "Variable":
		frappe.throw(_("Esta linha não é de valor variável"))
	parcela = next((p for p in doc.installments if p.number == int(number)), None)
	if parcela is None:
		frappe.throw(_("Mês não encontrado"))
	return doc, parcela


@frappe.whitelist(methods=["POST"])
def add_entry(line: str, number, supplier: str, value, paid_on=None):
	"""Valor variavel: lanca um gasto no mes (fornecedor + valor + comprovante/NF unidos em um PDF)."""
	from frappe.utils import flt, getdate

	doc, parcela = _linha_variavel(line, number)
	if parcela.paid:
		frappe.throw(_("Mês fechado. Reabra o mês para lançar novos pagamentos."))
	supplier = (supplier or "").strip()
	if not supplier:
		frappe.throw(_("O fornecedor é obrigatório"))
	if flt(value) <= 0:
		frappe.throw(_("O valor deve ser maior que zero"))
	pdf = _receber_pdf()
	arquivo = _guardar_pdf(doc, number, supplier, pdf) if pdf else None
	doc.append(
		"entries",
		{
			"installment_number": int(number),
			"supplier": supplier,
			"value": flt(value),
			"paid_on": getdate(paid_on) if paid_on else getdate(),
			"file": arquivo,
		},
	)
	doc.save()
	return finance._serializar_linha(doc)


@frappe.whitelist()
def delete_entry(line: str, entry: str):
	doc = frappe.get_doc("CRM Payment Line", line)
	finance._check(doc.deal)
	linha = next((e for e in doc.entries if e.name == entry), None)
	if linha is None:
		frappe.throw(_("Lançamento não encontrado"))
	parcela = next((p for p in doc.installments if p.number == linha.installment_number), None)
	if parcela and parcela.paid:
		frappe.throw(_("Mês fechado. Reabra o mês antes de apagar."))
	if linha.file and frappe.db.exists("File", linha.file):
		frappe.delete_doc("File", linha.file, ignore_permissions=True)
	doc.remove(linha)
	doc.save()
	return finance._serializar_linha(doc)


@frappe.whitelist()
def close_month(line: str, number):
	"""Fecha o mes: o gasto vira o valor pago e o que sobra e redistribuido nos meses seguintes."""
	doc, parcela = _linha_variavel(line, number)
	lancados = [e for e in doc.entries if e.installment_number == int(number)]
	total = sum(float(e.value or 0) for e in lancados)
	if total <= 0:
		frappe.throw(_("Lance ao menos um pagamento neste mês"))
	ultimo = max((e.paid_on for e in lancados if e.paid_on), default=None)
	return finance.register_payment(line, number, total, str(ultimo) if ultimo else None)


def marcar_desfeito(line: str, number):
	"""Pagamento desfeito: o PDF fica guardado, mas so administradores o veem."""
	frappe.db.set_value(
		"File",
		{"panda_key": _chave(line, number)},
		"panda_key",
		"desfeito:" + _chave(line, number),
		update_modified=False,
	)


def _arquivos_do_deal(deal: str):
	return frappe.get_all(
		"File",
		{
			"attached_to_doctype": "CRM Deal",
			"attached_to_name": deal,
			"panda_key": ["like", "%parcela:%"],
		},
		["name", "file_name", "file_size", "creation", "panda_key"],
		order_by="creation asc",
	)


@frappe.whitelist()
def get_files(deal: str):
	"""Pastas virtuais Financeiro > Parcela N - MM-AAAA com seus PDFs."""
	finance._check(deal, "read")
	admin = _eh_admin()
	pastas = {}
	for f in _arquivos_do_deal(deal):
		desfeito = f.panda_key.startswith("desfeito:")
		if desfeito and not admin:
			continue
		_, line, n = f.panda_key.replace("desfeito:", "").split(":")
		pasta = pastas.get((line, n))
		if pasta is None:
			due = frappe.db.get_value("CRM Payment Installment", {"parent": line, "number": int(n)}, "due_date")
			rotulo = f"Parcela {n} - {due.strftime('%m-%Y')}" if due else f"Parcela {n}"
			pasta = pastas[(line, n)] = {
				"label": rotulo,
				"line": line,
				"number": int(n),
				"supplier": frappe.db.get_value("CRM Payment Line", line, "supplier"),
				"files": [],
			}
		pasta["files"].append(
			{"name": f.name, "file_name": f.file_name, "size": f.file_size, "undone": desfeito}
		)
	return {"folder": "Financeiro", "folders": sorted(pastas.values(), key=lambda p: (p["supplier"] or "", p["number"]))}


def _permitido(file_name: str):
	f = frappe.get_doc("File", file_name)
	if f.attached_to_doctype != "CRM Deal":
		frappe.throw(_("Arquivo inválido"), frappe.PermissionError)
	finance._check(f.attached_to_name, "read")
	if (f.panda_key or "").startswith("desfeito:") and not _eh_admin():
		frappe.throw(_("Sem permissão"), frappe.PermissionError)
	return f


@frappe.whitelist()
def download(file: str):
	f = _permitido(file)
	frappe.response.filename = f.file_name
	frappe.response.filecontent = f.get_content()
	frappe.response.type = "download"
	frappe.response.display_content_as = "attachment"


@frappe.whitelist()
def download_zip(deal: str, line: str | None = None, number=None):
	"""ZIP de uma pasta (linha + numero) ou de todo o Financeiro do projeto."""
	finance._check(deal, "read")
	admin = _eh_admin()
	buf = io.BytesIO()
	usados = set()
	with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
		for item in _arquivos_do_deal(deal):
			desfeito = item.panda_key.startswith("desfeito:")
			if desfeito and not admin:
				continue
			_, ln, n = item.panda_key.replace("desfeito:", "").split(":")
			if line and (ln != line or (number is not None and int(n) != int(number))):
				continue
			due = frappe.db.get_value("CRM Payment Installment", {"parent": ln, "number": int(n)}, "due_date")
			pasta = f"Parcela {n} - {due.strftime('%m-%Y')}" if due else f"Parcela {n}"
			caminho = f"Financeiro/{pasta}/{item.file_name}"
			base, i = caminho, 2
			while caminho in usados:
				caminho = base.replace(".pdf", f" ({i}).pdf")
				i += 1
			usados.add(caminho)
			z.writestr(caminho, frappe.get_doc("File", item.name).get_content())
	if not usados:
		frappe.throw(_("Nenhum arquivo para baixar"))
	frappe.response.filename = "Financeiro.zip" if not line else "Parcela.zip"
	frappe.response.filecontent = buf.getvalue()
	frappe.response.type = "download"
	frappe.response.display_content_as = "attachment"
