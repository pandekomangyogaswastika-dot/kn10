import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { ProductCard } from "../../components/ProductCard";
import { ProductDetail } from "../../components/ProductDetail";
import { CustomerPanel } from "../../components/CustomerPanel";
import { CartPanel } from "../../components/CartPanel";

export function SalesPortal({ 
  data, 
  selectedProduct, 
  breakdown, 
  onInspect, 
  onAdd, 
  cart, 
  setCart, 
  selectedCustomer, 
  setSelectedCustomer, 
  selectedAddress, 
  setSelectedAddress, 
  onCreateCustomer, 
  onSubmitOrder, 
  search, 
  setSearch, 
  onShowDetail,
  loading = false,
  settings = {},
  paymentTerms = [],
  selectedEntity = "all",
}) {
  const products = useMemo(() => 
    (data.products || []).filter((product) => 
      `${product.name} ${product.sku} ${product.category} ${product.color}`
        .toLowerCase()
        .includes(search.toLowerCase())
    ), 
    [data.products, search]
  );

  // Sub-fase 1.4 — preview ATP & Fulfillment Mode per item (READ-ONLY, debounced).
  const [allocation, setAllocation] = useState({ map: {}, loading: false, entityId: "" });
  const [transferRequests, setTransferRequests] = useState({});
  // Sub-fase 1.7 — rencana LOT per item (mixed-lot confirmation), debounced.
  const [lotPlan, setLotPlan] = useState({ requires_confirmation: false, lines: [], policy: {}, loading: false });
  // Sub-fase 1.7 — harga khusus disetujui per item (auto-apply di POS), debounced.
  const [specialMap, setSpecialMap] = useState({});
  useEffect(() => {
    if (!cart.length || !selectedCustomer?.id) { setSpecialMap({}); return undefined; }
    let cancelled = false;
    const entity_id = selectedEntity && selectedEntity !== "all" ? selectedEntity : (selectedCustomer?.entity_id || "");
    const timer = setTimeout(async () => {
      try {
        const results = await Promise.all(cart.map((i) =>
          axios.get(`${API}/price-approvals/effective`, {
            params: { customer_id: selectedCustomer.id, product_id: i.product.id, entity_id, quantity: i.quantity },
          }).then((r) => ({ pid: i.product.id, data: r.data })).catch(() => ({ pid: i.product.id, data: { has_special: false } }))
        ));
        if (cancelled) return;
        const map = {};
        results.forEach(({ pid, data }) => { if (data && data.has_special) map[pid] = data; });
        setSpecialMap(map);
      } catch (e) {
        if (!cancelled) setSpecialMap({});
      }
    }, 400);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [cart, selectedEntity, selectedCustomer]);
  useEffect(() => {
    if (!cart.length) {
      setAllocation({ map: {}, loading: false, entityId: "" });
      return undefined;
    }
    let cancelled = false;
    setAllocation((a) => ({ ...a, loading: true }));
    const timer = setTimeout(async () => {
      try {
        const entity_id =
          selectedEntity && selectedEntity !== "all"
            ? selectedEntity
            : (selectedCustomer?.entity_id || "");
        const res = await axios.post(`${API}/sales-orders/preview-allocation`, {
          entity_id,
          customer_id: selectedCustomer?.id || "",
          items: cart.map((i) => ({ product_id: i.product.id, quantity: i.quantity, unit: i.unit })),
        });
        if (cancelled) return;
        const map = {};
        (res.data.lines || []).forEach((l) => { map[l.product_id] = l; });
        setAllocation({ map, loading: false, entityId: res.data.entity_id || entity_id });
      } catch (e) {
        if (!cancelled) setAllocation({ map: {}, loading: false, entityId: "" });
      }
    }, 350);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [cart, selectedEntity, selectedCustomer]);

  // Sub-fase 1.7 — preview rencana LOT (mixed-lot confirmation), debounced & READ-ONLY.
  useEffect(() => {
    if (!cart.length || !selectedCustomer?.id) {
      setLotPlan({ requires_confirmation: false, lines: [], policy: {}, loading: false });
      return undefined;
    }
    let cancelled = false;
    setLotPlan((lp) => ({ ...lp, loading: true }));
    const timer = setTimeout(async () => {
      try {
        const entity_id = selectedEntity && selectedEntity !== "all" ? selectedEntity : (selectedCustomer?.entity_id || "");
        const res = await axios.post(`${API}/sales-orders/preview-lots`, {
          entity_id,
          customer_id: selectedCustomer?.id || "",
          items: cart.map((i) => ({ product_id: i.product.id, quantity: i.quantity, unit: i.unit })),
        });
        if (cancelled) return;
        setLotPlan({
          requires_confirmation: !!res.data.requires_confirmation,
          lines: res.data.lines || [],
          policy: res.data.policy || {},
          loading: false,
        });
      } catch (e) {
        if (!cancelled) setLotPlan({ requires_confirmation: false, lines: [], policy: {}, loading: false });
      }
    }, 400);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [cart, selectedEntity, selectedCustomer]);
  const handleRequestTransfer = async (line) => {
    const source = (line.cross_entity || [])[0];
    const destEntity =
      allocation.entityId ||
      (selectedEntity && selectedEntity !== "all" ? selectedEntity : (selectedCustomer?.entity_id || ""));
    const qty = line.breakdown?.inter_company || 0;
    if (!source || !destEntity || qty <= 0) return;
    setTransferRequests((t) => ({ ...t, [line.product_id]: "requesting" }));
    try {
      await axios.post(`${API}/transfers/inter-company`, {
        source_entity_id: source.entity_id,
        dest_entity_id: destEntity,
        items: [{ product_id: line.product_id, quantity: qty, unit: line.unit }],
        notes: "Permintaan dari POS preview (Fulfillment Assistant)",
      });
      setTransferRequests((t) => ({ ...t, [line.product_id]: "requested" }));
    } catch (e) {
      setTransferRequests((t) => ({ ...t, [line.product_id]: "error" }));
    }
  };
  
  return (
    <div data-testid="sales-portal-view" className="grid gap-4 lg:grid-cols-[1fr_340px]">
      <section>
        <div className="section-card mb-4">
          <div className="section-head">
            <div className="flex items-center gap-3 min-w-0">
              <span className="kicker">Sales POS</span>
              <h2 data-testid="sales-portal-title">Katalog Kain Nusantara</h2>
            </div>
            <div className="flex items-center gap-2 rounded-md border border-[#E5E5EA] bg-white px-2 py-1.5 min-w-[240px]">
              <Search size={14} className="text-[#6B6B73]" />
              <input 
                data-testid="product-search-input" 
                className="w-full bg-transparent text-[13px] outline-none" 
                placeholder="Cari SKU, motif, warna..." 
                value={search} 
                onChange={(e) => setSearch(e.target.value)} 
              />
            </div>
          </div>
          <p data-testid="sales-portal-subtitle" className="px-4 py-2 text-[12px] text-[#6B6B73]">
            Grid POS dengan stok real-time, reserved qty & breakdown gudang per produk.
          </p>
        </div>
        {selectedProduct && (
          <ProductDetail 
            product={selectedProduct} 
            breakdown={breakdown} 
            onClose={() => onInspect(null)} 
            onAdd={onAdd} 
          />
        )}
        <div data-testid="product-grid" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {loading && (
            <div className="col-span-full animate-pulse py-10 text-center text-[13px] text-[#6B6B73]">Memuat katalog produk…</div>
          )}
          {!loading && products.length === 0 && (
            <div data-testid="products-empty" className="col-span-full py-10 text-center text-[13px] text-[#6B6B73]">Tidak ada produk yang cocok dengan pencarian.</div>
          )}
          {!loading && products.map((product) => (
            <ProductCard 
              key={product.id} 
              product={product} 
              onAdd={onAdd} 
              onInspect={onInspect} 
            />
          ))}
        </div>
      </section>
      <aside className="grid content-start gap-3">
        <CustomerPanel 
          customers={data.customers || []} 
          selectedCustomer={selectedCustomer} 
          setSelectedCustomer={setSelectedCustomer} 
          selectedAddress={selectedAddress} 
          setSelectedAddress={setSelectedAddress} 
          onCreateCustomer={onCreateCustomer} 
          onShowDetail={onShowDetail} 
        />
        <CartPanel 
          cart={cart} 
          setCart={setCart} 
          selectedCustomer={selectedCustomer} 
          selectedAddress={selectedAddress} 
          onSubmitOrder={onSubmitOrder} 
          onShowDetail={onShowDetail} 
          settings={settings}
          paymentTerms={paymentTerms}
          allocationLines={allocation.map}
          allocationLoading={allocation.loading}
          transferRequests={transferRequests}
          onRequestTransfer={handleRequestTransfer}
          specialPrices={specialMap}
          lotPlan={lotPlan}
          lotPlanLoading={lotPlan.loading}
        />
      </aside>
    </div>
  );
}
