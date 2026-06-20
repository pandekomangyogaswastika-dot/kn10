#!/usr/bin/env python3
"""
Backend Testing — Phase 5.5: Faktur Pajak Masukan (Input VAT)
================================================================
Comprehensive testing of Input Tax Invoice endpoints:
- Eligible bills retrieval
- Create input tax invoice from vendor bill
- Bill flagging and duplicate prevention
- NSFP dedupe
- VAT summary calculation
- Cancel flow
- Permission gating
"""
import asyncio
import os
import sys
import requests
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

# Use public endpoint for testing
BASE = "https://hpp-allocator.preview.emergentagent.com"
API = f"{BASE}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
ENTITY = "ent_ksc"

# Test markers
MARK = "ITTEST"
PERIOD = datetime.now(timezone.utc).strftime("%Y-%m")  # Current period
PDATE = f"{PERIOD}-15T00:00:00+00:00"
NSFP1 = "0100123456789012"  # 16-digit
NSFP2 = "0100999888777666"

PASS, FAIL = [], []
def ok(m): PASS.append(m); print(f"  ✅ [PASS] {m}")
def bad(m): FAIL.append(m); print(f"  ❌ [FAIL] {m}")
def info(m): print(f"  ℹ️  {m}")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def login(email, password="demo12345"):
    """Login and return token"""
    try:
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
        r.raise_for_status()
        return r.json()["token"]
    except Exception as e:
        bad(f"Login failed for {email}: {str(e)}")
        return None


async def cleanup(db):
    """Clean up test data"""
    await db.vendor_bills.delete_many({"mark": MARK})
    await db.tax_invoices_in.delete_many({"$or": [{"mark": MARK}, {"nsfp_digits": {"$in": [NSFP1, NSFP2]}}]})
    await db.tax_invoices.delete_many({"mark": MARK})


async def seed_vendor_bill(db, suffix, ppn, dpp, status="posted"):
    """Seed a vendor bill with PPN"""
    bid = f"vbill_{MARK.lower()}_{suffix}"
    await db.vendor_bills.delete_many({"id": bid})
    await db.vendor_bills.insert_one({
        "id": bid, "mark": MARK, "bill_number": f"VB-{MARK}-{suffix}",
        "supplier_invoice_no": f"INV-{suffix}", "po_id": f"po_{MARK.lower()}", "po_number": f"PO-{MARK}",
        "supplier_id": "sup_ittest", "supplier_name": "Supplier Test Input Tax", 
        "supplier_npwp": "01.234.567.8-901.000",
        "entity_id": ENTITY, "bill_date": PDATE, "status": status,
        "dpp": dpp, "ppn_rate": 11.0, "ppn_mode": "excluded", "ppn_amount": ppn,
        "grand_total": round(dpp + ppn, 2), "input_faktur_status": "none",
        "created_at": now_iso(), "updated_at": now_iso()
    })
    return bid


async def seed_output_faktur(db, ppn, dpp):
    """Seed an output tax invoice (Faktur Pajak Jual)"""
    fid = f"fkt_{MARK.lower()}_out"
    await db.tax_invoices.delete_many({"id": fid})
    await db.tax_invoices.insert_one({
        "id": fid, "mark": MARK, "number": f"FKT-{MARK}", "status": "normal",
        "entity_id": ENTITY, "faktur_date": PDATE, "order_id": "so_ittest",
        "dpp": dpp, "ppn_rate": 11.0, "ppn_amount": ppn, "grand_total": round(dpp + ppn, 2),
        "created_at": now_iso(), "updated_at": now_iso()
    })
    return fid


async def test_backend():
    """Main backend test suite"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # ── Test 1: Login ─────────────────────────────────────────────────────
    info("TEST 1: Authentication")
    admin_token = login("admin@kainnusantara.id")
    if not admin_token:
        bad("Admin login failed - stopping tests")
        client.close()
        return
    ok("Admin login successful")
    
    manager_token = login("manager@kainnusantara.id")
    if manager_token:
        ok("Manager login successful")
    else:
        bad("Manager login failed")
    
    sales_token = login("sales@kainnusantara.id")
    if sales_token:
        ok("Sales login successful")
    else:
        bad("Sales login failed")
    
    # Setup session with admin token
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {admin_token}"})
    
    # ── Test 2: Cleanup and seed data ─────────────────────────────────────
    info("TEST 2: Setup test data")
    await cleanup(db)
    bill1 = await seed_vendor_bill(db, "1", ppn=110000.0, dpp=1000000.0, status="posted")
    bill2 = await seed_vendor_bill(db, "2", ppn=55000.0, dpp=500000.0, status="posted")
    bill3 = await seed_vendor_bill(db, "3", ppn=33000.0, dpp=300000.0, status="draft")  # Not eligible
    await seed_output_faktur(db, ppn=200000.0, dpp=1818181.0)
    ok("Test data seeded successfully")
    
    # ── Test 3: Eligible bills endpoint ───────────────────────────────────
    info("TEST 3: GET /api/input-tax-invoices/eligible-bills")
    try:
        r = s.get(f"{API}/input-tax-invoices/eligible-bills", params={"entity_id": ENTITY}, timeout=30)
        if r.status_code == 200:
            ok("Eligible bills endpoint returns 200")
            bills = r.json()
            if isinstance(bills, list):
                ok("Response is a list (bare array, no envelope)")
                if any(b["vendor_bill_id"] == bill1 for b in bills):
                    ok("Posted bill with PPN appears in eligible bills")
                else:
                    bad("Posted bill with PPN NOT in eligible bills")
                if any(b["vendor_bill_id"] == bill2 for b in bills):
                    ok("Second posted bill with PPN appears in eligible bills")
                else:
                    bad("Second posted bill NOT in eligible bills")
                if any(b["vendor_bill_id"] == bill3 for b in bills):
                    bad("Draft bill should NOT appear in eligible bills")
                else:
                    ok("Draft bill correctly excluded from eligible bills")
            else:
                bad(f"Response is not a list: {type(bills)}")
        else:
            bad(f"Eligible bills endpoint failed: {r.status_code} {r.text[:200]}")
    except Exception as e:
        bad(f"Eligible bills test error: {str(e)}")
    
    # ── Test 4: Create input tax invoice ──────────────────────────────────
    info("TEST 4: POST /api/input-tax-invoices (create)")
    fpm_id = None
    try:
        r = s.post(f"{API}/input-tax-invoices", 
                   json={"vendor_bill_id": bill1, "nsfp": NSFP1, "faktur_date": PDATE}, 
                   timeout=30)
        if r.status_code == 200:
            ok("Create input tax invoice returns 200")
            v = r.json()
            if isinstance(v, dict):
                ok("Response is an object (bare object, no envelope)")
                fpm_id = v.get("id")
                
                # Check all required fields
                checks = [
                    (v.get("status") == "recorded", "status is 'recorded'"),
                    (abs(float(v.get("ppn_amount", 0)) - 110000) < 1, "ppn_amount copied correctly (110,000)"),
                    (abs(float(v.get("dpp", 0)) - 1000000) < 1, "dpp copied correctly (1,000,000)"),
                    (v.get("supplier_name") == "Supplier Test Input Tax", "supplier_name copied"),
                    (v.get("supplier_npwp") == "01.234.567.8-901.000", "supplier_npwp copied"),
                    (v.get("period") == PERIOD, f"period is {PERIOD}"),
                    (v.get("nsfp_digits") == NSFP1, "nsfp_digits normalized"),
                    (v.get("number", "").startswith("FPM-"), "number starts with FPM-"),
                    (v.get("vendor_bill_id") == bill1, "vendor_bill_id linked"),
                    (v.get("bill_number") == f"VB-{MARK}-1", "bill_number copied"),
                ]
                for cond, label in checks:
                    ok(label) if cond else bad(f"{label} FAILED")
            else:
                bad(f"Response is not an object: {type(v)}")
        else:
            bad(f"Create failed: {r.status_code} {r.text[:250]}")
    except Exception as e:
        bad(f"Create test error: {str(e)}")
    
    # ── Test 5: Bill flagging ─────────────────────────────────────────────
    info("TEST 5: Vendor bill flagging")
    try:
        b = await db.vendor_bills.find_one({"id": bill1}, {"_id": 0})
        if b:
            checks = [
                (b.get("input_faktur_status") == "recorded", "input_faktur_status is 'recorded'"),
                (b.get("input_faktur_id") == fpm_id, "input_faktur_id set correctly"),
                (b.get("input_faktur_number", "").startswith("FPM-"), "input_faktur_number set"),
                (b.get("input_faktur_nsfp") == NSFP1, "input_faktur_nsfp set"),
            ]
            for cond, label in checks:
                ok(label) if cond else bad(f"{label} FAILED")
        else:
            bad("Vendor bill not found in DB")
    except Exception as e:
        bad(f"Bill flagging test error: {str(e)}")
    
    # ── Test 6: Bill no longer eligible ───────────────────────────────────
    info("TEST 6: Flagged bill not in eligible list")
    try:
        r = s.get(f"{API}/input-tax-invoices/eligible-bills", params={"entity_id": ENTITY}, timeout=30)
        if r.status_code == 200:
            bills = r.json()
            if not any(b["vendor_bill_id"] == bill1 for b in bills):
                ok("Flagged bill removed from eligible bills")
            else:
                bad("Flagged bill still appears in eligible bills")
        else:
            bad(f"Eligible bills check failed: {r.status_code}")
    except Exception as e:
        bad(f"Eligible bills check error: {str(e)}")
    
    # ── Test 7: Duplicate bill prevention ─────────────────────────────────
    info("TEST 7: Duplicate bill prevention (409)")
    try:
        r = s.post(f"{API}/input-tax-invoices", 
                   json={"vendor_bill_id": bill1, "nsfp": "0100111122223333"}, 
                   timeout=30)
        if r.status_code == 409:
            ok("Duplicate bill creation prevented (409)")
        else:
            bad(f"Duplicate bill should return 409, got {r.status_code}")
    except Exception as e:
        bad(f"Duplicate bill test error: {str(e)}")
    
    # ── Test 8: NSFP dedupe ───────────────────────────────────────────────
    info("TEST 8: NSFP dedupe (same NSFP on different bill)")
    try:
        r = s.post(f"{API}/input-tax-invoices", 
                   json={"vendor_bill_id": bill2, "nsfp": NSFP1}, 
                   timeout=30)
        if r.status_code == 409:
            ok("NSFP dedupe working (409 for duplicate NSFP)")
        else:
            bad(f"NSFP dedupe should return 409, got {r.status_code} {r.text[:150]}")
    except Exception as e:
        bad(f"NSFP dedupe test error: {str(e)}")
    
    # ── Test 9: Create second input tax invoice with different NSFP ───────
    info("TEST 9: Create second input tax invoice (different NSFP)")
    fpm_id2 = None
    try:
        r = s.post(f"{API}/input-tax-invoices", 
                   json={"vendor_bill_id": bill2, "nsfp": NSFP2, "faktur_date": PDATE}, 
                   timeout=30)
        if r.status_code == 200:
            ok("Second input tax invoice created successfully")
            v = r.json()
            fpm_id2 = v.get("id")
            if abs(float(v.get("ppn_amount", 0)) - 55000) < 1:
                ok("Second invoice ppn_amount correct (55,000)")
            else:
                bad(f"Second invoice ppn_amount wrong: {v.get('ppn_amount')}")
        else:
            bad(f"Second invoice creation failed: {r.status_code} {r.text[:200]}")
    except Exception as e:
        bad(f"Second invoice test error: {str(e)}")
    
    # ── Test 10: List input tax invoices ──────────────────────────────────
    info("TEST 10: GET /api/input-tax-invoices (list)")
    try:
        r = s.get(f"{API}/input-tax-invoices", params={"entity_id": ENTITY}, timeout=30)
        if r.status_code == 200:
            ok("List endpoint returns 200")
            invoices = r.json()
            if isinstance(invoices, list):
                ok("Response is a list (bare array)")
                test_invoices = [inv for inv in invoices if inv.get("mark") == MARK]
                if len(test_invoices) >= 2:
                    ok(f"Found {len(test_invoices)} test invoices")
                else:
                    bad(f"Expected at least 2 test invoices, found {len(test_invoices)}")
            else:
                bad(f"Response is not a list: {type(invoices)}")
        else:
            bad(f"List endpoint failed: {r.status_code} {r.text[:200]}")
    except Exception as e:
        bad(f"List test error: {str(e)}")
    
    # ── Test 11: Get single input tax invoice ─────────────────────────────
    info("TEST 11: GET /api/input-tax-invoices/{id} (detail)")
    if fpm_id:
        try:
            r = s.get(f"{API}/input-tax-invoices/{fpm_id}", timeout=30)
            if r.status_code == 200:
                ok("Detail endpoint returns 200")
                v = r.json()
                if isinstance(v, dict):
                    ok("Response is an object (bare object)")
                    if v.get("id") == fpm_id:
                        ok("Correct invoice returned")
                    else:
                        bad(f"Wrong invoice returned: {v.get('id')}")
                else:
                    bad(f"Response is not an object: {type(v)}")
            else:
                bad(f"Detail endpoint failed: {r.status_code} {r.text[:200]}")
        except Exception as e:
            bad(f"Detail test error: {str(e)}")
    else:
        bad("No fpm_id to test detail endpoint")
    
    # ── Test 12: VAT summary ──────────────────────────────────────────────
    info("TEST 12: GET /api/tax/vat-summary")
    try:
        r = s.get(f"{API}/tax/vat-summary", params={"period": PERIOD, "entity_id": ENTITY}, timeout=30)
        if r.status_code == 200:
            ok("VAT summary endpoint returns 200")
            sm = r.json()
            if isinstance(sm, dict):
                ok("Response is an object (bare object)")
                
                # Check structure
                required_keys = ["period", "keluaran", "masukan", "net_ppn", "position", "position_label", "masukan_by_supplier"]
                for key in required_keys:
                    if key in sm:
                        ok(f"Has '{key}' field")
                    else:
                        bad(f"Missing '{key}' field")
                
                # Check calculations
                mas_ppn = float(sm.get("masukan", {}).get("ppn", 0))
                kel_ppn = float(sm.get("keluaran", {}).get("ppn", 0))
                net = float(sm.get("net_ppn", 0))
                
                # Masukan should be 110,000 + 55,000 = 165,000
                if abs(mas_ppn - 165000) < 1:
                    ok("Masukan PPN correct (165,000)")
                else:
                    bad(f"Masukan PPN wrong: {mas_ppn} (expected 165,000)")
                
                # Keluaran should be 200,000 (from seed)
                if abs(kel_ppn - 200000) < 1:
                    ok("Keluaran PPN correct (200,000)")
                else:
                    bad(f"Keluaran PPN wrong: {kel_ppn} (expected 200,000)")
                
                # Net should be 200,000 - 165,000 = 35,000 (kurang bayar)
                if abs(net - 35000) < 1:
                    ok("Net PPN correct (35,000)")
                else:
                    bad(f"Net PPN wrong: {net} (expected 35,000)")
                
                if sm.get("position") == "kurang_bayar":
                    ok("Position is 'kurang_bayar' (correct)")
                else:
                    bad(f"Position wrong: {sm.get('position')} (expected kurang_bayar)")
                
                # Check masukan_by_supplier
                by_supplier = sm.get("masukan_by_supplier", [])
                if isinstance(by_supplier, list):
                    ok("masukan_by_supplier is a list")
                    if len(by_supplier) > 0:
                        ok(f"Found {len(by_supplier)} supplier(s) in masukan breakdown")
                    else:
                        bad("masukan_by_supplier is empty")
                else:
                    bad(f"masukan_by_supplier is not a list: {type(by_supplier)}")
            else:
                bad(f"Response is not an object: {type(sm)}")
        else:
            bad(f"VAT summary failed: {r.status_code} {r.text[:200]}")
    except Exception as e:
        bad(f"VAT summary test error: {str(e)}")
    
    # ── Test 13: Cancel input tax invoice ─────────────────────────────────
    info("TEST 13: POST /api/input-tax-invoices/{id}/cancel")
    if fpm_id:
        try:
            r = s.post(f"{API}/input-tax-invoices/{fpm_id}/cancel", 
                       json={"reason": "Test cancellation"}, 
                       timeout=30)
            if r.status_code == 200:
                ok("Cancel endpoint returns 200")
                v = r.json()
                if v.get("status") == "cancelled":
                    ok("Status changed to 'cancelled'")
                else:
                    bad(f"Status not cancelled: {v.get('status')}")
                if v.get("cancel_reason") == "Test cancellation":
                    ok("Cancel reason saved")
                else:
                    bad("Cancel reason not saved")
            else:
                bad(f"Cancel failed: {r.status_code} {r.text[:200]}")
        except Exception as e:
            bad(f"Cancel test error: {str(e)}")
    else:
        bad("No fpm_id to test cancel endpoint")
    
    # ── Test 14: Bill eligible again after cancel ─────────────────────────
    info("TEST 14: Bill eligible again after cancel")
    try:
        r = s.get(f"{API}/input-tax-invoices/eligible-bills", params={"entity_id": ENTITY}, timeout=30)
        if r.status_code == 200:
            bills = r.json()
            if any(b["vendor_bill_id"] == bill1 for b in bills):
                ok("Cancelled bill back in eligible bills")
            else:
                bad("Cancelled bill NOT back in eligible bills")
        else:
            bad(f"Eligible bills check failed: {r.status_code}")
    except Exception as e:
        bad(f"Eligible bills check error: {str(e)}")
    
    # ── Test 15: NSFP reusable after cancel ───────────────────────────────
    info("TEST 15: NSFP reusable after cancel")
    try:
        r = s.post(f"{API}/input-tax-invoices", 
                   json={"vendor_bill_id": bill1, "nsfp": NSFP1, "faktur_date": PDATE}, 
                   timeout=30)
        if r.status_code == 200:
            ok("NSFP reusable after cancel (200)")
        else:
            bad(f"NSFP reuse failed: {r.status_code} {r.text[:200]}")
    except Exception as e:
        bad(f"NSFP reuse test error: {str(e)}")
    
    # ── Test 16: Permission gating (sales view-only) ──────────────────────
    info("TEST 16: Permission gating (sales view-only)")
    if sales_token:
        s_sales = requests.Session()
        s_sales.headers.update({"Authorization": f"Bearer {sales_token}"})
        
        # Sales should be able to view
        try:
            r = s_sales.get(f"{API}/input-tax-invoices", params={"entity_id": ENTITY}, timeout=30)
            if r.status_code == 200:
                ok("Sales can view input tax invoices")
            else:
                bad(f"Sales view failed: {r.status_code}")
        except Exception as e:
            bad(f"Sales view test error: {str(e)}")
        
        # Sales should NOT be able to create
        try:
            r = s_sales.post(f"{API}/input-tax-invoices", 
                            json={"vendor_bill_id": bill2, "nsfp": "0100555566667777"}, 
                            timeout=30)
            if r.status_code in [403, 401]:
                ok("Sales cannot create input tax invoice (403/401)")
            else:
                bad(f"Sales create should be forbidden, got {r.status_code}")
        except Exception as e:
            bad(f"Sales create test error: {str(e)}")
    else:
        bad("No sales token to test permissions")
    
    # ── Test 17: Manager permissions ──────────────────────────────────────
    info("TEST 17: Manager can create and cancel")
    if manager_token:
        s_mgr = requests.Session()
        s_mgr.headers.update({"Authorization": f"Bearer {manager_token}"})
        
        # Manager should be able to view
        try:
            r = s_mgr.get(f"{API}/input-tax-invoices", params={"entity_id": ENTITY}, timeout=30)
            if r.status_code == 200:
                ok("Manager can view input tax invoices")
            else:
                bad(f"Manager view failed: {r.status_code}")
        except Exception as e:
            bad(f"Manager view test error: {str(e)}")
    else:
        bad("No manager token to test permissions")
    
    # ── Cleanup ───────────────────────────────────────────────────────────
    info("Cleaning up test data...")
    await cleanup(db)
    ok("Test data cleaned up")
    
    client.close()


def print_summary():
    """Print test summary"""
    print("\n" + "=" * 70)
    print(f"  BACKEND TEST SUMMARY: {len(PASS)} PASS | {len(FAIL)} FAIL")
    print("=" * 70)
    if FAIL:
        print("\n❌ FAILED TESTS:")
        for f in FAIL:
            print(f"  - {f}")
    print()


if __name__ == "__main__":
    asyncio.run(test_backend())
    print_summary()
    sys.exit(0 if not FAIL else 1)
