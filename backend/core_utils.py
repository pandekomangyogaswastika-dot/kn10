from datetime import datetime, timezone
from typing import Any, Dict, Optional
import hashlib
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
