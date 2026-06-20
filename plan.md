# Development Plan — Kain Nusantara (WMS/ERP) — Smart Guidelines + Seed + Documentation + Discovery E‑Questionnaire (v2.2)

---

# 🧭 SESSION HANDOFF + REVIEW MENYELURUH PURCHASING (Sesi #041 — 20 Jun 2026)

> **Untuk agent berikutnya.** Sesi ini TIDAK menulis fitur baru — fokus pada **review menyeluruh modul Pembelian** (scope, integrasi data, business process, flow/UX, bug, I/O, performa) + handoff. Bahasa kerja owner: **Bahasa Indonesia**. Backend & frontend RUNNING. Gate `verify_data_integrity` = **119 PASS / 0 FAIL**. esbuild exit 0.
>
> ⚠️ **WAJIB saat re-copy repo / restart container:** `cd /app/frontend && yarn install` (terapkan `resolutions: webpack-dev-server@4.15.2`, kalau tidak → layar putih `onAfterSetupMiddleware`). Backend deps sudah terpasang.

## 0) Kredensial uji
admin@kainnusantara.id · manager@kainnusantara.id · sales@… · warehouse@… — semua password **demo12345**. (Tombol quick-login hanya mengisi email; tetap klik **Masuk**.)

## 1) Status modul Pembelian (13 menu — semua ter-wire)
PO · Purchase Requisition · RFQ/Quotation · Saran Reorder · Pemasok · Approval Pembelian · Retur Beli · Tagihan Supplier (Vendor Bill/3-way) · Landed Cost (HPP) · Faktur Pajak Masukan · Hutang Supplier (AP) · BOM Printing (coming soon) · Pengelolaan Kas.

**Sudah SELESAI & terverifikasi (sesi-sesi lalu):** Phase 5.1 PPN/Diskon PO · 5.2 Vendor Bill + 3-Way · 5.3 Dye Lot/Grade · 5.4 Landed Cost · 5.5 Faktur Pajak Masukan · 6.1 RFQ · 6.2 4-Point Inspection · **Fase 8 Catch-weight / Dual-UoM**. 

**Sedang berjalan:** **Phase 7.2 PO Amendment / Version History (P2)**.

## 2) ✅ Yang sudah BENAR (terverifikasi sesi ini)
- **Pricing konsisten Sales↔Purchasing**: `compute_order_pricing(cfg_section=...)` dipakai bersama → diskon item/order + DPP + PPN 11% invariant-safe (`total_amount` tetap GROSS).
- **Multi-level approval BACKEND solid**: `build_approval_chain` + `current_pending_level` + `role_satisfies` + SoD (pembuat ≠ approver).
- **Traceability tekstil PO→GR→roll→Sales**: GR set `dye_lot`/`grade`/`base_unit_cost` (dari harga PO) per roll; `roll_service` allocation menghormati `dye_lot_strict`.
- **3-Way Matching** (PO ordered ↔ GR received ↔ Bill billed) + toleransi qty/harga + over-billing blocked + SoD approve.
- **Faktur Pajak Masukan** disnapshot dari Vendor Bill (DPP/PPN), NSFP dedupe (digit-only), rekap PPN Masukan vs Keluaran.
- **RBAC nav = permissions_config** (hasil fix H1 lampau).
- **Catch-weight / Dual-UoM** sudah aktif end-to-end (PO per kg/meter + GR override berat/panjang per roll) — verifikasi via POC `test_catch_weight_poc.py` (28/28) + gate hijau pada sesi sebelumnya.

## 3) ⚠️ KEKELIRUAN / GAP DITEMUKAN (urut prioritas — untuk diperbaiki)

### 🔴 P0-A — [RESOLVED ✅ Sesi #042] Tabrakan nomor PO + artefak test tertinggal
- **FIX:** Helper bersama `core_utils.next_doc_number(collection, field, prefix)` (max-based, deletion-safe) menggantikan SEMUA generator `count_documents()+1`.
- **Bukti:** POC `test_number_series_poc.py` **12/12**; gate seed_reset **119/0/0**.

### ✅ P0-B — [RESOLVED ✅ Sesi #042] Dualisme AP → UNIFIKASI ke Vendor Bill (SSOT)
- **Keputusan owner:** Vendor Bill = SATU-SATUNYA sumber hutang & pembayaran supplier; menu PO-based AP dihapus.
- **Catatan penting:** **DILARANG** mengembalikan pembayaran langsung di PO (`/purchase-orders/{id}/pay` sengaja 400).

### 🟠 P1-C — [DONE ✅ Sesi #042] Frontend Multi-Level Approval
- `features/purchasing/PurchaseApprovalView.jsx` sudah render approval chain bertingkat + role-aware lock + SoD.

### 🟠 P2 — [IN PROGRESS] Phase 7.2 PO Amendment / Version History
- Backend endpoint **sudah ditulis**: `POST /api/purchase-orders/{po_id}/amend`.
- **Belum diuji** dengan POC terisolasi.
- **Gate FAIL saat ini:** `backend/routers/purchase_orders.py` **848 baris** (batas 800) → 2 FAIL (`FILE_SIZE`, `MONSTER_FILE`).
- Frontend untuk amend + history/diff: **BELUM ADA**.

### 🟡 P2-D — [COSTING] HPP/COGS belum nyambung ke Sales (deferred, by design)
- `unit_cost` seed roll masih banyak None; HPP ditunda Fase 4 (sesuai KN_15). Bukan bug.

### 🟢 P3-E — Minor
- esbuild WARNING pre-existing di Sales `CreateSpecialOrderForm.jsx:314` (`>` literal dalam teks JSX) — kosmetik.
- Dua jalur menulis `roll.grade`: `qc_service.process_qc_decision` & `qc_inspection_service.inspect_roll`; pastikan urutan operasional (inspeksi dulu → accept) saat SOP QC.

### 🟢 P3-F — Performa (sehat untuk skala sekarang; catatan untuk skala besar)
- Loop agregasi Python pada payables (PO/Bill) aman pada seed sekarang; untuk skala ribuan perlu index + paginasi.

## 4) Backlog (disetujui owner, urut)
- ✅ ~~**P1:** Catch-weight / Dual-UoM pembelian~~ — SELESAI Sesi #043 (Fase 8).
- **P2 (aktif):** **Phase 7.2 PO Amendment / Version History**.
- **P2 berikutnya:** Blanket/Contract PO (call-off) · Kirim PO PDF ke supplier (email) · Multi-currency/FX · Budget/Commitment Control.

## 5) Rekomendasi URUTAN aksi agent berikutnya
- ✅ ~~1. Bersihkan state + perbaiki generator nomor → max-based (P0-A)~~
- ✅ ~~2. Selesaikan Frontend Phase 7.1 (P1-C)~~
- ✅ ~~3. Putuskan & rapikan AP dualism (P0-B)~~
- ✅ ~~4. Catch-weight / Dual-UoM (P1)~~
- **SEKARANG (P2): Phase 7.2 PO Amendment / Version History**
  1) Uji endpoint amend via POC (backend) 
  2) Refactor agar `purchase_orders.py` < 800 baris (fix 2 GATE FAIL)
  3) Implement UI amend + history/diff (FE)
  4) Jalankan semua gate + testing_agent_v3

> Setiap perubahan WAJIB lewat gate: `seed_reset.sh` → `health_check.py` → `verify_data_integrity.py` → `verify_api_contract.py` → `ux_audit.py` → `check_nav_map.py` + esbuild. Jangan rename `data-testid` yang sudah ada. Jaga invarian (`total_amount` GROSS, breakdown pajak di field terpisah).

## 6) Berkas referensi inti
- BE: `routers/purchase_orders.py` (approval chain, close/cancel, amend), `services/config_service.py` (`compute_order_pricing`/`build_approval_chain`/`role_satisfies`), `services/vendor_bill_service.py` (SSOT AP), `routers/inbound_receiving.py`.
- FE: `features/admin/PurchaseOrderManagement.jsx`, `features/admin/po/PODetailPanel.jsx`, `features/admin/po/POTimeline.jsx`, `features/admin/po/POCreateForm.jsx`.
- POC: `test_multilevel_approval_poc.py`, `test_catch_weight_poc.py`, **(baru) `test_po_amendment_poc.py`**.

---

> 📌 **MASTER ROADMAP (dari Assessment Vendor):** lihat `/app/docs/KN_DEVELOPMENT_PLAN_FROM_ASSESSMENT.md` — gap analysis assessment vs sistem eksisting + roadmap 6 fase. Status: DRAFT v1.

> 🏗️ **INFORMATION ARCHITECTURE (IA) BLUEPRINT:** lihat `/app/docs/KN_14_INFORMATION_ARCHITECTURE.md` — Status: DRAFT v1.

> ✅ **FASE 0 (Enabler) — SELESAI & TESTED (15 Jun 2026)**: Multi-Entity + Notification Center + Admin Entities tab.

> 🧩 **FASE 0.5 (Enabler 2) — Multi-Entity Inventory Ownership (Roll-as-SSOT) — ✅ IMPLEMENTED**.

---

## ✅ STATUS TERKINI (ringkas, ter-grounded)

### Stabilitas & UX/API Refactor (Selesai, Gate Hijau)
- Standarisasi API client FE (`axios, { API } from services/apiClient`).
- `ErrorNotice` + retry mechanics.
- `check_nav_map.py` dinamis.

### Purchasing — Fase 3 + Depth 1–3 (Sudah Ada & Teruji)
- Master Supplier + Supplier Price-List + Scorecard.
- Approval dinamis + deviasi harga.
- PR + reorder suggestions.
- Goods receipt inbound + QC.
- Purchase return.

### Dokumen Baru (Gap Analysis Purchasing)
- ✅ `/app/docs/PURCHASING_GAP_ANALYSIS.md`.

---

## 🔻 PURCHASING NEXT PHASE (BARU) — P2: Phase 7.2 PO Amendment / Version History

> Owner sudah menyetujui untuk melanjutkan **Phase 7.2** dengan keputusan:
> - (1.a) tuntaskan penuh (backend+frontend+gates)
> - (2.a) refactor agar compliance hijau (pindah logic amendment ke service)
> - (3.a) history/diff tampil di dalam Detail PO

### Prinsip Wajib
- **KODE MENANG** atas dokumen aspiratif.
- **Vendor Bill tetap SSOT AP** (jangan reintroduce pembayaran di PO).
- **Respons API**: array/objek telanjang (tanpa envelope).
- FE: semua call via `apiClient` (`axios, { API } ...`), path literal, guard `Array.isArray`.
- UI: shadcn/KNSelect, `tabular-nums`, lucide icons, `data-testid` lengkap.
- **Batas ukuran file**: router ≤800; `.jsx` ≤500.

---

## Objectives (Updated)
1. Menyediakan **PO Amendment** yang aman (audit trail + snapshot + diff) dan **reset approval chain** tanpa merusak stok/GR.
2. Menutup **2 compliance FAIL** (purchase_orders.py monster file) dengan refactor service extraction.
3. Menyediakan UI Admin yang lengkap untuk amend + history/diff dalam detail PO.
4. Memastikan invariants & contract tetap hijau lewat seluruh gate dan testing_agent_v3.

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

(isi tidak diubah dari plan sebelumnya)

---

### 5.2 — P0-2: Vendor Bill + 3-Way Matching
**Status: ✅ COMPLETED**

(isi tidak diubah dari plan sebelumnya)

---

### 5.3 — P0-4: Dye Lot + Grade aktual saat GR/QC
**Status: ✅ COMPLETED**

(isi tidak diubah dari plan sebelumnya)

---

### 5.4 — P0-5: Landed Cost
**Status: ✅ SELESAI & TERVERIFIKASI**

(isi tidak diubah dari plan sebelumnya)

---

### 5.5 — P0-3: Faktur Pajak Masukan (Input VAT)
**Status: ✅ SELESAI & TERVERIFIKASI**

(isi tidak diubah dari plan sebelumnya)

---

## 🆕 Phase 7.2 — P2: PO Amendment / Version History
**Status: IN PROGRESS (aktif sesi ini)**

### Target Outcome
- User dapat mengubah PO (supplier/warehouse/ETA/notes/items) dengan:
  - **Reason wajib** (audit)
  - **Snapshot sebelum amend**
  - **Diff changes** yang mudah dibaca
  - **Version increment** (v1 → v2 → ...)
  - **Reset approval chain** dari awal (multi-level)
  - **Guard partial receiving**: tidak bisa hapus item yang sudah diterima, dan qty tidak boleh < received_qty
  - **Inbound tasks idempotent**: tidak ada duplikasi task pada re-approval; expected_qty update sesuai qty baru

### 7.2.1 Backend — Verifikasi & POC (WAJIB sebelum FE)
**Status: NOT STARTED**
1. Tambah POC baru: `/app/test_po_amendment_poc.py`
   - Case A: reason kosong → 400.
   - Case B: amend PO status terminal (cancelled/rejected/completed/closed_short) → 400.
   - Case C: amend saat partial receiving:
     - tidak bisa hapus item yang sudah ada received_qty > 0.
     - tidak bisa turunkan qty < received_qty.
   - Case D: amend memicu reset approval:
     - `status` kembali `waiting_approval` bila chain butuh approval.
     - `approval_chain` rebuilt; `approval_level_current` reset.
   - Case E: snapshot+diff:
     - `po.version` naik.
     - `amendments[-1].snapshot_before` tersimpan.
     - `amendments[-1].changes` berisi perubahan item + header.
   - Case F: inbound tasks idempotent:
     - amend yang mengubah qty tidak menciptakan task ganda.
     - expected_qty task inbound update (bila task existing belum completed/cancelled).
2. Jalankan: `python test_po_amendment_poc.py` dan simpan ringkasan hasil di `/app/test_reports/iteration_XX.json`.

### 7.2.2 Backend — Refactor agar Compliance Hijau
**Status: NOT STARTED**
**Masalah:** `backend/routers/purchase_orders.py` 848 baris → 2 FAIL (`FILE_SIZE`, `MONSTER_FILE`).

**Rencana refactor (disetujui owner):**
1. Buat service baru: `backend/services/po_amendment_service.py`:
   - `diff_po_items(old_items, new_items)`
   - `amend_purchase_order(po_id, payload, actor)` (logic utama; router jadi thin wrapper)
   - Import pattern mengikuti service lain: `from db import db`, lazy import `audit` bila perlu.
2. Router `routers/purchase_orders.py`:
   - Endpoint `/purchase-orders/{po_id}/amend` hanya:
     - require_permission
     - panggil service
     - return safe_doc(result)
3. Pastikan **tidak regress**:
   - inbound task idempotency (`_create_inbound_tasks_for_po`) tetap dipakai.
   - Vendor Bill SSOT AP tidak tersentuh.
4. Jalankan gate compliance: `python scripts/validate_compliance.py` → **0 FAIL**.

### 7.2.3 Frontend — UI Amend + History/Diff (embedded di detail PO)
**Status: NOT STARTED**
1. Tambah tombol aksi di `PODetailPanel.jsx`:
   - Tombol: **"Revisi / Amend PO"** muncul untuk admin/manager dan status amendable (`waiting_approval|pending|receiving|partial`).
   - `data-testid="amend-po-button"`.
2. Tambah modal baru: `frontend/src/features/admin/po/POAmendModal.jsx`
   - Field edit header: supplier (master/atau manual), contact, warehouse (disabled bila sudah ada receipt), ETA, notes.
   - Edit items: tambah/hapus/ubah qty/unit/price/discount_percent (pakai KNSelect; guard empty states).
   - Reason WAJIB (`data-testid="po-amend-reason-input"`).
   - Submit memanggil `POST ${API}/purchase-orders/${po.id}/amend`.
   - Setelah sukses: refresh detail + list; tampilkan notice.
3. Tambah komponen history: `frontend/src/features/admin/po/POAmendmentHistory.jsx`
   - Ditampilkan di `PODetailPanel.jsx` sebagai section di bawah timeline atau sebelum actions.
   - Render versi saat ini (v{po.version}) + daftar amendment (desc) dengan:
     - meta: amended_at/by, reason
     - list `changes[]` (label, from→to) dengan `tabular-nums` untuk angka
     - opsional: expand/collapse `snapshot_before.items` bila perlu (hindari UI terlalu panjang)
   - `data-testid` per entry: `po-amendment-entry-${i}`.
4. Update `POTimeline.jsx`:
   - Tambahkan `amended` ke `EVENT_META` (ikon mis. `History`/`FileText`), agar timeline menampilkan event amendment dengan tone berbeda.
5. Wire parent `PurchaseOrderManagement.jsx`:
   - Tambah handler `handleAmendPO` untuk membuka modal + submit + refresh.
6. Pastikan ukuran file:
   - Komponen baru mencegah `PODetailPanel.jsx` membengkak (≤500 baris).

### 7.2.4 Gates & Verification (Definition of Done)
**Status: NOT STARTED**
Wajib dijalankan setelah perubahan:
1. `bash scripts/seed_reset.sh` (target: **119/0/0**)
2. `python scripts/health_check.py`
3. `python scripts/verify_data_integrity.py`
4. `python scripts/verify_api_contract.py`
   - Bila ada field baru yang dipakai FE dari PO detail, update BINDINGS (jangan mem-bypass gate).
5. `python scripts/ux_audit.py` (target: **0 ERROR**)
6. `python scripts/check_nav_map.py` (jika menyentuh nav; Phase 7.2 biasanya tidak)
7. `python scripts/validate_compliance.py` (target: **0 FAIL**) — memastikan `purchase_orders.py` < 800.
8. FE: `npx esbuild src/index.js --loader:.js=jsx --bundle --outfile=/dev/null`
9. `python scripts/audit_endpoint_sweep.py` (target: **0 5xx**)

### 7.2.5 Testing Agent
**Status: NOT STARTED**
- Jalankan `testing_agent_v3`:
  - Backend: uji amend endpoint (negatif/positif) + dampak status/approval/task.
  - Frontend: uji tombol amend, modal, reason mandatory, history/diff tampil, refresh list/detail.

---

## Next Actions (Updated)
1. **Phase 7.2 (P2) — Backend POC + refactor compliance** (prioritas 1).
2. **Phase 7.2 (P2) — Frontend Amend UI + embedded history/diff** (prioritas 2).
3. Jalankan semua gate + testing_agent_v3 sampai hijau.

---

## Success Criteria (Updated)
- Phase 7.2:
  - Amend PO bisa dilakukan dengan reason mandatory, snapshot+diff, version increment.
  - Approval chain selalu reset dari awal; SoD tetap berlaku pada approve.
  - Guard partial receiving benar (no delete received items, qty ≥ received).
  - Inbound tasks idempotent (tanpa duplikat; expected_qty ikut update).
  - UI menampilkan history/diff di detail PO.
  - **Gates hijau**: seed_reset 119/0/0, ux_audit 0 ERROR, verify_api_contract OK, compliance 0 FAIL (router < 800), esbuild OK, endpoint sweep 0 5xx.
- Tidak ada regressi:
  - Vendor Bill tetap SSOT AP (PO pay endpoint tetap diblokir).
  - Kontrak respons API tetap (tanpa envelope).
  - Tidak ada rename `data-testid` existing.
