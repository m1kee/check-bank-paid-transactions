import pandas as pd
from collections import Counter

df = pd.read_excel('data/2025-11-movements-2.xlsx')

# Filtrar pagos y convertir los montos a positivos
payments = df[df['Descripción'].isin(["Pago Pesos TAR", "Pago Pesos TEF PAGO NORMAL"])].copy()
payments["Monto ($)"] = payments["Monto ($)"] * -1

c1 = (~df['Descripción'].isin(["Pago Pesos TAR", "Pago Pesos TEF PAGO NORMAL"])) & (df["Cuotas"] == "01/01")
shopping = df[c1].copy()

# Matching uno a uno usando Counter
shopping_counts = Counter(shopping["Monto ($)"])
payments_counts = Counter(payments["Monto ($)"])

# Restar pagos a compras
for amount in payments_counts:
    match_count = min(shopping_counts[amount], payments_counts[amount])
    shopping_counts[amount] -= match_count

# Filtrar compras no pagadas
unpaid_rows = []
for idx, row in shopping.iterrows():
    if shopping_counts[row["Monto ($)"]] > 0:
        unpaid_rows.append(idx)
        shopping_counts[row["Monto ($)"]] -= 1

no_match = shopping.loc[unpaid_rows]
total = sum(no_match["Monto ($)"])

def clp_format(x):
    return f"${x:,.0f}".replace(",", ".")

print(no_match)
print(f"total not paid: {clp_format(total)}")

total_payments = sum(payments["Monto ($)"])
total_shopping = sum(shopping["Monto ($)"])
print(f"total payments: {clp_format(total_payments)}")
print(f"total shopping: {clp_format(total_shopping)}")
print(f"total difference: {clp_format(total_payments - total_shopping)}")