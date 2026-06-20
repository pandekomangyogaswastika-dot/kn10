# Development Plan — Kain Nusantara (WMS/ERP) — Smart Guidelines + Seed + Documentation + Discovery E‑Questionnaire (v2.1)

---

# 🧭 SESSION HANDOFF + REVIEW MENYELURUH PURCHASING (Sesi #041 — 20 Jun 2026)

> **Untuk agent berikutnya.** Sesi ini TIDAK menulis fitur baru — fokus pada **review menyeluruh modul Pembelian** (scope, integrasi data, business process, flow/UX, bug, I/O, performa) + handoff. Bahasa kerja owner: **Bahasa Indonesia**. Backend & frontend RUNNING. Gate `verify_data_integrity` = **119 PASS / 0 FAIL**. esbuild exit 0.
>
> ⚠️ **WAJIB saat re-copy repo / restart container:** `cd /app/frontend && yarn install` (terapkan `resolutions: webpack-dev-server@4.15.2`, kalau tidak → layar putih `onAfterSetupMiddleware`). Backend deps sudah terpasang.

## 0) Kredensial uji
admin@kainnusantara.id · manager@kainnusantara.id · sales@… · warehouse@… — semua password **demo12345**. (Tombol quick-login hanya mengisi email; tetap klik **Masuk**.)

## 1) Status modul Pembelian (13 menu — semua ter-wire)
PO · Purchase Requisition · RFQ/Quotation · Saran Reorder · Pemasok · Approval Pembelian · Retur Beli · Tagihan Supplier (Vendor Bill/3-way) · Landed Cost (HPP) · Faktur Pajak Masukan · Hutang Supplier (AP) · BOM Printing (coming soon) · Pengelolaan Kas.

**Sudah SELESAI & terverifikasi (sesi-sesi lalu):** Phase 5.1 PPN/Diskon PO · 5.2 Vendor Bill + 3-Way · 5.3 Dye Lot/Grade · 5.4 Landed Cost · 5.5 Faktur Pajak Masukan · 6.1 RFQ · 6.2 4-Point Inspection. **Phase 7.1 Multi-Level Approval = BACKEND SELESAI (POC lolos), FRONTEND BELUM (lihat §3-Task-A).**

## 2) ✅ Yang sudah BENAR (terverifikasi sesi ini)
- **Pricing konsisten Sales↔Purchasing**: `compute_order_pricing(cfg_section=...)` dipakai bersama → diskon item/order + DPP + PPN 11% invariant-safe (`total_amount` tetap GROSS).
- **Multi-level approval BACKEND solid**: `build_approval_chain` + `current_pending_level` + `role_satisfies` + SoD (pembuat ≠ approver). Terbukti: PO ≥500jt → chain 2 level (Manager→Direksi/admin). PO-00011/00012 punya `approval_chain` len=2.
- **Traceability tekstil PO→GR→roll→Sales**: GR set `dye_lot`/`grade`/`base_unit_cost` (dari harga PO) per roll; `roll_service` allocation menghormati `dye_lot_strict` (group by dye_lot). Field roll: `dye_lot, grade, qc_grade, defects, owner_entity_id, unit_cost, base_unit_cost, landed_cost_total` lengkap.
- **3-Way Matching** (PO ordered ↔ GR received ↔ Bill billed) + toleransi qty/harga + over-billing blocked + SoD approve.
- **Faktur Pajak Masukan** disnapshot dari Vendor Bill (DPP/PPN), NSFP dedupe (digit-only), rekap PPN Masukan vs Keluaran per periode → posisi kurang/lebih bayar.
- **RBAC nav = permissions_config** (hasil fix H1 lampau).

## 3) ⚠️ KEKELIRUAN / GAP DITEMUKAN (urut prioritas — untuk diperbaiki)

### 🔴 P0-A — [RESOLVED ✅ Sesi #042] Tabrakan nomor PO + artefak test tertinggal
- **FIX:** Helper bersama `core_utils.next_doc_number(collection, field, prefix)` (max-based, deletion-safe) menggantikan SEMUA generator `count_documents()+1`: PO (`purchase_orders.py`), PR→PO (`purchase_requisition_service.py`), RFQ-award→PO (`rfq_service.py`), SO (`sales_orders.py`), TRF (`transfers.py` ×2), SJ (`shipment_service.py`), FKT (`tax_invoice_service.py`), dan inline CASH (`purchase_orders.py`/`landed_cost.py`/`vendor_bills.py`).
- **Bukti:** POC `test_number_series_poc.py` **12/12** (reproduksi skenario hapus-tengah: count+1 → PO-00012 DUPLIKAT vs next_doc_number → PO-00013 AMAN). Real API: create PO → PO-00010 (max+1). Gate seed_reset **119/0/0**. testing_agent iter_33 backend 13/13.
- Generator yang SUDAH aman sebelumnya (SUP/VB/RFQ#/PR#/FPM/LCV/CASH-helper) dibiarkan (lulus gate).

### 🔴 P0-B — [INTEGRASI] Dualisme AP (potensi double-count hutang & kas) — MENUNGGU KEPUTUSAN OWNER
- **Dua sistem AP berjalan paralel tanpa rekonsiliasi:**
  - Menu **Hutang Supplier (AP)** = `/purchase-orders/payables/summary` + endpoint PO `/pay` → AP dihitung langsung dari `grand_total` PO (`_po_financials`).
  - Menu **Tagihan Supplier** = `/vendor-bills/payables/summary` + endpoint bill `/pay` → AP dari Vendor Bill posted (`bill_financials`).
- **Masalah:** bayar Vendor Bill TIDAK mengurangi `outstanding` PO, dan payables PO TIDAK mengurangi nilai yang sudah ditagih bill. `sync_po_billing` hanya menulis `billed_total`/`unbilled_total` (informasional) tapi `_po_financials` mengabaikannya. → Satu PO bisa tampil outstanding penuh di **Hutang Supplier (AP)** sekaligus di **Tagihan Supplier**; keduanya juga bisa mencatat `cash_transaction` keluar terpisah → **hutang & kas keluar dobel**.
- **Catatan:** belum termanifestasi di data seekarang (vendor_bills=0). Tapi arsitektur mengizinkannya begitu Vendor Bill dipakai.
- **Rekomendasi (perlu keputusan owner):** Jadikan Vendor Bill satu-satunya sumber AP. Pilihan: (a) `_po_financials`/payables PO menampilkan **hanya unbilled** (= grand_total − billed_total) + sembunyikan tombol PO `/pay` bila sudah ada bill; atau (b) retire menu "Hutang Supplier (AP)" PO-based, arahkan ke Vendor Bill. Tegaskan PO `/pay` hanya untuk DP/uang muka (kalau memang dibutuhkan) dengan label jelas.

### 🟠 P1-C — [DONE ✅ Sesi #042] Frontend Multi-Level Approval
- **File:** `/app/frontend/src/features/purchasing/PurchaseApprovalView.jsx` (419 baris).
- **Selesai:** (1) render `approval_chain[]` sebagai stepper per-tingkat (L1 Manager ✓ / L2 Direksi ⏳) + nama approver + tanggal; (2) tombol Setujui **role-aware** via `roleSatisfies(user.role, pendingLevel.required_role)` + cek SoD (pembuat tak bisa approve) → bila tak memenuhi tampil kunci "Menunggu {role}"; (3) progres "Tingkat X dari Y" + banner alasan. Backward-compatible untuk PO lama tanpa chain (sintesis 1 tingkat).
- **Demo data seed:** PO-00010 (2-tingkat, keduanya pending) & PO-00011 (L1 approved manager, L2 admin pending).
- **Bukti:** testing_agent iter_33 — backend 13/13, frontend 100%, 0 bug (1 React-key minor sudah diperbaiki di `ManagerDashboard.jsx`). E2E API: manager approve L1 → L2 → manager 403 → admin approve L2 → fully approved + inbound task. esbuild 0, ux_audit 0 ERROR, compliance 0 FAIL.

### 🟡 P2-D — [COSTING] HPP/COGS belum nyambung ke Sales (deferred, by design)
- Semua 34 seed `inventory_rolls` punya `unit_cost = None`. `base_unit_cost` hanya terisi untuk GR baru. Landed-cost basis "nilai" jatuh ke fallback kuantitas untuk roll seed. COGS belum dipakai di margin Sales. **Sesuai KN_15 (HPP ditunda Fase 4)** — bukan bug, tapi catat untuk akurasi costing nanti.

### 🟢 P3-E — Minor
- esbuild WARNING pre-existing di **Sales** `CreateSpecialOrderForm.jsx:314` (`>` literal dalam teks JSX) — kosmetik, sebaiknya ganti `{'>'}`.
- Dua jalur menulis `roll.grade`: `qc_service.process_qc_decision` (saat accept) & `qc_inspection_service.inspect_roll` (4-point). Keduanya per-roll; pastikan urutan operasional (inspeksi 4-point dulu → accept) agar tidak saling menimpa. Verifikasi saat uji QC.

### 🟢 P3-F — Performa (sehat untuk skala sekarang; catatan untuk skala besar)
- List endpoint pakai cap `.to_list(200..2000)` & aggregasi payables menghitung `_po_financials`/`bill_financials` per-dokumen di Python (loop) — **aman di data sekarang** (PO 11, rolls 34). Untuk skala ribuan: pertimbangkan index (`entity_id`, `status`, `supplier_id`, `po_number`/`bill_number`) + paginasi server-side + pra-hitung agregat. Tidak ada N+1 query berat pada path purchasing yang ditemukan.

## 4) Backlog (disetujui owner, urut)
- **P1:** Catch-weight / Dual-UoM pembelian (beli kg, terima kg aktual + konversi).
- **P2:** Phase 7.2 PO Amendment / Version History · Blanket/Contract PO (call-off) · Kirim PO PDF ke supplier (email) · Multi-currency/FX · Budget/Commitment Control.

## 5) Rekomendasi URUTAN aksi agent berikutnya
1. **Bersihkan state** (`seed_reset.sh`) + perbaiki generator nomor PO/PR/RFQ→PO ke max-based → tutup P0-A (cegah duplikat nomor). 
2. **Selesaikan Frontend Phase 7.1** (P1-C) — task yang di-pause; backend sudah siap.
3. **Putuskan & rapikan AP dualism** (P0-B) bersama owner (butuh keputusan desain).
4. Lanjut backlog: Phase 7.2 PO Amendment, lalu Catch-weight.
> Setiap perubahan WAJIB lewat gate: `seed_reset.sh` → `health_check.py` → `verify_data_integrity.py` → `verify_api_contract.py` → `ux_audit.py` → `check_nav_map.py` + esbuild. Jangan rename `data-testid` yang sudah ada. Jaga invarian (`total_amount` GROSS, breakdown pajak di field terpisah).

## 6) Berkas referensi inti
- BE: `routers/purchase_orders.py` (approval chain, payables PO, pay/close/cancel), `services/config_service.py` (`compute_order_pricing`/`build_approval_chain`/`role_satisfies`), `services/vendor_bill_service.py` (`bill_financials`/`sync_po_billing`), `services/input_tax_service.py`, `services/rfq_service.py`, `services/landed_cost_service.py`, `routers/inbound_receiving.py` (GR→roll base_unit_cost), `services/roll_service.py` (alokasi dye_lot).
- FE: `features/purchasing/PurchaseApprovalView.jsx` (TARGET 7.1), `PayablesView.jsx` (AP PO), `VendorBillsView.jsx`, `InputTaxView.jsx`, `LandedCostView.jsx`, `RFQView.jsx`; `config/navigationConfig.js`.
- POC: `test_multilevel_approval_poc.py`, `test_vendor_bill_poc.py`, `test_input_tax_poc.py`, `test_rfq_poc.py`, `test_qc_inspection_poc.py`, `test_landed_cost_poc.py`.

---


> 📌 **MASTER ROADMAP (dari Assessment Vendor):** lihat `/app/docs/KN_DEVELOPMENT_PLAN_FROM_ASSESSMENT.md` — gap analysis assessment vs sistem eksisting + roadmap 6 fase (Sales, HRD, Purchasing, Finance, Warehouse+RFID, Additional) + BI. Status: DRAFT v1, menunggu konfirmasi prioritas user.

> 🏗️ **INFORMATION ARCHITECTURE (IA) BLUEPRINT:** lihat `/app/docs/KN_14_INFORMATION_ARCHITECTURE.md` — fondasi IA menyeluruh (navigasi + data/entity) untuk seluruh 6 fase + BI, dengan Multi-Entity sebagai lapisan fundamental. Status: **DRAFT v1 — LIVING DOC**.

> ✅ **FASE 0 (Enabler) — SELESAI & TESTED (15 Jun 2026):** Multi-Entity (`business_entities`: ent_ksc/ent_kanda + `entity_id` scoped pada transaksi; master SHARED) · Entity Switcher (TopBar) · Notification Center (`notifications`, generator REAL + dedupe) · field master baru (customer npwp/credit_limit/sales_pic, product harga_pokok/gramasi) · Admin Entities tab. Gates HIJAU (64/0/0, compliance 56/0/0, ux 0 ERROR). testing_agent: backend 39/39, frontend 100%. **NEXT:** Fase 1 (Sales) bila disetujui user.

> 🧩 **FASE 0.5 (Enabler 2) — Multi-Entity Inventory Ownership (Roll-as-SSOT) — ✅ ENABLER IMPLEMENTED (Session #016):** atas arahan user, kepemilikan stok dipisah **per entitas pada level ROLL** (`inventory_rolls` = SSOT fisik), **gudang netral/shared**, `inventory_balances` jadi proyeksi kunci `(product+warehouse+owner_entity)`, **integritas lot** (1 pengiriman idealnya 1 lot; mixed-lot hanya bila qty > lot tunggal + konfirmasi), **inter-company transfer WAJIB** sebelum entitas jual barang entitas lain (extend `warehouse_transfers`), HPP/`unit_cost` ditunda Fase 4. Visibilitas Sales: gudang+owner+lot. **Detail: `docs/KN_15_INVENTORY_OWNERSHIP_LOT.md`**.

---

## ✅ STATUS TERKINI (ringkas, ter-grounded)

### Stabilitas & UX/API Refactor (Selesai, Gate Hijau)
- L1: verifikasi empty-state emoji “🎉” tidak ada.
- L2: standarisasi API client FE (migrasi `fetch` → `axios, { API } from services/apiClient`).
- L3: modernisasi `scripts/check_nav_map.py` (parse dinamis `navigationConfig.js`, tidak hardcode string).
- M3: `ErrorNotice` + retry mechanics di list view.
- M4: timeline detail untuk Sales/Purchase Returns (`submitted_at/submitted_by` + `ReturnTimeline`).
- M5: busy state (disable) untuk aksi PO (hindari double-submit).
- M6: ApprovalInbox agregasi lintas modul + fix bug pagination parsing.
- L1b: ganti emoji UI (✓⚠🎯📞✅) → lucide-react.

### Purchasing — Fase 3 + Depth 1–3 (Sudah Ada & Teruji)
- Master Supplier + Supplier Price-List (MOQ, masa berlaku, UOM) + Scorecard.
- PO approval dinamis + price deviation approval + notifikasi approver.
- PR (Purchase Requisition) + reorder suggestions + special order → PR bridge.
- Goods receipt inbound + toleransi + eskalasi + QC hold/quarantine + QC decision.
- Purchase return (Nota Debit) + AP/hutang + pembayaran kas.

### Dokumen Baru (Gap Analysis Purchasing)
- ✅ Laporan lengkap: `/app/docs/PURCHASING_GAP_ANALYSIS.md`.

---

## 🔻 PURCHASING NEXT PHASE (BARU) — P0 Upgrade ke “Manufacturing-Grade”

> User menyetujui roadmap gap analysis dan meminta mulai dari rekomendasi: **P0-1 (PPN & Diskon pada PO)** lalu **P0-2 (Vendor Bill + 3-Way Matching)**, dilanjut **P0-4 (Dye Lot/Grade)** dan **P0-5 (Landed Cost)**.

### Prinsip Wajib
- **JANGAN bypass gate scripts**: `seed_reset.sh` → `health_check.py` → `verify_data_integrity.py` → `verify_api_contract.py` → `ux_audit.py`.
- **Jangan rename `data-testid` yang sudah ada**.
- Semua perubahan harus **INVARIANT-SAFE**: `total_amount` tetap GROSS (Σ subtotal), breakdown diskon/pajak tersimpan di field terpisah.

---

## Objectives (Updated)
1. Naikkan modul Purchasing dari “operasional kuat” ke “P2P + compliance siap produksi”: **(DONE) PPN/Diskon PO**, lalu Vendor Bill/3-way match, textile traceability (dye lot/grade), dan landed cost.
2. Pertahankan kontrak API dan integritas data (gate-driven) tanpa regressi UX.
3. Mengunci standar perhitungan diskon+pajak di Purchasing agar konsisten dengan Sales (`compute_order_pricing`) — **(DONE untuk PO)**.

---

## Implementation Steps (Revisi — mempertahankan struktur utama plan)

### Phase 1 — Core Flow POC (Guided Tour Overlay + Role Filter)
**Status Phase 1: COMPLETED** ✅ (tidak ada perubahan)

---

### Phase 2 — V1 App Development (Stabilisasi & UX polish minimal)
**Status Phase 2: COMPLETED** ✅ (tidak ada perubahan)

---

### Phase 3 — Feature Expansion (On-demand)
**Status Phase 3: COMPLETED** ✅ (tidak ada perubahan)

---

### Phase 4 — System Cleanup & Production Readiness
**Status Phase 4: COMPLETED** ✅ (tidak ada perubahan)

---

## 🆕 Phase 5 — Purchasing P0 Upgrade (PPN/Diskon PO → Vendor Bill/3-Way → Dye Lot/Grade → Landed Cost)

### 5.1 — P0-1: PPN & Diskon pada Purchase Order
**Status: COMPLETED ✅ (Fully Validated)**

#### Target Outcome
- PO menyimpan breakdown harga **diskon item + diskon order + DPP + PPN + grand_total** (konsisten dengan Sales).
- `total_amount` tetap **GROSS** (Σ subtotal) untuk menjaga invarian lama.
- AP/outstanding dihitung dari **grand_total** (atau fallback aman untuk data lama).

#### Backend — yang sudah diimplementasi
1. **Schemas** (`backend/schemas.py`)
   - `POItemCreate.discount_percent: float = 0`
   - `PurchaseOrderCreate.order_discount_percent: float = 0`
   - `PurchaseOrderCreate.tax_mode: str = ""` (override: `non_ppn` / ikut konfigurasi)
2. **Config** (`backend/services/config_service.py`)
   - `compute_order_pricing` diperluas secara backward compatible:
     - `cfg_section` ("sales"|"purchasing")
     - `tax_override` (mis. `non_ppn`)
   - Toggle purchasing: `settings.purchasing.allow_item_discount`, `settings.purchasing.allow_order_discount` (default True).
3. **PO create** (`backend/routers/purchase_orders.py`)
   - Create memakai `compute_order_pricing(..., cfg_section="purchasing", tax_override=payload.tax_mode)`.
   - Menyimpan field breakdown lengkap:
     - `items_discount_total`, `order_discount_percent`, `order_discount_amount`, `discount_total`, `net_subtotal`, `dpp`, `ppn_rate`, `ppn_mode`, `is_pkp`, `ppn_amount`, `grand_total`, `tax_mode`.
   - `outstanding` awal = **grand_total**.
4. **PR → PO convert** (`backend/services/purchase_requisition_service.py`)
   - PO hasil konversi juga punya breakdown PPN (invariant-safe) + `outstanding=grand_total`.
5. **Financials/AP** (`_po_financials` di `backend/routers/purchase_orders.py`)
   - Basis tagihan/hutang memakai `grand_total` bila ada.
   - Fallback aman untuk PO lama tanpa breakdown (basis gross/ordered value).
6. **Gate** (`scripts/verify_data_integrity.py`)
   - Tambah blok **INV-DB-PO** untuk PO ber-breakdown (di-gate pada `net_subtotal` agar seed PO lama tidak gagal):
     - `total_amount == Σ items.subtotal`
     - `net_subtotal == total_amount − discount_total`
     - konsistensi PPN (included/excluded) dan `grand_total`
     - `line_total == subtotal − discount_amount`, diskon 0–100.

#### Frontend — yang sudah diimplementasi
1. **POCreateForm.jsx**
   - Input diskon item: `data-testid="item-discount-input"`.
   - Input diskon order: `data-testid="order-discount-input"`.
   - Mode pajak: `data-testid="po-tax-mode-select"`.
   - Ringkasan estimasi live (mengambil `tax` dari `/settings/effective`) + DPP/PPN/grand.
2. **PurchaseOrderManagement.jsx**
   - Extend state `emptyForm` dan `newItem` dengan field baru.
   - List menampilkan `grand_total ?? total_amount`.
3. **PODetailPanel.jsx**
   - Kartu **Rincian Harga & Pajak**: Subtotal/Diskon/DPP/PPN Masukan/Grand Total.
   - Kartu AP relabel: “Total Tagihan”.
   - Per-item subtotal menampilkan `line_total` bila ada.

#### Verification (Wajib) — sudah dijalankan
- `bash scripts/seed_reset.sh` → **PASS 119 | FAIL 0**
- `python scripts/health_check.py` → **PASS 20 | FAIL 0**
- `python scripts/ux_audit.py` → **ERROR 0**
- Esbuild compile OK; screenshot form  detail sesuai perhitungan.
- Testing agent backend: **36/36 PASS (100%)**, 0 bug.

#### Exit Criteria — tercapai
- Semua gate hijau.
- Backward compatible: PO seed lama tetap bisa dibuka (fallback financials).
- Payables/outstanding benar dengan basis `grand_total`.

---

### 5.2 — P0-2: Vendor Bill + 3-Way Matching
**Status: ✅ COMPLETED — backend 52/52 PASS (testing agent), semua gate hijau, FE terintegrasi**

#### Target Outcome — tercapai
- Dokumen **Vendor Bill** (tagihan supplier) terpisah dari PO. ✅
- **3-way matching**: PO (ordered) ↔ GR (received_qty) ↔ Vendor Bill (billed_qty). ✅
- AP/hutang berbasis Vendor Bill posted, dengan toleransi qty/price configurable. ✅

#### Backend — yang sudah diimplementasi
- Koleksi baru: `vendor_bills` (prefix `vbill_`), nomor `VB-NNNNN`.
  - Terdaftar di `verify_contract.py` CANONICAL_COLLECTIONS + section `ENTITY_REGISTRY.md` (L0 self-check 35 koleksi konsisten).
- `services/vendor_bill_service.py`: `evaluate_match` (3-way), `bill_financials`, `already_billed_map`
  (DRAFT tidak me-reserve qty; reserve = pending/posted/paid), `sync_po_billing`, `build_billing_context`.
- `routers/vendor_bills.py`: list, detail, `POST /vendor-bills`, `/submit`, `/approve`, `/reject`,
  `/pay`, `/cancel`, `GET /vendor-bills/payables/summary`, `GET /purchase-orders/{id}/billing-context`.
  - Re-evaluasi match saat submit (anti race/over-billing antar draft).
  - Matched → auto-post; warning (variance dalam toleransi) → pending_approval (SoD: pembuat ≠ approver, role manager+); blocked (over-billing) → tak bisa submit (400).
  - Pay → `cash_transaction(out, ref_type=vendor_bill)` + update AP; dedupe `supplier_invoice_no` per supplier (409).
- `schemas.py`: VendorBillCreate/ItemInput/PaymentCreate/Decision.
- `config_service.py`: settings.purchasing `bill_qty_tolerance_percent` (default 0), `bill_price_tolerance_percent` (default 5).
- `permissions_config.py`: modul `vendor_bill` (admin/manager full+pay, sales/warehouse view).
- `seed_realistic.py`: `vendor_bills` masuk daftar clear (seed_reset bersih).

#### Frontend — yang sudah diimplementasi
- Nav **Pembelian → Tagihan Supplier** (`vendor-bills`) + PAGE_META.
- `VendorBillsView.jsx`: kartu AP aging summary, tab status, list, quick actions.
- `VendorBillCreateModal.jsx`: pilih PO → `billing-context` prefill, preview 3-way match LIVE per item (badge Cocok/Selisih/Over-bill) + total, Simpan Draft / Submit&Posting.
- `VendorBillDetailPanel.jsx`: kartu keuangan, exceptions match, tabel item (PO vs bill price), timeline, aksi submit/approve/reject/pay/cancel.

#### Verification (Wajib) — sudah dijalankan
- POC isolasi `test_vendor_bill_poc.py` → **31/31 PASS** (matched/over-billing/price-variance/SoD/payment/RBAC/dedupe).
- `bash scripts/seed_reset.sh` → **PASS 119 | FAIL 0** (incl. L0 self-check 35 koleksi).
- `verify_api_contract.py` → CHECK A/B/C **OK** (235 route unik, 103 path FE cocok).
- `audit_endpoint_sweep.py` → **0 5xx/EXC**; `ux_audit.py` → **ERROR 0** (87 file); esbuild clean.
- Testing agent E2E → backend **52/52 PASS (100%)**, frontend kritikal OK, 0 bug.

#### Exit Criteria — tercapai
- Vendor Bill + 3-way matching berjalan, AP berbasis bill, audit trail PO↔GR↔Bill + toleransi. ✅
- Backward compatible (PO lama tanpa breakdown tetap bisa ditagih via fallback financials). ✅
- Semua gate hijau, tidak ada regresi UI/UX, tidak ada rename data-testid. ✅

---

### 5.3 — P0-4: Dye Lot + Grade aktual saat GR/QC
**Status: ✅ COMPLETED (backend wired + POC 14/14 + FE terintegrasi + gate hijau). testing_agent E2E final.**

#### Resume sesi lanjutan (repo kn10 re-copy → lanjut dari pause)
- Backend wiring SISA item A SELESAI:
  - `inbound_receiving.complete_inbound_receiving`: body opsional `GRCompletePayload` (backward-compatible — tanpa body tetap jalan); roll simpan `dye_lot`/`grade`/`defects`; **multi-roll** bila `payload.rolls` diisi (validasi Σ panjang ≈ qty toleransi ±2%, `roll_no` increment per roll, konversi base unit per roll).
  - `qc_service.process_qc_decision(... accept_grade="A", defects=None)`: saat ACCEPT → roll available di-set `grade`/`qc_grade`/`defects`; router `qc_decision` meneruskan `accept_grade`/`defects`.
  - `routers/customers.py`: create+update simpan `enforce_single_dye_lot`, `lot_policy`, `allocation_policy`.
  - `server.py`: `backfill_roll_dye_lot()` startup migration (roll lama `dye_lot=$lot`, `grade=A`, `defects=[]`) + `inventory.py` initial-stock set `dye_lot`/`defects`.
  - `ENTITY_REGISTRY.md`: `inventory_rolls` (+`dye_lot`,`qc_grade`,`defects`, grade enum +BS) & `customers` (+`enforce_single_dye_lot`).
- **POC `test_dyelot_poc.py` → 14/14 PASS** (single dye_lot, multi-roll, validasi Σ panjang, QC grade+defects, enforce_single_dye_lot: reserved 60/backorder 40 vs mixed reserved 100).
- Frontend SELESAI: `InboundScanInterface` (input Dye Lot + KNSelect Grade), `QCInspection` (KNSelect grade diterima + input defects), `CustomerPanel` (toggle enforce_single_dye_lot + KNSelect lot_policy), `RollsTable` (kolom Dye Lot + badge defects).
- Gate hijau: esbuild bersih, `seed_reset` **119/0/0**, `verify_api_contract` A/B/C OK, `health_check` 20/0, `audit_endpoint_sweep` 0×5xx, `ux_audit` **0/0**.

#### Target Outcome
- Tangkap `dye_lot` dan `grade` aktual per roll saat penerimaan (GR).
- QC decision dapat menetapkan grade (A/B/C/BS) / defect profile per qty diterima.
- Allocation/fulfillment bisa menegakkan "single dye lot" untuk customer tertentu.

#### Design (disepakati, gate-safe)
- `dye_lot` = atribut tekstil baru pada roll (DEFAULT = `lot` agar backward-compatible & invarian roll lama tetap valid). `lot` generik TETAP ada (gate "roll: lot wajib terisi" tak terganggu).
- Enforcement single-dye-lot lewat policy baru `dye_lot_strict` (bool): saat aktif, planner alokasi GROUP BY `dye_lot` + paksa `strict_single`. Field `lots`/`lot_mode` pada alokasi TETAP diturunkan dari `lot` reserved rolls → gate INV-LOT-1 (single⟺≤1 lot / mixed⟺≥2) tetap konsisten.
- Customer flag `enforce_single_dye_lot` → map ke `dye_lot_strict=True` di `get_allocation_policy`.

#### ✅ SUDAH DIKERJAKAN (backend, ADDITIVE — backend tetap load HTTP 200, BELUM DIUJI)
1. `backend/schemas.py`:
   - `POReceiveItem` += `dye_lot:str=""`, `grade:str=""`.
   - BARU `GRRollLine(length, dye_lot, grade, defects[])` + `GRCompletePayload(dye_lot, grade, rolls[])`.
   - `QCDecision` += `accept_grade:str="A"`, `defects:List[str]=[]`.
   - `CustomerCreate` += `enforce_single_dye_lot:bool=False`, `lot_policy:str=""`.
2. `backend/services/config_service.py`:
   - `DEFAULT_GLOBAL_SETTINGS["allocation"]` += `dye_lot_strict:False`.
   - `_sanitize_alloc` handle `dye_lot_strict` (bool).
   - `get_allocation_policy`: customer `enforce_single_dye_lot` → `base["dye_lot_strict"]=True`.
3. `backend/services/roll_service.py`:
   - `_build_allocation_plan`: bila `dye_lot_strict` → group key = `dye_lot` (fallback `lot`) + `lot_mode="strict_single"`.
   - `_make_roll` (sintetis/seed) += `"dye_lot": lot`.
   - `allocate_and_reserve_rolls`: track `dye_lots` per bucket; alokasi += `dye_lot`, `dye_lots`, `dye_lot_strict`.
   - `preview_line_allocation` += `dye_lot_strict`.
4. `backend/routers/inbound_receiving.py`:
   - Endpoint `scan-receive` simpan `dye_lot`, `grade` ke task (DONE). **complete & qc-decision BELUM di-wire (lihat sisa).**

#### ⛔ SISA YANG HARUS DIKERJAKAN (PRIORITAS BERURUTAN)
**A. Backend wiring (selesaikan dulu — ini yang membuat fitur benar-benar jalan):**
1. `inbound_receiving.py › complete_inbound_receiving`:
   - import `GRCompletePayload` (dari schemas) + `Body` (fastapi). Tambah param opsional: `payload: GRCompletePayload = Body(default=None)` (HARUS backward-compatible — pemanggilan tanpa body harus tetap jalan).
   - Saat buat roll: tambah field `"dye_lot": <payload.dye_lot or task.dye_lot or lot>`, `"grade": <payload.grade or task.grade or "A">`, `"defects": []`.
   - Bila `payload.rolls` terisi → buat MULTI roll (loop), tiap roll pakai `length/dye_lot/grade/defects` sendiri; validasi `Σ length ≈ final_qty` (dalam unit task, konversi ke base unit seperti `gr_base_qty`). Bila kosong → satu roll (perilaku sekarang) + dye_lot/grade.
   - PENTING: `roll_no` sequence harus increment per roll bila multi-roll.
2. `services/qc_service.py › process_qc_decision`:
   - Tambah param `accept_grade:str="A"`, `defects:List[str]=None`.
   - Saat ACCEPT (`_consume_quarantine ... "available"`) → `extra_set` += `{"grade": accept_grade, "defects": defects or [], "qc_grade": accept_grade}`.
3. `inbound_receiving.py › qc_decision`: teruskan `payload.accept_grade`, `payload.defects` ke `process_qc_decision(...)`.
4. `routers/customers.py`: `create_customer` simpan `enforce_single_dye_lot`, `lot_policy`, (opsional `allocation_policy`); `update_customer` allowed-list += `enforce_single_dye_lot`, `lot_policy`, `allocation_policy`.
5. **Migration/backfill** rolls lama: `db.inventory_rolls.update_many({"dye_lot":{"$exists":False}}, [{"$set":{"dye_lot":"$lot"}}])` — taruh di startup migration `server.py` (cari blok migrasi existing) ATAU jalankan via re-seed (`generate_rolls_from_balances` sudah set dye_lot=lot untuk seed baru). Wajib agar semua roll punya `dye_lot`.
6. `ENTITY_REGISTRY.md`: update section `rolls` (tambah `dye_lot`, `defects`, `qc_grade`) + `customers` (tambah `enforce_single_dye_lot`, `lot_policy`). (Tidak menambah koleksi baru → tak perlu sentuh CANONICAL_COLLECTIONS.)

**B. POC test (WAJIB sebelum frontend):** buat `test_dyelot_poc.py`:
   - GR complete dengan dye_lot → roll punya dye_lot; GR multi-roll breakdown → N roll dengan dye_lot/grade beda.
   - QC accept dengan accept_grade="B" + defects → roll available grade B + defects.
   - Customer `enforce_single_dye_lot=true` → SO alokasi hanya 1 dye_lot (cek `allocations[].dye_lots` len==1, atau backorder bila 1 dye_lot tak cukup). Bandingkan dengan customer tanpa flag (boleh mixed).

**C. Frontend (setelah backend hijau):**
   - Inbound scan UI (`features/wms/Inbound*` / scan interface): input `dye_lot` + `grade` (KNSelect grade A/A+/B/C/BS).
   - QC inspection UI (`QCInspection`): saat accept → pilih `accept_grade` + input `defects` (chips/comma).
   - Customer form (master data customer): toggle `enforce_single_dye_lot` + select `lot_policy`.
   - Tampilkan `dye_lot` + `grade` di display roll/inventory (`InventoryStockView`/roll detail) & di preview alokasi SO (`dye_lots`).
   - WAJIB: semua path FE literal (CHECK B), data-testid pada elemen interaktif, KNSelect (bukan native select), ErrorNotice.

**D. Verifikasi akhir:** `seed_reset.sh` (119/0), `verify_api_contract` (A/B/C), `audit_endpoint_sweep` (0×5xx), `ux_audit` (0), esbuild bersih, lalu `testing_agent_v3` E2E (skip uji kamera/drag-drop).

#### Catatan teknis penting
- Backend SAAT INI load HTTP 200 (edit aditif aman). Tapi fitur GR/QC dye_lot BELUM aktif end-to-end (complete/qc belum pakai field baru). Jangan klaim "selesai" sebelum item A–D tuntas & diuji.
- Grade enum diperluas: A | A+ | B | C | BS (BS = barang sisa/seconds). Tidak ada gate yang memvalidasi enum grade (aman).
- File yang sudah disentuh sesi ini: schemas.py, config_service.py, roll_service.py, inbound_receiving.py (scan saja).

---

### 5.4 — P0-5: Landed Cost
**Status: ✅ SELESAI & TERVERIFIKASI** (sesi 027 — copy ulang repo + verifikasi)

#### Keputusan desain owner (disetujui)
- **1a** Basis alokasi = proporsional NILAI (base_unit_cost × length_initial), fallback ke kuantitas lalu rata.
- **2a** GR set base HPP roll dari harga PO (`base_unit_cost`=`unit_cost` per BASE unit); landed cost menambah di atas (additive).
- **3a** Koleksi baru `landed_cost_vouchers` (prefix `lcv_`, nomor `LCV-NNNNN`).
- **4a** Lifecycle pola Vendor Bill: draft → submit → approve (SoD, manager+) → applied → pay → paid; pembayaran catat `cash_transaction(out, ref_type=landed_cost)`.

#### Target Outcome — TERCAPAI
- ✅ Dokumen biaya tambahan (freight/bea/asuransi/handling) + alokasi ke HPP roll (`inventory_rolls.unit_cost` +per_unit, `landed_cost_total`, `landed_cost_refs`).
- ✅ Audit trail landed cost → roll/unit_cost (timeline voucher + audit_logs + refs di roll).

#### Implementasi
- BE: `routers/landed_cost.py` (list/detail/create/submit/approve/reject/apply/pay/cancel + payables summary + po landed-cost-context), `services/landed_cost_service.py` (alokasi value/quantity, idempotent apply), `schemas.py` (LandedCost*), `inbound_receiving.py` (GR set base HPP dari harga PO), `permissions_config.py` (modul `landed_cost`), `server.py` register + backfill migration, `verify_contract.py` canonical, `ENTITY_REGISTRY.md` section + roll fields.
- FE: `features/purchasing/LandedCostView.jsx` + `LandedCostCreateModal.jsx` + `LandedCostDetailPanel.jsx`, nav `Pembelian → Landed Cost (HPP)`, `App.js` wiring.

#### Verifikasi (sesi 027)
- ✅ POC `test_landed_cost_poc.py` → **17/17 PASS** (base HPP, alokasi value, submit, SoD 403, apply→unit_cost, idempotent 409, pay→cash).
- ✅ Gates: `seed_reset` 119/0/0, `verify_contract` OK, `verify_api_contract` ERROR 0, `health_check` 0 FAIL, `audit_endpoint_sweep` 5xx=0, `ux_audit` 0 ERROR, `check_nav_map` PASS, `esbuild` exit 0.
- ✅ `testing_agent_v3`: backend lifecycle 10/10 + POC 17/17 + FE code review (semua testid hadir), 0 bug.
- ✅ FE live: view render (KPI/tabs/empty state) + create modal interaktif (PO multi-select, basis nilai, baris biaya) terverifikasi via screenshot.

#### Catatan
- Setup fix wajib saat copy ulang repo: pin `webpack-dev-server@4.15.2` via `resolutions` + `yarn install` (node_modules basi pakai 5.x → `onAfterSetupMiddleware` invalid → layar putih).
- `validate_compliance` WARN naming `db.landed_cost_vouchers` (sama seperti `db.vendor_bills`) = diterima owner (konsisten domain), bukan FAIL baru.

---

## Next Actions (Updated)
1. ✅ **Phase 5.2 — Vendor Bill + 3-Way Matching: SELESAI** (backend 52/52, gate hijau, FE terintegrasi).
2. ✅ **Phase 5.3 — Dye Lot + Grade: SELESAI** (backend wired, POC 14/14, FE terintegrasi, gate hijau, testing_agent backend 15/15 + frontend 8/8, 0 bug).
3. ✅ **Phase 5.4 — Landed Cost: SELESAI & TERVERIFIKASI** (POC 17/17, testing_agent BE 10/10, gate semua hijau, FE live terverifikasi, 0 bug). **Phase 5 (Purchasing P0 Upgrade) tuntas.**

---

### 5.5 — P0-3: Faktur Pajak Masukan (Input VAT)
**Status: ✅ SELESAI & TERVERIFIKASI** (sesi 038)

#### Keputusan desain owner (disetujui)
- **Sumber** = Vendor Bill (DPP/PPN sudah dihitung di bill; status posted/paid, ppn_amount>0).
- **Rekap PPN Masukan vs Keluaran** per periode (YYYY-MM) → posisi kurang/lebih bayar.
- **NSFP** supplier disimpan + DEDUPE (digit-only, di antara status recorded) — tanpa flag creditable.

#### Implementasi
- BE: koleksi kanonik baru `tax_invoices_in` (prefix `fpm_`, No. internal `FPM-NNNNN`).
  `routers/input_tax.py` (list/detail/create/cancel + `eligible-bills` + `/tax/vat-summary`),
  `services/input_tax_service.py` (snapshot dari bill, NSFP dedupe, rekap masukan vs keluaran),
  `schemas.py` (InputTaxInvoiceCreate/Cancel), `permissions_config.py` modul `input_tax`,
  `server.py` register + backfill `vendor_bills.input_faktur_status`, `verify_contract.py` canonical,
  `ENTITY_REGISTRY.md` section. Lifecycle: recorded → cancelled (cancel → bill eligible lagi, NSFP reusable).
- FE: `features/purchasing/InputTaxView.jsx` (tab **Faktur Masukan** + **Rekap PPN**) + `InputTaxCreateModal.jsx`
  (pilih Vendor Bill eligible → preview DPP/PPN → input NSFP + tanggal faktur), nav `Pembelian → Faktur Pajak Masukan`, `App.js`.

#### Verifikasi (sesi 038)
- ✅ POC `test_input_tax_poc.py` → **19/19 PASS** (eligible bills, create dari bill DPP/PPN disalin, bill flag + dedupe bill 409, NSFP dedupe 409, rekap masukan vs keluaran + net kurang bayar, cancel → eligible lagi + NSFP reusable).
- ✅ Gates: `seed_reset` hijau (canonical `tax_invoices_in`), `verify_api_contract` 0/0, `ux_audit` 0/0 (92 file), `health_check` 0 FAIL, `audit_endpoint_sweep` 5xx=0, `check_nav_map` PASS, `esbuild` exit 0.
- ✅ `testing_agent_v3` iter_30: BE 57/60 (3 false-positive dari data seed lama, fitur benar) + FE semua elemen terverifikasi, **0 bug**.
- ✅ FE live (screenshot): summary cards, tab Faktur Masukan + Rekap PPN (PPN Keluaran Rp 2.150.500 dari 2 faktur seed, posisi "Kurang Bayar"), create modal interaktif.

#### Catatan
- Default seed belum punya Vendor Bill posted ber-PPN → modul create menampilkan empty-bills (benar). Output faktur seed (2 dok) membuat Rekap Keluaran non-zero.
- `validate_compliance` WARN naming `db.tax_invoices_in` (sama seperti `db.vendor_bills`/`db.landed_cost_vouchers`) = diterima owner.

#### Next (disetujui user, urut)
1. ✅ **P1 — RFQ / Quotation: SELESAI & TERVERIFIKASI** (Phase 6.1 — POC 15/15, testing_agent BE 74/74, gate semua hijau, FE live terverifikasi, 0 bug).
2. ✅ **P1 — GSM/Lebar aktual per-roll + 4-Point Inspection: SELESAI & TERVERIFIKASI** (Phase 6.2 — POC 13/13, testing_agent BE 12/12, gate semua hijau, FE live terverifikasi, 0 bug).

---

### 6.2 — P1: 4-Point Inspection + GSM/Lebar aktual per-roll (QC)
**Status: ✅ SELESAI & TERVERIFIKASI** (sesi 040)

#### Keputusan desain owner (disetujui)
- **Tahap**: saat QC (task `qc_pending`) — per roll, set grade & terima/tolak.
- **Skor**: 4-point SEDERHANA = total poin defect (Σ point_value×count, point_value 1..4); tanpa normalisasi luas.
- **Grade**: poin ≤a_max → A, ≤b_max → B, >b_max → C. Ambang **configurable** (`qc.grade_thresholds`, default 20/40).
- **GSM/Lebar aktual**: dicatat saja (tanpa pass/fail otomatis).
- **Hasil**: set `roll.grade` dari inspeksi; tanpa aksi karantina otomatis.

#### Implementasi
- BE: TANPA koleksi baru — modif `inventory_rolls` (field `inspection`, set `grade`+`defects`).
  Config `qc.grade_thresholds` + `four_point_enabled` (`config_service`), `services/qc_inspection_service.py`
  (compute_points, grade_from_points, inspect_roll, rolls_for_task), `routers/qc_inspection.py`
  (`GET /qc/grade-thresholds`, `GET /inbound/qc/tasks/{id}/rolls`, `POST /inbound/rolls/{id}/inspect`),
  `schemas` (RollInspectionInput/RollDefectInput), `server.py` register, `ENTITY_REGISTRY` roll fields. Permission: modul `wms`.
- FE: `features/wms/RollInspectionModal.jsx` (kartu roll + form 4-point: input poin 1..4 + GSM/lebar aktual,
  live total poin + predicted grade, Simpan & Set Grade) terintegrasi ke `QCInspection.jsx` via tombol
  "4-Point Roll" per baris antrian. `App.js` teruskan `selectedEntity`.

#### Verifikasi (sesi 040)
- ✅ POC `test_qc_inspection_poc.py` → **13/13 PASS** (points=Σpv×count, grade A/B/C + boundary 20→A/40→B,
  roll.grade tersimpan, GSM/lebar aktual tersimpan, validasi pv 1..4 → 400, ambang configurable a_max=5).
- ✅ Gates: seed_reset **119/0/0**, verify_api_contract **0/0**, ux_audit **0 ERROR**, health 0 FAIL, sweep **5xx=0**, nav-map PASS, esbuild exit 0.
- ✅ `testing_agent_v3` iter_32: BE **12/12** + FE semua testid hadir, **0 bug**. FE live (screenshot): modal 4-point,
  Total Poin 10 → Grade A live, GSM 145 / Lebar 115, Simpan & Set Grade. QC decision lama tetap utuh.

#### Catatan
- Permission pakai modul `wms` (sejalan QC queue/decision existing) — tanpa modul baru.
- **Phase 6 (P1 sourcing + QC) tuntas**: 6.1 RFQ/Quotation + 6.2 4-Point Inspection.

---

### 6.1 — P1: RFQ / Quotation (Sourcing)
**Status: ✅ SELESAI & TERVERIFIKASI** (sesi 039)

#### Keputusan desain owner (disetujui)
- **Sumber**: PR approved (tarik item) **dan** standalone manual.
- **Quote**: purchaser input manual harga per supplier yang diundang.
- **Award**: dukung **FULL** (1 supplier → 1 PO) **dan** **PER-LINE** (split → beberapa PO).
- **Compare**: matriks item×supplier + harga terendah/baris + total/supplier + rekomendasi pemenang.
- **Award → upsert** `supplier_price_lists` dari harga pemenang (source=rfq_award).

#### Implementasi
- BE: koleksi kanonik `rfqs` (prefix `rfq_`, No. `RFQ-NNNNN`). Status draft → open → awarded | cancelled.
  `routers/rfq.py` (list/detail/compare/create/send/quote/award/cancel),
  `services/rfq_service.py` (build-from-PR, compare matrix + rekomendasi, award→PO via `compute_order_pricing`+approval+inbound tasks, price-list upsert),
  `schemas.py` (RFQCreate/Item/Quote*/Award*/Decision), `permissions_config` modul `rfq`,
  `server.py` register, `verify_contract` canonical, `ENTITY_REGISTRY` section.
  Award penuh→1 PO; per-baris→1 PO/supplier; PR sumber → PR 'converted' + po_id. PO.source_rfq_id/number.
- FE: `features/purchasing/RFQView.jsx` (list+tabs) + `RFQCreateModal.jsx` (manual/PR + undang supplier) + `RFQDetailPanel.jsx` (input penawaran per supplier, matriks banding harga + sorot terendah + badge termurah, award full/per-baris). Nav `Pembelian → RFQ / Quotation`, `App.js`.

#### Verifikasi (sesi 039)
- ✅ POC `test_rfq_poc.py` → **15/15 PASS** (create manual+PR, send, cross-quote, compare lowest/recommended, award full→1 PO + price-list upsert, award per-line→2 PO, PR converted, idempotent 409).
- ✅ Gates: seed_reset **119/0/0** (canonical `rfqs`), verify_api_contract **0/0**, ux_audit **0 ERROR**, health_check **0 FAIL**, sweep **5xx=0**, check_nav_map PASS, esbuild exit 0.
- ✅ `testing_agent_v3` iter_31: BE **74/74** + FE 0 UI/integration bug (selain catatan pre-existing quick-login). FE live (screenshot): list, create modal, detail panel matriks banding (Bali 10rb/Toba 20rb tersorot, Toba 2.2jt "termurah") + award.

#### Catatan
- Pre-existing minor: tombol quick-login (Admin/Sales/dst) hanya isi email, perlu klik "Masuk" — di luar scope RFQ.
- `validate_compliance` WARN naming `db.rfqs` = diterima owner (konsisten domain).

---

## Success Criteria (Updated)
- Purchasing P0-1 (DONE):
  - PO menyimpan breakdown diskon+pajak invariant-safe.
  - Payables/outstanding benar (grand_total) dan backward compatible.
  - Gate scripts semua hijau.
- Purchasing P0-2 (Next):
  - Vendor Bill + 3-way matching berjalan, AP berbasis bill.
  - Audit trail jelas (PO↔GR↔Bill) + toleransi.
  - Gate scripts semua hijau.
- Textile readiness (Next):
  - Dye lot + grade tertangkap aktual dan bisa dipakai untuk kontrol alokasi.
- Tidak ada regressi UI/UX (ux_audit 0 error) dan tidak ada rename data-testid.
