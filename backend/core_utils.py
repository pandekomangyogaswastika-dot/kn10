from datetime import datetime, timezone
from typing import Any, Dict, Optional
import hashlib
import re
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def next_doc_number(collection: str, field: str, prefix: str, width: int = 5) -> str:
    """Generate nomor dokumen berurutan yang AMAN-HAPUS (deletion-safe).

    Mengambil nomor TERTINGGI yang sudah ada untuk `prefix` lalu +1.
    Ini menggantikan pola `count_documents()+1` yang BISA menghasilkan
    nomor DUPLIKAT begitu ada dokumen yang terhapus (RC-5 / P0-A).

    Contoh: next_doc_number("purchase_orders", "po_number", "PO-") -> "PO-00010".

    Catatan: pemindaian numerik (bukan sekadar sort leksikografis) agar aman
    terhadap lebar digit yang tidak seragam pada data lama. Koleksi nomor-seri
    pada skala aplikasi ini kecil sehingga biaya pindai dapat diabaikan.
    """
    from db import db
    coll = db[collection]
    pat = re.compile(r"(\d+)\s*$")
    n = 0
    async for d in coll.find(
        {field: {"$regex": f"^{re.escape(prefix)}"}}, {"_id": 0, field: 1}
    ):
        val = d.get(field)
        if isinstance(val, str):
            m = pat.search(val)
            if m:
                n = max(n, int(m.group(1)))
    return f"{prefix}{n + 1:0{width}d}"


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def timeline_entry(event: str, label: str, actor: str = "", note: str = "") -> Dict[str, Any]:
    """Entri riwayat/timeline standar (dipakai PO approval history, dll)."""
    return {"event": event, "label": label, "actor": actor or "Sistem",
            "at": now_iso(), "note": note or ""}


def _coerce(value: Any) -> Any:
    """Recursively make a MongoDB document JSON-serializable."""
    try:
        from bson import ObjectId
        if isinstance(value, ObjectId):
            return str(value)
    except ImportError:
        pass
    if isinstance(value, dict):
        return {k: _coerce(v) for k, v in value.items() if k != "_id"}
    if isinstance(value, list):
        return [_coerce(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    # datetime, etc.
    try:
        return str(value)
    except Exception:
        return None


def safe_doc(doc: Optional[Any]) -> Optional[Any]:
    """Recursively remove _id fields and convert ObjectId to str."""
    if doc is None:
        return None
    return _coerce(doc)


def hash_password(password: str) -> str:
    return hashlib.sha256(f"kain-nusantara::{password}".encode()).hexdigest()


# ── Multi-Entity (Fase 0) ─────────────────────────────────────────────────────
# Entitas legal utama grup. Dipakai sebagai default entity_id untuk data lama
# (backfill) & transaksi baru bila konteks entitas belum dipilih.
DEFAULT_ENTITY_ID = "ent_ksc"  # PT Kain Suka Cita
