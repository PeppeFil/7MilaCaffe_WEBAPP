const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const { test } = require("node:test");

test("cash cart applies promo after add, decrease, search and removal", () => {
  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, {
      value: "", textContent: "", innerHTML: "", hidden: false,
      classList: { toggle() {} }, setAttribute() {}, addEventListener() {},
      querySelectorAll() { return []; },
    });
    return elements.get(id);
  };
  element("scontoTipo").value = "nessuno";
  element("scontoValore").value = "0";
  const product = {id: 1, nome: "Borbone 55", prezzo_vendita: 11,
    quantita_disponibile: 400, formato_confezione: "55 capsule",
    promozione: {etichetta: "50 + 5 OMAGGIO", descrizione: "Promo",
      prezzi: [{quantita:4,totale:34},{quantita:2,totale:18},{quantita:1,totale:11}]},
  };
  const context = vm.createContext({
    document: {getElementById: element, querySelectorAll() {return [];}},
    window: {}, bootstrap: {Modal: class {}}, initialProducts:[product],
    fetch: () => new Promise(() => {}), AbortController, URLSearchParams,
    Intl, console, setTimeout, clearTimeout,
  });
  vm.runInContext(fs.readFileSync("app/static/js/cassa.js", "utf8"), context);
  const formatted = value => new Intl.NumberFormat("it-IT", {style:"currency",currency:"EUR"}).format(value);
  for (const total of [11,18,29,34,45,52,63,68]) {
    context.window.addToCart(1);
    assert.equal(element("totaleNettoView").textContent, formatted(total));
  }
  assert.match(element("cartBody").innerHTML, /Promo automatica/);
  assert.match(element("productGrid").innerHTML, /product-promo-badge/);
  assert.match(element("productGrid").innerHTML, /50 \+ 5 OMAGGIO/);
  vm.runInContext("state.products = []", context);
  context.window.changeCartQty(1, -1);
  assert.equal(element("totaleNettoView").textContent, formatted(63));
  element("scontoTipo").value = "percentuale";
  element("scontoValore").value = "10";
  vm.runInContext("updateTotals()", context);
  assert.equal(element("totaleNettoView").textContent, formatted(56.7));
  element("scontoTipo").value = "nessuno";
  vm.runInContext("updateTotals()", context);
  assert.equal(element("totaleNettoView").textContent, formatted(63));
  context.window.removeCartItem(1);
  assert.equal(element("totaleNettoView").textContent, formatted(0));
});
