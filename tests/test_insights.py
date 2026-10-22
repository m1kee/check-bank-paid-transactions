"""Installments (12), subscriptions (15), alerts (16), export (19), charts (14) and the insights that join them."""
import datetime
import unittest

import pandas as pd

from bankcheck import alerts, charts, export, installments, recurring
from bankcheck.analysis import analyze
from bankcheck.categories import default_rules
from bankcheck.formatting import format_amount
from bankcheck.insights import build_insights, pending_by_age
from tests.helpers import movements


class InstallmentTests(unittest.TestCase):
    def test_remaining_installments_and_debt(self):
        [plan] = installments.installment_plans(movements([("2026-10-05", "NOTEBOOK", 45000, "03/12")])).to_dict("records")
        self.assertEqual((plan["Remaining"], plan["Remaining Debt"]), (9, 405000))
        self.assertEqual(plan["Ends"], pd.Period("2027-07", "M"))

    def test_latest_charge_of_each_purchase_counts_once(self):
        df = movements([("2026-09-05", "NOTEBOOK", 45000, "02/12"), ("2026-10-05", "NOTEBOOK", 45000, "03/12")])
        plans = installments.installment_plans(df)
        self.assertEqual(plans["Current"].tolist(), [3])

    def test_monthly_commitment_is_the_sum_of_active_installments(self):
        df = movements(
            [
                ("2026-10-05", "NOTEBOOK", 45000, "03/12"),
                ("2026-10-06", "SILLA", 20000, "02/03"),
                ("2026-10-07", "TERMINADA", 10000, "06/06"),
                ("2026-10-08", "CAFE", 2500, "01/01"),
            ]
        )
        plans = installments.installment_plans(df)
        self.assertEqual(installments.summary(plans), {"CLP": (65000, 405000 + 20000)})

    def test_projection_goes_down_as_plans_end(self):
        df = movements([("2026-10-05", "NOTEBOOK", 45000, "10/12"), ("2026-10-06", "SILLA", 20000, "02/03")])
        projection = installments.projection(installments.installment_plans(df), months=4)
        self.assertEqual(projection["Amount"].tolist(), [65000, 45000, 0, 0])
        self.assertEqual(projection["Month"].iloc[0], pd.Period("2026-11", "M"))


class SubscriptionTests(unittest.TestCase):
    def test_monthly_charge_for_three_months_is_detected(self):
        df = movements([("2026-08-14", "NETFLIX.COM", 7990), ("2026-09-14", "NETFLIX.COM", 7990), ("2026-10-14", "NETFLIX.COM", 7990)])
        [sub] = recurring.detect_subscriptions(df)
        self.assertEqual((sub.description, sub.amount, sub.annual_cost, sub.charges), ("NETFLIX.COM", 7990, 95880, 3))
        self.assertFalse(sub.price_increased)

    def test_price_increase_is_flagged(self):
        df = movements(
            [("2026-07-14", "NETFLIX.COM", 7990), ("2026-08-14", "NETFLIX.COM", 7990),
             ("2026-09-14", "NETFLIX.COM", 7990), ("2026-10-14", "NETFLIX.COM", 9990)]
        )
        [sub] = recurring.detect_subscriptions(df)
        self.assertTrue(sub.price_increased)
        self.assertEqual(sub.price_change, 2000)

    def test_irregular_or_short_series_are_not_subscriptions(self):
        two_months = movements([("2026-09-14", "SPOTIFY", 4990), ("2026-10-14", "SPOTIFY", 4990)])
        weekly = movements([("2026-10-01", "LIDER", 20000), ("2026-10-08", "LIDER", 20000), ("2026-10-15", "LIDER", 20000)])
        self.assertEqual(recurring.detect_subscriptions(two_months), [])
        self.assertEqual(recurring.detect_subscriptions(weekly), [])

    def test_merchant_codes_do_not_split_a_subscription(self):
        df = movements([("2026-08-03", "SPOTIFY P1A2", 4990), ("2026-09-03", "SPOTIFY X9Y8", 4990), ("2026-10-03", "SPOTIFY Q7W6", 4990)])
        self.assertEqual(len(recurring.detect_subscriptions(df)), 1)

    def test_cancelled_subscription_is_not_shown(self):
        df = movements(
            [("2026-03-03", "GYM", 30000), ("2026-04-03", "GYM", 30000), ("2026-05-03", "GYM", 30000), ("2026-10-20", "CAFE", 2500)]
        )
        self.assertEqual(recurring.detect_subscriptions(df), [])


class AlertTests(unittest.TestCase):
    def test_two_identical_charges_the_same_day(self):
        df = movements([("2026-10-02", "CAFE", 2500), ("2026-10-02", "CAFE", 2500), ("2026-10-03", "UBER", 4500)])
        [alert] = alerts.find_alerts(df)
        self.assertEqual(alert.kind, alerts.DUPLICATE)
        self.assertIn("mismo día", alert.detail)

    def test_no_alerts_for_normal_movements(self):
        df = movements([("2026-10-02", "CAFE", 2500), ("2026-10-05", "CAFE", 2500), ("2026-10-03", "UBER", 4500)])
        self.assertEqual(alerts.find_alerts(df), [])

    def test_unusual_amount(self):
        rows = [(f"2026-09-{d:02d}", "LIDER", 20000) for d in (1, 8, 15, 22)] + [("2026-10-08", "LIDER", 90000)]
        kinds = [a.kind for a in alerts.find_alerts(movements(rows))]
        self.assertEqual(kinds, [alerts.UNUSUAL])

    def test_new_merchant_and_city_need_some_history(self):
        df = movements([("2026-07-01", "LIDER", 20000, "01/01", "SANTIAGO"), ("2026-10-10", "TIENDA NUEVA", 9000, "01/01", "VALPARAISO")])
        kinds = sorted(a.kind for a in alerts.find_alerts(df))
        self.assertEqual(kinds, [alerts.NEW_CITY, alerts.NEW_MERCHANT])
        short = movements([("2026-10-01", "LIDER", 20000), ("2026-10-10", "TIENDA NUEVA", 9000)])
        self.assertEqual(alerts.find_alerts(short), [])

    def test_old_movements_raise_no_alerts(self):
        df = movements([("2026-05-02", "CAFE", 2500), ("2026-05-02", "CAFE", 2500), ("2026-10-03", "UBER", 4500)])
        self.assertNotIn(alerts.DUPLICATE, [a.kind for a in alerts.find_alerts(df)])


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.results = analyze(movements([("2026-10-03", "UBER TRIP", 4500), ("2026-10-07", "LIDER EXPRESS", 23450)]))

    def test_text_for_whatsapp(self):
        self.assertEqual(
            export.pending_text(self.results, datetime.date(2026, 10, 21)),
            "Pendientes al 21/10/2026:\n• 03/10 UBER TRIP — $4.500\n• 07/10 LIDER EXPRESS — $23.450\nTotal: $27.950",
        )

    def test_nothing_pending(self):
        results = analyze(movements([("2026-10-03", "UBER", 4500), ("2026-10-04", "PAGO ONLINE", -4500)]))
        self.assertEqual(export.pending_text(results, datetime.date(2026, 10, 21)), "Sin pendientes al 21/10/2026.")

    def test_csv(self):
        lines = export.pending_csv(self.results).lstrip("﻿").splitlines()
        self.assertEqual(lines[0], "Moneda,Fecha,Descripción,Ciudad,Monto")
        self.assertEqual(lines[1], "CLP,2026-10-03,UBER TRIP,,4500")


class ChartTests(unittest.TestCase):
    def test_columns_scale_to_the_largest_value_and_escape(self):
        html = charts.columns([("1", 50, "<b>1 oct</b>"), ("2", 100, "2 oct")], format_amount)
        self.assertIn('style="height:50.0%"', html)
        self.assertIn('style="height:100.0%"', html)
        self.assertIn("&lt;b&gt;", html)

    def test_empty_chart(self):
        self.assertIn("Sin datos", charts.columns([("1", 0, "x")], format_amount))
        self.assertIn("Sin datos", charts.bars([], format_amount))

    def test_bars_with_previous_month_have_a_legend(self):
        html = charts.bars([("Delivery", 100, 50)], format_amount, previous_label="septiembre", current_label="octubre")
        self.assertIn("viz-legend", html)
        self.assertIn("previous", html)


class BuildInsightsTests(unittest.TestCase):
    def test_spending_compares_with_previous_month(self):
        df = movements([("2026-09-10", "LIDER", 10000), ("2026-10-10", "LIDER", 25000), ("2026-10-11", "UBER TRIP", 5000)])
        insights = build_insights(df, default_rules())
        self.assertEqual(insights.month, pd.Period("2026-10", "M"))
        self.assertEqual(insights.total_spent, 30000)
        self.assertEqual(insights.previous_spent, 10000)
        self.assertEqual(insights.spending["Category"].iloc[0], "Supermercado")

    def test_pending_by_age(self):
        [result] = analyze(movements([("2026-10-20", "A", 1000), ("2026-10-01", "B", 2000), ("2026-08-01", "C", 4000)]))
        self.assertEqual(
            pending_by_age(result, datetime.date(2026, 10, 21)),
            [("0–7 días", 1000), ("8–30 días", 2000), ("Más de 30 días", 4000)],
        )


if __name__ == "__main__":
    unittest.main()
