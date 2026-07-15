const state = { products: [], cart: {} };

const searchInput = document.getElementById("searchInput");
const categoriaFilter = document.getElementById("categoriaFilter");
const categoryChips = Array.from(document.querySelectorAll(".category-chip"));
const productGrid = document.getElementById("productGrid");
const cartBody = document.getElementById("cartBody");
const cartItemCount = document.getElementById("cartItemCount");
const emptyCartMsg = document.getElementById("emptyCartMsg");
const scontoTipo = document.getElementById("scontoTipo");
const scontoValore = document.getElementById("scontoValore");
const metodoPagamento = document.getElementById("metodoPagamento");
const customerId = document.getElementById("customerId");
const noteCliente = document.getElementById("noteCliente");
const totaleNettoView = document.getElementById("totaleNettoView");
const checkoutForm = document.getElementById("checkoutForm");
const checkoutButton = document.getElementById("checkoutButton");
const cartPayload = document.getElementById("cartPayload");
const customerCheckoutModalElement = document.getElementById("customerCheckoutModal");
const customerCheckoutModal = new bootstrap.Modal(customerCheckoutModalElement);
const customerSearch = document.getElementById("checkoutCustomerSearch");
const customerChoices = Array.from(document.querySelectorAll(".customer-choice"));
const customerNoResults = document.getElementById("customerNoResults");
const checkoutConfirmButton = document.getElementById("checkoutConfirmButton");
let debounceTimer = null;
let activeRequest = null;

function euro(value) {
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
  }).format(Number(value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function productImage(product, className = "product-image") {
  const name = escapeHtml(product.nome);
  if (!product.immagine_url) {
    return `<div class="${className}-fallback" aria-hidden="true"><i class="bi bi-cup-hot"></i></div>`;
  }
  return `<img class="${className}" src="${escapeHtml(product.immagine_url)}" alt="Foto ${name}" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('div'), {className:'${className}-fallback', textContent:'☕'}))">`;
}

function setGridBusy(isBusy) {
  productGrid.setAttribute("aria-busy", String(isBusy));
  productGrid.classList.toggle("is-loading", isBusy);
}

function renderLoadingState() {
  if (state.products.length) {
    setGridBusy(true);
    return;
  }
  productGrid.innerHTML = Array.from({ length: 8 }, () => `
    <div class="product-tile product-skeleton" aria-hidden="true">
      <span class="skeleton-image"></span>
      <span class="skeleton-line skeleton-line-wide"></span>
      <span class="skeleton-line"></span>
    </div>
  `).join("");
  setGridBusy(true);
}

function loadProducts() {
  if (activeRequest) activeRequest.abort();
  const requestController = new AbortController();
  activeRequest = requestController;

  const params = new URLSearchParams();
  if (searchInput.value.trim()) params.append("q", searchInput.value.trim());
  if (categoriaFilter.value) params.append("categoria_id", categoriaFilter.value);
  renderLoadingState();

  fetch(`/cassa/search?${params.toString()}`, {
    signal: requestController.signal,
    headers: { Accept: "application/json" },
  })
    .then((response) => (response.ok ? response.json() : Promise.reject(new Error("request"))))
    .then((data) => {
      state.products = Array.isArray(data) ? data : [];
      renderProductGrid();
    })
    .catch((error) => {
      if (error.name === "AbortError") return;
      productGrid.innerHTML = `
        <div class="product-grid-state">
          <i class="bi bi-wifi-off" aria-hidden="true"></i>
          <strong>Impossibile caricare i prodotti.</strong>
          <span>Controlla la connessione e riprova.</span>
          <button type="button" class="btn btn-outline-light retry-products">Riprova</button>
        </div>`;
    })
    .finally(() => {
      if (activeRequest !== requestController) return;
      activeRequest = null;
      setGridBusy(false);
    });
}

function availabilityMarkup(stock) {
  if (stock <= 0) return '<span class="product-stock is-out">Esaurito</span>';
  if (stock <= 3) return `<span class="product-stock is-low">Ultimi ${stock}</span>`;
  return "";
}

function quantityMarkup(product, quantity) {
  const productId = Number(product.id);
  const stock = Number(product.quantita_disponibile) || 0;
  if (stock <= 0) {
    return `<button type="button" class="product-add" disabled aria-label="${escapeHtml(product.nome)} esaurito"><i class="bi bi-plus-lg" aria-hidden="true"></i></button>`;
  }
  if (!quantity) {
    return `<button type="button" class="product-add" data-product-action="add" data-product-id="${productId}" aria-label="Aggiungi ${escapeHtml(product.nome)}"><i class="bi bi-plus-lg" aria-hidden="true"></i></button>`;
  }
  return `
    <div class="product-quantity" aria-label="${quantity} nel carrello">
      <button type="button" data-product-action="decrease" data-product-id="${productId}" aria-label="Riduci quantità di ${escapeHtml(product.nome)}">−</button>
      <strong>${quantity}</strong>
      <button type="button" data-product-action="increase" data-product-id="${productId}" aria-label="Aumenta quantità di ${escapeHtml(product.nome)}" ${quantity >= stock ? "disabled" : ""}>+</button>
    </div>`;
}

function renderProductGrid() {
  setGridBusy(false);
  if (!state.products.length) {
    productGrid.innerHTML = `
      <div class="product-grid-state">
        <i class="bi bi-search" aria-hidden="true"></i>
        <strong>Nessun prodotto trovato.</strong>
        <span>Prova a modificare la ricerca o la categoria.</span>
      </div>`;
    return;
  }

  productGrid.innerHTML = state.products.map((product) => {
    const productId = Number(product.id);
    const stock = Number(product.quantita_disponibile) || 0;
    const quantity = state.cart[productId]?.quantita || 0;
    const classes = ["product-tile"];
    if (quantity) classes.push("is-selected");
    if (stock <= 0) classes.push("is-out-of-stock");

    return `
      <article class="${classes.join(" ")}" data-product-card="${productId}" tabindex="${stock > 0 ? "0" : "-1"}" title="${escapeHtml(product.nome)}">
        <div class="product-media">
          ${productImage(product)}
          ${quantity ? `<span class="product-selected-badge" aria-label="${quantity} nel carrello"><i class="bi bi-check-lg" aria-hidden="true"></i></span>` : ""}
          ${availabilityMarkup(stock)}
        </div>
        <div class="product-card-body">
          <strong class="product-tile-name">${escapeHtml(product.nome)}</strong>
          <span class="product-tile-meta">${escapeHtml(product.marca)}</span>
          <span class="product-tile-format">${escapeHtml(product.formato_confezione || "Formato non indicato")}</span>
          <div class="product-card-footer">
            <strong class="product-tile-price">${euro(product.prezzo_vendita)}</strong>
            ${quantityMarkup(product, quantity)}
          </div>
        </div>
      </article>`;
  }).join("");
}

window.addToCart = function addToCart(productId) {
  const product = state.products.find((item) => Number(item.id) === Number(productId));
  if (!product) return;
  const stock = Number(product.quantita_disponibile) || 0;
  const currentQty = state.cart[productId]?.quantita || 0;
  if (stock <= 0 || currentQty + 1 > stock) return;

  state.cart[productId] = {
    prodotto_id: Number(product.id),
    nome: product.nome,
    marca: product.marca,
    formato_confezione: product.formato_confezione || "",
    immagine_url: product.immagine_url || "",
    prezzo_unitario: Number(product.prezzo_vendita),
    quantita: currentQty + 1,
    quantita_disponibile: stock,
  };
  renderCart();
};

window.changeCartQty = function changeCartQty(productId, delta) {
  const row = state.cart[productId];
  if (!row) return;
  const next = row.quantita + delta;
  if (next <= 0) delete state.cart[productId];
  else if (next <= row.quantita_disponibile) row.quantita = next;
  else return;
  renderCart();
};

window.removeCartItem = function removeCartItem(productId) {
  delete state.cart[productId];
  renderCart();
};

function renderCart() {
  const rows = Object.values(state.cart);
  emptyCartMsg.hidden = Boolean(rows.length);
  cartItemCount.textContent = `${rows.length} ${rows.length === 1 ? "prodotto" : "prodotti"}`;
  checkoutButton.disabled = !rows.length;

  cartBody.innerHTML = rows.map((row) => `
    <div class="cart-line" role="listitem">
      <div class="cart-line-image">${productImage(row, "cart-product-image")}</div>
      <div class="cart-line-info">
        <strong title="${escapeHtml(row.nome)}">${escapeHtml(row.nome)}</strong>
        <small>${escapeHtml(row.formato_confezione || row.marca || "")}</small>
      </div>
      <button type="button" class="cart-remove" data-cart-action="remove" data-product-id="${Number(row.prodotto_id)}" aria-label="Rimuovi ${escapeHtml(row.nome)} dal carrello"><i class="bi bi-x-lg" aria-hidden="true"></i></button>
      <div class="quantity-control">
        <button type="button" data-cart-action="decrease" data-product-id="${Number(row.prodotto_id)}" aria-label="Riduci quantità di ${escapeHtml(row.nome)}">−</button>
        <span>${Number(row.quantita)}</span>
        <button type="button" data-cart-action="increase" data-product-id="${Number(row.prodotto_id)}" aria-label="Aumenta quantità di ${escapeHtml(row.nome)}" ${row.quantita >= row.quantita_disponibile ? "disabled" : ""}>+</button>
      </div>
      <strong class="cart-line-total">${euro(row.prezzo_unitario * row.quantita)}</strong>
    </div>`).join("");

  renderProductGrid();
  updateTotals();
}

function updateTotals() {
  const lordo = Object.values(state.cart).reduce(
    (sum, row) => sum + row.prezzo_unitario * row.quantita,
    0,
  );
  let sconto = Math.max(0, Number(scontoValore.value || 0));
  if (scontoTipo.value === "percentuale") sconto = (lordo * sconto) / 100;
  totaleNettoView.textContent = euro(lordo - Math.min(sconto, lordo));
}

productGrid.addEventListener("click", (event) => {
  const retryButton = event.target.closest(".retry-products");
  if (retryButton) {
    loadProducts();
    return;
  }

  const actionButton = event.target.closest("[data-product-action]");
  if (actionButton) {
    event.stopPropagation();
    const productId = Number(actionButton.dataset.productId);
    if (actionButton.dataset.productAction === "decrease") changeCartQty(productId, -1);
    else addToCart(productId);
    return;
  }

  const card = event.target.closest("[data-product-card]");
  if (card && !card.classList.contains("is-out-of-stock")) {
    addToCart(Number(card.dataset.productCard));
  }
});

productGrid.addEventListener("keydown", (event) => {
  const card = event.target.closest("[data-product-card]");
  if (!card || event.target !== card || !["Enter", " "].includes(event.key)) return;
  event.preventDefault();
  addToCart(Number(card.dataset.productCard));
});

cartBody.addEventListener("click", (event) => {
  const button = event.target.closest("[data-cart-action]");
  if (!button) return;
  const productId = Number(button.dataset.productId);
  if (button.dataset.cartAction === "remove") removeCartItem(productId);
  else changeCartQty(productId, button.dataset.cartAction === "increase" ? 1 : -1);
});

checkoutForm.addEventListener("submit", (event) => {
  const items = Object.values(state.cart).map((row) => ({
    prodotto_id: row.prodotto_id,
    quantita: row.quantita,
  }));
  if (!items.length) {
    event.preventDefault();
    return;
  }
  cartPayload.value = JSON.stringify({
    items,
    sconto_tipo: scontoTipo.value,
    sconto_valore: scontoValore.value || 0,
    metodo_pagamento: metodoPagamento.value,
    customer_id: customerId.value || null,
    note_cliente: noteCliente.value,
  });
});

checkoutButton.addEventListener("click", () => {
  if (!Object.keys(state.cart).length) return;
  customerId.value = "";
  customerSearch.value = "";
  customerChoices.forEach((choice) => {
    choice.hidden = false;
    choice.classList.toggle("is-selected", choice.dataset.customerId === "");
  });
  customerNoResults.hidden = true;
  customerCheckoutModal.show();
  customerSearch.focus();
});

customerChoices.forEach((choice) => {
  choice.addEventListener("click", () => {
    customerId.value = choice.dataset.customerId || "";
    customerChoices.forEach((item) => item.classList.toggle("is-selected", item === choice));
  });
});

customerSearch.addEventListener("input", () => {
  const query = customerSearch.value.trim().toLocaleLowerCase("it");
  let visible = 0;
  customerChoices.forEach((choice) => {
    const matches = !query || choice.dataset.customerSearch.includes(query);
    choice.hidden = !matches;
    if (matches) visible += 1;
  });
  customerNoResults.hidden = visible !== 0;
});

checkoutConfirmButton.addEventListener("click", () => {
  customerCheckoutModal.hide();
  checkoutForm.requestSubmit();
});

document.querySelectorAll(".payment-choice").forEach((button) => {
  button.addEventListener("click", () => {
    metodoPagamento.value = button.dataset.payment;
    document.querySelectorAll(".payment-choice").forEach((choice) => {
      const selected = choice === button;
      choice.classList.toggle("active", selected);
      choice.setAttribute("aria-pressed", String(selected));
    });
  });
});

categoryChips.forEach((button) => {
  button.addEventListener("click", () => {
    categoriaFilter.value = button.dataset.category || "";
    categoryChips.forEach((chip) => {
      const selected = chip === button;
      chip.classList.toggle("active", selected);
      chip.setAttribute("aria-pressed", String(selected));
    });
    loadProducts();
  });
});

searchInput.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(loadProducts, 200);
});
searchInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  event.preventDefault();
  clearTimeout(debounceTimer);
  loadProducts();
});
scontoTipo.addEventListener("change", updateTotals);
scontoValore.addEventListener("input", updateTotals);

state.products = Array.isArray(initialProducts) ? initialProducts : [];
renderCart();
loadProducts();
