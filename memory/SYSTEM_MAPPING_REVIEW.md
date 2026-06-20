# SYSTEM MAPPING REVIEW — Kain Nusantara (KN7)
## Konteks Development (hasil pembacaan menyeluruh seluruh dokumen)

> **Tujuan dokumen:** Peta sistem eksisting yang TERVERIFIKASI terhadap kode nyata,
> agar development berikutnya tidak menimbulkan konflik data / drift / arah yang salah.
> **Aturan emas:** **KODE MENANG atas DOKUMEN.** Bila dokumen (KN_02/03/04/07, PRD lama,
> plan.md) bertentangan dengan kode → ikuti kode + perbaiki dokumen.
> **Disusun:** Sesi migrasi `/tmp/KN7` → `/app` + verifikasi + pembacaan dokumen lengkap.

---

## 1. STATUS LINGKUNGAN (verified live)

- Kode KN7 dimigrasi ke `/app` (backend + frontend), `.env` `/app` dipertahankan (MONGO_URL, DB_NAME, REACT_APP_BACKEND_URL).
- Dependency: semua paket inti sudah ada di environment; hanya `openpyxl` yang di-install (dipakai `routers/admin.py` import/export). Konflik `litellm` di requirements.txt TIDAK relevan (paket sudah terpasang).
- Services: backend (8001) + frontend (3000) RUNNING. Login & dashboard terverifikasi.
- Seed + Gate: `bash scripts/seed_reset.sh` → **86 PASS / 0 FAIL / 0 WARN**; `health_check.py` 20 PASS/3 WARN(kosong)/0 FAIL; `audit_endpoint_sweep.py` **0×5xx**.
- Kredensial demo (password semua: `demo12345`):
  `admin@kainnusantara.id` (admin), `sales@kainnusantara.id` (sales),
  `manager@kainnusantara.id` (manager), `warehouse@kainnusantara.id` / `warehouse2@kainnusantara.id` (warehouse).
- Catatan minor: SESSION_HANDOFF menyebut `DB_NAME=kain_nusantara`, tetapi `/app/.env` memakai `test_database`. Backend & seed sama-sama memakai `test_database` → konsisten & berfungsi. Tidak diubah (hindari risiko).

---

## 2. KONTRAK NYATA KODE (BINDING — bukan KN_07 aspiratif)

| Aspek | KONTRAK NYATA (ikuti ini) | Dokumen aspiratif (JANGAN diikuti) |
|------|---------------------------|-------------------------------------|
| Auth login | `POST /api/auth/login {email,password}` → `{"token":"sess_..","user":{..},"onboarding":..}` | PRD/KN_03: JWT + HttpOnly cookie |
| Token | field **`token`** (bukan `access_token`), header `Authorization: Bearer sess_..` | KN_03: access/refresh JWT |
| Password | **SHA256** `hash_password()` salt `kain-nusantara::` (core_utils) | PRD/KN_02/03: bcrypt/passlib |
| Bentuk respons list | **ARRAY langsung** `[...]` | KN_07: envelope `{success,data,meta}` |
| Bentuk respons detail | **objek langsung** | KN_07: `{success,data}` |
| URL | `/api/...` (TANPA `/v1`) | KN_07: `/api/v1/{domain}/...` |
| State FE | React state lokal + axios (`services/apiClient.js`) + hook `useAppActions.js` | KN_02: Zustand + TanStack Query |
| Chart | **Recharts** | KN_02: Apache ECharts |
| Realtime | **polling** (belum WebSocket/Redis) | KN_05: WebSocket+Redis |
| ID | UUID string berprefiks (`so_`, `prod_`, ...) via `new_id()` | — |
| Waktu | `now_iso()` UTC ISO-8601 | — |

**Util wajib dipakai (jangan re-implement):**
backend `core_utils.py` (`now_iso`, `new_id`, `safe_doc`, `hash_password`), `dependencies.py`
(`current_user`, `require_role`, `require_permission`, `audit`); frontend `formatCurrency`/`formatQty`,
`cn()`, dan SEMUA API call lewat `hooks/useAppActions.js` (bukan axios langsung di komponen).

---

## 3. KOLEKSI TERIMPLEMENTASI (verified di kode) — SSOT: ENTITY_REGISTRY.md

Core: `users`, `sessions`, `products`, `customers`, `warehouses`, `uoms`
Sales: `sales_orders`, `invoices`
Inventory (Roll-as-SSOT): `inventory_rolls` (SSOT fisik) → `inventory_balances` (proyeksi 3-key product+warehouse+owner_entity) → `inventory_movements` (append-only)
WMS: `wms_tasks` (flow_type inbound|outbound — SATU koleksi), `warehouse_transfers` (intra + inter_entity), `cycle_count_sessions`
Procurement: `purchase_orders` (supplier = STRING, belum master)
Documents: `document_templates`, `generated_documents`
Governance: `permission_settings`, `audit_logs`, `user_onboarding`
Multi-entity (Fase 0): `business_entities` (ent_), `notifications` (ntf_)
Config (Fase 1A): `system_settings` (set_), `payment_terms` (pterm_), `approval_rules` (aprule_)

**Invarian data WAJIB (di-enforce verify_data_integrity.py):**
- `on_hand == available+reserved+committed+picked+packed+quarantine+blocked+damaged`; tak ada bucket negatif.
- `balance == Σ inventory_rolls` (per proyeksi) — terutama setelah GR (GR membuat ROLL, bukan `$inc`).
- SO: `total_amount == Σ items.subtotal` (GROSS); `subtotal == price × quantity`. Diskon/PPN di field TERPISAH.
- Backorder (L4-BO): `quantity == reserved_qty + backorder_qty`; `waiting_stock ⟺ Σ backorder>0`; owner-scoped.
- Number-series unik (SO-NNNNN, PO-NNNNN). Dashboard KPI == sumber data (intent invariants).

**Nama field penting:** SO item = `quantity` & `price` (BUKAN `qty`/`unit_price`); transfer item = `qty` (domain beda, benar). SO number field = `number`.

---

## 4. PROGRESS FASE (verified)

- ✅ Fase 0 — Multi-Entity + Notification Center
- ✅ Fase 0.5 — Roll-as-SSOT Inventory Ownership (owner-scoped reservasi, FEFO, ownership matrix)
- ✅ Fase 1A — Configuration Foundation (settings/payment_terms/approval_rules)
- ✅ Fase 1B — Configuration Consumption (PPN otomatis, diskon item/order, approval dinamis)
- ✅ Sub-fase 1.4 — ATP & Fulfillment Modes (preview-allocation READ-ONLY, Status Stok board)
- ✅ Sub-fase 1.5 — Inter-Company Transfer Flow (mutasi kepemilikan B→E)
- ✅ Sub-fase 1.6 + 1.6.1 — Backorder Lifecycle (waiting_stock, auto-fulfill saat GR, decouple approval) ← TERBARU

**Belum (lanjutan Fase 1 Sales):** allocation policy R1/R2 configurable, mixed-lot confirmation UI, pengiriman parsial FISIK backorder (multi-shipment Surat Jalan), pegging/earmarking, HPP/unit_cost (Fase 4).

---

## 5. ROADMAP 6 FASE (KN_DEVELOPMENT_PLAN_FROM_ASSESSMENT — master)

- **Fase 1 — Sales & Marketing:** special price (`price_approvals` pra_), faktur pajak (`tax_invoices` fkt_), return/BS (`sales_returns` sret_), special order (`special_orders` sord_), price list (`customer_price_lists` cpl_), status SO diperluas, katalog publik.
- **Fase 2 — HRD:** `hr_employees`, `attendance_records`, `kpi_records`, `design_gallery` (+AI Gemini).
- **Fase 3 — Purchasing:** `suppliers` master (refactor PO string→FK), approval pembelian, `bom_printing`, `cash_transactions`, toleransi ±2%.
- **Fase 4 — Finance:** `chart_of_accounts`, `journal_entries`, `bank_accounts`, tax, AR aging+denda, closing bulanan, auto-posting, HPP.
- **Fase 5 — Warehouse+RFID:** Zone→Rack→Level→Bin, `warehouse_locations`/`rfid_tags`/`rfid_devices`/`rfid_events`, gate monitor, simulator.
- **Fase 6 — Additional / BI.**

> Semua entitas masa depan SUDAH didaftarkan PLANNED di ENTITY_REGISTRY (prefix + nama) → daftar dulu sebelum coding agar tak duplikat.

---

## 6. TEMUAN DRIFT DOKUMEN (penting — laporkan jujur)

1. **Discovery module** — `plan.md` (panjang) masih menggambarkan modul Discovery sbg "COMPLETED",
   PADAHAL sudah **DIHAPUS TOTAL 17 Jun 2026** (lihat PRD changelog v1.3 + ENTITY_REGISTRY baris 537 + KN_13 baris 581 yang masih stale ✅). **Kode benar (tidak ada discovery); plan.md & KN_13 stale.**
2. **KN_02/03/04/07** = standar **ASPIRATIF** (JWT/cookie/bcrypt/Redis/Zustand/TanStack/ECharts/`/api/v1`/`inventory_items`). **Kode nyata berbeda** (lihat §2). Guardrails sudah menegaskan ini.
3. **PRD §2.1/§5** menyebut "JWT+Bcrypt" & koleksi `inbound_tasks/outbound_tasks/transfers` — **stale/keliru** (nyata: SHA256+sess_; `wms_tasks`+`warehouse_transfers`).

> Rekomendasi: saat menyentuh area terkait, sinkronkan dokumen stale (plan.md Discovery, KN_13 discovery, PRD auth) — tapi TIDAK mengubah kode yang sudah benar.

---

## 7. ATURAN MAIN DEVELOPMENT (dari KN_00 + GUARDRAILS)

- **Bahasa ke user: Indonesia.** Kode: English. UI label: Indonesia.
- **Batas file:** React .jsx ≤500, Python router ≤800, util .js ≤300, CSS ≤400. (`outbound_picking.py` 552 → pantau).
- **STOP & ASK** sebelum: drop/migrate koleksi, hapus/rename endpoint, ubah auth, tambah dependency, tambah menu di luar Navigation Map.
- **Sebelum buat koleksi/endpoint/komponen baru:** cek ENTITY_REGISTRY + CODEBASE_MAP + grep existing (cegah duplikat/RC-1).
- **Definition of Done (Gate A/B/C):** seed_reset hijau + health_check 0 FAIL + endpoint_sweep 0×5xx + ux_audit tak menambah ERROR + validate_compliance tak menambah pelanggaran + testing_agent_v3 untuk perubahan signifikan. Loading/empty/error state wajib; angka pakai `tabular-nums`; elemen interaktif punya `data-testid`.
- **Anti RC-10 (false positive):** "200/running/no-error" BUKAN bukti. Bukti = nilai data benar + invarian terpenuhi + UI menampilkan data.

---

**Kesimpulan:** Sistem = ERP/WMS multi-entitas matang, sehat (semua gate hijau), siap dikembangkan.
Fase Sales (1.7+) atau lompat ke Fase 2/3/4/5 — **menunggu keputusan prioritas user.**
