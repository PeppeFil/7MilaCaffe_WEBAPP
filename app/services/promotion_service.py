from decimal import Decimal


BORBONE_55_SKU = "BORBONE-NESPRESSO-NERA-55-PROMO"
BORBONE_55_PROMO = {
    "etichetta": "50 + 5 OMAGGIO",
    "descrizione": "1 pacco 11 EUR - 2 pacchi 18 EUR - 4 pacchi 34 EUR",
    "prezzi": [
        {"quantita": 4, "totale": 34},
        {"quantita": 2, "totale": 18},
        {"quantita": 1, "totale": 11},
    ],
}


def promozione_prodotto(prodotto):
    return BORBONE_55_PROMO if prodotto.sku_barcode == BORBONE_55_SKU else None


def totale_prodotto(prodotto, quantita: int) -> Decimal:
    promo = promozione_prodotto(prodotto)
    if not promo:
        return Decimal(str(prodotto.prezzo_vendita)) * quantita
    totale = Decimal("0.00")
    for fascia in promo["prezzi"]:
        gruppi, quantita = divmod(quantita, fascia["quantita"])
        totale += gruppi * Decimal(fascia["totale"])
    return totale
