"""Customers router: CRUD + addresses."""
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Request
from pymongo import ReturnDocument
from db import db
from dependencies import require_permission, audit
from core_utils import new_id, now_iso, safe_doc, DEFAULT_ENTITY_ID
from schemas import CustomerAddress, CustomerCreate, GenericPatch

router = APIRouter(prefix="/api")


@router.get("/customers")
async def list_customers(entity_id: str = None) -> List[Dict[str, Any]]:
    query = {}
    if entity_id and entity_id != "all":
        query["entity_id"] = entity_id
    return await db.customers.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.post("/customers")
async def create_customer(payload: CustomerCreate, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "customer", "create")
    count = await db.customers.count_documents({}) + 1
    customer = {
        "id": new_id("cust"),
        "code": f"CUST-{count:04d}",
        "name": payload.name,
        "pic_name": payload.pic_name,
        "phone": payload.phone,
        "email": payload.email,
        "type": payload.type,
        "city": payload.city,
        "npwp": payload.npwp,
        "credit_limit": payload.credit_limit,
        "sales_pic": payload.sales_pic,
        "entity_id": payload.entity_id or DEFAULT_ENTITY_ID,
        "enforce_single_dye_lot": bool(payload.enforce_single_dye_lot),  # P0-4
        "lot_policy": payload.lot_policy or "",                          # P0-4 / KN_15
        "allocation_policy": {},                                          # override per-customer (opsional)
        "status": "active",
        "created_by": actor["name"],
        "created_at": now_iso(),
        "addresses": [
            CustomerAddress(
                recipient_name=payload.pic_name, phone=payload.phone,
                city=payload.city, address=payload.address, is_primary=True
            ).model_dump()
        ],
    }
    await db.customers.insert_one(customer)
    await audit(actor["name"], "customer_created", "customer", customer["id"], customer)
    return safe_doc(customer)


@router.patch("/customers/{customer_id}")
async def update_customer(customer_id: str, payload: GenericPatch, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "customer", "update")
    allowed = ["name", "pic_name", "phone", "email", "type", "city", "status", "addresses",
               "npwp", "credit_limit", "sales_pic", "entity_id",
               "enforce_single_dye_lot", "lot_policy", "allocation_policy"]
    data = {k: v for k, v in payload.data.items() if k in allowed}
    data["updated_at"] = now_iso()
    customer = await db.customers.find_one_and_update(
        {"id": customer_id}, {"$set": data},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer tidak ditemukan")
    await audit(actor["name"], "customer_updated", "customer", customer_id, customer)
    return customer


@router.post("/customers/{customer_id}/addresses")
async def add_customer_address(customer_id: str, payload: CustomerAddress, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "customer", "update")
    address = payload.model_dump()
    customer = await db.customers.find_one_and_update(
        {"id": customer_id},
        {"$push": {"addresses": address}, "$set": {"updated_at": now_iso()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer tidak ditemukan")
    await audit(actor["name"], "customer_address_added", "customer", customer_id, address)
    return customer
