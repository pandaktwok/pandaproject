"""Testes de Contatos/Fornecedores/WhatsApp. Rodar no Docker:
docker compose exec frappe bash -c "cd frappe-bench && bench --site crm.localhost run-tests --module crm.panda.tests.test_contatos"
"""
import frappe
from frappe.tests.utils import FrappeTestCase

from crm.panda import chat, contatos as ct


class TestContatos(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_origens_multiplas_e_legado(self):
		self.assertEqual(ct.origens_de("Newsletter do site, WhatsApp"), ["Newsletter", "WhatsApp"])
		self.assertEqual(ct.origens_de(""), ["Manual"])
		self.assertEqual(ct.origens_de("E-mail"), ["E-mail"])

	def test_telefone_brasileiro(self):
		for x in ("(48) 99654-5728", "48996545728", "+55 48 99654-5728", "5548996545728"):
			self.assertEqual(ct.telefone_normalizado(x), "5548996545728")
		self.assertEqual(ct.telefone_br("5548996545728"), "(48) 99654-5728")
		self.assertTrue(ct.mesmo_telefone("5548996545728", "554896545728"))  # sem o 9
		self.assertFalse(ct.mesmo_telefone("5548996545728", "5511996545728"))

	def test_fornecedor_cria_contato_com_origem_fornecedor(self):
		r = ct.vincular_fornecedor("Fornecedor Teste", "(48) 98888-7777", "", "")
		self.assertTrue(r["created"] and not r["linked"])
		self.assertIn("Fornecedor", ct.origens_de(frappe.db.get_value("Contact", r["contact"], "panda_origem")))
		r2 = ct.vincular_fornecedor("Outro Nome", "5548988887777", "", "")  # mesmo numero
		self.assertTrue(r2["linked"] and not r2["created"])
		self.assertEqual(r2["contact"], r["contact"])

	def test_fornecedor_so_com_nome_nao_cria_contato(self):
		r = ct.vincular_fornecedor("So Nome")
		self.assertEqual(r, {"contact": None, "linked": False, "created": False})

	def test_fornecedor_vincula_por_email_e_soma_origem(self):
		c = ct.criar_contato("Maria", "", "maria@teste.com", "WhatsApp")
		r = ct.vincular_fornecedor("Maria Fornecedora", "", "maria@teste.com")
		self.assertTrue(r["linked"])
		self.assertEqual(sorted(ct.origens_de(frappe.db.get_value("Contact", c, "panda_origem"))), ["Fornecedor", "WhatsApp"])

	def test_listar_nunca_repete_pessoa_entre_as_partes(self):
		a = ct.criar_contato("So Newsletter Teste", "", "so-news@teste.com", "Newsletter do site")
		b = ct.criar_contato("News e Whats Teste", "5548977776666", "nw@teste.com", "Newsletter do site")
		ct.adicionar_origem(b, "WhatsApp")
		r = ct.listar(q="teste")
		cont, news = {x["name"] for x in r["contatos"]}, {x["name"] for x in r["newsletters"]}
		self.assertIn(a, news)
		self.assertIn(b, cont)
		self.assertFalse(cont & news)
		self.assertEqual({x["name"] for x in ct.listar(origem="WhatsApp")["contatos"]} >= {b}, True)

	def test_capturar_contato_do_whatsapp(self):
		c = chat._capturar_contato("5548966665555", "Fulano de Tal", grupo="Grupo SCCS")
		self.assertEqual(frappe.db.get_value("Contact", c, "first_name"), "Fulano de Tal")
		self.assertIn("WhatsApp", ct.origens_de(frappe.db.get_value("Contact", c, "panda_origem")))
		self.assertIn("Grupo SCCS", frappe.db.get_value("Contact", c, "panda_grupos"))
		# segunda vez: nao duplica nem troca o nome
		c2 = chat._capturar_contato("(48) 96666-5555", "Outro Nome", grupo="Grupo SCCS")
		self.assertEqual(c, c2)
		self.assertEqual(frappe.db.get_value("Contact", c, "first_name"), "Fulano de Tal")

	def test_jid_so_numero_real(self):
		self.assertEqual(chat._jid_para_numero("5548966665555@s.whatsapp.net"), "5548966665555")
		self.assertEqual(chat._jid_para_numero("123456@lid"), "")
