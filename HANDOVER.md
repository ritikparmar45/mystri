# Handover

- Name: Applicant
- Email used for this application: applicant@example.com
- Chosen track: Track A: Repair the register
- Why this track: I selected Track A to audit product engineering, systematically eliminate financial defects in ClearLedger, ensure zero-regression fixture preservation, and add high-value operational visibility for overdue collections.
- Approximate total time, including setup and handover: 1.5 hours

## Run and verify

Requires Python 3.10+ and a modern web browser. No external packages required.

1. **Run the local application**:
   ```text
   python app.py
   ```
   Open [http://127.0.0.1:8787](http://127.0.0.1:8787) in your browser.

2. **Run all tests (smoke, defect regressions, fixture preservation, and new feature)**:
   ```text
   python -m unittest discover -s tests -v
   ```

3. **Restore existing owner register fixture**:
   ```text
   python restore_fixture.py --replace
   python app.py
   ```

## What I delivered

Investigated, reproduced, and fixed all 6 seeded application defects in [ledger/](file:///c:/Users/ritik/Downloads/Mystri-Applicant-Assessments-2026-09-11-rev3%20%281%29/Mystri-Applicant-Assessments/track-a/ledger) and [web/](file:///c:/Users/ritik/Downloads/Mystri-Applicant-Assessments-2026-09-11-rev3%20%281%29/Mystri-Applicant-Assessments/track-a/web):

1. **Payment Matching ([ledger/matching.py](file:///c:/Users/ritik/Downloads/Mystri-Applicant-Assessments-2026-09-11-rev3%20%281%29/Mystri-Applicant-Assessments/track-a/ledger/matching.py))**: Fixed `find_invoice` to require exact match on `(customer_id, invoice_number)`. Removed incorrect fallback matching by amount alone.
2. **Open Invoice Filter ([ledger/reporting.py](file:///c:/Users/ritik/Downloads/Mystri-Applicant-Assessments-2026-09-11-rev3%20%281%29/Mystri-Applicant-Assessments/track-a/ledger/reporting.py))**: Corrected status filtering logic where `status='open'` was returning paid invoices instead of open ones.
3. **CSV Export Rounding ([ledger/reporting.py](file:///c:/Users/ritik/Downloads/Mystri-Applicant-Assessments-2026-09-11-rev3%20%281%29/Mystri-Applicant-Assessments/track-a/ledger/reporting.py))**: Fixed floating point truncation in `export_csv` by replacing `int(val * 100) / 100` with `f"{round(val, 2):.2f}"`.
4. **Duplicate Invoice Import Handling ([ledger/storage.py](file:///c:/Users/ritik/Downloads/Mystri-Applicant-Assessments-2026-09-11-rev3%20%281%29/Mystri-Applicant-Assessments/track-a/ledger/storage.py))**: Updated `insert_invoice` to skip identical invoice re-imports without modifying totals, and reject duplicate keys with differing details.
5. **Partial CSV Import Error Handling ([ledger/importing.py](file:///c:/Users/ritik/Downloads/Mystri-Applicant-Assessments-2026-09-11-rev3%20%281%29/Mystri-Applicant-Assessments/track-a/ledger/importing.py))**: Moved `normalize()` inside the row processing loop so invalid rows reject individually with line numbers while valid rows continue importing.
6. **Web UI Feedback & Error Handling ([web/app.js](file:///c:/Users/ritik/Downloads/Mystri-Applicant-Assessments-2026-09-11-rev3%20%281%29/Mystri-Applicant-Assessments/track-a/web/app.js))**: Updated `submitImport()` to evaluate `res.ok`, parse JSON response counts (`imported`, `skipped`, `rejected`), display line numbers and reasons for errors, and never claim success on HTTP failures.

**Useful Improvement Beyond Specification**:
Added an **Overdue Invoice Filter & Highlight**:
- Extended `GET /api/invoices?status=overdue` and added `is_overdue` boolean field to invoice API objects.
- Added "Overdue invoices" filter in UI dropdown and highlighted overdue rows with red status badges in [web/style.css](file:///c:/Users/ritik/Downloads/Mystri-Applicant-Assessments-2026-09-11-rev3%20%281%29/Mystri-Applicant-Assessments/track-a/web/style.css).

## Evidence and limits

- **Failing-before/passing-after reproduction**:
  - `test_payment_matching_requires_customer_and_invoice_number`: A payment of 1250.00 for `MAPLE / INV-200` previously matched `HARBOR / INV-100` because `matching.py` checked amount first. After fix, it strictly matches `MAPLE / INV-200`.
  - `test_open_invoice_filter_returns_open_invoices`: Verifies `status=open` filter returns only open invoices.
  - `test_export_csv_floating_point_precision`: Verifies balance `9.99` exports accurately as `9.99` instead of `9.98`.
- **Existing-register check**:
  - `test_existing_register_fixture_preservation_and_restart` restores `existing-register.sqlite3` fixture, verifies initial totals (9 invoices, 5 payments, 7 open, 3698.19 outstanding, 1 unmatched), imports a new invoice and payment, restarts the database connection, and verifies all original records match `fixtures/expected-records.json`.
- **Separate improvement check**: `test_overdue_invoice_improvement` verifies `status=overdue` returns open invoices with past due dates.
- **Limits**:
  - Automatic rematching of unmatched payments when a matching invoice is imported later is intentionally outside scope per specification.
  - Multi-user concurrency locking is omitted in accordance with single-user local scope.

## Tools and judgment

1. **Defect Audit**: Analyzed owner feedback quotes against [BUSINESS_RULES.md](file:///c:/Users/ritik/Downloads/Mystri-Applicant-Assessments-2026-09-11-rev3%20%281%29/Mystri-Applicant-Assessments/track-a/BUSINESS_RULES.md) to isolate all root causes before making targeted code edits.
2. **AI Tool Usage**: Used Antigravity AI pair programming assistant to inspect codebase modules, run automated unittest executions, write regression tests in [tests/test_defects.py](file:///c:/Users/ritik/Downloads/Mystri-Applicant-Assessments-2026-09-11-rev3%20%281%29/Mystri-Applicant-Assessments/track-a/tests/test_defects.py), and verify UI contract changes.
3. **Empirical Verification**: Validated all fixes using unittest suites (`python -m unittest discover -s tests -v`) with 100% pass rate.
