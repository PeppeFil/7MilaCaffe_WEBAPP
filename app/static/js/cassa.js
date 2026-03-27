const state = {
  products: [],
  cart: {},
};

const searchInput = document.getElementById("searchInput");
const categoriaFilter = document.getElementById("categoriaFilter");
const productGrid = document.getElementById("productGrid");
const cartBody = document.getElementById("cartBody");
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
  return `EUR ${Number(value).toFixed(2)}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function loadProducts() {
  const params = new URLSearchParams();
  if (searchInput.value.trim()) params.append("q", searchInput.value.trim());
  if (categoriaFilter.value) params.append("categoria_id", categoriaFilter.value);

  fetch(`/cassa/search?${params.toString()}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error("Ricerca prodotti non disponibile.");
      }
      return response.json();
    })
    .then((data) => {
      state.products = Array.isArray(data) ? data : [];
      renderProductGrid();
    })
    .catch(() => {
      productGrid.innerHTML =
        "<p class='text-warning mb-0'>Impossibile caricare i prodotti.</p>";
    });
}

function renderProductGrid() {
  if (!state.products.length) {
    productGrid.innerHTML = "<p class='text-light'>Nessun prodotto trovato.</p>";
    return;
  }
  productGrid.innerHTML = state.products
    .map(
      (product) => `
        <div class="product-card">
          <h6>${escapeHtml(product.nome)}</h6>
          <div class="meta">${escapeHtml(product.marca)}${
            product.categoria ? ` - ${escapeHtml(product.categoria)}` : ""
          }</div>
          <div class="meta">Barcode: ${escapeHtml(product.sku_barcode || "-")}</div>
          <div class="meta">Disponibile: ${Number(product.quantita_disponibile) || 0}</div>
          <div class="d-flex justify-content-between align-items-center mt-2">
            <strong>${euro(product.prezzo_vendita)}</strong>
            <button type="button" class="btn btn-sm btn-coffee" onclick="addToCart(${Number(product.id)})">Aggiungi</button>
          </div>
        </div>
      `,
    )
    .join("");
}

window.addToCart = function addToCart(productId) {
  const product = state.products.find((item) => item.id === productId);
  if (!product) return;

  const currentQty = state.cart[productId]?.quantita || 0;
  if (currentQty + 1 > product.quantita_disponibile) {
    alert("Quantita superiore alla disponibilita.");
    return;
  }

  state.cart[productId] = {
    prodotto_id: product.id,
    nome: product.nome,
    prezzo_unitario: Number(product.prezzo_vendita),
    quantita: currentQty + 1,
    quantita_disponibile: product.quantita_disponibile,
  };
  renderCart();
};

window.updateCartQty = function updateCartQty(productId, value) {
  const q = Number(value);
  if (!state.cart[productId]) return;
  if (q <= 0) {
    delete state.cart[productId];
    renderCart();
    return;
  }
  if (q > state.cart[productId].quantita_disponibile) {
    alert("Quantita superiore alla disponibilita.");
    return;
  }
  state.cart[productId].quantita = q;
  renderCart();
};

window.removeCartRow = function removeCartRow(productId) {
  delete state.cart[productId];
  renderCart();
};

function renderCart() {
  const rows = Object.values(state.cart);
  emptyCartMsg.style.display = rows.length ? "none" : "block";

  cartBody.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.nome)}</td>
          <td>
            <input type="number" min="1" max="${Number(row.quantita_disponibile)}" value="${Number(row.quantita)}" class="form-control form-control-sm" onchange="updateCartQty(${Number(row.prodotto_id)}, this.value)">
          </td>
          <td>${euro(row.prezzo_unitario)}</td>
          <td>${euro(row.prezzo_unitario * row.quantita)}</td>
          <td><button type="button" class="btn btn-sm btn-outline-danger" onclick="removeCartRow(${Number(row.prodotto_id)})">x</button></td>
        </tr>
      `,
    )
    .join("");

  updateTotals();
}

function updateTotals() {
  const rows = Object.values(state.cart);
  const lordo = rows.reduce(
    (acc, row) => acc + row.prezzo_unitario * row.quantita,
    0,
  );

  let sconto = Number(scontoValore.value || 0);
  if (sconto < 0) sconto = 0;

  if (scontoTipo.value === "percentuale") {
    sconto = (lordo * sconto) / 100;
  }
  if (sconto > lordo) sconto = lordo;

  const netto = lordo - sconto;
  totaleNettoView.value = euro(netto);
}

checkoutForm.addEventListener("submit", (event) => {
  const items = Object.values(state.cart).map((row) => ({
    prodotto_id: row.prodotto_id,
    quantita: row.quantita,
  }));
  if (!items.length) {
    event.preventDefault();
    alert("Il carrello e vuoto.");
    return;
  }

  const payload = {
    items,
    sconto_tipo: scontoTipo.value,
    sconto_valore: scontoValore.value || 0,
    metodo_pagamento: metodoPagamento.value,
    customer_id: customerId.value || null,
    vat_rate_id: vatRateId.value || null,
    note_cliente: noteCliente.value,
  };
  cartPayload.value = JSON.stringify(payload);
});

searchInput.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(loadProducts, 250);
});
categoriaFilter.addEventListener("change", loadProducts);
scontoTipo.addEventListener("change", updateTotals);
scontoValore.addEventListener("input", updateTotals);

state.products = Array.isArray(initialProducts) ? initialProducts : [];
renderProductGrid();
loadProducts();
