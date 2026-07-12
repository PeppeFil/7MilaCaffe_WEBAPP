const state = { products: [], cart: {} };

const searchInput = document.getElementById("searchInput");
const categoriaFilter = document.getElementById("categoriaFilter");
const productGrid = document.getElementById("productGrid");
const cartBody = document.getElementById("cartBody");
const cartItemCount = document.getElementById("cartItemCount");
const emptyCartMsg = document.getElementById("emptyCartMsg");
const scontoTipo = document.getElementById("scontoTipo");
const scontoValore = document.getElementById("scontoValore");
const metodoPagamento = document.getElementById("metodoPagamento");
const customerId = document.getElementById("customerId");
const vatRateId = document.getElementById("vatRateId");
const noteCliente = document.getElementById("noteCliente");
const totaleNettoView = document.getElementById("totaleNettoView");
const checkoutForm = document.getElementById("checkoutForm");
const cartPayload = document.getElementById("cartPayload");
let debounceTimer = null;

function euro(value) {
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(Number(value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

function productImage(product) {
  if (!product.immagine_url) return "<div class='product-image-fallback' aria-hidden='true'>☕</div>";
  return `<img class="product-image" src="${escapeHtml(product.immagine_url)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('div'), {className:'product-image-fallback', textContent:'☕'}))">`;
}

function loadProducts() {
  const params = new URLSearchParams();
  if (searchInput.value.trim()) params.append("q", searchInput.value.trim());
  if (categoriaFilter.value) params.append("categoria_id", categoriaFilter.value);
  fetch(`/cassa/search?${params.toString()}`)
    .then((response) => response.ok ? response.json() : Promise.reject())
    .then((data) => { state.products = Array.isArray(data) ? data : []; renderProductGrid(); })
    .catch(() => { productGrid.innerHTML = "<p class='text-warning mb-0'>Impossibile caricare i prodotti.</p>"; });
}

function renderProductGrid() {
  if (!state.products.length) {
    productGrid.innerHTML = "<p class='text-light'>Nessun prodotto trovato.</p>";
    return;
  }
  productGrid.innerHTML = state.products.map((product) => `
    <button type="button" class="product-tile" onclick="addToCart(${Number(product.id)})" aria-label="Aggiungi ${escapeHtml(product.nome)}">
      ${productImage(product)}
      <span class="product-tile-name">${escapeHtml(product.nome)}</span>
      <span class="product-tile-meta">${escapeHtml(product.marca)}${product.formato_confezione ? ` · ${escapeHtml(product.formato_confezione)}` : ""}</span>
      <span class="product-tile-price">${euro(product.prezzo_vendita)}</span>
      <span class="product-tile-stock">Disponibili: ${Number(product.quantita_disponibile) || 0}</span>
    </button>`).join("");
}

window.addToCart = function addToCart(productId) {
  const product = state.products.find((item) => item.id === productId);
  if (!product) return;
  const currentQty = state.cart[productId]?.quantita || 0;
  if (currentQty + 1 > product.quantita_disponibile) {
    alert("Quantità superiore alla disponibilità.");
    return;
  }
  state.cart[productId] = {
    prodotto_id: product.id, nome: product.nome, prezzo_unitario: Number(product.prezzo_vendita),
    quantita: currentQty + 1, quantita_disponibile: product.quantita_disponibile,
  };
  renderCart();
};

window.changeCartQty = function changeCartQty(productId, delta) {
  const row = state.cart[productId];
  if (!row) return;
  const next = row.quantita + delta;
  if (next <= 0) delete state.cart[productId];
  else if (next <= row.quantita_disponibile) row.quantita = next;
  else { alert("Quantità superiore alla disponibilità."); return; }
  renderCart();
};

function renderCart() {
  const rows = Object.values(state.cart);
  const quantity = rows.reduce((total, row) => total + row.quantita, 0);
  emptyCartMsg.hidden = Boolean(rows.length);
  cartItemCount.textContent = `${quantity} ${quantity === 1 ? "prodotto" : "prodotti"}`;
  cartBody.innerHTML = rows.map((row) => `
    <div class="cart-line">
      <div><strong>${escapeHtml(row.nome)}</strong><small>${euro(row.prezzo_unitario)}</small></div>
      <div class="quantity-control">
        <button type="button" onclick="changeCartQty(${Number(row.prodotto_id)}, -1)" aria-label="Riduci quantità">−</button>
        <span>${Number(row.quantita)}</span>
        <button type="button" onclick="changeCartQty(${Number(row.prodotto_id)}, 1)" aria-label="Aumenta quantità">+</button>
      </div>
      <strong>${euro(row.prezzo_unitario * row.quantita)}</strong>
    </div>`).join("");
  updateTotals();
}

function updateTotals() {
  const lordo = Object.values(state.cart).reduce((sum, row) => sum + row.prezzo_unitario * row.quantita, 0);
  let sconto = Math.max(0, Number(scontoValore.value || 0));
  if (scontoTipo.value === "percentuale") sconto = (lordo * sconto) / 100;
  totaleNettoView.textContent = euro(lordo - Math.min(sconto, lordo));
}

checkoutForm.addEventListener("submit", (event) => {
  const items = Object.values(state.cart).map((row) => ({ prodotto_id: row.prodotto_id, quantita: row.quantita }));
  if (!items.length) { event.preventDefault(); alert("Il carrello è vuoto."); return; }
  cartPayload.value = JSON.stringify({
    items, sconto_tipo: scontoTipo.value, sconto_valore: scontoValore.value || 0,
    metodo_pagamento: metodoPagamento.value, customer_id: customerId.value || null,
    vat_rate_id: vatRateId.value || null, note_cliente: noteCliente.value,
  });
});

document.querySelectorAll(".payment-choice").forEach((button) => button.addEventListener("click", () => {
  metodoPagamento.value = button.dataset.payment;
  document.querySelectorAll(".payment-choice").forEach((choice) => choice.classList.toggle("active", choice === button));
}));
searchInput.addEventListener("input", () => { clearTimeout(debounceTimer); debounceTimer = setTimeout(loadProducts, 200); });
categoriaFilter.addEventListener("change", loadProducts);
scontoTipo.addEventListener("change", updateTotals);
scontoValore.addEventListener("input", updateTotals);
state.products = Array.isArray(initialProducts) ? initialProducts : [];
renderProductGrid();
loadProducts();
