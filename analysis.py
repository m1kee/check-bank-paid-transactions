import pandas as pd
import sys
from collections import Counter
import config  # Imports our config.py file
from utils import format_clp

def analyze_movements(cleaned_file_path: str):
    """
    Reads the clean XLSX file and performs the analysis of
    purchases vs. payments to find unpaid movements.
    """
    print(f"\n[Analyzing]: Reading clean file: {cleaned_file_path}")
    
    try:
        df = pd.read_excel(cleaned_file_path)
    except FileNotFoundError:
        print(f"Error: Clean file not found: '{cleaned_file_path}'", file=sys.stderr)
        return
    except Exception as e:
        print(f"Error reading processed file: {e}", file=sys.stderr)
        return

    # 1. Filter payments and convert amounts to positive
    payment_filter = df['Description'].isin(config.PAYMENT_TERMS)
    payments = df[payment_filter].copy()
    payments["Amount ($)"] = payments["Amount ($)"].abs() # Use .abs() for safety

    # 2. Filter purchases
    shopping_filter = (~payment_filter) & (df["Installments"] == config.PURCHASE_INSTALLMENT_CONDITION)
    shopping = df[shopping_filter].copy()

    # 3. One-to-one matching using Counter
    shopping_counts = Counter(shopping["Amount ($)"])
    payments_counts = Counter(payments["Amount ($)"])

    # 4. Subtract payments from purchases
    for amount in payments_counts:
        match_count = min(shopping_counts[amount], payments_counts[amount])
        shopping_counts[amount] -= match_count

    # 5. Filter unpaid purchases
    unpaid_rows = []
    for idx, row in shopping.iterrows():
        amount = row["Amount ($)"]
        if shopping_counts[amount] > 0:
            unpaid_rows.append(idx)
            shopping_counts[amount] -= 1

    no_match = shopping.loc[unpaid_rows].sort_values(by="Date")
    total_unpaid = sum(no_match["Amount ($)"])
    
    total_payments = sum(payments["Amount ($)"])
    total_shopping = sum(shopping["Amount ($)"])

    # 6. Print the final report
    print("\n--- FINAL ANALYSIS REPORT ---")
    if not no_match.empty:
        print("UNPAID PURCHASES (NO 1-TO-1 MATCH):")
        # Print without the pandas index
        print(no_match.to_string(index=False))
    else:
        print("Congratulations! All single-installment purchases have an associated payment.")
        
    print("---------------------------------")
    print(f"Total unpaid (no match):    {format_clp(total_unpaid)}")
    print("---------------------------------")
    print(f"Total payments (1 install):   {format_clp(total_payments)}")
    print(f"Total purchases (1 install): {format_clp(total_shopping)}")
    print(f"Difference (Pay - Shop):  {format_clp(total_payments - total_shopping)}")
    print("--- Analysis Complete ---")