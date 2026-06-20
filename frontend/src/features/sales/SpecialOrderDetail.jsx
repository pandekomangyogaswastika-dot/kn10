/**
 * Special Order Detail View
 * Shows status timeline, custom item details, approval actions
 */
import { useState } from "react";
import axios, { API } from "../../services/apiClient";
import {
  AlertCircle, ArrowLeft, Check, CheckCircle2, Clock, ClipboardList, Loader2,
  Package, Sparkles, X, XCircle
} from "lucide-react";


// Helpers
function fmtNum(n, d = 0) {
  return new Intl.NumberFormat("id-ID", { minimumFractionDigits: d, maximumFractionDigits: d }).format(n || 0);
}

function fmtDate(s) {
  if (!s) return "-";
  return new Date(s).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

const STATUS_STYLE = {
  draft:             { cls: "pill-muted",   label: "Draft", icon: Clock },
  pending_approval:  { cls: "pill-warning", label: "Menunggu Approval", icon: Clock },
  confirmed:         { cls: "pill-info",    label: "Confirmed", icon: CheckCircle2 },
  in_production:     { cls: "pill-purple",  label: "Dalam Produksi", icon: Package },
  ready:             { cls: "pill-success", label: "Ready", icon: CheckCircle2 },
  shipped:           { cls: "pill-primary", label: "Shipped", icon: Package },
  done:              { cls: "pill-success", label: "Done", icon: CheckCircle2 },
  cancelled:         { cls: "pill-danger",  label: "Cancelled", icon: XCircle },
};

function StatusPill({ status }) {
  const s = STATUS_STYLE[status] || { cls: "pill-muted", label: status, icon: Clock };
  const Icon = s.icon;
  return (
    <span className={`status-pill ${s.cls}`}>
      <Icon size={11} /> {s.label}
    </span>
  );
}

export default function SpecialOrderDetail({
  order,
  token,
  currentUser,
  onBack,
  onUpdate,
  notice,
  onClearNotice
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const canApprove = order.status === "pending_approval" && ["manager", "admin"].includes(currentUser?.role);
  const canTransition = ["admin", "manager"].includes(currentUser?.role);

  async function handleApprove() {
    if (!window.confirm(`Approve special order ${order.number}?`)) return;

    setLoading(true);
    try {
      const res = await axios.post(
        `${API}/special-orders/${order.id}/approve`,
        { notes: "" },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      onUpdate(res.data);
    } catch (e) {
      setError("Gagal approve: " + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  }

  async function handleReject() {
    if (!rejectReason.trim()) return;

    setLoading(true);
    try {
      const res = await axios.post(
        `${API}/special-orders/${order.id}/reject`,
        { reason: rejectReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      onUpdate(res.data);
      setShowRejectModal(false);
      setRejectReason("");
    } catch (e) {
      setError("Gagal reject: " + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusTransition(newStatus) {
    if (!window.confirm(`Update status ke ${newStatus}?`)) return;

    setLoading(true);
    try {
      const res = await axios.post(
        `${API}/special-orders/${order.id}/status`,
        { status: newStatus, notes: "" },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      onUpdate(res.data);
    } catch (e) {
      setError("Gagal update status: " + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  }

  async function handleCreatePR() {
    if (!window.confirm("Buat Purchase Requisition (pengadaan) untuk special order ini?")) return;
    setLoading(true);
    try {
      const res = await axios.post(
        `${API}/special-orders/${order.id}/create-pr`,
        { submit_now: true },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      onUpdate(res.data.special_order);
      setError(null);
    } catch (e) {
      setError("Gagal membuat PR: " + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  }

  // Status transition buttons based on current status
  const statusActions = {
    confirmed: { next: "in_production", label: "Mulai Produksi" },
    in_production: { next: "ready", label: "Mark as Ready" },
    ready: { next: "shipped", label: "Ship to Customer" },
    shipped: { next: "done", label: "Mark as Done" },
  };

  const action = statusActions[order.status];

  return (
    <div data-testid="special-order-detail-view" className="view-container">
      {/* Back */}
      <button className="back-button" onClick={onBack}>
        <ArrowLeft size={14} /> Kembali ke Daftar Special Order
      </button>

      {/* Notice */}
      {notice && (
        <div className="notice-bar success">
          <CheckCircle2 size={14} /> {notice}
          <button onClick={onClearNotice}><X size={12} /></button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="notice-bar danger">
          <AlertCircle size={14} /> {error}
          <button onClick={() => setError(null)}><X size={12} /></button>
        </div>
      )}

      {/* Header */}
      <div className="detail-header">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h2 className="detail-title" data-testid="special-order-number">
              <Sparkles size={18} className="text-purple-500" /> {order.number}
            </h2>
            <StatusPill status={order.status} />
            {order.requires_approval && (
              <span className="feature-badge badge-orange">Requires Approval</span>
            )}
          </div>
          <p className="detail-subtitle">
            Customer: <strong>{order.customer_name}</strong>
            {" "}• Dibuat: {fmtDate(order.created_at)} oleh {order.created_by}
          </p>
        </div>

        {/* Actions */}
        <div className="detail-actions">
          {canApprove && (
            <>
              <button
                data-testid="approve-special-order-btn"
                className="primary-button"
                onClick={handleApprove}
                disabled={loading}
              >
                <Check size={13} /> Approve
              </button>
              <button
                data-testid="reject-special-order-btn"
                className="danger-button"
                onClick={() => setShowRejectModal(true)}
                disabled={loading}
              >
                <X size={13} /> Reject
              </button>
            </>
          )}

          {action && canTransition && (
            <button
              data-testid="status-transition-btn"
              className="secondary-button"
              onClick={() => handleStatusTransition(action.next)}
              disabled={loading}
            >
              {loading ? <Loader2 size={13} className="spin" /> : <Check size={13} />}
              {action.label}
            </button>
          )}

          {["confirmed", "in_production"].includes(order.status) && !order.linked_pr_id && (
            <button
              data-testid="special-order-create-pr-btn"
              className="primary-button"
              onClick={handleCreatePR}
              disabled={loading}
              title="Jembatan ke pengadaan (Purchase Requisition)"
            >
              {loading ? <Loader2 size={13} className="spin" /> : <ClipboardList size={13} />}
              Buat PR Pengadaan
            </button>
          )}

          {order.linked_pr_number && (
            <div className="info-chip success" data-testid="special-order-linked-pr">
              <ClipboardList size={13} />
              PR: {order.linked_pr_number}
            </div>
          )}

          {order.status === "approved" && (
            <div className="info-chip success">
              <CheckCircle2 size={13} />
              Approved oleh {order.approved_by} pada {fmtDate(order.approved_at)}
            </div>
          )}

          {order.status === "cancelled" && (
            <div className="info-chip danger">
              <XCircle size={13} />
              {order.rejected_by ? (
                <>Ditolak: {order.reject_reason}</>
              ) : (
                <>Cancelled</>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="detail-grid-2col">
        {/* Left: Custom Item Details */}
        <div className="section-card">
          <div className="section-header">
            <Package size={14} /> Custom Item Details
          </div>

          <div className="space-y-4">
            <div>
              <div className="font-semibold mb-1">Deskripsi:</div>
              <div className="text-lg">{order.custom_item?.description || "-"}</div>
            </div>

            {order.custom_item?.specifications && Object.keys(order.custom_item.specifications).length > 0 ? (
              <div>
                <div className="font-semibold mb-2">Spesifikasi Custom:</div>
                <table className="data-table">
                  <tbody>
                    {Object.entries(order.custom_item.specifications).map(([key, value]) => (
                      <tr key={key}>
                        <td className="font-medium">{key}</td>
                        <td>{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-sm text-muted italic">Belum ada spesifikasi custom.</div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-muted">Quantity</div>
                <div className="font-semibold text-lg">
                  {fmtNum(order.custom_item?.quantity, 2)} {order.custom_item?.unit}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted">Target Price</div>
                <div className="font-semibold text-lg tabular-nums">
                  Rp {fmtNum(order.custom_item?.target_price, 0)}
                </div>
              </div>
            </div>

            <div>
              <div className="text-sm text-muted">Total Amount</div>
              <div className="font-bold text-2xl text-primary tabular-nums">
                Rp {fmtNum(order.total_amount, 0)}
              </div>
            </div>

            <div>
              <div className="text-sm text-muted">Expected Delivery</div>
              <div className="font-medium">
                <Clock size={12} className="inline mr-1" />
                {fmtDate(order.expected_delivery)}
              </div>
            </div>

            {order.notes && (
              <div>
                <div className="text-sm text-muted">Notes</div>
                <div className="section-notes">{order.notes}</div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Customer & Status History */}
        <div className="space-y-4">
          {/* Customer Info */}
          <div className="section-card">
            <div className="section-header">Customer Info</div>
            <div className="space-y-2">
              <div>
                <div className="text-sm text-muted">Name</div>
                <div className="font-semibold">{order.customer_name}</div>
              </div>
              {order.customer_email && (
                <div>
                  <div className="text-sm text-muted">Email</div>
                  <div>{order.customer_email}</div>
                </div>
              )}
              {order.customer_phone && (
                <div>
                  <div className="text-sm text-muted">Phone</div>
                  <div>{order.customer_phone}</div>
                </div>
              )}
              {order.shipping_address && (
                <div>
                  <div className="text-sm text-muted">Shipping Address</div>
                  <div className="text-sm">
                    {order.shipping_address.street && <div>{order.shipping_address.street}</div>}
                    <div>
                      {order.shipping_address.city && `${order.shipping_address.city}, `}
                      {order.shipping_address.province}
                      {order.shipping_address.postal_code && ` ${order.shipping_address.postal_code}`}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Status History */}
          {order.status_history && order.status_history.length > 0 && (
            <div className="section-card">
              <div className="section-header">Status Timeline</div>
              <div className="space-y-2">
                {order.status_history.slice().reverse().map((hist, i) => {
                  const s = STATUS_STYLE[hist.status] || {};
                  const Icon = s.icon || Clock;
                  return (
                    <div key={i} className="flex items-start gap-3 text-sm">
                      <Icon size={14} className="text-muted mt-0.5" />
                      <div className="flex-1">
                        <div className="font-medium">{s.label || hist.status}</div>
                        <div className="text-xs text-muted">
                          {fmtDate(hist.timestamp)} • {hist.user}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="modal-overlay" data-testid="reject-modal">
          <div className="modal-card small">
            <h3 className="modal-title">Reject Special Order {order.number}?</h3>
            <p className="modal-subtitle">Berikan alasan penolakan</p>
            <textarea
              data-testid="reject-reason-input"
              className="textarea"
              rows={3}
              placeholder="Alasan penolakan..."
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
            />
            <div className="modal-actions">
              <button className="secondary-button" onClick={() => setShowRejectModal(false)}>
                Batal
              </button>
              <button
                data-testid="confirm-reject-btn"
                className="danger-button"
                disabled={!rejectReason.trim() || loading}
                onClick={handleReject}
              >
                {loading ? <Loader2 size={13} className="spin" /> : <X size={13} />}
                {" "}Reject Order
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
