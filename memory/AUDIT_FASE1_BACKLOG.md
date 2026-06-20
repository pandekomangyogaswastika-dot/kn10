# AUDIT FASE 1 — KN7 (per ENGINEERING_GUARDRAILS)
**Tanggal audit:** sesi lanjutan · **Cakupan:** Fase 0 → Sub-fase 1.7 (semua yang sudah ter-deliver)
**Metode:** seluruh gate/audit script dijalankan + scan ukuran file + review kontrak & dokumen.
**Catatan:** Audit-only. Belum ada perbaikan diterapkan; semua temuan dicatat sebagai backlog.

---

## A. RINGKASAN GATE (BLOCKING / Definition-of-Done)

| Gate | Hasil | Status |
|------|-------|--------|
| `verify_contract.py --all` | Tidak ada koleksi terlarang; semua kanonik | ✅ OK |
| `verify_api_contract.py` (FE↔BE) | ERROR 0 / WARN 0 | ✅ OK |
| `verify_data_integrity.py` | **86 PASS / 0 FAIL / 0 WARN** (semua invarian) | ✅ OK |
| `audit_endpoint_sweep.py` | OK 45 · EMPTY 4 · **5xx/EXC 0** · 4xx 10 (terkontrol) | ✅ OK |
| `audit_collection_drift.py` | Hanya koleksi kosong (belum di-seed) | ✅ INFO |
| `find_dead_services.py` | 9/9 service terpakai, 0 dead | ✅ OK |
| `health_check.py` | 20 PASS / 3 WARN (kosong) / 0 FAIL | ✅ OK |

**Kesimpulan fungsional:** Tidak ditemukan bug fungsional / pelanggaran invarian / 5xx pada Fase 0–1.7.
Sistem sehat secara data & kontrak. Temuan di bawah bersifat **standar/registrasi/UX-polish/doc-drift**.

---

## B. GATE NON-BLOCKING (perlu perhatian)

| Gate | Hasil |
|------|-------|
| `validate_compliance.py` | **53 PASS / 2 FAIL / 2 WARN** → lihat BUG-01..03 |
| `ux_audit.py` | 0 ERROR / **23 WARN** (di 48 file) → lihat UX-01..03 |
| `check_nav_map.py` | **NEEDS ATTENTION / 27 issue** → lihat NAV-01..02 |

---

## C. BACKLOG TERSTRUKTUR

### 🔴 HIGH — Regresi standar diperkenalkan di Sub-fase 1.7 (DoD blocker)

**BUG-01 — [FILE_SIZE] `frontend/src/features/sales/PriceApprovals.jsx` 558 baris > batas 500 (MONSTER_FILE)**
- Sumber: `validate_compliance.py` (FAIL ×2).
- Dampak: melanggar batas ukuran file guardrails; 1.7 belum benar-benar "DONE" menurut gate ini.
- Rekomендasi: refactor → pisahkan form (`PriceApprovalForm.jsx`), kartu (`PriceApprovalCard.jsx`),
  dan/atau hook data (`usePriceApprovals.js`). Target setiap file < 500.
- Estimasi: kecil (1–2 jam). **Disarankan diperbaiki paling awal.**

### 🟠 MEDIUM — Registrasi koleksi belum lengkap (Sub-fase 1.7)

**BUG-02 — `price_approvals` belum terdaftar di hardcoded list `validate_compliance.py`**
- Lokasi: `scripts/validate_compliance.py` → `check_entity_registry_sync()` `known_collections` (≈baris 296)
  dan whitelist `check_naming()` (≈baris 495).
- Dampak: WARN "tidak ada di ENTITY_REGISTRY" & WARN "domain prefix" (false-positive checker).
- Catatan: koleksi SUDAH terdaftar di `ENTITY_REGISTRY.md` + `verify_contract.CANONICAL_COLLECTIONS` +
  `seed_realistic.clear_collections`. Yang kurang hanya list di validate_compliance.py.
- Rekomendasi: tambahkan `price_approvals` ke kedua list checker tsb. (kecil)
- Pelajaran (proses): **registrasi koleksi baru perlu 4 tempat** → ENTITY_REGISTRY.md, verify_contract.py,
  validate_compliance.py (2 list), seed_realistic.clear. Tambahkan ke checklist guardrails.

### 🟡 LOW — UX polish (sebagian pre-existing, sebagian 1.7)

**UX-01 — Native `<select>` (WARN W2)** — gunakan komponen Select shadcn.
- File: `features/sales/PriceApprovals.jsx` (1.7), `AdminWorkspace`, `OrdersView`,
  `InitialStockForm`, `TransferCreateForm` (pre-existing).

**UX-02 — Tampilan uang tanpa `tabular-nums` (WARN W1)** — `features/orders/OrdersView.jsx` (pre-existing).

**UX-03 — Chart tanpa `<Tooltip>` (WARN W4)** — chart dashboard/reports (pre-existing).

> ux_audit baseline: 0 ERROR (lulus). Semua di atas WARN, bukan blocker.

### 🟠 MEDIUM — Navigasi vs KN_13 (pre-existing)

**NAV-01 — Konvensi `data-testid` nav tidak sesuai KN_13**
- `check_nav_map.py` mengharapkan testid `nav-home`, `nav-pos`, `nav-orders`, `nav-wms`, dst. dan
  `wms-tab-stok/inbound/outbound/transfer/cycle`. Kode aktual memakai skema berbeda (berfungsi).
- Dampak: gate nav-map "NEEDS ATTENTION" (bukan gate blocking). Drift dokumen↔kode.
- Rekomendasi: pilih SATU — (a) tambah testid sesuai KN_13 di Sidebar/WMS tabs, atau
  (b) update KN_13 + check_nav_map ke konvensi aktual. (sedang)

**NAV-02 — Kedalaman navigasi (11 view switch)** — KN_13 sarankan hierarki lebih datar. (low)

### 🟡 LOW — Ukuran file mendekati/di atas pedoman (pantau; tidak di-gate)

**SIZE-01 — `frontend/src/hooks/useAppActions.js` 485 baris** > pedoman util .js 300.
- Tidak di-flag gate (hook diperlakukan beda), tapi melebihi pedoman. Pertimbangkan pecah per-domain hook.

**SIZE-02 — pantau:** `services/roll_service.py` 583, `routers/transfers.py` 565,
`routers/outbound_picking.py` 552 — semua **masih < 800** (batas router/service), jadi BUKAN pelanggaran.
CODEBASE_MAP lama menandai outbound_picking "MELEBIHI BATAS" (acuan 500 usang) → perlu sinkron acuan.

### 🟠 MEDIUM/LOW — Doc-vs-code drift (SSOT accuracy)

**DOC-01 — `plan.md` USANG (MED)** — masih menggambarkan modul "Discovery" sebagai COMPLETED,
padahal sudah DIHAPUS 17 Jun 2026 (PRD changelog v1.3 + ENTITY_REGISTRY). → tandai/buang bagian itu.

**DOC-02 — `KN_13_NAVIGATION_MAP.md` USANG (MED)** — masih mereferensikan route `/discovery/` ✅.

**DOC-03 — `PRD.md §2.1/§5` USANG (LOW)** — tertulis "JWT + Bcrypt" & koleksi
`inbound_tasks/outbound_tasks/transfers`. Aktual: SHA256+`sess_`, `wms_tasks`(flow_type)+`warehouse_transfers`.

**DOC-04 — `KN_02/03/04/07` ASPIRATIF tapi tidak ditandai jelas (LOW)** — menulis envelope `{success,data}`,
`/api/v1`, Redis, Zustand, TanStack, ECharts, `inventory_items/inventory_stock` yang TIDAK dipakai kode.
Rekomendasi: beri header tegas "ASPIRATIONAL/TARGET — bukan kontrak berjalan" agar agent lain tak salah.

### 🟡 LOW — Code smell (Sub-fase 1.7)

**SMELL-01 — `download_attachment` menyuntik `request.scope["headers"]`** untuk fallback auth via query-param
(`?auth=`) demi `<img>/<a>`. Berfungsi & teruji, tapi sebaiknya pakai dependency khusus / signed short-lived
token agar lebih bersih & aman. (low)

---

## D. PRIORITAS USULAN PERBAIKAN (saat keputusan fix diambil)
1. BUG-01 (refactor PriceApprovals.jsx < 500) — DoD blocker, mudah.
2. BUG-02 (lengkapi registrasi price_approvals di validate_compliance.py) — mudah, hilangkan 2 WARN.
3. DOC-01/02 (bersihkan referensi Discovery yang usang) — cegah kebingungan agent.
4. NAV-01 (selaraskan testid nav ↔ KN_13) — sedang.
5. UX-01..03, SIZE-01, DOC-03/04, SMELL-01 — polish bertahap.

> **Tidak ada item yang memblokir fungsi berjalan.** Semua gate invarian/kontrak/health HIJAU.
> Backlog ini murni peningkatan kepatuhan standar, kebersihan kode, dan akurasi dokumen.

---

## E. GAP FUNGSIONAL TERENCANA (ditemukan saat audit)

**GAP-UOM — Engine Konversi UOM (Multi-UOM) belum ada / field placeholder tak terpakai**
- Severity: **MEDIUM** (fondasi lintas-modul; bukan bug runtime).
- Bukti:
  - `routers/uoms.py` = CRUD datar (code/name/base_type/precision) — TANPA faktor konversi.
  - `product.uom_conversions[]` ada di skema + seed `[]` + field PATCH, **TIDAK dikonsumsi** kode mana pun
    (no-op placeholder → termasuk dead-field/tech-debt).
  - SO/PO/inventory mengasumsikan `base_unit` tunggal (meter); tidak ada `base_quantity`.
- Kebutuhan terdokumentasi & RESOLVED tapi TIDAK terjadwal: KN_16 I3, KN_15 E12, KN_01, SYSTEM_ANALYSIS,
  COMPREHENSIVE_ERP_ASSESSMENT (UOM Conversion Table).
- Tindakan: **DITAMBAHKAN ke roadmap → `plan.md` Sub-fase 1.13 — UOM Conversion Engine** (lihat detail di plan.md).
- Rekomendasi: aktifkan `uom_conversions` + `services/uom_service.py` + `base_quantity` di SO/PO,
  + invarian `base_quantity == to_base(unit, qty)` di verify_data_integrity. Prioritas urutan menunggu user.

