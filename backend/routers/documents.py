"""Documents router: templates CRUD + document generation + barcode labels."""
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pymongo import ReturnDocument
from db import db
from dependencies import require_permission, audit
from core_utils import new_id, now_iso, safe_doc
from schemas import BarcodeGenerate, DocumentGenerate, GenericPatch, TemplatePayload
from services.inventory_service import render_order_html

router = APIRouter(prefix="/api")


@router.get("/document-templates")
async def list_templates(request: Request) -> List[Dict[str, Any]]:
    await require_permission(request, "template", "view")
    return await db.document_templates.find({}, {"_id": 0}).sort("name", 1).to_list(50)


@router.post("/document-templates")
async def create_template(payload: TemplatePayload, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "template", "create")
    template = {**payload.model_dump(), "id": new_id("tmpl"), "status": "active",
                "created_by": actor["name"], "created_at": now_iso()}
    await db.document_templates.insert_one(template)
    await audit(actor["name"], "template_created", "document_template", template["id"], template)
    return safe_doc(template)


@router.patch("/document-templates/{template_id}")
async def update_template(template_id: str, payload: GenericPatch, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "template", "update")
    allowed = ["document_type", "name", "header", "footer", "columns", "logo_url",
               "paper_size", "orientation", "margin_mm", "signature_left", "signature_right",
               "section_order", "status"]
    data = {k: v for k, v in payload.data.items() if k in allowed}
    data["updated_at"] = now_iso()
    template = await db.document_templates.find_one_and_update(
        {"id": template_id}, {"$set": data},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    await audit(actor["name"], "template_updated", "document_template", template_id, data)
    return template


@router.delete("/document-templates/{template_id}")
async def delete_template(template_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "template", "delete")
    template = await db.document_templates.find_one_and_update(
        {"id": template_id},
        {"$set": {"status": "inactive", "updated_at": now_iso()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    await audit(actor["name"], "template_deactivated", "document_template", template_id, template)
    return template


@router.post("/documents/generate")
async def generate_document(payload: DocumentGenerate, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "document", "create")
    html_content = await render_order_html(payload.source_id, payload.document_type)
    doc = {
        "id": new_id("doc"),
        "document_type": payload.document_type,
        "source_id": payload.source_id,
        "html": html_content,
        "created_by": actor["name"],
        "created_at": now_iso(),
    }
    await db.generated_documents.insert_one(doc)
    await audit(actor["name"], "document_generated", "document", doc["id"],
                {"document_type": payload.document_type, "source_id": payload.source_id})
    return safe_doc(doc)


@router.get("/documents/preview/{order_id}")
async def preview_document(order_id: str, document_type: str = "surat_jalan", request: Request = None) -> HTMLResponse:
    html_content = await render_order_html(order_id, document_type)
    return HTMLResponse(content=html_content)


@router.post("/documents/barcode")
async def generate_barcode(payload: BarcodeGenerate, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "document", "create")
    if payload.target_type == "product":
        product = safe_doc(await db.products.find_one({"id": payload.target_id}, {"_id": 0}))
        if not product:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
        label_html = f"""
        <html><head><style>body{{font-family:Arial,sans-serif;margin:0;padding:4px}}
        .label{{width:80mm;padding:6px;border:1px solid #ccc;text-align:center}}
        h3{{margin:0;font-size:11px}} p{{margin:2px 0;font-size:9px}} .barcode{{font-size:22px;letter-spacing:4px}}</style></head>
        <body><div class='label'><h3>{product.get('name','-')}</h3><div class='barcode'>||| {product.get('sku','')} |||</div>
        <p>SKU: {product.get('sku','')}</p><p>{product.get('category','')} | {product.get('variant','')} | {product.get('color','')}</p>
        <p>Grade: {product.get('grade','')} | Supplier: {product.get('supplier','')}</p></div></body></html>
        """
        await audit(actor["name"], "barcode_generated", "product", payload.target_id,
                    {"label_size": payload.label_size})
        return {"label_html": label_html, "target_type": payload.target_type, "target_id": payload.target_id}
    elif payload.target_type == "wms_task":
        task = safe_doc(await db.wms_tasks.find_one({"id": payload.target_id}, {"_id": 0}))
        if not task:
            raise HTTPException(status_code=404, detail="WMS task tidak ditemukan")
        label_html = f"""
        <html><head><style>body{{font-family:Arial,sans-serif;margin:0;padding:4px}}
        .label{{width:80mm;padding:6px;border:1px solid #ccc;text-align:center}}
        h3{{margin:0;font-size:11px}} p{{margin:2px 0;font-size:9px}} .barcode{{font-size:22px;letter-spacing:4px}}</style></head>
        <body><div class='label'><h3>{task.get('product_name','-')}</h3><div class='barcode'>||| {task.get('sku','')} |||</div>
        <p>Batch: {task.get('batch','-')} | Lot: {task.get('lot','-')} | Roll: {task.get('roll_id','-')}</p>
        <p>Bin: {task.get('bin_id','-')} | WH: {task.get('warehouse_name','-')}</p>
        <p>Task: {str(task.get('id',''))[:12]} | {str(task.get('flow_type','')).upper()}</p></div></body></html>
        """
        await audit(actor["name"], "barcode_generated", "wms_task", payload.target_id,
                    {"label_size": payload.label_size})
        return {"label_html": label_html, "target_type": payload.target_type, "target_id": payload.target_id}
    raise HTTPException(status_code=400, detail="target_type tidak valid")
