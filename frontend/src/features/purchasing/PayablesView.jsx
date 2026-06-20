import { useEffect, useState } from "react";
import axios, { API } from "../../services/apiClient";
import { Landmark, AlertTriangle, CheckCircle2 } from "lucide-react";
import { formatCurrency } from "../../utils/formatters";
import ErrorNotice from "../../components/ErrorNotice";

/**
 * PayablesView (Depth #1C) — Hutang Supplier (AP) + aging.
 */
function AgingPill({ bucket }) {
  const map = {
    "0-30": "pill-success", "31-60": "pill-warning", "61-90": "pill-warning", ">90": "pill-danger",
  };
  return <span className={`status-pill ${map[bucket] || "pill-muted"}`}>{bucket} hari</span>;
}
function PayPill({ status }) {
  const map = { unpaid: ["pill-danger", "Belum Bayar"], partial: ["pill-warning", "Sebagian"], paid: ["pill-success", "Lunas"] };
  const [cls, label] = map[status] || ["pill-muted", status];
  return <span className={`status-pill ${cls}`}>{label}</span>;
}

export default function PayablesView({ currentUser, selectedEntity }) {
  const [data, setData] = useState({ total_outstanding: 0, aging: {}, by_supplier: [], purchase_orders: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => { load(); }, [selectedEntity]); // eslint-disable-line

  async function load() {
    setLoading(true);
    try {
      const params = (selectedEntity && selectedEntity !== "all") ? { entity_id: selectedEntity } : {};
      const res = await axios.get(`${API}/purchase-orders/payables/summary`, { params });
      setData(res.data || {});
      setError("");
    } catch (e) {
      setError(e.response?.data?.detail || "Gagal memuat data hutang.");
    } finally {
      setLoading(false);
    }
  }

  const aging = data.aging || {};

  return (
    <div data-testid="payables-view">
      <ErrorNotice message={error} onRetry={load} onDismiss={() => setError("")} testId="payables-error" />

      {/* Summary */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mb-3">
        <div data-testid="ap-total-card" className="section-card">
          <div className="section-body">
            <p className="text-[10px] font-bold uppercase text-[#6B6B73] mb-1">Total Hutang (AP)</p>
            <p className="text-[20px] font-bold tabular-nums text-red-600">{formatCurrency(data.total_outstanding)}</p>
            <p className="text-[10px] text-[#9A9BA3] mt-1">{data.purchase_orders?.length || 0} PO outstanding</p>
          </div>
        </div>
        {["0-30", "31-60", "61-90", ">90"].map((b) => (
          <div key={b} data-testid={`ap-aging-${b}`} className="section-card">
            <div className="section-body">
              <div className="flex items-center justify-between mb-1">
                <p className="text-[10px] font-bold uppercase text-[#6B6B73]">Aging {b} hari</p>
                {b === ">90" && (aging[b] || 0) > 0 && <AlertTriangle size={13} className="text-red-500" />}
              </div>
              <p className={`text-[16px] font-bold tabular-nums ${b === ">90" && (aging[b] || 0) > 0 ? "text-red-600" : "text-[#0F1115]"}`}>{formatCurrency(aging[b])}</p>
            </div>
          </div>
        ))}
      </div>

      {/* By supplier */}
      <div className="section-card mb-3">
        <div className="section-head"><div className="flex items-center gap-2"><Landmark size={16} className="text-[#0058CC]" /><h2 data-testid="payables-title">Hutang per Supplier</h2></div></div>
        <div className="overflow-hidden">
          {loading ? (
            <div className="py-8 text-center text-[12px] text-[#6B6B73]">Memuat...</div>
          ) : (data.by_supplier || []).length === 0 ? (
            <div data-testid="payables-empty" className="flex flex-col items-center gap-2 py-10 text-center text-[12px] text-[#6B6B73]">
              <CheckCircle2 size={28} className="text-[#16A34A]" />
              <span>Tidak ada hutang outstanding.</span>
            </div>
          ) : (
            <div className="divide-y divide-[#EFF0F2]">
              {data.by_supplier.map((s, i) => (
                <div key={i} data-testid={`ap-supplier-${i}`} className="flex items-center justify-between px-3 py-2.5 hover:bg-[#FAFBFC]">
                  <div><p className="text-[12px] font-semibold">{s.supplier_name}</p><p className="text-[10.5px] text-[#6B6B73]">{s.po_count} PO</p></div>
                  <span className="text-[13px] font-bold tabular-nums text-red-600">{formatCurrency(s.outstanding)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* PO-level outstanding */}
      <div className="section-card">
        <div className="section-head"><h2 className="text-[13px] font-bold">Rincian PO Outstanding</h2></div>
        <div className="overflow-hidden">
          <div className="grid grid-cols-[80px_1.2fr_110px_110px_100px_110px] px-3 py-1.5 bg-[#FAFBFC] text-[10px] font-bold uppercase text-[#6B6B73] border-b border-[#EFF0F2]">
            <span>PO</span><span>Supplier</span><span className="text-right">Total</span><span className="text-right">Sisa</span><span>Bayar</span><span>Aging</span>
          </div>
          {loading ? (
            <div className="py-8 text-center text-[12px] text-[#6B6B73]">Memuat...</div>
          ) : (data.purchase_orders || []).length === 0 ? (
            <div className="py-10 text-center text-[12px] text-[#6B6B73]">Tidak ada PO outstanding.</div>
          ) : (
            <div className="divide-y divide-[#EFF0F2] max-h-[480px] overflow-y-auto">
              {data.purchase_orders.map((po) => (
                <div key={po.po_id} data-testid={`ap-po-${po.po_id}`} className="grid grid-cols-[80px_1.2fr_110px_110px_100px_110px] items-center px-3 py-2.5 hover:bg-[#FAFBFC]">
                  <span className="text-[11.5px] font-bold text-[#0058CC]">{po.po_number}</span>
                  <span className="text-[12px] font-semibold truncate">{po.supplier_name}</span>
                  <span className="text-[11.5px] tabular-nums text-right">{formatCurrency(po.total_amount)}</span>
                  <span className="text-[12px] font-bold tabular-nums text-right text-red-600">{formatCurrency(po.outstanding)}</span>
                  <PayPill status={po.payment_status} />
                  <AgingPill bucket={po.aging_bucket} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
