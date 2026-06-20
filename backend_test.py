"""
Backend Testing for Kain Nusantara ERP/WMS
Tests P0-A (deletion-safe doc numbering) and P1-C (multi-level approval)
"""
import requests
import sys
from typing import Dict, Any, Optional

BASE_URL = "https://handoff-continuation.preview.emergentagent.com/api"

class TestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.admin_token = None
        self.manager_token = None
        self.failures = []

    def log(self, message: str, level: str = "INFO"):
        prefix = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(level, "•")
        print(f"{prefix} {message}")

    def test(self, name: str, method: str, endpoint: str, expected_status: int,
             data: Optional[Dict] = None, token: Optional[str] = None,
             check_response: Optional[callable] = None) -> tuple[bool, Any]:
        """Run a single API test"""
        self.tests_run += 1
        url = f"{BASE_URL}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.log(f"Test #{self.tests_run}: {name}", "INFO")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            response_data = {}
            try:
                response_data = response.json()
            except:
                pass

            if success:
                # Additional response checks
                if check_response and not check_response(response_data):
                    success = False
                    self.log(f"  Response validation failed", "FAIL")
                    self.failures.append(f"{name}: Response validation failed")
                    self.tests_failed += 1
                else:
                    self.tests_passed += 1
                    self.log(f"  PASSED (status: {response.status_code})", "PASS")
            else:
                self.log(f"  FAILED - Expected {expected_status}, got {response.status_code}", "FAIL")
                if response_data:
                    self.log(f"  Response: {response_data}", "FAIL")
                self.failures.append(f"{name}: Expected {expected_status}, got {response.status_code}")
                self.tests_failed += 1

            return success, response_data

        except Exception as e:
            self.log(f"  FAILED - Error: {str(e)}", "FAIL")
            self.failures.append(f"{name}: {str(e)}")
            self.tests_failed += 1
            return False, {}

    def login(self, email: str, password: str) -> Optional[str]:
        """Login and return token"""
        self.log(f"Logging in as {email}...", "INFO")
        success, data = self.test(
            f"Login {email}",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'token' in data:
            self.log(f"  Login successful, token obtained", "PASS")
            return data['token']
        self.log(f"  Login failed", "FAIL")
        return None

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100) if self.tests_run > 0 else 0:.1f}%")
        
        if self.failures:
            print("\n" + "="*70)
            print("FAILURES:")
            print("="*70)
            for i, failure in enumerate(self.failures, 1):
                print(f"{i}. {failure}")
        
        print("="*70)


def main():
    runner = TestRunner()
    
    print("="*70)
    print("KAIN NUSANTARA ERP/WMS - BACKEND TESTING")
    print("Testing P0-A (Deletion-safe numbering) & P1-C (Multi-level approval)")
    print("="*70)
    print()

    # ========== AUTHENTICATION ==========
    print("\n" + "="*70)
    print("PHASE 1: AUTHENTICATION")
    print("="*70)
    
    runner.admin_token = runner.login("admin@kainnusantara.id", "demo12345")
    if not runner.admin_token:
        print("❌ CRITICAL: Admin login failed. Cannot continue.")
        return 1
    
    runner.manager_token = runner.login("manager@kainnusantara.id", "demo12345")
    if not runner.manager_token:
        print("❌ CRITICAL: Manager login failed. Cannot continue.")
        return 1

    # ========== P0-A: DELETION-SAFE DOCUMENT NUMBERING ==========
    print("\n" + "="*70)
    print("PHASE 2: P0-A - DELETION-SAFE DOCUMENT NUMBERING")
    print("="*70)
    
    # Get existing POs to check current max number
    runner.log("Checking existing PO numbers...", "INFO")
    success, pos = runner.test(
        "List existing POs",
        "GET",
        "purchase-orders",
        200,
        token=runner.admin_token
    )
    
    if success:
        po_numbers = [po.get('po_number', '') for po in pos if po.get('po_number', '').startswith('PO-')]
        runner.log(f"  Found {len(po_numbers)} POs", "INFO")
        if po_numbers:
            max_po = max(po_numbers)
            runner.log(f"  Current max PO number: {max_po}", "INFO")
    
    # Create new PO - should get PO-00012 (after PO-00011)
    runner.log("Creating new PO to test max-based numbering...", "INFO")
    new_po_data = {
        "warehouse_id": "wh_jakarta",
        "supplier_name": "Test Supplier",
        "supplier_contact": "Test Contact",
        "items": [
            {
                "product_id": "prod_batik_mega",
                "quantity": 10.0,
                "unit": "meter",
                "price": 185000
            }
        ],
        "expected_delivery_date": "2026-07-01",
        "notes": "Test PO for deletion-safe numbering",
        "created_by": "Admin"
    }
    
    success, new_po = runner.test(
        "Create new PO (test max-based numbering)",
        "POST",
        "purchase-orders",
        200,
        data=new_po_data,
        token=runner.admin_token,
        check_response=lambda r: r.get('po_number') == 'PO-00012'
    )
    
    if success:
        runner.log(f"  New PO number: {new_po.get('po_number')}", "PASS")
        if new_po.get('po_number') == 'PO-00012':
            runner.log(f"  ✓ Correct! Max-based numbering working (expected PO-00012)", "PASS")
        else:
            runner.log(f"  ✗ WRONG! Expected PO-00012, got {new_po.get('po_number')}", "FAIL")
    
    # Test SO numbering
    runner.log("Checking SO numbering...", "INFO")
    success, sos = runner.test(
        "List existing SOs",
        "GET",
        "sales-orders",
        200,
        token=runner.admin_token
    )
    
    if success:
        so_numbers = [so.get('number', '') for so in sos if so.get('number', '').startswith('SO-')]
        if so_numbers:
            max_so = max(so_numbers)
            runner.log(f"  Current max SO number: {max_so}", "INFO")

    # ========== P1-C: MULTI-LEVEL APPROVAL BACKEND ==========
    print("\n" + "="*70)
    print("PHASE 3: P1-C - MULTI-LEVEL APPROVAL (BACKEND)")
    print("="*70)
    
    # Test PO-00010 (2 levels, both pending)
    runner.log("Testing PO-00010 (2-level approval, both pending)...", "INFO")
    
    # (a) Manager approves PO-00010 -> should stay waiting_approval, move to L2
    runner.log("(a) Manager approves PO-00010 (L1)...", "INFO")
    success, po_010_after_l1 = runner.test(
        "Manager approves PO-00010 L1",
        "POST",
        "purchase-orders/po_010/approve",
        200,
        token=runner.manager_token,
        check_response=lambda r: (
            r.get('status') == 'waiting_approval' and
            r.get('approval_level_current') == 2 and
            r.get('required_approval_role') == 'admin'
        )
    )
    
    if success:
        runner.log(f"  Status: {po_010_after_l1.get('status')}", "INFO")
        runner.log(f"  Current level: {po_010_after_l1.get('approval_level_current')}", "INFO")
        runner.log(f"  Required role: {po_010_after_l1.get('required_approval_role')}", "INFO")
        chain = po_010_after_l1.get('approval_chain', [])
        if len(chain) >= 2:
            runner.log(f"  L1 status: {chain[0].get('status')}", "INFO")
            runner.log(f"  L2 status: {chain[1].get('status')}", "INFO")
    
    # (b) Manager tries to approve PO-00010 again -> should get 403
    runner.log("(b) Manager tries to approve PO-00010 again (should fail - needs admin)...", "INFO")
    runner.test(
        "Manager tries PO-00010 L2 (should fail)",
        "POST",
        "purchase-orders/po_010/approve",
        403,
        token=runner.manager_token
    )
    
    # (c) Admin approves PO-00010 -> should become 'pending', fully approved, inbound task created
    runner.log("(c) Admin approves PO-00010 (L2 - final)...", "INFO")
    success, po_010_final = runner.test(
        "Admin approves PO-00010 L2 (final)",
        "POST",
        "purchase-orders/po_010/approve",
        200,
        token=runner.admin_token,
        check_response=lambda r: (
            r.get('status') == 'pending' and
            r.get('approval_status') == 'approved'
        )
    )
    
    if success:
        runner.log(f"  Status: {po_010_final.get('status')}", "PASS")
        runner.log(f"  Approval status: {po_010_final.get('approval_status')}", "PASS")
        chain = po_010_final.get('approval_chain', [])
        if len(chain) >= 2:
            runner.log(f"  L1 status: {chain[0].get('status')} (by {chain[0].get('approved_by')})", "INFO")
            runner.log(f"  L2 status: {chain[1].get('status')} (by {chain[1].get('approved_by')})", "INFO")
        
        # Check if inbound task was created
        runner.log("  Checking if inbound task was created...", "INFO")
        success_task, tasks = runner.test(
            "Get inbound tasks for PO-00010",
            "GET",
            "inbound/tasks?po_id=po_010",
            200,
            token=runner.admin_token
        )
        if success_task:
            runner.log(f"  Inbound tasks created: {len(tasks)}", "PASS" if len(tasks) > 0 else "FAIL")
    
    # Test PO-00011 (L1 approved by manager, L2 admin pending)
    runner.log("\nTesting PO-00011 (L1 approved, L2 pending)...", "INFO")
    
    # Manager tries to approve PO-00011 -> should get 403 (needs admin)
    runner.log("Manager tries to approve PO-00011 (should fail - needs admin)...", "INFO")
    runner.test(
        "Manager tries PO-00011 (should fail)",
        "POST",
        "purchase-orders/po_011/approve",
        403,
        token=runner.manager_token
    )
    
    # Admin approves PO-00011 -> should become fully approved
    runner.log("Admin approves PO-00011 (L2 - final)...", "INFO")
    success, po_011_final = runner.test(
        "Admin approves PO-00011 L2 (final)",
        "POST",
        "purchase-orders/po_011/approve",
        200,
        token=runner.admin_token,
        check_response=lambda r: (
            r.get('status') == 'pending' and
            r.get('approval_status') == 'approved'
        )
    )
    
    if success:
        runner.log(f"  Status: {po_011_final.get('status')}", "PASS")
        runner.log(f"  Approval status: {po_011_final.get('approval_status')}", "PASS")

    # ========== P0-B: SSOT AP (Vendor Bill) ==========
    print("\n" + "="*70)
    print("PHASE 4: P0-B - SSOT AP (VENDOR BILL UNIFICATION)")
    print("="*70)
    
    runner.log("Testing P0-B: PO payment endpoint should be blocked...", "INFO")
    
    # Test that POST /api/purchase-orders/{id}/pay returns 400
    runner.log("(a) Attempting to pay PO directly (should return 400)...", "INFO")
    success, pay_response = runner.test(
        "POST /api/purchase-orders/po_009/pay (should be blocked)",
        "POST",
        "purchase-orders/po_009/pay",
        400,
        data={"amount": 1000000, "payment_method": "transfer", "notes": "Test payment"},
        token=runner.admin_token
    )
    
    if success:
        detail = pay_response.get('detail', '')
        if 'Vendor Bill' in detail or 'Tagihan Supplier' in detail:
            runner.log(f"  ✓ Correct error message directing to Vendor Bill", "PASS")
        else:
            runner.log(f"  ⚠ Error message doesn't mention Vendor Bill: {detail}", "WARN")
    
    # Test Vendor Bill endpoints (SSOT) are healthy
    runner.log("(b) Testing Vendor Bill endpoints (SSOT)...", "INFO")
    
    success, bills = runner.test(
        "GET /api/vendor-bills (SSOT endpoint)",
        "GET",
        "vendor-bills",
        200,
        token=runner.admin_token
    )
    
    if success:
        runner.log(f"  Vendor bills endpoint healthy (found {len(bills)} bills)", "PASS")
    
    success, summary = runner.test(
        "GET /api/vendor-bills/payables/summary",
        "GET",
        "vendor-bills/payables/summary",
        200,
        token=runner.admin_token
    )
    
    if success:
        runner.log(f"  Payables summary endpoint healthy", "PASS")
        if 'total_outstanding' in summary:
            runner.log(f"  Total outstanding AP: {summary.get('total_outstanding', 0)}", "INFO")
    
    # Test PO list still works and has billing summary fields
    runner.log("(c) Testing PO list has billing summary fields...", "INFO")
    success, pos_check = runner.test(
        "GET /api/purchase-orders (check billing fields)",
        "GET",
        "purchase-orders",
        200,
        token=runner.admin_token
    )
    
    if success and len(pos_check) > 0:
        sample_po = pos_check[0]
        has_billing = 'billed_total' in sample_po or 'unbilled_total' in sample_po
        if has_billing:
            runner.log(f"  ✓ PO has billing summary fields", "PASS")
        else:
            runner.log(f"  ⚠ PO missing billing summary fields (may be OK if no bills yet)", "WARN")

    # ========== P1-C: SoD (Segregation of Duties) ==========
    print("\n" + "="*70)
    print("PHASE 5: P1-C - SEGREGATION OF DUTIES (SoD)")
    print("="*70)
    
    runner.log("Testing SoD: creator cannot approve their own PO...", "INFO")
    runner.log("Note: Seed POs created by 'Admin' without created_by_id, so SoD won't block.", "WARN")
    runner.log("Creating a new PO with created_by_id to test SoD...", "INFO")
    
    # Create PO that requires approval
    sod_po_data = {
        "warehouse_id": "wh_jakarta",
        "supplier_name": "Test Supplier SoD",
        "supplier_contact": "Test Contact",
        "items": [
            {
                "product_id": "prod_batik_mega",
                "quantity": 1000.0,  # Large qty to trigger approval
                "unit": "meter",
                "price": 185000
            }
        ],
        "expected_delivery_date": "2026-07-01",
        "notes": "Test PO for SoD",
        "created_by": "Dewi Rahayu"  # Manager creates it
    }
    
    success, sod_po = runner.test(
        "Manager creates PO (should need approval)",
        "POST",
        "purchase-orders",
        200,
        data=sod_po_data,
        token=runner.manager_token,
        check_response=lambda r: r.get('approval_required') == True
    )
    
    if success and sod_po.get('approval_required'):
        po_id = sod_po.get('id')
        runner.log(f"  Created PO {sod_po.get('po_number')} (id: {po_id})", "INFO")
        runner.log(f"  Created by: {sod_po.get('created_by')} (id: {sod_po.get('created_by_id')})", "INFO")
        
        # Manager tries to approve their own PO -> should get 403 (SoD)
        runner.log("Manager tries to approve their own PO (should fail - SoD)...", "INFO")
        runner.test(
            "Manager approves own PO (should fail - SoD)",
            "POST",
            f"purchase-orders/{po_id}/approve",
            403,
            token=runner.manager_token
        )

    # ========== PRINT SUMMARY ==========
    runner.print_summary()
    
    return 0 if runner.tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
