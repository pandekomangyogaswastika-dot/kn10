# Gap Analysis Modul Purchasing — Kain Nusantara ERP
**Konteks:** Manufaktur/Distribusi Tekstil Indonesia
**Pembanding:** Odoo (Purchase + Inventory) & SAP/Oracle (P2P Enterprise)
**Metode:** Audit kode aktual (backend routers/services + frontend) + benchmark ERP mature
**Tanggal:** Sesi lanjutan (post L1–L3, M3–M6, L1b)

---

## 1. RINGKASAN EKSEKUTIF

Modul Purchasing Kain Nusantara sudah **jauh di atas rata-rata** untuk skala UMKM/menengah:
hulu→hilir dari Purchase Requisition (PR) → approval → Purchase Order (PO) → Goods Receipt
(GR) + QC Hold/Quarantine → Purchase Return (Nota Debit) → AP/Hutang + pembayaran kas, plus
Supplier Master + Price-List + Scorecard + Reorder Replenishment.

Namun, dibandingkan ERP mature (Odoo/SAP) dan **kebutuhan spesifik industri tekstil Indonesia**,
ada **6 gap fundamental (P0)** yang menahan modul ini naik kelas ke "manufacturing-grade":

| # | Gap P0 | Dampak |
|---|--------|--------|
| 1 | **3-Way Matching + Vendor Bill** | Tidak ada kontrol PO↔GR↔Invoice. AP dihitung langsung dari PO → risiko bayar lebih dari yang ditagih/diterima |
| 2 | **PPN & Diskon pada PO + Faktur Pajak Masukan** | PO tanpa pajak/diskon. PPN Masukan tidak tercatat → tidak bisa kredit pajak (non-compliant PKP) |
| 3 | **Dye Lot + Grade aktual saat terima** | Grade di-hardcode "A". Dye lot pakai field generik. Risiko shade mismatch (cacat fatal tekstil) |
| 4 | **Landed Cost / Biaya Angkut** | Freight/bea/asuransi tidak dialokasi ke HPP → costing & margin tidak akurat (krusial untuk impor benang) |
| 5 | **RFQ / Request for Quotation** | Tidak ada tender multi-supplier + perbandingan harga → potensi penghematan hilang |
| 6 | **Blanket/Contract PO (call-off)** | Tidak ada PO payung untuk pembelian benang/greige berulang dengan jadwal release |

---

## 2. INVENTARIS FITUR PURCHASING SAAT INI (ter-grounded dari kode)

### 2.1 Purchase Requisition (PR) — `routers/purchase_requisitions.py`, `services/purchase_requisition_service.py`
- Buat PR dari 3 sumber: `manual` | `reorder` | `special_order`.
- Mendukung item **katalog & non-katalog** (deskripsi bebas untuk special order).
- Estimasi harga (`est_price`), subtotal, `total_est_amount` (ada invarian data-integrity L4-PR).
- Approval **dinamis** dari matriks (`evaluate_approval` berbasis total).
- Lifecycle: `draft → pending_approval → approved → converted | rejected | cancelled`.
- **Segregation of Duties (SoD)**: pembuat PR tidak boleh approve PR-nya sendiri.
- **Konversi PR → PO** (pilih supplier + gudang, auto-resolve harga price-list).
- **Reorder Suggestions** (`reorder-suggestions`): berbasis `reorder_point`/`reorder_qty`,
  proyeksi `available + on_order` (anti double-order), lead-time → ETA, supplier preferensi.

### 2.2 Purchase Order (PO) — `routers/purchase_orders.py`
- Buat PO dari Supplier Master (FK) **atau** supplier manual (backward-compat).
- Baris item: `product_id, quantity, unit, price, subtotal, received_qty`.
- **Auto-isi harga** dari Supplier Price-List (`resolve_price`, tiered MOQ + masa berlaku).
- **Price-Deviation Guard**: jika harga PO > price-list + threshold% → wajib approval.
- Approval matriks dinamis (amount threshold + price deviation), SoD aktif.
- Status: `waiting_approval → pending → receiving → partial | completed | closed_short | cancelled | rejected`.
- **Timeline** lengkap (created, submitted, approved, received, paid, dll).
- **Toleransi penerimaan ±X%** (configurable, default 2% — cocok untuk benang).
- **Short-Close** (tutup-kurang) bila barang tak terkirim penuh.
- **PO Payment** → catat `cash_transaction` (kas keluar) + update AP, `payment_status` (unpaid/partial/paid), `outstanding`.
- **Dokumen Surat Penerimaan Barang** (HTML/print).

### 2.3 Account Payable (AP / Hutang) — `purchase-orders/payables/summary`
- Aging buckets `0-30 / 31-60 / 61-90 / >90`, ringkasan per-supplier & per-PO.
- `_po_financials`: total, received_value, returned_amount, amount_paid, outstanding.
- **CATATAN:** AP dihitung **langsung dari PO** (total − retur − bayar). **Belum ada Vendor Bill.**

### 2.4 Supplier Intelligence — `routers/suppliers.py`, `services/supplier_service.py`
- CRUD Supplier Master (code, npwp, pic, phone, email, kota, `goods_type`, `payment_term_code`, `lead_time_days`).
- **Price-List** per (supplier, product): price, unit, **MOQ (`min_qty`)**, lead-time, masa berlaku, currency.
- `resolve_price`: pilih tier MOQ terbaik + validitas tanggal, fallback ke harga produk.
- **Scorecard** dari data NYATA: on-time rate, avg lead-time, fill-rate, reject/quality rate, total spend, **rating komposit 0–5**.

### 2.5 Goods Receipt + QC — `routers/inbound_receiving.py`, `services/qc_service.py`
- Scan-receive (batch/lot/roll/bin), enforce toleransi, **eskalasi** ke manager bila selisih.
- **QC Hold/Quarantine** saat GR (configurable `qc_on_receipt`): barang masuk → roll `quarantine` (BUKAN langsung available).
- **QC Decision**: accept (→available, auto-fulfill backorder) / reject (`damaged` | `return` → auto Nota Debit).
- **Roll-as-SSOT** (KN_15): semua transisi di level roll, balance di-rebuild dari rolls.

### 2.6 Purchase Return / Nota Debit — `routers/purchase_returns.py`
- Buat retur (dengan/tanpa PO), item + alasan + kondisi, workflow approval.
- Auto-generate dari QC reject (`source=qc_reject`), `submitted_at/by` + timeline (M4).

### 2.7 Cash Management — `routers/cash.py`
- Kas kecil (per entitas) / kas besar (gabungan); pembayaran PO ↔ cash transaction.

### 2.8 Konfigurasi Purchasing (`config_service.py`)
```
receive_tolerance_percent: 2.0
require_supplier_master: False
qc_on_receipt: True
price_deviation_approval_percent: 10.0
sales.quotation_enabled: False   ← flag RFQ ADA tapi belum diimplementasi
```

---

## 3. GAP ANALYSIS DETAIL (vs Odoo & SAP/Oracle + Tekstil)

### A. PROCURE-TO-PAY CORE

#### A1. ⛔ 3-Way Matching + Vendor Bill (P0)
- **Sekarang:** AP = PO total − retur − bayar. Tidak ada dokumen tagihan supplier terpisah.
- **Odoo:** `purchase.order` → `stock.picking` (GRN) → `account.move` (Vendor Bill). Bill di-match
  ke PO+receipt; ada "Bill Control" (on ordered qty / on received qty) + 3-way match status.
- **SAP:** MIRO Invoice Verification dengan GR/IR clearing account; toleransi harga/qty.
- **Gap:** Tidak ada kontrol bahwa yang dibayar = yang ditagih = yang diterima. Risiko overpayment,
  tidak ada GR/IR reconciliation, tidak ada pencatatan tagihan parsial vs PO.

#### A2. ⛔ RFQ / Request for Quotation (P0)
- **Sekarang:** Langsung buat PO/PR→PO. `quotation_enabled: False`.
- **Odoo:** RFQ → kirim ke banyak vendor → bandingkan → confirm jadi PO. Purchase Agreements.
- **SAP:** RFQ (ME41) → Quotation (ME47) → Price Comparison (ME49).
- **Gap:** Tidak ada tahap penawaran kompetitif → tidak ada audit trail "kenapa supplier X dipilih".

#### A3. ⛔ Blanket / Contract PO (call-off) (P0)
- **Sekarang:** Hanya PO transaksional satu kali.
- **Odoo/SAP:** Blanket Order / Outline Agreement (Value/Quantity Contract) dengan release/call-off.
- **Gap (tekstil):** Pembelian benang/greige biasanya kontrak volume tahunan + penarikan bertahap
  sesuai harga & jadwal disepakati. Tidak terdukung.

### B. COMPLIANCE INDONESIA

#### B1. ⛔ PPN & Diskon pada PO (P0)
- **Sekarang:** `POItemCreate` = {product_id, quantity, unit, price}. `total_amount` = Σ subtotal, TANPA pajak/diskon.
  (Padahal Sales sudah punya `discount_percent` item & order.)
- **Gap:** Tidak bisa hitung DPP, PPN 11%, diskon supplier, grand total bersih. Tidak sinkron dengan modul tax (PPN excluded/included sudah ada di `config.tax`).

#### B2. ⛔ Faktur Pajak Masukan / Input VAT (P0)
- **Sekarang:** `tax_invoice_service` hanya sisi **Keluaran** (jual).
- **Gap:** PKP wajib mencatat Faktur Pajak Masukan dari supplier untuk **pengkreditan PPN**. Belum ada
  entity faktur pajak masukan, nomor seri, validasi, rekap PPN Masukan vs Keluaran.

### C. TEKSTIL-SPECIFIC (prioritas user)

#### C1. ⛔ Dye Lot Tracking (P0)
- **Sekarang:** Roll punya `lot`/`batch` **generik** (auto `LOT-{po_number}`). Allocation `lot_mode: prefer_single`.
- **Gap:** **Dye lot** (nomor pencelupan) adalah identitas warna/shade kritis di tekstil — kain beda dye
  lot bisa beda shade walau motif/warna "sama". Perlu: tangkap dye lot saat GR, tegakkan "satu SO/cutting dari satu dye lot", peringatan shade-mismatch.

#### C2. ⛔ Grade / Quality aktual saat terima (P0)
- **Sekarang:** Roll grade **hardcoded `"A"`** di `inbound_receiving.complete` (~line 318). QC hanya accept/reject **qty**, tidak menetapkan grade.
- **Gap:** Tekstil butuh grading A / B / BS (reject) saat inspeksi; harga & alokasi beda per grade.

#### C3. ⚠ GSM/Gramasi & Lebar aktual per-roll (P1)
- **Sekarang:** `gramasi` & `lebar` ada di **product master** (untuk catch-weight kg). Tidak dicatat **aktual per roll** saat terima.
- **Gap:** Gramasi & lebar aktual sering menyimpang dari spec; perlu capture + toleransi (mis. GSM ±5%, usable width).

#### C4. ⚠ 4-Point Inspection System (P1)
- **Sekarang:** QC = accept/reject qty + disposisi.
- **Gap:** Standar global inspeksi kain (4-point/100 yd²) untuk grading defect objektif. Tidak ada.

#### C5. ⚠ Catch-weight / Dual-UoM pembelian (P1)
- **Sekarang:** UOM engine meter↔kg (gramasi×lebar) ada; konversi di GR sudah jalan.
- **Gap:** Beli benang per **kg**, kelola per cone/kg; beli kain per **roll/meter**. Perlu dual-UoM eksplisit di PO + rekonsiliasi berat aktual saat terima (catch-weight).

### D. APPROVAL & KONTROL

#### D1. ⚠ Multi-level / Sequential Approval (P2)
- **Sekarang:** `evaluate_approval` → satu `required_role`. ApprovalInbox agregasi lintas modul (M6).
- **Gap:** Tidak ada rantai bertingkat (SPV→Manager→Direktur) sequential dengan jejak per level + delegasi.

#### D2. ⚠ Budget / Commitment Control (P2)
- **Gap:** Tidak ada cek anggaran sebelum PR/PO (commitment accounting).

### E. OPERATIONAL / UX

| Item | Status | Catatan |
|------|--------|---------|
| PO Revisi/Amendment + version history | ⛔ | Hanya cancel; tak bisa edit PO |
| Delivery schedule per-line (multiple deliveries) | ⚠ | received_qty akumulatif, tanpa jadwal |
| Kirim PO (PDF) ke supplier via email | ⛔ | Belum ada |
| Multi-currency / FX (impor) | ⚠ | Field currency ada, FX tidak ada |
| Drop-ship / direct delivery | ⛔ | Belum ada |
| Supplier consignment purchasing (alur lengkap) | ⚠ | `ownership_type` ada, alur beli belum |

---

## 4. ROADMAP IMPLEMENTASI (Prioritas)

### 🔴 FASE P0 — Fondasi P2P + Compliance + Tekstil Inti
1. **PPN & Diskon pada PO** — tambah `discount_percent` (item & order), `tax_mode`, DPP, PPN, grand_total.
   Sinkron `config.tax`. (Backend schema + create logic + UI PO form + detail).
2. **Vendor Bill + 3-Way Matching** — entity `vendor_bills`; match PO↔GR↔Bill (qty/price + toleransi);
   AP beralih berbasis Bill (bukan PO langsung); GR/IR clearing konsep.
3. **Faktur Pajak Masukan** — entity input VAT (nomor seri, DPP, PPN), rekap Masukan vs Keluaran.
4. **Dye Lot + Grade aktual saat GR/QC** — capture `dye_lot` & `grade` per roll saat terima; QC set grade A/B/BS;
   tegakkan single dye-lot pada fulfillment kritikal (extend allocation).
5. **Landed Cost** — dokumen biaya tambahan (freight/bea/asuransi) → alokasi ke HPP roll (by value/qty/weight).

### 🟠 FASE P1 — Sourcing & QC Tekstil
6. **RFQ / Quotation** — RFQ multi-supplier → perbandingan harga → konversi ke PO (aktifkan `quotation_enabled`).
7. **GSM/Lebar aktual per-roll + toleransi** — capture saat GR + flag deviasi spec.
8. **4-Point Inspection** — form defect scoring → grade otomatis.
9. **Catch-weight / Dual-UoM PO** — beli kg, terima kg aktual + konversi.

### 🟡 FASE P2 — Kontrol Lanjutan & UX
10. **Blanket/Contract PO** + call-off release schedule.
11. **Multi-level sequential approval** + delegasi.
12. **PO amendment/version history**.
13. **Kirim PO PDF ke supplier** (email), **multi-currency/FX**, **drop-ship**, **budget control**.

---

## 5. REKOMENDASI LANGKAH BERIKUTNYA
Mulai dari **P0-1 (PPN/Diskon PO)** + **P0-2 (Vendor Bill/3-Way Match)** karena keduanya saling terkait
dan memberi dampak terbesar pada integritas keuangan & compliance. Disusul **P0-4 (Dye Lot/Grade)** untuk
nilai tekstil inti. Setiap item harus melewati gate `seed_reset.sh` → `health_check.py` →
`verify_api_contract.py` → `ux_audit.py`.
