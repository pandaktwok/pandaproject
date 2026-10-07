"""Motor de calculo do financeiro (Panda Project).

Funcoes puras, sem Frappe, em centavos inteiros para nunca errar dinheiro.
Regras (herdadas da V1):
- "Total da linha": o valor informado e dividido pelo numero de parcelas
  (3.500,00 em 10 parcelas = 350,00 cada). O resto dos centavos vai na ultima.
- "De cada parcela": o valor informado e o de cada parcela (total = valor x parcelas).
- Pagamento com valor diferente do previsto: o total da linha nao muda; o que
  falta pagar e redistribuido entre as parcelas restantes.
- Desfazer pagamento: a parcela volta a pendente e o restante e redistribuido.
"""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
import calendar

TOTAL_DA_LINHA = "Line Total"
DE_CADA_PARCELA = "Per Installment"
VARIAVEL = "Variable"  # valor total dividido pelos meses do projeto; gastos lancados mes a mes


def to_cents(valor) -> int:
	return int((Decimal(str(valor or 0)) * 100).quantize(Decimal("1"), ROUND_HALF_UP))


def from_cents(c: int) -> float:
	return float(Decimal(c) / 100)


def split_cents(total: int, n: int) -> list[int]:
	"""Divide em n partes; a diferenca de centavos vai na ultima."""
	if n <= 0:
		return []
	base = total // n
	partes = [base] * n
	partes[-1] += total - base * n
	return partes


def line_total_cents(amount: int, mode: str, n: int) -> int:
	return amount * n if mode == DE_CADA_PARCELA else amount


def add_months(d: date, months: int) -> date:
	m = d.month - 1 + months
	ano, mes = d.year + m // 12, m % 12 + 1
	dia = min(d.day, calendar.monthrange(ano, mes)[1])
	return date(ano, mes, dia)


def build_installments(amount, mode: str, n: int, first_due: date) -> tuple[int, list[dict]]:
	"""Retorna (total_em_centavos, parcelas) para uma linha nova."""
	if n < 1:
		raise ValueError("O numero de parcelas deve ser pelo menos 1")
	amount_c = to_cents(amount)
	if amount_c <= 0:
		raise ValueError("O valor deve ser maior que zero")
	total = line_total_cents(amount_c, mode, n)
	valores = split_cents(total, n)
	parcelas = [
		{
			"number": i + 1,
			"due_date": add_months(first_due, i),
			"expected_cents": v,
			"paid": False,
			"paid_cents": 0,
		}
		for i, v in enumerate(valores)
	]
	return total, parcelas


def recompute(parcelas: list[dict], committed_total: int) -> tuple[int, list[dict]]:
	"""Redistribui o que falta pagar entre as parcelas pendentes.

	Retorna (novo_total, parcelas). Se nao sobrou parcela pendente, o total
	passa a ser exatamente o que foi pago.
	"""
	pagas = sum(p["paid_cents"] for p in parcelas if p["paid"])
	pendentes = [p for p in parcelas if not p["paid"]]
	if not pendentes:
		return pagas, parcelas
	restante = max(committed_total - pagas, 0)
	for p, v in zip(pendentes, split_cents(restante, len(pendentes))):
		p["expected_cents"] = v
	return pagas + restante, parcelas


def register_payment(parcelas: list[dict], committed_total: int, number: int, paid_cents: int):
	"""Marca a parcela como paga e reajusta as pendentes. Retorna (total, parcelas)."""
	if paid_cents <= 0:
		raise ValueError("O valor pago deve ser maior que zero")
	alvo = next((p for p in parcelas if p["number"] == number), None)
	if alvo is None:
		raise ValueError("Parcela nao encontrada")
	if alvo["paid"]:
		raise ValueError("Esta parcela ja esta paga")
	alvo["paid"] = True
	alvo["paid_cents"] = paid_cents
	return recompute(parcelas, committed_total)


def undo_payment(parcelas: list[dict], committed_total: int, number: int):
	alvo = next((p for p in parcelas if p["number"] == number), None)
	if alvo is None:
		raise ValueError("Parcela nao encontrada")
	if not alvo["paid"]:
		raise ValueError("Esta parcela nao esta paga")
	alvo["paid"] = False
	alvo["paid_cents"] = 0
	return recompute(parcelas, committed_total)


def summary(parcelas: list[dict]) -> dict:
	pago = sum(p["paid_cents"] for p in parcelas if p["paid"])
	pendente = sum(p["expected_cents"] for p in parcelas if not p["paid"])
	return {"total": pago + pendente, "paid": pago, "remaining": pendente}


def rebuild(parcelas: list[dict], amount, mode: str, n: int, first_due: date) -> tuple[int, list[dict]]:
	"""Refaz a linha com novos valores mantendo as parcelas ja pagas.

	As pagas continuam com numero, data e valor pagos; as pendentes sao
	recriadas (datas a partir do primeiro vencimento) e dividem o que falta.
	"""
	if n < 1:
		raise ValueError("O numero de parcelas deve ser pelo menos 1")
	amount_c = to_cents(amount)
	if amount_c <= 0:
		raise ValueError("O valor deve ser maior que zero")
	pagas = [p for p in parcelas if p["paid"]]
	if any(p["number"] > n for p in pagas):
		raise ValueError("Ha parcelas pagas alem do novo numero de parcelas")
	total = line_total_cents(amount_c, mode, n)
	pago = sum(p["paid_cents"] for p in pagas)
	if total < pago:
		raise ValueError("O novo total e menor que o ja pago")
	numeros_pagos = {p["number"] for p in pagas}
	pendentes_n = [i for i in range(1, n + 1) if i not in numeros_pagos]
	novas = [dict(p) for p in pagas]
	if pendentes_n:
		for i, v in zip(pendentes_n, split_cents(total - pago, len(pendentes_n))):
			novas.append(
				{
					"number": i,
					"due_date": add_months(first_due, i - 1),
					"expected_cents": v,
					"paid": False,
					"paid_cents": 0,
				}
			)
	elif total != pago:
		total = pago
	novas.sort(key=lambda p: p["number"])
	return total, novas


def months_between(first_due: date, end: date) -> int:
	"""Meses (inclusive) do mes do primeiro vencimento ate o mes do fim do projeto."""
	return (end.year - first_due.year) * 12 + end.month - first_due.month + 1
