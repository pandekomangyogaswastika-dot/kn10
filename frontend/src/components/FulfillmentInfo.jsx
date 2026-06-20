import { ArrowLeftRight, Check } from "lucide-react";
import { formatQty } from "../utils/formatters";
import { modeMeta } from "../utils/fulfillment";

/**
 * Info ketersediaan/fulfillment (ATP) per baris cart + tombol minta transfer inter-company.
 * Dipisah dari CartPanel agar file tetap ramping (compliance < 500 baris).
 */
export function FulfillmentInfo({ line, loading, reqStatus, onRequestTransfer }) {
  if (!line) {
    if (loading) {
      return <p className="mt-2 text-[10px] text-[#8E8E93]">Mengecek ketersediaan (ATP)…</p>;
    }
    return null;
  }
  const meta = modeMeta(line.primary_mode);
  const bo = line.breakdown?.backorder || 0;
  const ic = line.breakdown?.inter_company || 0;
  const source = (line.cross_entity || [])[0];
  return (
    <div
      data-testid={`cart-item-fulfillment-${line.product_id}`}
      className="mt-2 rounded-md border border-[#EFF0F2] bg-white p-2"
    >
      <div className="flex items-center justify-between gap-2">
        <span
          data-testid={`cart-item-mode-${line.product_id}`}
          data-mode={line.primary_mode}
          className={`status-pill ${meta.cls}`}
        >
          {line.primary_mode === "inter_company" && <ArrowLeftRight size={11} />}
          {meta.label}
        </span>
        <span className="text-[10px] text-[#6B6B73] tabular-nums">
          ATP <span className="font-bold text-[#1C1C1E]">{formatQty(line.own_atp)}</span>
        </span>
      </div>
      <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-[#6B6B73] tabular-nums">
        <span>Stok: <span className="font-semibold text-[#126E2C]">{formatQty(line.own_available)}</span></span>
        <span>Incoming: <span className="font-semibold text-[#8C4A00]">{formatQty(line.own_incoming)}</span></span>
        {ic > 0 && (
          <span>Inter-Co: <span className="font-semibold text-[#6B219A]">{formatQty(ic)}</span></span>
        )}
      </div>
      {bo > 0 && (
        <p className="mt-1 text-[10px] font-semibold text-[#A8221A] tabular-nums">
          Backorder {formatQty(bo)} {line.unit}
        </p>
      )}
      <p className="mt-1 text-[10px] leading-snug text-[#8E8E93]">{line.explanation}</p>
      {line.primary_mode === "inter_company" && ic > 0 && source && (
        <div className="mt-2">
          {reqStatus === "requested" ? (
            <p
              data-testid={`transfer-requested-${line.product_id}`}
              className="flex items-center gap-1 rounded-md bg-[#EEF4FF] px-2 py-1.5 text-[10px] font-semibold text-[#0058CC]"
            >
              <Check size={12} className="flex-shrink-0" /> Transfer diminta — menunggu approval {source.entity_name}
            </p>
          ) : (
            <button
              type="button"
              data-testid={`request-transfer-${line.product_id}`}
              disabled={reqStatus === "requesting" || !onRequestTransfer}
              onClick={() => onRequestTransfer && onRequestTransfer(line)}
              className="flex w-full items-center justify-center gap-1.5 rounded-md border border-[#C9B6E8] bg-[#F7F2FE] px-2 py-1.5 text-[10px] font-bold text-[#6B219A] transition hover:bg-[#F0E8FB] disabled:opacity-50"
            >
              <ArrowLeftRight size={12} />
              {reqStatus === "requesting"
                ? "Memproses…"
                : reqStatus === "error"
                ? "Gagal — coba lagi"
                : `Minta Transfer dari ${source.entity_name} (${formatQty(ic)} ${line.unit})`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
