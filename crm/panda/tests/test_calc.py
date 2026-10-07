import unittest
from datetime import date

from crm.panda import calc as c


def mk(amount, mode, n, due=date(2026, 1, 31)):
	return c.build_installments(amount, mode, n, due)


class TestCalc(unittest.TestCase):
	def test_total_da_linha_10_parcelas(self):
		total, p = mk("3500.00", c.TOTAL_DA_LINHA, 10)
		self.assertEqual(total, 350000)
		self.assertTrue(all(x["expected_cents"] == 35000 for x in p))

	def test_de_cada_parcela(self):
		total, p = mk("3500.00", c.DE_CADA_PARCELA, 10)
		self.assertEqual(total, 3500000)
		self.assertTrue(all(x["expected_cents"] == 350000 for x in p))

	def test_resto_de_centavos_na_ultima(self):
		total, p = mk("100.00", c.TOTAL_DA_LINHA, 3)
		self.assertEqual([x["expected_cents"] for x in p], [3333, 3333, 3334])
		self.assertEqual(sum(x["expected_cents"] for x in p), total)

	def test_vencimentos_mensais_fim_de_mes(self):
		_, p = mk("100", c.TOTAL_DA_LINHA, 3, date(2026, 1, 31))
		self.assertEqual([x["due_date"] for x in p], [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)])

	def test_pagar_a_mais_reajusta_restantes(self):
		total, p = mk("1000", c.TOTAL_DA_LINHA, 4)  # 250 cada
		novo, p = c.register_payment(p, total, 1, c.to_cents("400"))
		self.assertEqual(novo, total)  # total da linha nao muda
		self.assertEqual([x["expected_cents"] for x in p[1:]], [20000, 20000, 20000])

	def test_pagar_a_menos_reajusta_restantes(self):
		total, p = mk("1000", c.TOTAL_DA_LINHA, 4)
		novo, p = c.register_payment(p, total, 1, c.to_cents("100"))
		self.assertEqual([x["expected_cents"] for x in p[1:]], [30000, 30000, 30000])
		self.assertEqual(c.summary(p)["total"], total)

	def test_ultima_parcela_diferente_muda_o_total(self):
		total, p = mk("100", c.TOTAL_DA_LINHA, 1)
		novo, p = c.register_payment(p, total, 1, c.to_cents("90"))
		self.assertEqual(novo, 9000)
		self.assertEqual(c.summary(p)["remaining"], 0)

	def test_desfazer_restaura(self):
		total, p = mk("1000", c.TOTAL_DA_LINHA, 4)
		_, p = c.register_payment(p, total, 1, c.to_cents("400"))
		novo, p = c.undo_payment(p, total, 1)
		self.assertEqual(novo, total)
		self.assertTrue(all(x["expected_cents"] == 25000 for x in p))
		self.assertFalse(p[0]["paid"])

	def test_pagar_duas_vezes_falha(self):
		total, p = mk("1000", c.TOTAL_DA_LINHA, 2)
		c.register_payment(p, total, 1, 50000)
		with self.assertRaises(ValueError):
			c.register_payment(p, total, 1, 50000)

	def test_resumo_total_e_restante_batem(self):
		total, p = mk("1000", c.TOTAL_DA_LINHA, 4)
		_, p = c.register_payment(p, total, 2, c.to_cents("300"))
		s = c.summary(p)
		self.assertEqual(s["total"], s["paid"] + s["remaining"])
		self.assertEqual(s["total"], total)

	def test_valor_invalido(self):
		with self.assertRaises(ValueError):
			mk("0", c.TOTAL_DA_LINHA, 3)
		with self.assertRaises(ValueError):
			mk("10", c.TOTAL_DA_LINHA, 0)


if __name__ == "__main__":
	unittest.main()


class TestRebuild(unittest.TestCase):
	def test_mantem_pagas_e_redistribui(self):
		total, ps = c.build_installments(1000, c.TOTAL_DA_LINHA, 4, date(2026, 1, 10))
		total, ps = c.register_payment(ps, total, 1, 25000)
		novo, ps2 = c.rebuild(ps, 2000, c.TOTAL_DA_LINHA, 5, date(2026, 2, 5))
		self.assertEqual(novo, 200000)
		self.assertEqual(len(ps2), 5)
		self.assertTrue(ps2[0]["paid"])
		self.assertEqual(ps2[0]["due_date"], date(2026, 1, 10))
		self.assertEqual(ps2[1]["due_date"], date(2026, 3, 5))
		self.assertEqual(sum(p["expected_cents"] for p in ps2 if not p["paid"]), 175000)

	def test_erros(self):
		total, ps = c.build_installments(1000, c.TOTAL_DA_LINHA, 4, date(2026, 1, 10))
		total, ps = c.register_payment(ps, total, 4, 25000)
		with self.assertRaises(ValueError):
			c.rebuild(ps, 1000, c.TOTAL_DA_LINHA, 3, date(2026, 1, 10))
		with self.assertRaises(ValueError):
			c.rebuild(ps, 100, c.TOTAL_DA_LINHA, 4, date(2026, 1, 10))
