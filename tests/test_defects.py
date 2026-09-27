import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from ledger import storage, reporting, importing

ROOT = Path(__file__).resolve().parent.parent


class DefectAndRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / 'ledger.sqlite3'
        self.db = storage.connect(self.db_path)
        storage.seed(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_payment_matching_requires_customer_and_invoice_number(self):
        # Defect 1 check: Amount alone must NOT establish identity.
        # Payment for MAPLE/INV-200 (amount 1250.00) must match MAPLE/INV-200, not HARBOR/INV-100 (also 1250.00).
        csv_data = "payment_id,customer_id,invoice_number,amount\nP-MAPLE,MAPLE,INV-200,1250.00\n"
        res = importing.import_csv(self.db, csv_data, 'payments')
        self.assertEqual(res['imported'], 1)
        
        invoices = {r['invoice_number']: r for r in reporting.invoices(self.db)}
        self.assertEqual(invoices['INV-200']['paid'], 1250.00)
        self.assertEqual(invoices['INV-200']['status'], 'paid')
        self.assertEqual(invoices['INV-100']['paid'], 0.00)

        # Unmatched payment with matching amount but non-existent invoice reference
        csv_unmatched = "payment_id,customer_id,invoice_number,amount\nP-UNMATCHED,HARBOR,NO-SUCH-INV,1250.00\n"
        res2 = importing.import_csv(self.db, csv_unmatched, 'payments')
        self.assertEqual(res2['imported'], 1)
        ov = reporting.overview(self.db)
        unmatched_ids = [p['payment_id'] for p in ov['unmatched_payments']]
        self.assertIn('P-UNMATCHED', unmatched_ids)

    def test_open_invoice_filter_returns_open_invoices(self):
        # Defect 2 check: status=open must return open invoices, status=paid must return paid invoices.
        open_invs = reporting.invoices(self.db, 'open')
        paid_invs = reporting.invoices(self.db, 'paid')
        
        self.assertTrue(all(r['status'] == 'open' for r in open_invs))
        self.assertTrue(all(r['status'] == 'paid' for r in paid_invs))
        self.assertGreater(len(open_invs), 0)
        self.assertGreater(len(paid_invs), 0)

    def test_export_csv_floating_point_precision(self):
        # Defect 3 check: 9.99 invoice balance for INV-300 must not be truncated to 9.98 in CSV export.
        csv_text = reporting.export_csv(self.db)
        self.assertIn('NORTH,INV-300,19.99,10.00,9.99,open', csv_text)


    def test_invoice_reimport_handling(self):
        # Defect 4 check: Re-importing identical invoice skips it; different details rejects it.
        # Identical re-import
        csv_same = "customer_id,invoice_number,amount,due_date\nHARBOR,INV-100,1250.00,2026-09-01\n"
        res_same = importing.import_csv(self.db, csv_same, 'invoices')
        self.assertEqual(res_same['skipped'], 1)
        self.assertEqual(res_same['imported'], 0)
        
        # Overview outstanding stays 3209.99
        self.assertEqual(reporting.overview(self.db)['summary']['outstanding'], 3209.99)

        # Re-import with different amount
        csv_diff = "customer_id,invoice_number,amount,due_date\nHARBOR,INV-100,1300.00,2026-09-01\n"
        res_diff = importing.import_csv(self.db, csv_diff, 'invoices')
        self.assertEqual(res_diff['rejected'], 1)
        self.assertEqual(res_diff['imported'], 0)

    def test_partial_csv_import_row_by_row_validation(self):
        # Defect 5 check: An invalid row rejects only that row while valid rows are imported.
        csv_mixed = (
            "customer_id,invoice_number,amount,due_date\n"
            "HARBOR,TEST-1,100.00,2026-09-10\n"
            "BAD_CUST,TEST-2,200.00,2026-09-10\n"
            "MAPLE,TEST-3,300.00,2026-09-10\n"
        )
        res = importing.import_csv(self.db, csv_mixed, 'invoices')
        self.assertEqual(res['imported'], 2)
        self.assertEqual(res['rejected'], 1)
        self.assertEqual(len(res['errors']), 1)
        self.assertEqual(res['errors'][0]['line'], 3)

    def test_overdue_invoice_improvement(self):
        # Useful Improvement check: status=overdue filter
        overdue_invs = reporting.invoices(self.db, 'overdue')
        self.assertTrue(all(r['is_overdue'] and r['status'] == 'open' for r in overdue_invs))

    def test_existing_register_fixture_preservation_and_restart(self):
        # Existing register check: Verify fixture data and persistence across app restart
        fixture_path = ROOT / 'fixtures' / 'existing-register.sqlite3'
        temp_fixture_path = Path(self.tmp.name) / 'existing_test.sqlite3'
        
        # Copy fixture
        import shutil
        shutil.copy2(fixture_path, temp_fixture_path)
        
        db_fixture = storage.connect(temp_fixture_path)
        ov_before = reporting.overview(db_fixture)
        self.assertEqual(ov_before['summary']['invoice_count'], 9)
        self.assertEqual(ov_before['summary']['open_count'], 7)
        self.assertEqual(ov_before['summary']['outstanding'], 3698.19)
        self.assertEqual(len(ov_before['unmatched_payments']), 1)
        
        # Import new invoice and payment
        importing.import_csv(db_fixture, "customer_id,invoice_number,amount,due_date\nHARBOR,NEW-FIX-1,500.00,2026-09-20\n", 'invoices')
        importing.import_csv(db_fixture, "payment_id,customer_id,invoice_number,amount\nNEW-PAY-1,HARBOR,NEW-FIX-1,500.00\n", 'payments')
        db_fixture.close()
        
        # Restart app / reconnect database
        db_restarted = storage.connect(temp_fixture_path)
        ov_after = reporting.overview(db_restarted)
        
        # Total invoices should now be 10, open count still 7, outstanding 3698.19
        self.assertEqual(ov_after['summary']['invoice_count'], 10)
        self.assertEqual(ov_after['summary']['outstanding'], 3698.19)
        
        # Verify original fixture records still exist intact
        expected_json = json.loads((ROOT / 'fixtures' / 'expected-records.json').read_text(encoding='utf-8'))
        invoices_by_id = {r['id']: r for r in reporting.invoices(db_restarted)}
        for exp in expected_json['invoices']:
            exp_id = exp['id']
            self.assertIn(exp_id, invoices_by_id)
            self.assertEqual(invoices_by_id[exp_id]['invoice_number'], exp['invoice_number'])
            self.assertEqual(invoices_by_id[exp_id]['amount'], float(exp['amount']))
        
        db_restarted.close()


if __name__ == '__main__':
    unittest.main()
