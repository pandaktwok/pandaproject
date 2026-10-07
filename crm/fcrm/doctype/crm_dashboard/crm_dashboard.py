# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CRMDashboard(Document):
	pass


def default_manager_dashboard_layout():
	"""
	Returns the default layout for the CRM Manager Dashboard.
	"""
	import json

	def n(nome, x, y, tip):
		return {"name": nome, "type": "number_chart", "tooltip": tip, "layout": {"x": x, "y": y, "w": 5, "h": 3, "i": nome}}

	itens = [
		n("projetos_total", 0, 0, "Total de projetos"),
		n("projetos_andamento", 5, 0, "Projetos em andamento"),
		n("projetos_encerrados", 10, 0, "Projetos encerrados"),
		n("qtd_fornecedores", 15, 0, "Fornecedores"),
		n("valor_total_projetos", 0, 3, "Valor total dos projetos"),
		n("valor_medio_projeto", 5, 3, "Valor médio por projeto"),
		n("media_por_fornecedor", 10, 3, "Gasto médio por fornecedor"),
		{"name": "projetos_por_tipo_mes", "type": "axis_chart", "layout": {"x": 0, "y": 6, "w": 10, "h": 9, "i": "projetos_por_tipo_mes"}},
		{"name": "pagamentos_por_mes", "type": "axis_chart", "layout": {"x": 10, "y": 6, "w": 10, "h": 9, "i": "pagamentos_por_mes"}},
		{"name": "atividades", "type": "feed", "layout": {"x": 0, "y": 15, "w": 20, "h": 14, "i": "atividades"}},
	]
	return json.dumps(itens)


def create_default_manager_dashboard(force=False):
	"""
	Creates the default CRM Manager Dashboard if it does not exist.
	"""
	if not frappe.db.exists("CRM Dashboard", "Manager Dashboard"):
		doc = frappe.new_doc("CRM Dashboard")
		doc.title = "Manager Dashboard"
		doc.layout = default_manager_dashboard_layout()
		doc.insert(ignore_permissions=True)
	else:
		doc = frappe.get_doc("CRM Dashboard", "Manager Dashboard")
		if force:
			doc.layout = default_manager_dashboard_layout()
			doc.save(ignore_permissions=True)
	return doc.layout
