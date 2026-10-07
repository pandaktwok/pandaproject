"""Padroes do Panda Project V2 (marca, idioma, fuso).

Roda em after_migrate, mas so aplica uma vez (flag em DefaultValue),
para nao sobrescrever mudancas feitas depois pelo cliente.
"""
import frappe

FLAG = "panda_defaults_applied"
FLAG_V2 = "panda_defaults_v2"
FLAG_V3 = "panda_defaults_v3"
FLAG_V4 = "panda_defaults_v4"
FLAG_V5 = "panda_defaults_v5"
FLAG_V6 = "panda_defaults_v6"
FLAG_V7 = "panda_defaults_v7"
FLAG_V8 = "panda_defaults_v8"
FLAG_V9 = "panda_defaults_v9"
FLAG_V10 = "panda_defaults_v10"


def apply_defaults():
	_apply_v1()
	_apply_v2()
	_apply_v3()
	_apply_v4()
	_apply_v5()
	_apply_v6()
	_apply_v7()
	_apply_v8()
	_apply_v9()
	_apply_v10()
	_criar_campo_arquivos()
	_desligar_lead_automatico()


def _apply_v7():
	"""E-mail para envio de nota no formulario de criacao e no painel lateral do Projeto."""
	if frappe.db.get_default(FLAG_V7):
		return
	import json

	for nome in ("CRM Deal-Quick Entry", "CRM Deal-Side Panel"):
		if not frappe.db.exists("CRM Fields Layout", nome):
			continue
		layout = json.loads(frappe.db.get_value("CRM Fields Layout", nome, "layout") or "[]")
		if nome.endswith("Quick Entry"):
			layout.append({"name": "nota_section", "columns": [{"name": "column_p6", "fields": ["invoice_email"]}]})
		else:
			for sec in layout:
				for col in sec.get("columns", []):
					if "deal_owner" in col.get("fields", []):
						col["fields"].append("invoice_email")
		frappe.db.set_value("CRM Fields Layout", nome, "layout", json.dumps(layout))
	frappe.db.set_default(FLAG_V7, "1")
	frappe.db.commit()
	frappe.clear_cache()


def _apply_v8():
	"""Real brasileiro (BRL) habilitado e definido como moeda padrao."""
	if frappe.db.get_default(FLAG_V8):
		return
	if frappe.db.exists("Currency", "BRL"):
		frappe.db.set_value("Currency", "BRL", {"enabled": 1, "symbol": "R$"})
	else:
		frappe.get_doc(
			{"doctype": "Currency", "currency_name": "BRL", "enabled": 1, "symbol": "R$", "fraction": "Centavo",
			 "number_format": "#.###,##"}
		).insert(ignore_permissions=True)
	if not frappe.db.get_single_value("FCRM Settings", "currency"):
		frappe.db.set_single_value("FCRM Settings", "currency", "BRL")
	frappe.db.set_single_value("System Settings", "currency_precision", 2)
	frappe.db.set_single_value("Global Defaults", "default_currency", "BRL")
	frappe.db.set_default(FLAG_V8, "1")
	frappe.db.commit()
	frappe.clear_cache()


def _apply_v10():
	"""Marca PandaProject: logo da tela de login/barra do Frappe e nome da marca (so se ainda nao personalizados)."""
	if frappe.db.get_default(FLAG_V10):
		return
	logo = "/assets/crm/images/brand/logo-horizontal-claro-1400w.png"
	try:
		if not frappe.db.get_single_value("Website Settings", "app_logo"):
			frappe.db.set_single_value("Website Settings", "app_logo", logo)
		if not frappe.db.get_single_value("Navbar Settings", "app_logo"):
			frappe.db.set_single_value("Navbar Settings", "app_logo", logo)
		frappe.db.set_single_value("Website Settings", "app_name", "PandaProject")
		if not frappe.db.get_single_value("FCRM Settings", "brand_name") or frappe.db.get_single_value(
			"FCRM Settings", "brand_name"
		) in ("Frappe CRM", "CRM"):
			frappe.db.set_single_value("FCRM Settings", "brand_name", "PandaProject")
	except Exception:
		frappe.log_error(title="PandaProject: marca")
	frappe.db.set_default(FLAG_V10, "1")
	frappe.db.commit()
	frappe.clear_cache()


def _apply_v9():
	"""Painel novo (numeros, graficos por tipo, pagamentos e feed) como layout padrao, uma vez."""
	if frappe.db.get_default(FLAG_V9):
		return
	from crm.fcrm.doctype.crm_dashboard.crm_dashboard import create_default_manager_dashboard

	create_default_manager_dashboard(force=True)
	frappe.db.set_default(FLAG_V9, "1")
	frappe.db.commit()


def _apply_v6():
	"""Datas em dia/mes/ano e numeros no padrao brasileiro."""
	if frappe.db.get_default(FLAG_V6):
		return
	frappe.db.set_single_value("System Settings", "date_format", "dd/mm/yyyy")
	frappe.db.set_single_value("System Settings", "number_format", "#.###,##")
	frappe.db.set_default(FLAG_V6, "1")
	frappe.db.commit()
	frappe.clear_cache()


def _apply_v5():
	"""Organizacao: so o nome e obrigatorio; o resto e opcional."""
	if frappe.db.get_default(FLAG_V5):
		return
	import json

	quick = [
		{"name": "org_section", "columns": [{"name": "column_o1", "fields": ["organization_name"]}]},
		{"name": "org_contato_section", "hideBorder": True, "columns": [
			{"name": "column_o2", "fields": ["website", "social_media"]},
			{"name": "column_o3", "fields": ["tax_id", "whatsapp"]},
		]},
		{"name": "org_endereco_section", "hideBorder": True, "columns": [{"name": "column_o4", "fields": ["address"]}]},
	]
	side = [
		{"label": "Details", "name": "details_section", "opened": True, "columns": [
			{"name": "column_IJOV", "fields": ["organization_name", "tax_id", "website", "social_media", "whatsapp", "address"]},
		]},
	]
	for nome, layout in (("CRM Organization-Quick Entry", quick), ("CRM Organization-Side Panel", side)):
		if frappe.db.exists("CRM Fields Layout", nome):
			frappe.db.set_value("CRM Fields Layout", nome, "layout", json.dumps(layout))
	frappe.db.set_default(FLAG_V5, "1")
	frappe.db.commit()
	frappe.clear_cache()


def _apply_v4():
	"""Formulario de criacao do Projeto, painel lateral e tipos de projeto."""
	if frappe.db.get_default(FLAG_V4):
		return
	import json

	quick = [
		{"name": "projeto_section", "columns": [
			{"name": "column_p1", "fields": ["organization", "project_name"]},
			{"name": "column_p2", "fields": ["deal_value", "project_type"]},
		]},
		{"name": "deal_section", "columns": [
			{"name": "column_p3", "fields": ["status"]},
			{"name": "column_p4", "fields": ["deal_owner"]},
		]},
		{"name": "descricao_section", "columns": [{"name": "column_p5", "fields": ["description"]}]},
	]
	side = [
		{"label": "Contacts", "name": "contacts_section", "opened": True, "editable": False, "contacts": []},
		{"label": "Details", "name": "organization_section", "opened": True, "columns": [
			{"name": "column_na2Q", "fields": [
				"organization", "project_name", "project_type", "deal_value",
				"expected_closure_date", "description", "deal_owner",
			]},
		]},
	]
	for nome, layout in (("CRM Deal-Quick Entry", quick), ("CRM Deal-Side Panel", side)):
		if frappe.db.exists("CRM Fields Layout", nome):
			frappe.db.set_value("CRM Fields Layout", nome, "layout", json.dumps(layout))

	for tipo, cor in (("Municipal", "blue"), ("Estadual", "green"), ("Federal", "orange"),
			("Fundo", "purple"), ("Educação", "teal")):
		if not frappe.db.exists("CRM Project Type", tipo):
			frappe.get_doc({"doctype": "CRM Project Type", "project_type": tipo, "color": cor}).insert(
				ignore_permissions=True
			)

	frappe.db.set_default(FLAG_V4, "1")
	frappe.db.commit()
	frappe.clear_cache()


def _apply_v3():
	"""As 5 etapas do Projeto (substituem as etapas de vendas do Frappe CRM)."""
	if frappe.db.get_default(FLAG_V3):
		return
	etapas = [
		("Criação e captação de recursos", "gray", "Open", 10),
		("Aprovação", "blue", "Ongoing", 30),
		("Execução", "orange", "Ongoing", 60),
		("Prestação de contas", "purple", "Ongoing", 90),
		("Concluído", "green", "Won", 100),
	]
	for pos, (nome, cor, tipo, prob) in enumerate(etapas, start=1):
		if frappe.db.exists("CRM Deal Status", nome):
			continue
		doc = frappe.new_doc("CRM Deal Status")
		doc.deal_status = nome
		doc.color = cor
		doc.type = tipo
		doc.probability = prob
		doc.position = pos
		doc.insert(ignore_permissions=True)
	# Remove as etapas de vendas que nenhum projeto usa
	novos = [e[0] for e in etapas]
	for antigo in frappe.get_all("CRM Deal Status", filters={"name": ["not in", novos]}, pluck="name"):
		if not frappe.db.exists("CRM Deal", {"status": antigo}):
			frappe.delete_doc("CRM Deal Status", antigo, force=True, ignore_permissions=True)
	frappe.db.set_default(FLAG_V3, "1")
	frappe.db.commit()
	frappe.clear_cache()


def _apply_v2():
	"""Nome do app na tela de login e no titulo do site."""
	if frappe.db.get_default(FLAG_V2):
		return
	for doctype in ("System Settings", "Website Settings"):
		if frappe.get_meta(doctype).has_field("app_name"):
			frappe.db.set_single_value(doctype, "app_name", "Panda Project")
	frappe.db.set_default(FLAG_V2, "1")
	frappe.db.commit()
	frappe.clear_cache()


def _apply_v1():
	if frappe.db.get_default(FLAG):
		return

	# Idioma e fuso do sistema
	frappe.db.set_single_value("System Settings", "language", "pt-BR")
	frappe.db.set_single_value("System Settings", "time_zone", "America/Sao_Paulo")

	# Cadastro fechado: so entra quem for convidado
	frappe.db.set_single_value("Website Settings", "disable_signup", 1)

	# Marca
	frappe.db.set_single_value("FCRM Settings", "brand_name", "Panda Project")

	# Idioma dos usuarios ja existentes
	frappe.db.sql("update `tabUser` set language='pt-BR' where name not in ('Guest')")

	frappe.db.set_default(FLAG, "1")
	frappe.db.commit()
	frappe.clear_cache()


def _criar_campo_arquivos():
	"""Campo interno que liga o PDF unido a linha/parcela do pagamento."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if not frappe.db.exists("Custom Field", {"dt": "Contact", "fieldname": "panda_origem"}):
		create_custom_field(
			"Contact",
			{
				"fieldname": "panda_origem",
				"fieldtype": "Data",
				"label": "Origem",
				"read_only": 1,
				"in_standard_filter": 1,
				"insert_after": "company_name",
			},
		)
	for fn, tipo, rotulo, extra in (
		("panda_base_legal", "Select", "Base legal (LGPD)", {"options": "\nConsentimento\nExecução de contrato\nLegítimo interesse\nObrigação legal"}),
		("panda_consentimento_em", "Date", "Data do consentimento", {}),
	):
		if not frappe.db.exists("Custom Field", {"dt": "Contact", "fieldname": fn}):
			create_custom_field(
				"Contact",
				{"fieldname": fn, "fieldtype": tipo, "label": rotulo, "insert_after": "panda_origem", **extra},
			)
	for fn, tipo, rotulo, extra in (
		("panda_documento", "Data", "CPF/CNPJ", {}),
		("panda_grupos", "Small Text", "Grupos do WhatsApp", {"read_only": 1}),
		("panda_foto_em", "Datetime", "Foto atualizada em", {"hidden": 1, "read_only": 1}),
	):
		if not frappe.db.exists("Custom Field", {"dt": "Contact", "fieldname": fn}):
			create_custom_field(
				"Contact", {"fieldname": fn, "fieldtype": tipo, "label": rotulo, "insert_after": "panda_origem", **extra}
			)
	if not frappe.db.exists("Custom Field", {"dt": "File", "fieldname": "panda_key"}):
		create_custom_field(
			"File",
			{
				"fieldname": "panda_key",
				"fieldtype": "Data",
				"label": "Panda Key",
				"hidden": 1,
				"read_only": 1,
				"search_index": 1,
			},
		)


def _desligar_lead_automatico():
	"""E-mail recebido nao cria lead nem contato sozinho (gera lixo). Roda a cada migracao."""
	frappe.db.sql("update `tabEmail Account` set append_to=NULL, create_contact=0 where append_to is not null or create_contact=1")
	try:
		frappe.db.sql("update `tabIMAP Folder` set append_to=NULL where append_to is not null")
	except Exception:
		pass
	frappe.db.commit()
