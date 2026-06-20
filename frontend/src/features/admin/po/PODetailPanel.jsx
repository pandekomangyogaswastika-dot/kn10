import { useState } from "react";
import { FileText, CheckCircle, XCircle, AlertCircle, Wallet, RotateCcw, Ban } from "lucide-react";
import { formatCurrency } from "../../../utils/formatters";
import { getStatusBadge, getPaymentBadge } from "./poUtils";
import POTimeline from "./POTimeline";
import PODeviationBanner from "./PODeviationBanner";
import KNSelect from "../../../components/KNSelect";

/**
 * PODetailPanel — panel kanan detail PO (Depth #1: progress, AP/pembayaran, tutup-kurang, retur).
 * Props: po, currentUser, onClose, onApprove, onCancel, onPay, onCloseShort
 */
export default function PODetailPanel({ po, currentUser, onClose, onApprove, onCancel, onPay, onCloseShort }) {
  const [showPay, setShowPay] = useState(false);
  const [payAmount, setPayAmount] = useState("");
  const [payType, setPayType] = useState("kas_besar");
  const [payMethod, setPayMethod] = useState("transfer");
  const [payError, setPayError] = useState("");
  const [busy, setBusy] = useState(false);

  if (!po) {
    return (
      <div className="section-card flex items-center justify-center min-h-[200px] border-dashed">
        <div className="text-center p-6">
          <FileText size={28} className="mx-auto mb-2 text-gray-300" />
          <p className="text-[12px] text-[#6B6B73]">Pilih PO untuk lihat detail</p>
        </div>
      </div>
    );
  }

  const canManage = ["admin", "manager"].includes(currentUser?.role);
  const fin = po.financials || {};
  const goodsReceived = ["receiving", "partial", "completed", "closed_short"].includes(po.status);

  async function submitPay() {
    const amt = Number(payAmount);
    if (!amt || amt <= 0) { setPayError("Nominal harus lebih dari 0."); return; }
    setPayError("");
    setBusy(true);
    try {
      const ok = await onPay(po.id, { amount: amt, cash_type: payType, method: payMethod });
      if (ok) { setShowPay(false); setPayAmount(""); }
    } finally {
      setBusy(false);
    }
  }

  async function doApprove() {
    setBusy(true);
    try { await onApprove(po.id); } finally { setBusy(false); }
  }

  return (
    <div className="section-card self-start" data-testid="po-detail-panel">
      <div className="section-head">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase text-[#0058CC]">{po.po_number}</p>
          <div className="mt-0.5 flex items-center gap-1">{getStatusBadge(po.status)}{goodsReceived && getPaymentBadge(fin.payment_status)}</div>
        </div>
        <button className="icon-button" onClick={onClose}><XCircle size={14} /></button>
      </div>

      <div className="section-body space-y-3">
        {/* Supplier + Gudang */}
        <div className="grid grid-cols-2 gap-2 text-[11.5px]">
          <div className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2">
            <p className="text-[10px] text-[#6B6B73] uppercase font-semibold mb-0.5">Supplier</p>
            <p className="font-semibold">{po.supplier_name}</p>
            <p className="text-[10.5px] text-[#6B6B73]">{po.supplier_contact}</p>
          </div>
          <div className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2">
            <p className="text-[10px] text-[#6B6B73] uppercase font-semibold mb-0.5">Gudang</p>
            <p className="font-semibold">{po.warehouse_name}</p>
            <p className="text-[10.5px] text-[#6B6B73]">{po.warehouse_city}</p>
          </div>
        </div>

        {/* Items with receive progress (Depth 1A) */}
        <div className="rounded-md border border-[#EFF0F2] overflow-hidden">
          <div className="px-2.5 py-1.5 bg-[#FAFBFC] text-[10px] font-bold uppercase text-[#6B6B73] border-b border-[#EFF0F2]">
            Items & Progress Terima ({po.items?.length || 0})
          </div>
          {po.items?.map((item, i) => {
            const ordered = Number(item.quantity || 0);
            const rcv = Number(item.received_qty || 0);
            const pct = ordered > 0 ? Math.min(100, Math.round((rcv / ordered) * 100)) : 0;
            const done = pct >= 100;
            return (
              <div key={i} data-testid={`po-item-${i}`} className="px-2.5 py-1.5 border-b border-[#EFF0F2] last:border-0 text-[11px]">
                <div className="flex justify-between items-center">
                  <p className="font-semibold truncate">{item.sku}</p>
                  <p className="font-bold tabular-nums">{formatCurrency(item.line_total ?? item.subtotal ?? ordered * (item.price || 0))}</p>
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <div className="flex-1 h-1.5 rounded-full bg-[#EFF0F2] overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${pct}%`, background: done ? "#16A34A" : "#0058CC" }} />
                  </div>
                  <span className="text-[10px] tabular-nums text-[#6B6B73] whitespace-nowrap">{rcv}/{ordered} {item.unit}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* P0-1 — Rincian harga: diskon + DPP + PPN Masukan (PO ber-breakdown) */}
        {po.net_subtotal != null && (
          <div data-testid="po-pricing-breakdown" className="rounded-md border border-[#EFF0F2] overflow-hidden text-[11.5px]">
            <div className="px-2.5 py-1.5 bg-[#FAFBFC] text-[10px] font-bold uppercase text-[#6B6B73] border-b border-[#EFF0F2]">Rincian Harga & Pajak</div>
            <div className="p-2.5 space-y-1">
              <Row label="Subtotal" value={formatCurrency(po.total_amount)} />
              {Number(po.discount_total) > 0 && <Row label="Diskon" value={`- ${formatCurrency(po.discount_total)}`} tone="text-amber-700" />}
              <Row label="DPP" value={formatCurrency(po.dpp)} />
              <Row label={`PPN Masukan${Number(po.ppn_rate) > 0 ? ` (${po.ppn_rate}%)` : ""}`}
                value={Number(po.ppn_amount) > 0 ? formatCurrency(po.ppn_amount) : "—"} />
              <div className="flex justify-between border-t border-[#EFF0F2] pt-1 mt-1">
                <span className="font-bold">Grand Total</span>
                <span data-testid="po-grand-total" className="font-bold tabular-nums text-[#007AFF]">{formatCurrency(po.grand_total)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Financial summary (Depth 1C) */}
        {goodsReceived && (
          <div data-testid="po-financials" className="rounded-md border border-[#EFF0F2] overflow-hidden text-[11.5px]">
            <div className="px-2.5 py-1.5 bg-[#FAFBFC] text-[10px] font-bold uppercase text-[#6B6B73] border-b border-[#EFF0F2]">Keuangan / Hutang (AP)</div>
            <div className="p-2.5 space-y-1">
              <Row label="Total Tagihan" value={formatCurrency(fin.total_amount)} />
              {fin.returned_amount > 0 && <Row label="Retur (Nota Debit)" value={`- ${formatCurrency(fin.returned_amount)}`} tone="text-amber-700" />}
              <Row label="Sudah Dibayar" value={formatCurrency(fin.amount_paid)} tone="text-green-700" />
              <div className="flex justify-between border-t border-[#EFF0F2] pt-1 mt-1">
                <span className="font-bold">Sisa Hutang</span>
                <span data-testid="po-outstanding" className="font-bold tabular-nums text-red-600">{formatCurrency(fin.outstanding)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Returns linked (Depth 1B) */}
        {po.returns?.length > 0 && (
          <div className="rounded-md border border-[#EFF0F2] overflow-hidden">
            <div className="px-2.5 py-1.5 bg-[#FAFBFC] text-[10px] font-bold uppercase text-[#6B6B73] border-b border-[#EFF0F2]">Retur Beli</div>
            {po.returns.map((r) => (
              <div key={r.id} className="flex items-center justify-between px-2.5 py-1.5 border-b border-[#EFF0F2] last:border-0 text-[11px]">
                <div><p className="font-semibold">{r.number}</p><p className="text-[10px] text-[#6B6B73]">{r.debit_note_number || r.status}</p></div>
                <span className="font-bold tabular-nums text-amber-700">{formatCurrency(r.total_amount)}</span>
              </div>
            ))}
          </div>
        )}

        {po.status === "waiting_approval" && po.required_approval_role && (
          <div data-testid="po-approval-badge" className="flex items-center gap-2 rounded-md border border-[#FFE2B8] bg-[#FFF7EC] px-2.5 py-1.5 text-[11px] text-[#9A5B00]">
            <AlertCircle size={13} />
            <span>Butuh approval role <b className="uppercase">{po.required_approval_role}</b> sebelum inbound task dibuat.</span>
          </div>
        )}
        {po.price_deviation?.flagged && <PODeviationBanner deviation={po.price_deviation} />}
        {po.status === "closed_short" && (
          <div className="rounded-md border border-stone-200 bg-stone-50 px-2.5 py-1.5 text-[11px] text-stone-600">
            PO ditutup-kurang. Alasan: {po.close_reason || "—"}
          </div>
        )}

        {/* Depth #3 — Riwayat / timeline approval PO */}
        <POTimeline po={po} />

        {/* Payment form */}
        {showPay && (
          <div data-testid="po-pay-form" className="rounded-md border border-[#D6E4FF] bg-[#F5F9FF] p-2.5 space-y-2">
            <p className="text-[11px] font-bold text-[#0058CC]">Catat Pembayaran</p>
            {payError && <p data-testid="po-pay-error" className="text-[10.5px] text-[#C62828]">{payError}</p>}
            <div>
              <label className="block text-[10px] font-semibold text-[#6B6B73] mb-0.5">Nominal (sisa {formatCurrency(fin.outstanding)})</label>
              <input data-testid="po-pay-amount" type="number" value={payAmount} onChange={(e) => setPayAmount(e.target.value)} className="field" placeholder="0" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <KNSelect data-testid="po-pay-cashtype" value={payType} onValueChange={setPayType} className="field"
                options={[{ value: "kas_besar", label: "Kas Besar" }, { value: "kas_kecil", label: "Kas Kecil" }]} />
              <KNSelect data-testid="po-pay-method" value={payMethod} onValueChange={setPayMethod} className="field"
                options={[{ value: "transfer", label: "Transfer" }, { value: "tunai", label: "Tunai" }, { value: "giro", label: "Giro" }]} />
            </div>
            <div className="flex gap-2">
              <button data-testid="po-pay-submit" onClick={submitPay} disabled={busy} className="flex-1 primary-button justify-center">{busy ? "Memproses…" : "Bayar"}</button>
              <button onClick={() => setShowPay(false)} disabled={busy} className="secondary-button">Batal</button>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col gap-1.5">
          {po.status === "waiting_approval" && canManage && (
            <button data-testid="approve-po-button" onClick={doApprove} disabled={busy} className="primary-button justify-center">
              <CheckCircle size={13} /> {busy ? "Memproses…" : "Approve PO"}
            </button>
          )}
          {goodsReceived && fin.outstanding > 0 && canManage && (
            <button data-testid="pay-po-button" disabled={busy} onClick={() => { setShowPay(!showPay); setPayAmount(String(fin.outstanding || "")); }} className="primary-button justify-center">
              <Wallet size={13} /> Bayar PO
            </button>
          )}
          {["receiving", "partial", "pending"].includes(po.status) && canManage && (
            <button data-testid="close-po-button" disabled={busy} onClick={() => onCloseShort(po.id)} className="secondary-button justify-center">
              <Ban size={13} /> Tutup PO (Kurang)
            </button>
          )}
          {po.status === "completed" && (
            <button data-testid="view-receiving-goods-doc"
              onClick={() => window.open(`/api/inbound/po/${po.id}/receiving-goods-document`, "_blank")}
              className="secondary-button justify-center">
              <FileText size={13} /> Dokumen Goods Receipt
            </button>
          )}
          {["waiting_approval", "pending"].includes(po.status) && canManage && (
            <button data-testid="cancel-po-button" disabled={busy} onClick={() => onCancel(po.id)} className="danger-button justify-center">
              Batalkan PO
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, tone }) {
  return (
    <div className="flex justify-between">
      <span className="text-[#6B6B73]">{label}</span>
      <span className={`font-semibold tabular-nums ${tone || ""}`}>{value}</span>
    </div>
  );
}
