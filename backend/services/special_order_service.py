"""Special Order Service - Sub-fase 1.12

Handles business logic for Special Orders (custom products not in catalog).
Simple approval: amount > threshold requires manager approval.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List
from db import db
from core_utils import new_id, now_iso

# Simple approval threshold (IDR)
APPROVAL_THRESHOLD = 10_000_000

# Status constants (aligned with SO)
STATUS_DRAFT = "draft"
STATUS_PENDING_APPROVAL = "pending_approval"
STATUS_APPROVED = "approved"
STATUS_CONFIRMED = "confirmed"
STATUS_IN_PRODUCTION = "in_production"
STATUS_READY = "ready"
STATUS_SHIPPED = "shipped"
STATUS_DONE = "done"
STATUS_CANCELLED = "cancelled"


async def generate_special_order_number() -> str:
    """Generate unique Special Order number: SORD-YYMMDD-XXXX"""
    today = datetime.now(timezone.utc).strftime("%y%m%d")
    prefix = f"SORD-{today}"
    
    # Get highest sequence for today
    latest = await db.special_orders.find_one(
        {"number": {"$regex": f"^{prefix}"}},
        sort=[("number", -1)]
    )
    
    if latest:
        last_num = int(latest["number"].split("-")[-1])
        seq = last_num + 1
    else:
        seq = 1
    
    return f"{prefix}-{seq:04d}"


async def evaluate_special_order_approval(total_amount: float, current_status: str) -> str:
    """Determine initial status based on amount.
    
    Returns:
        - 'draft' if amount <= threshold
        - 'pending_approval' if amount > threshold
    """
    if current_status != STATUS_DRAFT:
        return current_status
    
    if total_amount > APPROVAL_THRESHOLD:
        return STATUS_PENDING_APPROVAL
    
    return STATUS_DRAFT


async def can_approve_special_order(special_order: Dict[str, Any], user_role: str) -> bool:
    """Check if user can approve special order.
    
    Args:
        special_order: Special order document
        user_role: Current user's role
    
    Returns:
        True if user can approve (manager/admin)
    """
    if special_order["status"] != STATUS_PENDING_APPROVAL:
        return False
    
    return user_role in ["manager", "admin"]


async def approve_special_order(special_order_id: str, approved_by: str) -> Dict[str, Any]:
    """Approve special order and transition to confirmed status.
    
    Args:
        special_order_id: Special order ID
        approved_by: User email who approved
    
    Returns:
        Updated special order document
    """
    result = await db.special_orders.find_one_and_update(
        {"id": special_order_id, "status": STATUS_PENDING_APPROVAL},
        {
            "$set": {
                "status": STATUS_CONFIRMED,
                "approved_by": approved_by,
                "approved_at": now_iso(),
                "updated_at": now_iso()
            }
        },
        return_document=True
    )
    
    if not result:
        raise ValueError("Special order not found or not in pending_approval status")
    
    result.pop("_id", None)
    return result


async def reject_special_order(special_order_id: str, rejected_by: str, reason: str) -> Dict[str, Any]:
    """Reject special order.
    
    Args:
        special_order_id: Special order ID
        rejected_by: User email who rejected
        reason: Rejection reason
    
    Returns:
        Updated special order document
    """
    result = await db.special_orders.find_one_and_update(
        {"id": special_order_id, "status": STATUS_PENDING_APPROVAL},
        {
            "$set": {
                "status": STATUS_CANCELLED,
                "rejected_by": rejected_by,
                "rejected_at": now_iso(),
                "reject_reason": reason,
                "updated_at": now_iso()
            }
        },
        return_document=True
    )
    
    if not result:
        raise ValueError("Special order not found or not in pending_approval status")
    
    result.pop("_id", None)
    return result


async def transition_special_order_status(
    special_order_id: str,
    new_status: str,
    updated_by: str
) -> Dict[str, Any]:
    """Transition special order to new status.
    
    Valid transitions:
    - confirmed → in_production (purchasing started)
    - in_production → ready (item produced/received)
    - ready → shipped (dispatched to customer)
    - shipped → done (delivered)
    
    Args:
        special_order_id: Special order ID
        new_status: Target status
        updated_by: User email
    
    Returns:
        Updated special order document
    """
    VALID_TRANSITIONS = {
        STATUS_CONFIRMED: [STATUS_IN_PRODUCTION],
        STATUS_IN_PRODUCTION: [STATUS_READY],
        STATUS_READY: [STATUS_SHIPPED],
        STATUS_SHIPPED: [STATUS_DONE],
    }
    
    special_order = await db.special_orders.find_one({"id": special_order_id})
    if not special_order:
        raise ValueError("Special order not found")
    
    current_status = special_order["status"]
    
    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        raise ValueError(
            f"Invalid status transition: {current_status} → {new_status}"
        )
    
    result = await db.special_orders.find_one_and_update(
        {"id": special_order_id},
        {
            "$set": {
                "status": new_status,
                "updated_at": now_iso(),
                "updated_by": updated_by
            },
            "$push": {
                "status_history": {
                    "status": new_status,
                    "timestamp": now_iso(),
                    "user": updated_by
                }
            }
        },
        return_document=True
    )
    
    result.pop("_id", None)
    return result
