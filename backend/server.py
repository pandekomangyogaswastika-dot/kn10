"""Kain Nusantara API — modular FastAPI application."""
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from db import client, db
from core_utils import hash_password, new_id, now_iso
from permissions_config import DEFAULT_PERMISSIONS

# Import all routers
from routers import (
    auth, users, dashboard, products, customers, warehouses, uoms,
    inventory, sales_orders, invoices, wms, documents, admin,
    reporting, audit, cycle_count, onboarding, label_printer, transfers,
    purchase_orders, inbound_receiving, outbound_picking,
    entities, notifications, settings, price_approvals, pegging, tax_invoices,
    sales_returns, special_orders, approval_rules, approval_requests,
    suppliers, cash, purchase_returns, purchase_requisitions, vendor_bills,
    landed_cost, input_tax, rfq, qc_inspection
)


# ─── Seed helpers ────────────────────────────────────────────────────────────

async def seed_data() -> None:
    """Insert demo data only if collections are empty."""
    if await db.users.count_documents({}) == 0:
        await db.users.insert_many([
            {"id": "user_admin_01", "name": "Budi Santoso", "email": "admin@kainnusantara.id",
             "role": "admin", "password_hash": hash_password("demo12345"), "status": "active", "created_at": now_iso()},
            {"id": "user_sales_01", "name": "Ayu Marketing", "email": "sales@kainnusantara.id",
             "role": "sales", "password_hash": hash_password("demo12345"), "status": "active", "created_at": now_iso()},
            {"id": "user_manager_01", "name": "Dewi Manager", "email": "manager@kainnusantara.id",
             "role": "manager", "password_hash": hash_password("demo12345"), "status": "active", "created_at": now_iso()},
            {"id": "user_wh_01", "name": "Eko Warehouse", "email": "warehouse@kainnusantara.id",
             "role": "warehouse", "password_hash": hash_password("demo12345"), "status": "active", "created_at": now_iso()},
        ])

    if await db.uoms.count_documents({}) == 0:
        await db.uoms.insert_many([
            {"id": "uom_meter", "code": "MTR", "name": "Meter", "base_type": "length", "precision": 2, "factor_to_base": 1.0, "status": "active", "created_at": now_iso()},
            {"id": "uom_yard", "code": "YRD", "name": "Yard", "base_type": "length", "precision": 2, "factor_to_base": 0.9144, "status": "active", "created_at": now_iso()},
            {"id": "uom_cm", "code": "CM", "name": "Cm", "base_type": "length", "precision": 2, "factor_to_base": 0.01, "status": "active", "created_at": now_iso()},
            {"id": "uom_inch", "code": "INCH", "name": "Inch", "base_type": "length", "precision": 2, "factor_to_base": 0.0254, "status": "active", "created_at": now_iso()},
            {"id": "uom_roll", "code": "RLL", "name": "Roll", "base_type": "volume", "precision": 0, "status": "active", "created_at": now_iso()},
            {"id": "uom_pcs", "code": "PCS", "name": "Pcs", "base_type": "count", "precision": 0, "status": "active", "created_at": now_iso()},
        ])

    if await db.warehouses.count_documents({}) == 0:
        await db.warehouses.insert_many([
            {
                "id": "wh_jakarta", "code": "WH-JKT", "name": "Gudang Jakarta Utara", "city": "Jakarta",
                "lat": -6.1751, "lng": 106.8650, "active": True, "created_at": now_iso(),
                "zones": [{"id": "zone_jkt_a", "name": "Zone A", "racks": [
                    {"id": "rack_jkt_a1", "name": "Rack A1", "bins": [
                        {"id": "bin_jkt_a1_01", "code": "A1-01", "capacity": 500},
                        {"id": "bin_jkt_a1_02", "code": "A1-02", "capacity": 500},
                    ]}
                ]}]
            },
            {
                "id": "wh_bandung", "code": "WH-BDG", "name": "Gudang Bandung Kopo", "city": "Bandung",
                "lat": -6.9175, "lng": 107.6191, "active": True, "created_at": now_iso(),
                "zones": [{"id": "zone_bdg_a", "name": "Zone A", "racks": [
                    {"id": "rack_bdg_a1", "name": "Rack A1", "bins": [
                        {"id": "bin_bdg_a1_01", "code": "A1-01", "capacity": 600},
                    ]}
                ]}]
            },
            {
                "id": "wh_surabaya", "code": "WH-SBY", "name": "Gudang Surabaya Rungkut", "city": "Surabaya",
                "lat": -7.2504, "lng": 112.7688, "active": True, "created_at": now_iso(),
                "zones": [{"id": "zone_sby_a", "name": "Zone A", "racks": [
                    {"id": "rack_sby_a1", "name": "Rack A1", "bins": [
                        {"id": "bin_sby_a1_01", "code": "A1-01", "capacity": 400},
                    ]}
                ]}]
            },
        ])

    if await db.products.count_documents({}) == 0:
        await db.products.insert_many([
            {
                "id": "prod_batik_mega", "sku": "BTK-MEGA-001",
                "name": "Batik Mega Mendung Premium", "category": "Batik", "variant": "Premium",
                "color": "Biru-Merah", "motif": "Mega Mendung", "grade": "A",
                "supplier": "Cirebon Craft", "base_unit": "meter", "price": 185000,
                "image": "https://images.unsplash.com/photo-1582142839970-2b9e04b60f65?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                "status": "active", "uom_conversions": [], "batch_lot_rolls": [], "created_at": now_iso(), "updated_at": now_iso()
            },
            {
                "id": "prod_tenun_ikat", "sku": "TNI-GRGD-001",
                "name": "Tenun Ikat Garuda Premium", "category": "Tenun", "variant": "Premium",
                "color": "Emas-Coklat", "motif": "Garuda", "grade": "A",
                "supplier": "NTT Weaving Co", "base_unit": "meter", "price": 225000,
                "image": "https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                "status": "active", "uom_conversions": [], "batch_lot_rolls": [], "created_at": now_iso(), "updated_at": now_iso()
            },
            {
                "id": "prod_lurik_classic", "sku": "LRK-CLSC-001",
                "name": "Lurik Klasik Solo", "category": "Lurik", "variant": "Klasik",
                "color": "Hitam-Putih", "motif": "Garis Vertikal", "grade": "A",
                "supplier": "Solo Weave", "base_unit": "meter", "price": 95000,
                "image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                "status": "active", "uom_conversions": [], "batch_lot_rolls": [], "created_at": now_iso(), "updated_at": now_iso()
            },
            {
                "id": "prod_songket_palembang", "sku": "SGK-PLB-001",
                "name": "Songket Palembang Benang Emas", "category": "Songket", "variant": "Premium",
                "color": "Merah-Emas", "motif": "Bunga Cengkeh", "grade": "A+",
                "supplier": "Palembang Silk House", "base_unit": "meter", "price": 450000,
                "image": "https://images.unsplash.com/photo-1619855544858-e8e275c3b31a?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                "status": "active", "uom_conversions": [], "batch_lot_rolls": [], "created_at": now_iso(), "updated_at": now_iso()
            },
            {
                "id": "prod_ulos_batak", "sku": "ULS-BTK-001",
                "name": "Ulos Batak Ragidup", "category": "Ulos", "variant": "Tradisional",
                "color": "Merah-Hitam-Putih", "motif": "Ragidup", "grade": "A",
                "supplier": "Toba Craft", "base_unit": "meter", "price": 320000,
                "image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                "status": "active", "uom_conversions": [], "batch_lot_rolls": [], "created_at": now_iso(), "updated_at": now_iso()
            },
        ])

    if await db.inventory_balances.count_documents({}) == 0:
        await db.inventory_balances.insert_many([
            {"id": new_id("bal"), "product_id": "prod_batik_mega", "warehouse_id": "wh_jakarta",
             "on_hand_qty": 350, "reserved_qty": 0, "available_qty": 350, "blocked_qty": 0, "picked_qty": 0, "in_transit_qty": 0, "updated_at": now_iso()},
            {"id": new_id("bal"), "product_id": "prod_batik_mega", "warehouse_id": "wh_bandung",
             "on_hand_qty": 200, "reserved_qty": 0, "available_qty": 200, "blocked_qty": 0, "picked_qty": 0, "in_transit_qty": 0, "updated_at": now_iso()},
            {"id": new_id("bal"), "product_id": "prod_tenun_ikat", "warehouse_id": "wh_jakarta",
             "on_hand_qty": 150, "reserved_qty": 0, "available_qty": 150, "blocked_qty": 0, "picked_qty": 0, "in_transit_qty": 0, "updated_at": now_iso()},
            {"id": new_id("bal"), "product_id": "prod_tenun_ikat", "warehouse_id": "wh_surabaya",
             "on_hand_qty": 120, "reserved_qty": 0, "available_qty": 120, "blocked_qty": 0, "picked_qty": 0, "in_transit_qty": 0, "updated_at": now_iso()},
            {"id": new_id("bal"), "product_id": "prod_lurik_classic", "warehouse_id": "wh_bandung",
             "on_hand_qty": 500, "reserved_qty": 0, "available_qty": 500, "blocked_qty": 0, "picked_qty": 0, "in_transit_qty": 0, "updated_at": now_iso()},
            {"id": new_id("bal"), "product_id": "prod_lurik_classic", "warehouse_id": "wh_surabaya",
             "on_hand_qty": 300, "reserved_qty": 0, "available_qty": 300, "blocked_qty": 0, "picked_qty": 0, "in_transit_qty": 0, "updated_at": now_iso()},
            {"id": new_id("bal"), "product_id": "prod_songket_palembang", "warehouse_id": "wh_jakarta",
             "on_hand_qty": 80, "reserved_qty": 0, "available_qty": 80, "blocked_qty": 0, "picked_qty": 0, "in_transit_qty": 0, "updated_at": now_iso()},
            {"id": new_id("bal"), "product_id": "prod_ulos_batak", "warehouse_id": "wh_surabaya",
             "on_hand_qty": 60, "reserved_qty": 0, "available_qty": 60, "blocked_qty": 0, "picked_qty": 0, "in_transit_qty": 0, "updated_at": now_iso()},
        ])
        # Also seed initial movement records
        import asyncio
        movements = [
            {"id": new_id("mov"), "product_id": "prod_batik_mega", "warehouse_id": "wh_jakarta",
             "movement_type": "initial_stock", "quantity": 350, "unit": "meter",
             "batch": "BTK-2024-001", "lot": "LOT-001", "roll_id": "ROLL-001",
             "source_document": "seed", "timestamp": now_iso()},
            {"id": new_id("mov"), "product_id": "prod_batik_mega", "warehouse_id": "wh_bandung",
             "movement_type": "initial_stock", "quantity": 200, "unit": "meter",
             "batch": "BTK-2024-001", "lot": "LOT-001", "roll_id": "ROLL-002",
             "source_document": "seed", "timestamp": now_iso()},
            {"id": new_id("mov"), "product_id": "prod_tenun_ikat", "warehouse_id": "wh_jakarta",
             "movement_type": "initial_stock", "quantity": 150, "unit": "meter",
             "batch": "TNI-2024-001", "lot": "LOT-001", "roll_id": "ROLL-003",
             "source_document": "seed", "timestamp": now_iso()},
            {"id": new_id("mov"), "product_id": "prod_tenun_ikat", "warehouse_id": "wh_surabaya",
             "movement_type": "initial_stock", "quantity": 120, "unit": "meter",
             "batch": "TNI-2024-001", "lot": "LOT-002", "roll_id": "ROLL-004",
             "source_document": "seed", "timestamp": now_iso()},
            {"id": new_id("mov"), "product_id": "prod_lurik_classic", "warehouse_id": "wh_bandung",
             "movement_type": "initial_stock", "quantity": 500, "unit": "meter",
             "batch": "LRK-2024-001", "lot": "LOT-001", "roll_id": "ROLL-005",
             "source_document": "seed", "timestamp": now_iso()},
            {"id": new_id("mov"), "product_id": "prod_lurik_classic", "warehouse_id": "wh_surabaya",
             "movement_type": "initial_stock", "quantity": 300, "unit": "meter",
             "batch": "LRK-2024-001", "lot": "LOT-002", "roll_id": "ROLL-006",
             "source_document": "seed", "timestamp": now_iso()},
            {"id": new_id("mov"), "product_id": "prod_songket_palembang", "warehouse_id": "wh_jakarta",
             "movement_type": "initial_stock", "quantity": 80, "unit": "meter",
             "batch": "SGK-2024-001", "lot": "LOT-001", "roll_id": "ROLL-007",
             "source_document": "seed", "timestamp": now_iso()},
            {"id": new_id("mov"), "product_id": "prod_ulos_batak", "warehouse_id": "wh_surabaya",
             "movement_type": "initial_stock", "quantity": 60, "unit": "meter",
             "batch": "ULS-2024-001", "lot": "LOT-001", "roll_id": "ROLL-008",
             "source_document": "seed", "timestamp": now_iso()},
        ]
        await db.inventory_movements.insert_many(movements)

    if await db.customers.count_documents({}) == 0:
        await db.customers.insert_many([
            {
                "id": "cust_toko_kain", "code": "CUST-0001", "name": "Toko Kain Sejahtera",
                "pic_name": "Pak Hendra", "phone": "081234567890", "email": "hendra@tokokain.id",
                "type": "Retailer", "city": "Jakarta", "status": "active", "created_by": "seed", "created_at": now_iso(),
                "addresses": [{"id": "addr_001", "label": "Toko Utama", "recipient_name": "Pak Hendra",
                               "phone": "081234567890", "city": "Jakarta",
                               "address": "Jl. Mangga Besar Raya No. 45", "is_primary": True}]
            },
            {
                "id": "cust_butik_bali", "code": "CUST-0002", "name": "Butik Bali Indah",
                "pic_name": "Ibu Komang", "phone": "082345678901", "email": "komang@butikbali.id",
                "type": "Boutique", "city": "Denpasar", "status": "active", "created_by": "seed", "created_at": now_iso(),
                "addresses": [{"id": "addr_002", "label": "Butik Seminyak", "recipient_name": "Ibu Komang",
                               "phone": "082345678901", "city": "Denpasar",
                               "address": "Jl. Seminyak No. 88", "is_primary": True}]
            },
            {
                "id": "cust_moda_surabaya", "code": "CUST-0003", "name": "Moda Surabaya Fashion",
                "pic_name": "Bapak Andi", "phone": "083456789012", "email": "andi@modasby.id",
                "type": "Wholesaler", "city": "Surabaya", "status": "active", "created_by": "seed", "created_at": now_iso(),
                "addresses": [{"id": "addr_003", "label": "Gudang Pusat", "recipient_name": "Bapak Andi",
                               "phone": "083456789012", "city": "Surabaya",
                               "address": "Jl. Rungkut Industri No. 22", "is_primary": True}]
            },
        ])

    if await db.document_templates.count_documents({}) == 0:
        await db.document_templates.insert_many([
            {
                "id": "tmpl_sj_default", "document_type": "surat_jalan", "name": "Template SJ Standard",
                "header": "KAIN NUSANTARA — Enterprise Textile Warehouse",
                "footer": "Barang diterima dalam kondisi baik. Tanda tangan sebagai bukti penerimaan.",
                "columns": ["sku", "name", "qty", "unit", "batch", "lot"],
                "logo_url": "", "paper_size": "A4", "orientation": "portrait", "margin_mm": 12,
                "signature_left": "Disiapkan Oleh", "signature_right": "Diterima Oleh",
                "section_order": ["header", "customer", "items", "allocation", "signature", "footer"],
                "status": "active", "created_by": "seed", "created_at": now_iso()
            },
            {
                "id": "tmpl_inv_default", "document_type": "invoice", "name": "Template Invoice Standard",
                "header": "KAIN NUSANTARA — Invoice",
                "footer": "Pembayaran dalam 30 hari. Terima kasih atas kepercayaan Anda.",
                "columns": ["sku", "name", "qty", "unit", "price", "subtotal"],
                "logo_url": "", "paper_size": "A4", "orientation": "portrait", "margin_mm": 12,
                "signature_left": "Dibuat Oleh", "signature_right": "Disetujui Oleh",
                "section_order": ["header", "customer", "items", "signature", "footer"],
                "status": "active", "created_by": "seed", "created_at": now_iso()
            },
        ])

    if await db.permission_settings.count_documents({}) == 0:
        await db.permission_settings.insert_one(
            {"id": "default", "matrix": DEFAULT_PERMISSIONS, "updated_at": now_iso()}
        )


# ─── Fase 0: Multi-Entity + Notification Center ──────────────────────────────

PRIMARY_ENTITY_ID = "ent_ksc"
ENTITY_SCOPED_COLLECTIONS = ["sales_orders", "invoices", "purchase_orders", "customers"]


async def seed_entities() -> None:
    """Seed entitas legal grup Kain Nusantara (idempotent)."""
    if await db.business_entities.count_documents({}) == 0:
        await db.business_entities.insert_many([
            {"id": "ent_ksc", "legal_name": "PT Kain Suka Cita", "short_name": "KSC",
             "type": "PT", "npwp": "01.234.567.8-901.000",
             "address": "Jl. Soekarno Hatta No. 100", "city": "Bandung",
             "default_tax_mode": "ppn", "doc_prefix": "KSC", "logo_url": "",
             "status": "active", "created_by": "seed", "created_at": now_iso(), "updated_at": now_iso()},
            {"id": "ent_kanda", "legal_name": "CV Kanda Suka", "short_name": "Kanda",
             "type": "CV", "npwp": "02.345.678.9-012.000",
             "address": "Jl. Mangga Dua Raya No. 22", "city": "Jakarta",
             "default_tax_mode": "non_ppn", "doc_prefix": "KANDA", "logo_url": "",
             "status": "active", "created_by": "seed", "created_at": now_iso(), "updated_at": now_iso()},
        ])


async def backfill_entity_id() -> None:
    """Pastikan semua data transaksi lama punya entity_id (default entitas utama)."""
    for col in ENTITY_SCOPED_COLLECTIONS:
        await db[col].update_many({"entity_id": {"$exists": False}}, {"$set": {"entity_id": PRIMARY_ENTITY_ID}})
        await db[col].update_many({"entity_id": None}, {"$set": {"entity_id": PRIMARY_ENTITY_ID}})


async def sync_permission_modules() -> None:
    """Merge modul permission baru (mis. 'entity') ke matrix tersimpan, non-destruktif."""
    record = await db.permission_settings.find_one({"id": "default"})
    if not record:
        return
    matrix = record.get("matrix", {})
    changed = False
    for role, modules in DEFAULT_PERMISSIONS.items():
        matrix.setdefault(role, {})
        for module, actions in modules.items():
            if module not in matrix[role]:
                matrix[role][module] = actions
                changed = True
    if changed:
        await db.permission_settings.update_one(
            {"id": "default"}, {"$set": {"matrix": matrix, "updated_at": now_iso()}}
        )


async def sync_uom_factors() -> None:
    """Sub-fase 1.13 — set factor_to_base pada uoms length lama yang belum punya (idempotent)."""
    defaults = {"MTR": 1.0, "YRD": 0.9144, "CM": 0.01, "INCH": 0.0254}
    for code, factor in defaults.items():
        await db.uoms.update_one(
            {"code": code, "factor_to_base": {"$exists": False}},
            {"$set": {"factor_to_base": factor, "base_type": "length", "updated_at": now_iso()}},
        )
    # Tambah cm/inch bila belum ada (instalasi lama hanya punya MTR/YRD/RLL/PCS)
    for code, name, factor in [("CM", "Cm", 0.01), ("INCH", "Inch", 0.0254)]:
        if not await db.uoms.find_one({"code": code}):
            await db.uoms.insert_one({
                "id": f"uom_{code.lower()}", "code": code, "name": name,
                "base_type": "length", "precision": 2, "factor_to_base": factor,
                "status": "active", "created_at": now_iso(),
            })


async def sync_product_uom_examples() -> None:
    """Sub-fase 1.13 — contoh konversi VARIABLE + catch-weight per produk (idempotent, demo)."""
    await db.products.update_one(
        {"id": "prod_batik_mega", "$or": [{"uom_conversions": {"$exists": False}}, {"uom_conversions": []}]},
        {"$set": {"uom_conversions": [{"from_unit": "roll", "to_unit": "meter", "factor": 50}],
                  "updated_at": now_iso()}},
    )
    # Contoh catch-weight: gramasi & lebar agar unit "kg" tersedia (kg/m = 200×1.5/1000 = 0.3).
    await db.products.update_one(
        {"id": "prod_batik_mega", "$or": [{"gramasi": {"$in": [None, 0]}}, {"lebar": {"$in": [None, 0]}}]},
        {"$set": {"gramasi": 200, "lebar": 1.5, "updated_at": now_iso()}},
    )


async def seed_initial_notifications() -> None:
    """Generate notifikasi awal dari kondisi REAL (stok menipis / reservasi)."""
    if await db.notifications.count_documents({}) == 0:
        from services.notification_service import generate_system_notifications
        await generate_system_notifications()


# ─── Fase 0.5: Roll-as-SSOT Inventory Ownership ─────────────────────────────

async def backfill_inventory_owner() -> None:
    """Pastikan balances & movements lama punya owner_entity_id (default entitas utama)."""
    await db.inventory_balances.update_many(
        {"owner_entity_id": {"$exists": False}}, {"$set": {"owner_entity_id": PRIMARY_ENTITY_ID}}
    )
    await db.inventory_balances.update_many(
        {"owner_entity_id": None}, {"$set": {"owner_entity_id": PRIMARY_ENTITY_ID}}
    )
    await db.inventory_movements.update_many(
        {"owner_entity_id": {"$exists": False}}, {"$set": {"owner_entity_id": PRIMARY_ENTITY_ID}}
    )


async def backfill_roll_dye_lot() -> None:
    """P0-4 — pastikan roll lama punya `dye_lot` (default = `lot`), `grade` (default A),
    dan `defects` (default []). Invarian roll lama tetap valid (lot tetap terisi)."""
    await db.inventory_rolls.update_many(
        {"dye_lot": {"$exists": False}}, [{"$set": {"dye_lot": "$lot"}}]
    )
    await db.inventory_rolls.update_many(
        {"$or": [{"dye_lot": None}, {"dye_lot": ""}]}, [{"$set": {"dye_lot": "$lot"}}]
    )
    await db.inventory_rolls.update_many(
        {"grade": {"$exists": False}}, {"$set": {"grade": "A"}}
    )
    await db.inventory_rolls.update_many(
        {"defects": {"$exists": False}}, {"$set": {"defects": []}}
    )
    # P0-5 — default field landed cost untuk roll lama (HPP additive)
    await db.inventory_rolls.update_many(
        {"landed_cost_total": {"$exists": False}}, {"$set": {"landed_cost_total": 0.0}}
    )
    await db.inventory_rolls.update_many(
        {"landed_cost_refs": {"$exists": False}}, {"$set": {"landed_cost_refs": []}}
    )
    await db.inventory_rolls.update_many(
        {"base_unit_cost": {"$exists": False}}, [{"$set": {"base_unit_cost": "$unit_cost"}}]
    )
    # P0-3 — default field Faktur Pajak Masukan untuk vendor_bills lama
    await db.vendor_bills.update_many(
        {"input_faktur_status": {"$exists": False}}, {"$set": {"input_faktur_status": "none"}}
    )


async def ensure_inventory_rolls() -> None:
    """Generate inventory_rolls sintetis dari balances (idempotent — KN_15 §11)."""
    from services.roll_service import generate_rolls_from_balances
    await generate_rolls_from_balances(created_by="seed")


async def ensure_config_defaults() -> None:
    """Seed pengaturan default (settings/payment_terms/approval_rules) — Fase 1A, idempotent."""
    from services.config_service import seed_config_defaults
    await seed_config_defaults()


# ─── Fase 3: Procurement (Supplier Master + Pengelolaan Kas) ─────────────────

async def seed_procurement() -> None:
    """Seed master supplier + contoh transaksi kas (idempotent). Backfill PO.supplier_id."""
    if await db.suppliers.count_documents({}) == 0:
        base = [
            {"name": "Cirebon Craft", "npwp": "21.111.222.3-401.000", "pic_name": "Pak Wahyu",
             "phone": "081234500001", "city": "Cirebon", "goods_type": "Batik & Kain Cap", "entity_id": "ent_ksc"},
            {"name": "NTT Weaving Co", "npwp": "22.222.333.4-402.000", "pic_name": "Ibu Agnes",
             "phone": "082345600002", "city": "Kupang", "goods_type": "Tenun Ikat", "entity_id": "ent_ksc"},
            {"name": "Solo Weave", "npwp": "23.333.444.5-403.000", "pic_name": "Pak Joko",
             "phone": "085012300003", "city": "Solo", "goods_type": "Lurik & Benang", "entity_id": "ent_ksc"},
            {"name": "Palembang Silk House", "npwp": "24.444.555.6-404.000", "pic_name": "Ibu Sri",
             "phone": "081299900004", "city": "Palembang", "goods_type": "Songket & Benang Emas", "entity_id": "ent_ksc"},
            {"name": "Toba Craft", "npwp": "", "pic_name": "Pak Sahat",
             "phone": "081377700005", "city": "Medan", "goods_type": "Ulos", "entity_id": "ent_kanda"},
        ]
        docs = []
        for i, s in enumerate(base, start=1):
            docs.append({
                "id": new_id("sup"), "code": f"SUP-{i:05d}", "name": s["name"],
                "npwp": s["npwp"], "pic_name": s["pic_name"], "phone": s["phone"],
                "email": "", "address": "", "city": s["city"], "goods_type": s["goods_type"],
                "payment_term_code": "NET30", "entity_id": s["entity_id"], "notes": "",
                "status": "active", "created_by": "seed",
                "created_at": now_iso(), "updated_at": now_iso(),
            })
        await db.suppliers.insert_many(docs)

    # Backfill purchase_orders.supplier_id by name match (idempotent)
    sup_by_name = {s["name"]: s["id"] for s in await db.suppliers.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(500)}
    async for po in db.purchase_orders.find({"$or": [{"supplier_id": {"$exists": False}}, {"supplier_id": ""}]}, {"_id": 0, "id": 1, "supplier_name": 1}):
        sid = sup_by_name.get(po.get("supplier_name", ""))
        if sid:
            await db.purchase_orders.update_one({"id": po["id"]}, {"$set": {"supplier_id": sid}})

    if await db.cash_transactions.count_documents({}) == 0:
        examples = [
            {"cash_type": "kas_besar", "direction": "in",  "amount": 100000000, "category": "modal",
             "description": "Setoran modal awal kas besar", "entity_id": "all"},
            {"cash_type": "kas_kecil", "direction": "in",  "amount": 10000000,  "category": "transfer",
             "description": "Top-up kas kecil PT Kain Suka Cita", "entity_id": "ent_ksc"},
            {"cash_type": "kas_kecil", "direction": "out", "amount": 1500000,   "category": "operasional",
             "description": "Biaya operasional gudang", "entity_id": "ent_ksc"},
            {"cash_type": "kas_kecil", "direction": "out", "amount": 750000,    "category": "pembelian",
             "description": "Pembelian bahan printing", "entity_id": "ent_ksc"},
            {"cash_type": "kas_kecil", "direction": "in",  "amount": 5000000,   "category": "transfer",
             "description": "Top-up kas kecil CV Kanda Suka", "entity_id": "ent_kanda"},
        ]
        docs = []
        for i, e in enumerate(examples, start=1):
            docs.append({
                "id": new_id("cash"), "number": f"CASH-{i:05d}", **e,
                "ref_type": "manual", "ref_id": "", "txn_date": now_iso(),
                "status": "posted", "created_by": "seed",
                "created_at": now_iso(), "updated_at": now_iso(),
            })
        await db.cash_transactions.insert_many(docs)

    # Depth #2b — set reorder_point/reorder_qty default pada produk (idempotent)
    await db.products.update_many(
        {"reorder_point": {"$exists": False}},
        {"$set": {"reorder_point": 300.0, "reorder_qty": 500.0}})

    # Depth #2a — contoh Purchase Requisition (idempotent)
    if await db.purchase_requisitions.count_documents({}) == 0:
        prods = await db.products.find({"status": "active"}, {"_id": 0}).sort("sku", 1).to_list(5)
        wh = await db.warehouses.find_one({}, {"_id": 0, "id": 1, "name": 1})
        sup = await db.suppliers.find_one({}, {"_id": 0, "id": 1, "name": 1})
        if prods and wh:
            now = now_iso()
            def _mk(num, items, status, total, source="manual", appr=False):
                return {
                    "id": new_id("pr"), "number": num, "entity_id": "ent_ksc",
                    "warehouse_id": wh["id"], "warehouse_name": wh["name"],
                    "items": items, "total_est_amount": round(total, 2),
                    "source": source, "source_ref_id": "",
                    "preferred_supplier_id": (sup or {}).get("id", ""),
                    "preferred_supplier_name": (sup or {}).get("name", ""),
                    "reason": "Restock kebutuhan produksi", "needed_by_date": "",
                    "notes": "Contoh seed", "status": status,
                    "approval_required": appr,
                    "required_approval_role": "manager" if appr else None,
                    "approval_status": "approved" if status == "approved" else ("pending" if status == "pending_approval" else "not_submitted"),
                    "po_id": "", "po_number": "",
                    "created_by": "seed",
                    "approved_by": "seed (auto)" if status == "approved" else None,
                    "approved_at": now if status == "approved" else None,
                    "rejected_by": None, "rejected_at": None, "reject_reason": None,
                    "created_at": now, "updated_at": now,
                }
            def _items(plist):
                out = []
                tot = 0.0
                for p in plist:
                    price = float(p.get("harga_pokok", 0) or p.get("price", 0) or 0)
                    qty = 500.0
                    sub = round(price * qty, 2)
                    tot += sub
                    out.append({"product_id": p["id"], "sku": p.get("sku", ""),
                                "product_name": p.get("name", ""), "description": p.get("name", ""),
                                "quantity": qty, "unit": p.get("base_unit", "meter"),
                                "est_price": price, "subtotal": sub, "note": ""})
                return out, round(tot, 2)
            it1, t1 = _items(prods[:2])
            it2, t2 = _items(prods[2:4] if len(prods) >= 4 else prods[:1])
            await db.purchase_requisitions.insert_many([
                _mk("PR-00001", it1, "approved", t1, source="reorder", appr=False),
                _mk("PR-00002", it2, "pending_approval", t2, source="manual", appr=True),
            ])


# ─── App factory ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed_data()
    await seed_entities()
    await backfill_entity_id()
    await sync_permission_modules()
    await sync_uom_factors()
    await sync_product_uom_examples()
    await backfill_inventory_owner()
    await ensure_inventory_rolls()
    await backfill_roll_dye_lot()
    await ensure_config_defaults()
    await seed_procurement()
    await seed_initial_notifications()
    # Sub-fase 1.7 — init object storage (best-effort; tak menggagalkan startup)
    try:
        from services.storage_service import init_storage
        await init_storage()
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger("server").warning("[storage] init dilewati: %s", exc)
    yield
    client.close()


app = FastAPI(title="Kain Nusantara API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
for module in [
    auth, users, dashboard, products, customers, warehouses, uoms,
    inventory, sales_orders, invoices, wms, documents, admin,
    reporting, audit, cycle_count, onboarding, label_printer, transfers,
    purchase_orders, inbound_receiving, outbound_picking,
    entities, notifications, settings, price_approvals, pegging, tax_invoices,
    sales_returns, special_orders, approval_rules, approval_requests,
    suppliers, cash, purchase_returns, purchase_requisitions, vendor_bills,
    landed_cost, input_tax, rfq, qc_inspection
]:
    app.include_router(module.router)


@app.get("/api/")
async def root():
    return {"message": "Kain Nusantara API aktif"}
