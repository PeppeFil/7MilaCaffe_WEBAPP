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
const checkoutCustomerList = document.getElementById("checkoutCustomerList");
const customerNoResults = document.getElementById("customerNoResults");
const checkoutConfirmButton = document.getElementById("checkoutConfirmButton");
const customerSelectionPanel = document.getElementById("customerSelectionPanel");
const customerSelectionFooter = document.getElementById("customerSelectionFooter");
const customerCreationFooter = document.getElementById("customerCreationFooter");
const newCustomerForm = document.getElementById("checkoutNewCustomerForm");
const newCustomerError = document.getElementById("checkoutCustomerFormError");
const showNewCustomerButton = document.getElementById("showNewCustomerButton");
const cancelNewCustomerButton = document.getElementById("cancelNewCustomerButton");
const saveNewCustomerButton = document.getElementById("saveNewCustomerButton");
const singleQuantityModalElement = document.getElementById("singleQuantityModal");
const singleQuantityModal = new bootstrap.Modal(singleQuantityModalElement);
const singleQuantityImage = document.getElementById("singleQuantityImage");
const singleQuantityProductName = document.getElementById("singleQuantityProductName");
const singleQuantityStock = document.getElementById("singleQuantityStock");
const singleQuantityInput = document.getElementById("singleQuantityInput");
const singleQuantityError = document.getElementById("singleQuantityError");
const singleQuantityConfirm = document.getElementById("singleQuantityConfirm");
let debounceTimer = null;
let activeRequest = null;
let selectedSingleProductId = null;

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

function isSingleProduct(product) {
  return Boolean(product?.is_variante_singola)
    || String(product?.categoria || "").toLocaleLowerCase("it") === "singole";
}

function usesQuickSingleQuantity(product) {
  return isSingleProduct(product);
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
  if (usesQuickSingleQuantity(product)) {
    return `
      <button type="button" class="product-add product-quick-quantity" data-product-action="set-single" data-product-id="${productId}" aria-label="Scegli quantità di ${escapeHtml(product.nome)}">
        ${quantity ? `<strong>${quantity}</strong>` : "Qtà"}
        <i class="bi bi-calculator" aria-hidden="true"></i>
      </button>`;
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
    is_variante_singola: isSingleProduct(product),
  };
  renderCart();
};

function setCartQuantity(productId, quantity) {
  const product = state.products.find((item) => Number(item.id) === Number(productId))
    || state.cart[productId];
  if (!product) return false;
  const stock = Number(product.quantita_disponibile) || 0;
  const next = Math.trunc(Number(quantity));
  if (!Number.isFinite(next) || next < 1 || next > stock) return false;
  state.cart[productId] = {
    prodotto_id: Number(product.id || product.prodotto_id),
    nome: product.nome,
    marca: product.marca,
    formato_confezione: product.formato_confezione || "",
    immagine_url: product.immagine_url || "",
    prezzo_unitario: Number(product.prezzo_vendita ?? product.prezzo_unitario),
    quantita: next,
    quantita_disponibile: stock,
    is_variante_singola: true,
  };
  renderCart();
  return true;
}

function openSingleQuantity(productId) {
  const product = state.products.find((item) => Number(item.id) === Number(productId))
    || state.cart[productId];
  if (!product || !usesQuickSingleQuantity(product)) return;
  const stock = Number(product.quantita_disponibile) || 0;
  if (stock <= 0) return;
  selectedSingleProductId = Number(productId);
  singleQuantityProductName.textContent = product.nome;
  singleQuantityStock.textContent = `${stock} singole disponibili`;
  singleQuantityImage.innerHTML = productImage(product, "single-quantity-product-image");
  singleQuantityInput.max = String(stock);
  singleQuantityInput.value = String(state.cart[productId]?.quantita || 1);
  singleQuantityError.hidden = true;
  document.querySelectorAll("[data-single-quantity]").forEach((button) => {
    button.disabled = Number(button.dataset.singleQuantity) > stock;
  });
  singleQuantityModal.show();
  window.setTimeout(() => singleQuantityInput.select(), 150);
}

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

function cartQuantityMarkup(row) {
  const productId = Number(row.prodotto_id);
  if (usesQuickSingleQuantity(row)) {
    return `
      <button type="button" class="quantity-control single-cart-quantity" data-cart-action="set-single" data-product-id="${productId}" aria-label="Modifica quantità di ${escapeHtml(row.nome)}">
        <span>${Number(row.quantita)}</span>
        <small>Modifica</small>
        <i class="bi bi-pencil-square" aria-hidden="true"></i>
      </button>`;
  }
  return `
    <div class="quantity-control">
      <button type="button" data-cart-action="decrease" data-product-id="${productId}" aria-label="Riduci quantità di ${escapeHtml(row.nome)}">−</button>
      <span>${Number(row.quantita)}</span>
      <button type="button" data-cart-action="increase" data-product-id="${productId}" aria-label="Aumenta quantità di ${escapeHtml(row.nome)}" ${row.quantita >= row.quantita_disponibile ? "disabled" : ""}>+</button>
    </div>`;
}

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
      ${cartQuantityMarkup(row)}
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
    else if (actionButton.dataset.productAction === "set-single") openSingleQuantity(productId);
    else addToCart(productId);
    return;
  }

  const card = event.target.closest("[data-product-card]");
  if (card && !card.classList.contains("is-out-of-stock")) {
    const productId = Number(card.dataset.productCard);
    const product = state.products.find((item) => Number(item.id) === productId);
    if (usesQuickSingleQuantity(product)) openSingleQuantity(productId);
    else addToCart(productId);
  }
});

productGrid.addEventListener("keydown", (event) => {
  const card = event.target.closest("[data-product-card]");
  if (!card || event.target !== card || !["Enter", " "].includes(event.key)) return;
  event.preventDefault();
  const productId = Number(card.dataset.productCard);
  const product = state.products.find((item) => Number(item.id) === productId);
  if (usesQuickSingleQuantity(product)) openSingleQuantity(productId);
  else addToCart(productId);
});

cartBody.addEventListener("click", (event) => {
  const button = event.target.closest("[data-cart-action]");
  if (!button) return;
  const productId = Number(button.dataset.productId);
  if (button.dataset.cartAction === "remove") removeCartItem(productId);
  else if (button.dataset.cartAction === "set-single") openSingleQuantity(productId);
  else changeCartQty(productId, button.dataset.cartAction === "increase" ? 1 : -1);
});

document.querySelectorAll("[data-single-quantity]").forEach((button) => {
  button.addEventListener("click", () => {
    singleQuantityInput.value = button.dataset.singleQuantity;
    singleQuantityError.hidden = true;
  });
});

singleQuantityConfirm.addEventListener("click", () => {
  if (selectedSingleProductId === null) return;
  if (!setCartQuantity(selectedSingleProductId, singleQuantityInput.value)) {
    singleQuantityError.textContent = `Inserisci una quantità tra 1 e ${singleQuantityInput.max}.`;
    singleQuantityError.hidden = false;
    singleQuantityInput.focus();
    return;
  }
  singleQuantityModal.hide();
});

singleQuantityInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    singleQuantityConfirm.click();
  }
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

function customerChoices() {
  return Array.from(checkoutCustomerList.querySelectorAll(".customer-choice"));
}

function showCustomerSelection() {
  customerSelectionPanel.hidden = false;
  customerSelectionFooter.hidden = false;
  newCustomerForm.hidden = true;
  customerCreationFooter.hidden = true;
  newCustomerError.hidden = true;
}

function showCustomerCreation() {
  customerSelectionPanel.hidden = true;
  customerSelectionFooter.hidden = true;
  newCustomerForm.hidden = false;
  customerCreationFooter.hidden = false;
  newCustomerError.hidden = true;
  document.getElementById("cashCustomerName").focus();
}

function selectCustomerChoice(choice) {
  customerId.value = choice.dataset.customerId || "";
  customerChoices().forEach((item) => item.classList.toggle("is-selected", item === choice));
}

function newCustomerChoiceMarkup(cliente) {
  const contact = cliente.telefono || cliente.email || "Nessun contatto";
  const fiscal = cliente.partita_iva
    ? ` · P.IVA ${escapeHtml(cliente.partita_iva)}`
    : (cliente.codice_fiscale ? ` · CF ${escapeHtml(cliente.codice_fiscale)}` : "");
  const search = [
    cliente.display_name,
    cliente.telefono,
    cliente.email,
    cliente.codice_fiscale,
    cliente.partita_iva,
  ].filter(Boolean).join(" ").toLocaleLowerCase("it");
  return `
    <button type="button" class="customer-choice" data-customer-id="${Number(cliente.id)}" data-customer-search="${escapeHtml(search)}">
      <span class="customer-choice-icon"><i class="bi bi-person-vcard"></i></span>
      <span><strong>${escapeHtml(cliente.display_name)}</strong><small>${escapeHtml(contact)}${fiscal}</small></span>
      <i class="bi bi-check-circle-fill customer-choice-check"></i>
    </button>`;
}

checkoutButton.addEventListener("click", () => {
  if (!Object.keys(state.cart).length) return;
  customerId.value = "";
  customerSearch.value = "";
  customerChoices().forEach((choice) => {
    choice.hidden = false;
    choice.classList.toggle("is-selected", choice.dataset.customerId === "");
  });
  customerNoResults.hidden = true;
  newCustomerForm.reset();
  showCustomerSelection();
  customerCheckoutModal.show();
  customerSearch.focus();
});

checkoutCustomerList.addEventListener("click", (event) => {
  const choice = event.target.closest(".customer-choice");
  if (choice) selectCustomerChoice(choice);
});

customerSearch.addEventListener("input", () => {
  const query = customerSearch.value.trim().toLocaleLowerCase("it");
  let visible = 0;
  customerChoices().forEach((choice) => {
    const matches = !query || choice.dataset.customerSearch.includes(query);
    choice.hidden = !matches;
    if (matches) visible += 1;
  });
  customerNoResults.hidden = visible !== 0;
});

showNewCustomerButton.addEventListener("click", showCustomerCreation);
cancelNewCustomerButton.addEventListener("click", showCustomerSelection);

newCustomerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  newCustomerError.hidden = true;
  saveNewCustomerButton.disabled = true;
  const originalLabel = saveNewCustomerButton.innerHTML;
  saveNewCustomerButton.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Salvataggio';
  try {
    const response = await fetch("/cassa/clienti", {
      method: "POST",
      body: new FormData(newCustomerForm),
      headers: { Accept: "application/json" },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Impossibile salvare il cliente.");
    checkoutCustomerList.insertAdjacentHTML("beforeend", newCustomerChoiceMarkup(data));
    const choice = checkoutCustomerList.querySelector(`[data-customer-id="${Number(data.id)}"]`);
    selectCustomerChoice(choice);
    customerSearch.value = "";
    customerChoices().forEach((item) => { item.hidden = false; });
    customerNoResults.hidden = true;
    showCustomerSelection();
  } catch (error) {
    newCustomerError.textContent = error.message;
    newCustomerError.hidden = false;
  } finally {
    saveNewCustomerButton.disabled = false;
    saveNewCustomerButton.innerHTML = originalLabel;
  }
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
