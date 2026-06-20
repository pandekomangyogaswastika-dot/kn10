from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from core_utils import new_id


class CustomerAddress(BaseModel):
    id: str = Field(default_factory=lambda: new_id("addr"))
    label: str = "Alamat Utama"
    recipient_name: str
    phone: str = ""
    city: str
    address: str
    is_primary: bool = False


class CustomerCreate(BaseModel):
    name: str
    pic_name: str
    phone: str
    email: str = ""
    type: str = "Retail"
    city: str
    address: str
    npwp: str = ""
    credit_limit: float = 0
    sales_pic: str = ""
    entity_id: str = ""
    enforce_single_dye_lot: bool = False  # P0-4 — paksa alokasi 1 dye lot untuk customer ini
    lot_policy: str = ""                  # "" | prefer_single | strict_single | allow_mixed
    created_by: str = "Sales Demo"


class BusinessEntityCreate(BaseModel):
    """Entitas legal grup (Multi-Entity — Fase 0)."""
    legal_name: str
    short_name: str
    type: str = "PT"            # PT | CV
    npwp: str = ""
    address: str = ""
    city: str = ""
    default_tax_mode: str = "ppn"  # ppn | non_ppn
    doc_prefix: str = ""          # mis. KSC, KANDA — untuk nomor dokumen per entitas
    logo_url: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    name: str
    email: str
    role: str
    password: str = "demo12345"


class GenericPatch(BaseModel):
    data: Dict[str, Any]


class ProductPayload(BaseModel):
    sku: str
    name: str
    category: str = "Kain"
    variant: str = "Regular"
    color: str = "Natural"
    motif: str = "Polos"
    grade: str = "A"
    supplier: str = "Internal"
    base_unit: str = "meter"
    price: float = 0
    harga_pokok: float = 0
    gramasi: float = 0
    lebar: float = 0                      # Sub-fase 1.13 — lebar kain (meter), utk konversi kg (catch-weight)
    kg_per_meter: float = 0               # Fase 8 — faktor catch-weight eksplisit (kg/m); 0 = turunkan dari gramasi×lebar
    reorder_point: float = 0              # Depth #2b — ambang batas saran beli (0 = nonaktif)
    reorder_qty: float = 0               # Depth #2b — qty saran beli per replenishment (0 = pakai gap)
    image: str = "https://images.unsplash.com/photo-1774679817333-decf0d988dd5?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85"
    status: str = "active"
    uom_conversions: List[Dict[str, Any]] = []


class WarehousePayload(BaseModel):
    code: str
    name: str
    city: str
    bin_code: str = "A1-01"
    bin_capacity: float = 1000
    lat: Optional[float] = None
    lng: Optional[float] = None


class UOMPayload(BaseModel):
    code: str
    name: str
    base_type: str = "length"
    precision: int = 2
    factor_to_base: float = 1.0          # Sub-fase 1.13 — meter per 1 unit (FIXED, length only)


class TemplatePayload(BaseModel):
    document_type: str
    name: str
    header: str = "Kain Nusantara"
    footer: str = "Dokumen dibuat otomatis oleh sistem."
    columns: List[str] = []
    logo_url: str = ""
    paper_size: str = "A4"
    orientation: str = "portrait"
    margin_mm: int = 12
    signature_left: str = "Dibuat Oleh"
    signature_right: str = "Disetujui Oleh"
    section_order: List[str] = ["header", "customer", "items", "allocation", "signature", "footer"]


class PermissionUpdate(BaseModel):
    matrix: Dict[str, Dict[str, List[str]]]


class WMSTaskCreate(BaseModel):
    flow_type: str = "inbound"
    source_type: str = "supplier"
    product_id: str
    quantity: float
    unit: str = "meter"
    warehouse_id: str
    bin_id: str
    batch: str
    lot: str
    roll_id: str


class ScannerScan(BaseModel):
    scan_type: str
    scan_value: str
    actor: str = "Warehouse Demo"


class SalesOrderItemIn(BaseModel):
    product_id: str
    quantity: float
    unit: str
    base_quantity: float = 0             # Sub-fase 1.8/1.13 — qty dlm base unit (forward-compat)
    discount_percent: float = 0          # Fase 1B — diskon per item (0–100%)
    price_approval_id: str = ""          # Sub-fase 1.7 — harga khusus disetujui (override harga)


class SalesOrderCreate(BaseModel):
    customer_id: str
    shipping_address_id: str
    items: List[SalesOrderItemIn]
    sales_name: str = "Ayu Marketing"
    shipment_policy: str = "allow_partial_shipment"
    entity_id: str = ""
    order_discount_percent: float = 0     # Fase 1B — diskon level order (0–100%)
    payment_term_code: str = ""           # Fase 1B — term pembayaran (kode)
    allow_backorder: bool = False         # Sub-fase 1.6 — izinkan reservasi parsial + backorder
    confirm_mixed_lot: bool = False       # Sub-fase 1.7/MixedLot — konfirmasi pemenuhan lintas-lot


class AllocationPreviewItem(BaseModel):
    product_id: str
    quantity: float
    unit: str = "meter"


class AllocationPreviewIn(BaseModel):
    """Preview pemenuhan/ATP per baris SEBELUM order dibuat (Sub-fase 1.4, READ-ONLY)."""
    items: List[AllocationPreviewItem]
    entity_id: str = ""          # entitas penjual; kosong → default/owner customer
    customer_id: str = ""        # opsional (konteks kota; tidak mengubah ATP)


class InterCompanyTransferItem(BaseModel):
    product_id: str
    quantity: float
    unit: str = "meter"


class InterCompanyTransferCreate(BaseModel):
    """Sub-fase 1.5 — minta transfer kepemilikan antar-entitas (B→E) dari preview POS.
    EXTEND warehouse_transfers (transfer_kind=inter_entity)."""
    source_entity_id: str                       # B (pemilik stok)
    dest_entity_id: str                         # E (entitas penjual yang butuh)
    items: List[InterCompanyTransferItem]
    linked_order_id: Optional[str] = None       # SO pemicu (opsional)
    transfer_price: Optional[float] = None      # Fase 4 (nullable; tidak ada dampak akuntansi sekarang)
    notes: str = ""
    requested_by: str = ""


class PaymentSimulationCreate(BaseModel):
    amount: float = 0                    # Fase 1B — opsional; default = grand_total order
    method: str = "Transfer Simulasi"
    created_by: str = "Admin Demo"


class DocumentGenerate(BaseModel):
    document_type: str
    source_id: str
    actor: str = "Admin Demo"


class BarcodeGenerate(BaseModel):
    target_type: str
    target_id: str
    label_size: str = "80x50mm"


WAREHOUSE_PRIORITY = {
    "Jakarta": ["Jakarta", "Bandung", "Surabaya"],
    "Bandung": ["Bandung", "Jakarta", "Surabaya"],
    "Surabaya": ["Surabaya", "Bandung", "Jakarta"],
    "Denpasar": ["Surabaya", "Jakarta", "Bandung"],
}


# ─── Transfer Schemas ────────────────────────────────────────────────────────

class TransferItem(BaseModel):
    product_id: str
    qty: float
    unit: str = "meter"
    batch: str = ""
    lot: str = ""
    roll_id: str = ""


class TransferCreate(BaseModel):
    source_warehouse_id: str
    dest_warehouse_id: str
    items: List[TransferItem]
    notes: str = ""
    requested_by: str = "Warehouse User"


class TransferApprove(BaseModel):
    approved_by: str = "Manager"


class TransferReject(BaseModel):
    rejected_by: str = "Manager"
    reason: str = ""


class TransferStatusUpdate(BaseModel):
    status: str  # picking, staging, dispatched, completed
    updated_by: str = "Warehouse User"


# ─── Purchase Order Schemas ──────────────────────────────────────────────────

class POItemCreate(BaseModel):
    product_id: str
    quantity: float
    unit: str = "meter"
    price: float = 0.0
    discount_percent: float = 0       # P0-1 — diskon per item dari supplier (0–100%)


class PurchaseOrderCreate(BaseModel):
    supplier_id: str = ""             # Fase 3 — FK ke suppliers (opsional; fallback manual)
    supplier_name: str = ""           # snapshot/manual (backward compat bila tanpa supplier_id)
    supplier_contact: str = ""
    warehouse_id: str
    items: List[POItemCreate]
    expected_delivery_date: str = ""
    notes: str = ""
    created_by: str = "Admin"
    entity_id: str = ""
    order_discount_percent: float = 0  # P0-1 — diskon level order (0–100%)
    tax_mode: str = ""                # P0-1 — "" = ikut config | "ppn" (PPN Masukan) | "non_ppn"


# ─── Procurement Schemas (Fase 3 — Supplier Master + Pengelolaan Kas) ─────────

class SupplierCreate(BaseModel):
    name: str
    npwp: str = ""
    pic_name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    city: str = ""
    goods_type: str = ""              # jenis barang yang dipasok (benang/kain/bahan printing)
    payment_term_code: str = ""
    lead_time_days: int = 0           # Depth #3 — estimasi lead time default supplier (hari)
    entity_id: str = ""
    notes: str = ""
    created_by: str = "Admin"


# ─── Depth #3: Supplier Price-List (koleksi supplier_price_lists, prefix spl_) ─

class SupplierPriceListCreate(BaseModel):
    product_id: str
    price: float                      # harga beli per `unit`
    unit: str = ""                    # UOM; kosong → base_unit produk (UOM engine 1.13)
    min_qty: float = 0                # MOQ agar harga ini berlaku (0 = tanpa minimum)
    lead_time_days: int = 0           # lead time khusus produk; 0 = pakai default supplier
    valid_from: str = ""              # ISO/tanggal mulai berlaku; "" = sejak sekarang
    valid_until: str = ""             # ISO/tanggal kadaluarsa; "" = tanpa kadaluarsa
    currency: str = "IDR"
    notes: str = ""
    created_by: str = "Admin"


class CashTransactionCreate(BaseModel):
    cash_type: str = "kas_kecil"      # kas_kecil (per entitas) | kas_besar (gabungan)
    direction: str = "out"            # in (masuk) | out (keluar)
    amount: float
    category: str = ""                # pembelian | operasional | gaji | lain
    description: str = ""
    entity_id: str = ""               # untuk kas_kecil; kas_besar dipaksa "all"
    ref_type: str = ""                # purchase_order | manual | ...
    ref_id: str = ""
    txn_date: str = ""                # ISO; default = sekarang
    created_by: str = "Admin"


# ─── Depth #1: PO Payment + Retur Beli (Purchase Return / Nota Debit) ─────────

class POPaymentCreate(BaseModel):
    amount: float
    cash_type: str = "kas_besar"      # kas_kecil | kas_besar (sumber dana)
    entity_id: str = ""               # untuk kas_kecil
    method: str = "transfer"          # transfer | tunai | giro
    notes: str = ""
    paid_at: str = ""                 # ISO; default sekarang
    created_by: str = "Admin"


class POCloseRequest(BaseModel):
    reason: str = ""                  # alasan tutup kurang (short-close)
    created_by: str = "Admin"


# ─── Fase 5.2 (P0-2): Vendor Bill + 3-Way Matching ───────────────────────────

class VendorBillItemInput(BaseModel):
    product_id: str
    billed_qty: float                 # qty yang ditagih supplier pada bill ini
    price: float = 0.0                # harga per unit (0 = ikut harga PO)
    discount_percent: float = 0       # diskon per item (0–100%)


class VendorBillCreate(BaseModel):
    po_id: str                        # PO referensi (wajib — 3-way match)
    supplier_invoice_no: str = ""     # nomor invoice asli supplier (dedupe)
    bill_date: str = ""               # ISO; default sekarang
    due_date: str = ""                # jatuh tempo (aging AP)
    match_mode: str = "received"      # received (3-way ketat) | ordered (longgar)
    items: List[VendorBillItemInput]
    order_discount_percent: float = 0
    tax_mode: str = ""                # "" ikut PO/config | "ppn" | "non_ppn"
    notes: str = ""
    entity_id: str = ""
    submit_now: bool = False          # True = langsung submit setelah dibuat
    created_by: str = "Admin"


class VendorBillPaymentCreate(BaseModel):
    amount: float
    cash_type: str = "kas_besar"      # kas_kecil | kas_besar (sumber dana)
    entity_id: str = ""
    method: str = "transfer"          # transfer | tunai | giro
    notes: str = ""
    paid_at: str = ""
    created_by: str = "Admin"


class VendorBillDecision(BaseModel):
    notes: str = ""                   # alasan reject/cancel


# ── Fase 5.4 (P0-5): Landed Cost Voucher → alokasi HPP roll ────────────────────
class LandedCostLineInput(BaseModel):
    category: str = "freight"         # freight|duty|insurance|handling|other
    description: str = ""
    amount: float = 0.0               # nominal biaya (Rp)


class LandedCostCreate(BaseModel):
    po_ids: List[str]                 # PO referensi (≥1) sumber roll yang dibebani
    provider_name: str = ""           # penyedia jasa (forwarder/bea cukai/asuransi)
    supplier_invoice_no: str = ""     # nomor invoice penyedia (dedupe)
    basis: str = "value"              # value (proporsional nilai) | quantity (panjang)
    cost_lines: List[LandedCostLineInput]
    voucher_date: str = ""            # ISO; default sekarang
    due_date: str = ""                # jatuh tempo (AP landed cost)
    notes: str = ""
    entity_id: str = ""
    submit_now: bool = False          # True = langsung submit (pending_approval)
    created_by: str = "Admin"


class LandedCostPaymentCreate(BaseModel):
    amount: float
    cash_type: str = "kas_besar"      # kas_kecil | kas_besar (sumber dana)
    entity_id: str = ""
    method: str = "transfer"          # transfer | tunai | giro
    notes: str = ""
    paid_at: str = ""
    created_by: str = "Admin"


class LandedCostDecision(BaseModel):
    notes: str = ""                   # alasan reject/cancel


# ── Fase 5.5 (P0-3): Faktur Pajak Masukan (Input VAT) dari Vendor Bill ─────────
class InputTaxInvoiceCreate(BaseModel):
    vendor_bill_id: str               # Vendor Bill sumber (posted/paid, ber-PPN)
    nsfp: str                         # Nomor Seri Faktur Pajak supplier (16-digit; dedupe)
    faktur_date: str = ""             # tanggal faktur pajak supplier (default = bill_date)
    kode_transaksi: str = "01"        # kode transaksi faktur (default 01)
    notes: str = ""
    created_by: str = "Admin"


class InputTaxInvoiceCancel(BaseModel):
    reason: str                       # alasan pembatalan (wajib)


# ── Fase 6.1 (P1): RFQ / Quotation ────────────────────────────────────────────
class RFQItemInput(BaseModel):
    product_id: str
    quantity: float
    unit: str = "meter"
    note: str = ""
    line_id: str = ""


class RFQCreate(BaseModel):
    source: str = "manual"            # "manual" | "pr"
    pr_id: str = ""                   # bila source=pr
    title: str = ""
    entity_id: str = ""
    warehouse_id: str
    items: List[RFQItemInput] = []    # diabaikan bila source=pr (ditarik dari PR)
    supplier_ids: List[str] = []      # supplier yang diundang
    needed_by_date: str = ""
    due_date: str = ""                # batas akhir penawaran
    notes: str = ""
    created_by: str = "Admin"


class RFQQuoteLine(BaseModel):
    line_id: str
    price: float = 0
    available: bool = True
    note: str = ""


class RFQQuoteSubmit(BaseModel):
    supplier_id: str
    lines: List[RFQQuoteLine] = []
    valid_until: str = ""
    lead_time_days: int = 0
    note: str = ""


class RFQLineAward(BaseModel):
    line_id: str
    supplier_id: str
    price: float = 0


class RFQAward(BaseModel):
    mode: str = "full"                # "full" | "line"
    full_supplier_id: str = ""        # bila mode=full
    line_awards: List[RFQLineAward] = []  # bila mode=line


class RFQDecision(BaseModel):
    reason: str = ""


# ── Fase 6.2 (P1): QC 4-Point Inspection per roll ─────────────────────────────
class RollDefectInput(BaseModel):
    point_value: int                  # 1..4 (severity 4-point)
    count: int = 0                    # jumlah defect pada nilai poin ini
    note: str = ""


class RollInspectionInput(BaseModel):
    defects: List[RollDefectInput] = []
    gsm_actual: Optional[float] = None    # gramasi aktual (dicatat saja)
    width_actual: Optional[float] = None  # lebar aktual (dicatat saja)
    note: str = ""


class PurchaseReturnItem(BaseModel):
    product_id: str
    quantity: float
    unit: str = "meter"
    price: float = 0.0
    reason: str = ""                  # cacat | salah_kirim | kelebihan | lain
    condition: str = "damaged"        # damaged | ok


class PurchaseReturnCreate(BaseModel):
    supplier_id: str = ""
    po_id: str = ""                   # opsional — retur bisa tanpa PO referensi
    warehouse_id: str = ""
    items: List[PurchaseReturnItem]
    reason: str = ""
    notes: str = ""
    entity_id: str = ""
    submit_now: bool = False
    created_by: str = "Admin"


class PurchaseReturnDecision(BaseModel):
    notes: str = ""


class POReceiveItem(BaseModel):
    product_id: str
    actual_qty: float
    batch: str = ""
    lot: str = ""
    dye_lot: str = ""                     # P0-4 — dye lot aktual (warna/celup) per terima
    grade: str = ""                       # P0-4 — grade aktual saat terima ("" = default A)
    roll_id: str = ""
    bin_id: str = ""


class GRRollLine(BaseModel):
    """P0-4 — satu roll fisik saat Goods Receipt (panjang + dye lot + grade per roll).
    Fase 8 (catch-weight): `weight` = berat aktual roll (kg, opsional). Untuk PO yang
    dibeli per kg, isi `weight`; `length` (meter aktual) opsional → diturunkan dari faktor."""
    length: float = 0                     # panjang roll (base/meter; utk PO per-panjang)
    weight: float = 0                     # berat roll (kg) — catch-weight aktual (opsional)
    dye_lot: str = ""
    grade: str = "A"
    defects: List[str] = []


class GRCompletePayload(BaseModel):
    """P0-4 — body opsional saat selesaikan GR. Bila `rolls` diisi → multi-roll
    dengan dye_lot/grade per roll; bila kosong → satu roll pakai dye_lot/grade default."""
    dye_lot: str = ""
    grade: str = ""
    rolls: List[GRRollLine] = []


class QCDecision(BaseModel):
    """Depth #3a + P0-4 — keputusan inspeksi QC untuk 1 inbound task (qty dalam unit task)."""
    accept_qty: float = 0.0
    reject_qty: float = 0.0
    reject_disposition: str = "damaged"   # damaged | return
    accept_grade: str = "A"               # P0-4 — grade aktual untuk qty diterima (A|A+|B|C|BS)
    defects: List[str] = []               # P0-4 — profil cacat (mis. ["belang", "noda"])
    reason: str = ""


# ─── Inventory Roll Schema (Fase 0.5 — Roll-as-SSOT, KN_15) ──────────────────

class RollPayload(BaseModel):
    product_id: str
    warehouse_id: str
    owner_entity_id: str = ""        # default = entitas utama bila kosong
    lot: str
    quantity: float                  # = length_initial = length_remaining awal
    unit: str = "meter"
    grade: str = "A"
    batch: str = ""
    roll_no: str = ""
    bin_id: str = ""
    tracking_mode: str = "barcode"   # rfid | barcode | document | manual
    ownership_type: str = "internal" # internal | supplier_consignment | reseller_consignment


# ─── Configuration Foundation Schemas (Fase 1A — semua configurable) ─────────

class SettingsUpdate(BaseModel):
    scope: str = "global"            # "global" | entity_id
    tax: Optional[Dict[str, Any]] = None
    finance: Optional[Dict[str, Any]] = None
    sales: Optional[Dict[str, Any]] = None
    inventory: Optional[Dict[str, Any]] = None
    allocation: Optional[Dict[str, Any]] = None   # Sub-fase 1.7 — allocation policy
    purchasing: Optional[Dict[str, Any]] = None   # Depth #3 — procurement (deviasi harga, dll)


class PaymentTermPayload(BaseModel):
    code: str
    name: str
    type: str = "credit"             # cash | credit | dp | installment
    net_days: int = 0
    dp_percent: float = 0
    installment_count: int = 0
    sort: int = 99
    active: bool = True


class ApprovalRulePayload(BaseModel):
    doc_type: str                    # sales_order | purchase_order | transfer | discount
    entity_id: str = "all"
    min_amount: float = 0
    max_amount: Optional[float] = None
    required_role: str = ""          # "" = tidak butuh approval
    is_percent: bool = False
    sort: int = 99
    active: bool = True



# ─── Price Approval Schemas (Sub-fase 1.7 — Special Price / Approval Harga) ───

class PriceApprovalCreate(BaseModel):
    customer_id: str
    product_id: str
    requested_price: float               # harga khusus yang diajukan (per unit)
    min_quantity: float = 0              # qty minimum agar harga berlaku
    valid_until: str = ""                # "YYYY-MM-DD" atau ISO; "" = tanpa kadaluarsa
    reason: str = ""
    entity_id: str = ""                  # kosong → resolve dari entitas customer
    submit_now: bool = False             # True → langsung status pending (skip draft)


class PriceApprovalDecision(BaseModel):
    decision_notes: str = ""


# ─── Tax Invoice / Faktur Pajak Schemas (Sub-fase 1.9 — Faktur Pajak Jual) ───

class TaxInvoiceCreate(BaseModel):
    kode_transaksi: Optional[str] = "01"   # 01=normal ke ber-NPWP (default)
    faktur_date: Optional[str] = None      # ISO; default = sekarang
    nsfp: Optional[str] = None             # NSFP resmi 16-digit (opsional, diisi menyusul)


class TaxInvoiceNsfpUpdate(BaseModel):
    nsfp: str
    kode_transaksi: Optional[str] = None


class TaxInvoiceReplace(BaseModel):
    reason: Optional[str] = ""
    kode_transaksi: Optional[str] = None
    nsfp: Optional[str] = None


class TaxInvoiceCancel(BaseModel):
    reason: str


# ─── Sales Returns / Retur & Barang Sisa (Sub-fase 1.11) ─────────────────────

class SalesReturnItem(BaseModel):
    product_id:         str
    product_name:       str = ""
    quantity_returned:  float
    unit:               str = "meter"
    reason:             str = ""
    condition:          str = "ok"   # ok | damaged


class SalesReturnCreate(BaseModel):
    order_id:     str
    return_type:  str = "retur"      # retur | bs | penggantian
    items:        list[SalesReturnItem]
    notes:        str = ""
    entity_id:    str = ""
    submit_now:   bool = False       # True = langsung pending_approval


class SalesReturnDecision(BaseModel):
    notes: str = ""


# ─── Depth #2: Purchase Requisition (PR) + Reorder ───────────────────────────

class PurchaseRequisitionItem(BaseModel):
    product_id: str = ""              # opsional — kosong = item non-katalog (special order)
    description: str = ""            # wajib bila product_id kosong
    quantity: float
    unit: str = "meter"
    est_price: float = 0.0           # estimasi harga satuan (untuk evaluasi approval)
    note: str = ""


class PurchaseRequisitionCreate(BaseModel):
    items: List[PurchaseRequisitionItem]
    warehouse_id: str = ""
    entity_id: str = ""
    reason: str = ""                  # justifikasi kebutuhan
    needed_by_date: str = ""          # ISO/tanggal dibutuhkan
    source: str = "manual"            # manual | reorder | special_order
    source_ref_id: str = ""           # id special_order bila source=special_order
    preferred_supplier_id: str = ""
    notes: str = ""
    submit_now: bool = False          # True = langsung pending_approval (atau approved bila tak butuh approval)
    created_by: str = "Admin"


class PurchaseRequisitionDecision(BaseModel):
    notes: str = ""


class PurchaseRequisitionConvert(BaseModel):
    supplier_id: str = ""             # wajib (atau pakai preferred_supplier_id PR)
    warehouse_id: str = ""            # default = warehouse PR
    expected_delivery_date: str = ""
    notes: str = ""


class SpecialOrderToPR(BaseModel):
    """Jembatan Special Order → PR pengadaan (Depth #2c)."""
    est_price: float = 0.0            # estimasi biaya pengadaan per unit (default target_price)
    warehouse_id: str = ""
    needed_by_date: str = ""
    notes: str = ""
    submit_now: bool = False
