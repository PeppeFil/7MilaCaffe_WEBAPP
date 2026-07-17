"""Catalogo iniziale ricavato dalle fatture di acquisto di giugno 2026."""

import re
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func

from app.extensions import db
from app.models import (
    Brand,
    Category,
    Compatibility,
    Product,
    StoreInventory,
    StoreLocation,
    Supplier,
    User,
    VatRate,
)
from app.services.inventory_service import registra_movimento


# Foto reali di prodotto cercate online. Sono volutamente URL esterni, come richiesto:
# il fallback grafico della cassa entra in funzione se un fornitore rimuove una foto.
IMG_CAPSULE = "https://www.casacialde.it/upload/prodotti/1732878053.webp"
IMG_CIALDE = "https://www.casacialde.it/upload/prodotti/1732698493.webp"
IMG_DOLCE_GUSTO = "https://www.zicaffe.com/361-large_default/gustosa-dolce-gusto-caps.jpg"
IMG_MODO_MIO = "https://www.zicaffe.com/364-large_default/capsula-gustosa-a-modo-mio.jpg"
IMG_DON_CARLO = "https://www.galloenrico.com/shop/78-large_default/capsula-doncarlo-100-pz-nera.jpg"

# Immagini locali verificate per i prodotti consegnati dal negozio. Il nome del
# file coincide con il codice articolo, cosi l'associazione resta inequivocabile
# e la cassa non dipende dalla velocita o disponibilita di siti esterni.
def _local_product_image(barcode: str) -> str:
    return f"/static/img/products/{barcode}.webp"


IMMAGINI_PRODOTTI = {
    "8034028330636": _local_product_image("8034028330636"),
    "8034028336706": _local_product_image("8034028336706"),
    "8034028330476": _local_product_image("8034028330476"),
    "8034028330643": _local_product_image("8034028330643"),
    "8034028330674": _local_product_image("8034028330674"),
    "8034028330698": _local_product_image("8034028330698"),
    "8034028330483": _local_product_image("8034028330483"),
    "8034028338014": _local_product_image("8034028338014"),
    "8034028330780": _local_product_image("8034028330780"),
    "8034028330827": _local_product_image("8034028330827"),
    "8034028330506": _local_product_image("8034028330506"),
    "8055176432317": _local_product_image("8055176432317"),
    "8055176432348": _local_product_image("8055176432348"),
    "8055176432744": _local_product_image("8055176432744"),
    "8055176432751": "https://www.espressotoscano.it/media/catalog/product/cache/1/image/9df78eab33525d08d6e5fb8d27136e95/i/m/immagine_2026-03-26_160631.png",
    "8034028333880": "https://images.openfoodfacts.org/images/products/803/402/833/3880/front_it.3.400.jpg",
    "032415800016": _local_product_image("032415800016"),
    "032415800017": _local_product_image("032415800017"),
    "032415800018": _local_product_image("032415800018"),
    "032416202882": _local_product_image("032416202882"),
    "032415900030": _local_product_image("032415900030"),
    "032415900032": _local_product_image("032415900032"),
    "032315200058": _local_product_image("032315200058"),
    "032315200057": _local_product_image("032315200057"),
    "032315200059": _local_product_image("032315200059"),
    "042720306208": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_golosite_dg_chococup.png",
    "042720306207": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_golosite_dg_polvere_di_stelle.png",
    "042720306206": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_golosite_dg_coccoloso_1.png",
    "042720306209": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_golosite_dg_caramelloso.png",
    "042720306210": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_golosite_dg_nocciocao.png",
    "042720306211": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_golosite_dg_cioccolatoso.png",
    "042720306212": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_golosite_dg_te_a_limone_3.png",
    "042720306213": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_golosite_dg_lollorzo.png",
    "042720306214": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_golosite_dg_lollocappuccino.png",
    "042720306215": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_golosite_dg_lolloginseng.png",
    "8029804016927": "https://ditrapani.it/cdn/shop/files/FullSizeRender_1a319295-ecc5-48c6-84a1-21fda46566e6.jpg?v=1757769834",
    "8029804016965": "https://ditrapani.it/cdn/shop/files/FullSizeRender_2e701de5-7802-469b-b88a-0b980c1c3db2.jpg?v=1757776824",
    "8029804003859": "https://ingrocaffe.it/images/prodotti/1520_1.jpg",
    "8029804016941": "https://ingrocaffe.it/images/prodotti/1798_1.jpg",
    "8029804010901": "https://ingrocaffe.it/images/prodotti/796_1.jpg",
    "8029804009776": "https://coffeeshopitalia.com/cdn/shop/files/Screenshot_2023-08-27_alle_11.31.29.png?height=628&pad_color=ffffff&v=1693128703&width=1200",
    "DOG48G": "https://www.zicaffe.com/361-large_default/capsula-gustosa-dolce-gusto.jpg",
    "CLA50G": "https://www.zicaffe.com/364-large_default/capsula-gustosa-a-modo-mio.jpg",
    "CNE50G": "https://www.zicaffe.com/358-large_default/capsula-gustosa-nespresso.jpg",
    "CDG50": "https://www.kaffee.de/media/image/07/d3/50/1703_001.jpg",
}

# Prezzi di vendita concordati con il negozio. Vengono usati al primo import
# e mantengono coerente un eventuale nuovo database con la produzione.
PREZZI_VENDITA_MANUALI = {
    "8034028330674": Decimal("21.00"),  # Don Carlo Nera
    "8034028330698": Decimal("22.00"),  # Don Carlo Red
    "8034028330483": Decimal("23.00"),  # Don Carlo Blu
    "8034028338014": Decimal("25.00"),  # Don Carlo Oro
    "8034028330636": Decimal("21.00"),  # Respresso Nera
    "8034028336706": Decimal("22.00"),  # Respresso Red
    "8034028330476": Decimal("23.00"),  # Respresso Blu
    "8034028330643": Decimal("25.00"),  # Respresso Oro
    "REBDEK100N": Decimal("25.00"),  # Respresso Dek
    "8034028330780": Decimal("24.00"),  # Cialde Borbone Nera
    "8034028330827": Decimal("26.00"),  # Cialde Borbone Red
    "8034028330506": Decimal("28.00"),  # Cialde Borbone Blu
    "AMSDEK100NDONCARLO": Decimal("25.00"),  # Don Carlo Dek
    "44BDEK150N": Decimal("32.00"),  # Cialde Borbone Dek
    "032315200057": Decimal("24.00"),  # Cialde Lollo Classico
    "032315200058": Decimal("27.00"),  # Cialde Lollo Oro
    "032315200059": Decimal("27.00"),  # Cialde Lollo Dek
    "032415800016": Decimal("20.00"),  # Passione Mito Classica
    "032415800017": Decimal("22.00"),  # Passione Mito Oro
    "032415800018": Decimal("22.00"),  # Passione Mito Dek
    "032415900030": Decimal("20.00"),  # Passione Espresso Classica
    "032415900032": Decimal("22.00"),  # Passione Espresso Dek
    "8029804016927": Decimal("17.00"),  # Cialde Barbaro Nera
    "8029804016965": Decimal("17.00"),  # Cialde Barbaro Rosa
    "8029804009776": Decimal("19.00"),  # Barbaro A Modo Mio Rosa
    "8029804003859": Decimal("24.00"),  # Barbaro Dolce Gusto Blu
}


IMMAGINI_PRODOTTI_PER_NOME = {
    "caffe donna regina": "/static/img/products/donna-regina.jpg",
}


# Le fatture del catalogo riportano gli imponibili. Nel gestionale il costo
# d'acquisto viene invece conservato IVA inclusa, per avere margini e valore
# di magazzino confrontabili con i prezzi di vendita al pubblico.
ALIQUOTE_IVA_ACQUISTO = {
    "Capsule": Decimal("22"),
    "Cialde": Decimal("22"),
    "Capsule solubili": Decimal("10"),
    "Solubili": Decimal("10"),
    "Grani": Decimal("22"),
}


def _costo_iva_inclusa(costo_imponibile: Decimal, categoria: str) -> Decimal:
    aliquota = ALIQUOTE_IVA_ACQUISTO[categoria]
    return (costo_imponibile * (Decimal("1") + aliquota / Decimal("100"))).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )


def _aliquota_prodotto(categoria: str) -> int:
    return 10 if ALIQUOTE_IVA_ACQUISTO[categoria] == Decimal("10") else 22


def _product(
    barcode: str,
    nome: str,
    brand: str,
    supplier: str,
    category: str,
    compatibility: str,
    formato: str,
    costo: str,
    quantita: int,
    image: str,
) -> dict:
    return {
        "barcode": barcode,
        "nome": nome,
        "brand": brand,
        "supplier": supplier,
        "category": category,
        "compatibility": compatibility,
        "formato": formato,
        "costo": _costo_iva_inclusa(Decimal(costo), category),
        "quantita": quantita,
        "image": IMMAGINI_PRODOTTI.get(barcode, image),
    }


def _borbone_product(
    barcode: str,
    nome: str,
    category: str,
    compatibility: str,
    formato: str,
    prezzo_listino: str,
    quantita: int = 0,
    image: str = "",
    confezioni_per_collo: int = 1,
) -> dict:
    """Converte il listino Borbone nella singola unità vendibile.

    Dalle conferme d'ordine viene considerato soltanto lo sconto base del 5%; gli
    ulteriori sconti promozionali riportati nei documenti non entrano nel costo.
    Il costo viene poi salvato IVA inclusa secondo la categoria del prodotto.
    """
    imponibile_unitario = (
        Decimal(prezzo_listino)
        / Decimal(confezioni_per_collo)
        * Decimal("0.95")
    )
    row = _product(
        barcode,
        nome,
        "Caffe Borbone",
        "Caffe Borbone SRL",
        category,
        compatibility,
        formato,
        str(imponibile_unitario),
        quantita,
        image,
    )
    row["aggiorna_costo_da_fattura"] = True
    row["documento_origine"] = "Fatture e conferme d'ordine Borbone aprile-giugno 2026"
    return row


CATALOGO_REALE = [
    # Caffe Borbone. Prezzo di listino meno il solo sconto base del 5%, poi IVA.
    _product("8034028330636", "Respresso Borbone Nera", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Nespresso", "100 capsule", "11.49", 16, IMG_CAPSULE),
    _borbone_product("8034028336706", "Respresso Borbone Red", "Capsule", "Nespresso", "100 capsule", "13.64", 16, IMG_CAPSULE),
    _borbone_product("8034028330476", "Respresso Borbone Blu", "Capsule", "Nespresso", "100 capsule", "14.15", 32, IMG_CAPSULE),
    _borbone_product("8034028330643", "Respresso Borbone Oro", "Capsule", "Nespresso", "100 capsule", "15.27", 16, IMG_CAPSULE),
    _borbone_product("8034028330674", "Don Carlo Borbone Nera", "Capsule", "Lavazza A Modo Mio", "100 capsule", "13.00", 32, IMG_DON_CARLO),
    _borbone_product("8034028330698", "Don Carlo Borbone Red", "Capsule", "Lavazza A Modo Mio", "100 capsule", "13.64", 32, IMG_DON_CARLO),
    _borbone_product("8034028330483", "Don Carlo Borbone Blu", "Capsule", "Lavazza A Modo Mio", "100 capsule", "14.15", 64, IMG_DON_CARLO),
    _borbone_product("8034028338014", "Don Carlo Borbone Oro Compostabile", "Capsule", "Lavazza A Modo Mio", "100 capsule", "15.27", 16, IMG_DON_CARLO),
    _borbone_product("8034028330780", "Cialde Borbone Nera", "Cialde", "ESE 44 mm", "150 cialde", "15.44", 20, IMG_CIALDE),
    _borbone_product("8034028330827", "Cialde Borbone Red", "Cialde", "ESE 44 mm", "150 cialde", "16.75", 20, IMG_CIALDE),
    _borbone_product("8034028330506", "Cialde Borbone Blu", "Cialde", "ESE 44 mm", "150 cialde", "18.77", 20, IMG_CIALDE),
    _product("8055176432317", "Borbone Dolce Gusto Blu", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Dolce Gusto", "50 capsule", "7.03", 20, IMG_DOLCE_GUSTO),
    _product("8055176432348", "Borbone Dolce Gusto Red", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Dolce Gusto", "50 capsule", "7.03", 20, IMG_DOLCE_GUSTO),
    _product("8055176432744", "Respresso Borbone 100% Arabica Compostabile", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Nespresso", "50 capsule", "7.41", 5, IMG_CAPSULE),
    _product("8055176432751", "Don Carlo Borbone 100% Arabica Compostabile", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Lavazza A Modo Mio", "50 capsule", "7.41", 5, IMG_DON_CARLO),
    _borbone_product("8034028333880", "Caffe Borbone Ginseng", "Capsule solubili", "Sistema Borbone", "4 x 18 capsule", "14.28", 3, IMG_CAPSULE),
    # Articoli presenti nei nuovi documenti ma non ancora nell'anagrafica.
    # La giacenza parte da zero: i documenti storici servono al costo, non a
    # simulare merce che potrebbe essere già stata venduta o trasferita.
    _borbone_product("REBDEK100N", "Respresso Borbone Dek", "Capsule", "Nespresso", "100 capsule", "15.27"),
    _borbone_product("REBMIANAPOLI10X10N", "Respresso Borbone Mia Napoli Viola", "Capsule", "Nespresso", "10 capsule", "14.15", confezioni_per_collo=10),
    _borbone_product("AMSDEK100NDONCARLO", "Don Carlo Borbone Dek", "Capsule", "Lavazza A Modo Mio", "100 capsule", "15.27"),
    _borbone_product("44BDEK150N", "Cialde Borbone Dek", "Cialde", "ESE 44 mm", "150 cialde", "21.07"),
    _borbone_product("LVBROSSA100N", "Borbone Lavazza Blue Rossa", "Capsule", "Lavazza Blue", "100 capsule", "17.10"),
    _borbone_product("LVBORO100N", "Borbone Lavazza Blue Oro", "Capsule", "Lavazza Blue", "100 capsule", "19.00"),
    _borbone_product("BLTBBLU100N", "Borbone Bialetti Blu", "Capsule", "Bialetti", "100 capsule", "15.22"),
    _borbone_product("BLTBRED100N", "Borbone Bialetti Red", "Capsule", "Bialetti", "100 capsule", "14.44"),
    _borbone_product("DGBBLU90N", "Borbone Dolce Gusto Blu 90", "Capsule", "Dolce Gusto", "90 capsule", "12.80"),
    _borbone_product("DGBRED90N", "Borbone Dolce Gusto Red 90", "Capsule", "Dolce Gusto", "90 capsule", "12.80"),
    _borbone_product("CFIBBLU48X10", "Borbone Caffitaly Blu", "Capsule", "Caffitaly", "10 capsule", "126.64", confezioni_per_collo=48),
    _borbone_product("CFIBRED48X10", "Borbone Caffitaly Rossa", "Capsule", "Caffitaly", "10 capsule", "122.05", confezioni_per_collo=48),
    _borbone_product("GRBRED006REDVENDING", "Borbone Grani Red Vending", "Grani", "Grani", "1 kg", "60.96", confezioni_per_collo=6),
    _borbone_product("GRBBLU006SUPERVENDIN", "Borbone Grani Supervending", "Grani", "Grani", "1 kg", "65.83", confezioni_per_collo=6),
    _borbone_product("DGSUPERGIN4X16", "Borbone Super Ginseng Dolce Gusto", "Solubili", "Dolce Gusto", "16 capsule", "14.04", confezioni_per_collo=4),
    _borbone_product("AMGINSENG6X16", "Borbone Ginseng A Modo Mio", "Solubili", "Lavazza A Modo Mio", "16 capsule", "15.73", confezioni_per_collo=6),
    _borbone_product("RESGINSEN6X10", "Borbone Ginseng Respresso", "Solubili", "Nespresso", "10 capsule", "9.95", confezioni_per_collo=6),
    _borbone_product("AMTHELIMONE6X16", "Borbone Te al Limone A Modo Mio", "Solubili", "Lavazza A Modo Mio", "16 capsule", "15.73", confezioni_per_collo=6),
    _borbone_product("AMNOCCIOLINO6X16", "Borbone Nocciolino A Modo Mio", "Solubili", "Lavazza A Modo Mio", "16 capsule", "15.73", confezioni_per_collo=6),
    # Dical - fattura 22/06/2026. I costi includono sconti e omaggi ripartiti sulla giacenza ricevuta.
    _product("032415800016", "Passione Mito Classica", "Lollo", "Dical SRL", "Capsule", "Lavazza A Modo Mio", "100 capsule", "10.58", 148, IMG_MODO_MIO),
    _product("032415800017", "Passione Mito Oro", "Lollo", "Dical SRL", "Capsule", "Lavazza A Modo Mio", "100 capsule", "11.02", 33, IMG_MODO_MIO),
    _product("032415800018", "Passione Mito Dek", "Lollo", "Dical SRL", "Capsule", "Lavazza A Modo Mio", "100 capsule", "12.34", 30, IMG_MODO_MIO),
    _product("032416202882", "Passione Dolcissima Classica", "Lollo", "Dical SRL", "Capsule", "Dolce Gusto", "96 capsule", "13.52", 33, IMG_DOLCE_GUSTO),
    _product("032415900030", "Passione Espresso Classica", "Lollo", "Dical SRL", "Capsule", "Nespresso", "100 capsule", "11.52", 66, IMG_CAPSULE),
    _product("032415900032", "Passione Espresso Dek", "Lollo", "Dical SRL", "Capsule", "Nespresso", "100 capsule", "12.34", 10, IMG_CAPSULE),
    _product("032315200058", "Cialde Lollo Oro", "Lollo", "Dical SRL", "Cialde", "ESE 44 mm", "150 cialde", "15.26", 22, IMG_CIALDE),
    _product("032315200057", "Cialde Lollo Classico", "Lollo", "Dical SRL", "Cialde", "ESE 44 mm", "150 cialde", "14.28", 33, IMG_CIALDE),
    _product("032315200059", "Cialde Lollo Dek", "Lollo", "Dical SRL", "Cialde", "ESE 44 mm", "150 cialde", "16.68", 20, IMG_CIALDE),
    _product("042720306208", "Chococup Dolce Gusto", "Dical", "Dical SRL", "Capsule solubili", "Dolce Gusto", "10 capsule", "1.91", 16, IMG_DOLCE_GUSTO),
    _product("042720306207", "Polvere di Stelle Dolce Gusto", "Dical", "Dical SRL", "Capsule solubili", "Dolce Gusto", "10 capsule", "1.64", 16, IMG_DOLCE_GUSTO),
    _product("042720306206", "Coccoloso Dolce Gusto", "Dical", "Dical SRL", "Capsule solubili", "Dolce Gusto", "10 capsule", "1.91", 16, IMG_DOLCE_GUSTO),
    _product("042720306209", "Caramelloso Dolce Gusto", "Dical", "Dical SRL", "Capsule solubili", "Dolce Gusto", "10 capsule", "1.91", 16, IMG_DOLCE_GUSTO),
    _product("042720306210", "Nocciocao Dolce Gusto", "Dical", "Dical SRL", "Capsule solubili", "Dolce Gusto", "10 capsule", "1.64", 16, IMG_DOLCE_GUSTO),
    _product("042720306211", "Cioccolatoso Dolce Gusto", "Dical", "Dical SRL", "Capsule solubili", "Dolce Gusto", "10 capsule", "1.64", 24, IMG_DOLCE_GUSTO),
    _product("042720306212", "Tè al Limone Dolce Gusto", "Dical", "Dical SRL", "Capsule solubili", "Dolce Gusto", "10 capsule", "1.29", 24, IMG_DOLCE_GUSTO),
    _product("042720306213", "Lollorzo Dolce Gusto", "Dical", "Dical SRL", "Capsule solubili", "Dolce Gusto", "10 capsule", "1.29", 16, IMG_DOLCE_GUSTO),
    _product("042720306214", "LolloCappuccino Dolce Gusto", "Dical", "Dical SRL", "Capsule solubili", "Dolce Gusto", "10 capsule", "1.91", 16, IMG_DOLCE_GUSTO),
    _product("042720306215", "LolloGinseng Dolce Gusto", "Dical", "Dical SRL", "Capsule solubili", "Dolce Gusto", "10 capsule", "1.91", 24, IMG_DOLCE_GUSTO),
    _product("032423401923", "Passionesse Lollo Nera", "Lollo", "Dical SRL", "Capsule", "Esse Caffe", "100 capsule", "10.43", 10, IMG_CAPSULE),
    # Nutis / Caffe Barbaro - fattura 10/06/2026
    _product("8029804003859", "Caffe Barbaro DG Blu", "Caffe Barbaro", "Nutis SRL", "Capsule", "Dolce Gusto", "100 capsule", "15.61", 70, IMG_DOLCE_GUSTO),
    _product("8029804016989", "Caffe Barbaro DG Celeste Dek", "Caffe Barbaro", "Nutis SRL", "Capsule", "Dolce Gusto", "90 capsule", "15.38", 20, IMG_DOLCE_GUSTO),
    _product("8029804016941", "Caffe Barbaro DG Rosa", "Caffe Barbaro", "Nutis SRL", "Capsule", "Dolce Gusto", "90 capsule", "13.34", 10, IMG_DOLCE_GUSTO),
    _product("8029804016927", "Cialde Barbaro Nera", "Caffe Barbaro", "Nutis SRL", "Cialde", "ESE 44 mm", "140 cialde", "11.48", 81, IMG_CIALDE),
    _product("8029804010901", "Caffe Barbaro Esse Blu", "Caffe Barbaro", "Nutis SRL", "Capsule", "Esse Caffe", "100 capsule", "13.34", 20, IMG_CAPSULE),
    _product("8029804009776", "Caffe Barbaro A Modo Mio Rosa", "Caffe Barbaro", "Nutis SRL", "Capsule", "Lavazza A Modo Mio", "100 capsule", "13.34", 20, IMG_MODO_MIO),
    _product("8029804016965", "Cialde Barbaro Rosa", "Caffe Barbaro", "Nutis SRL", "Cialde", "ESE 44 mm", "140 cialde", "11.48", 30, IMG_CIALDE),
    # Zicaffe - fattura 28/05/2026. Le quantita includono la merce omaggio.
    _product("DOG48G", "Zicaffe Gustosa Dolce Gusto", "Zicaffe", "Zicaffe SPA", "Capsule", "Dolce Gusto", "48 capsule", "10.08", 67, IMG_DOLCE_GUSTO),
    _product("CLA50G", "Zicaffe Gustosa A Modo Mio", "Zicaffe", "Zicaffe SPA", "Capsule", "Lavazza A Modo Mio", "50 capsule", "8.59", 67, IMG_MODO_MIO),
    _product("CNE50G", "Zicaffe Gustosa Nespresso", "Zicaffe", "Zicaffe SPA", "Capsule", "Nespresso", "50 capsule", "7.38", 34, IMG_CAPSULE),
    _product("CDG50", "Zicaffe Gustosa Cialde", "Zicaffe", "Zicaffe SPA", "Cialde", "ESE 44 mm", "50 cialde", "7.02", 74, IMG_CIALDE),
]


def sync_catalogo_reale() -> tuple[int, int]:
    """Crea il catalogo solo se il codice a barre non e gia presente."""
    categorie = _ensure_by_name(Category, {row["category"] for row in CATALOGO_REALE})
    marche = _ensure_by_name(Brand, {row["brand"] for row in CATALOGO_REALE})
    compatibilita = _ensure_by_name(Compatibility, {row["compatibility"] for row in CATALOGO_REALE})
    fornitori = _ensure_by_name(Supplier, {row["supplier"] for row in CATALOGO_REALE})
    aliquote_iva = {
        int(rate.aliquota): rate
        for rate in VatRate.query.filter(VatRate.aliquota.in_([10, 22]), VatRate.attiva.is_(True)).all()
    }
    if 10 not in aliquote_iva or 22 not in aliquote_iva:
        raise RuntimeError("Aliquote IVA 10% e 22% non configurate.")
    operatore = User.query.filter_by(attivo=True).order_by(User.id.asc()).first()
    punto_vendita_iniziale = StoreLocation.query.filter_by(codice="via-pepoli", attivo=True).first()
    punti_vendita = StoreLocation.query.filter_by(attivo=True).all()

    creati = 0
    presenti = 0
    for row in CATALOGO_REALE:
        esistente = Product.query.filter_by(sku_barcode=row["barcode"]).first()
        if esistente:
            # Le giacenze e i prezzi di vendita restano invariati. Per gli
            # articoli riconosciuti nei nuovi documenti riallineiamo invece il
            # costo al listino -5% e l'anagrafica tecnica.
            esistente.nome = row["nome"]
            esistente.immagine_url = row["image"]
            esistente.marca_id = marche[row["brand"]].id
            esistente.categoria_id = categorie[row["category"]].id
            esistente.compatibilita_id = compatibilita[row["compatibility"]].id
            esistente.formato_confezione = row["formato"]
            esistente.fornitore_id = fornitori[row["supplier"]].id
            esistente.vat_rate_id = aliquote_iva[_aliquota_prodotto(row["category"])].id
            if row.get("aggiorna_costo_da_fattura"):
                esistente.prezzo_acquisto = row["costo"]
                esistente.note = (
                    f"Costo aggiornato da {row['documento_origine']}: "
                    "applicato soltanto lo sconto base del 5%."
                )
            presenti += 1
            continue

        prezzo_vendita = PREZZI_VENDITA_MANUALI.get(
            row["barcode"],
            (row["costo"] * Decimal("1.30")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
        )
        product = Product(
            nome=row["nome"],
            categoria_id=categorie[row["category"]].id,
            marca_id=marche[row["brand"]].id,
            vat_rate_id=aliquote_iva[_aliquota_prodotto(row["category"])].id,
            compatibilita_id=compatibilita[row["compatibility"]].id,
            formato_confezione=row["formato"],
            prezzo_acquisto=row["costo"],
            prezzo_vendita=prezzo_vendita,
            quantita_disponibile=0,
            quantita_minima_alert=max(2, min(10, row["quantita"] // 10)),
            sku_barcode=row["barcode"],
            immagine_url=row["image"],
            fornitore_id=fornitori[row["supplier"]].id,
            note=(
                f"Importato da {row['documento_origine']}; giacenza iniziale non caricata."
                if row.get("documento_origine")
                else "Importato dai listini di acquisto di giugno 2026."
            ),
            attivo=True,
        )
        db.session.add(product)
        db.session.flush()
        if row["quantita"] > 0 and operatore:
            registra_movimento(
                prodotto=product,
                tipo_movimento="carico",
                quantita=row["quantita"],
                operatore_id=operatore.id,
                motivo="Carico iniziale da listino giugno 2026",
                riferimento_entita=row["supplier"],
                punto_vendita_id=punto_vendita_iniziale.id if punto_vendita_iniziale else None,
            )
        elif row["quantita"] > 0:
            product.quantita_disponibile = row["quantita"]
        else:
            for punto_vendita in punti_vendita:
                db.session.add(
                    StoreInventory(
                        punto_vendita_id=punto_vendita.id,
                        prodotto_id=product.id,
                        quantita_disponibile=0,
                        quantita_minima_alert=product.quantita_minima_alert,
                    )
                )
        creati += 1

    # Alcuni articoli vengono creati manualmente e non appartengono al listino
    # iniziale: aggiorniamo comunque le foto locali quando il nome coincide.
    for nome, immagine_url in IMMAGINI_PRODOTTI_PER_NOME.items():
        prodotto = Product.query.filter(func.lower(Product.nome) == nome).first()
        if prodotto:
            prodotto.immagine_url = immagine_url

    # Donna Regina non aveva uno SKU nel primo import; la riconosciamo per nome
    # per evitare un doppione e applichiamo lo stesso criterio contabile.
    donna_regina = Product.query.filter(
        func.lower(Product.nome).like("%donna regina%")
    ).first()
    if donna_regina:
        donna_regina.prezzo_acquisto = _costo_iva_inclusa(
            Decimal("14.22") * Decimal("0.95"), "Cialde"
        )
        donna_regina.formato_confezione = "170 cialde"
        donna_regina.note = (
            "Costo aggiornato dalle conferme d'ordine Borbone: "
            "applicato soltanto lo sconto base del 5%."
        )

    db.session.commit()
    return creati, presenti


SINGLE_SKU_SUFFIX = "-SINGOLA"
SINGLE_CATEGORY_NAME = "Singole"


def _unita_per_confezione(formato: str | None) -> int | None:
    """Restituisce il primo numero del formato, se rappresenta una confezione valida."""
    match = re.search(r"\d+", formato or "")
    if not match:
        return None
    unita = int(match.group())
    return unita if unita > 0 else None


def _sku_singola(prodotto: Product) -> str:
    sku_sorgente = (prodotto.sku_barcode or "").strip()
    if sku_sorgente.casefold() in {"none", "null"}:
        sku_sorgente = ""
    if sku_sorgente:
        # Il campo SKU ammette 80 caratteri; conserviamo il suffisso identificativo.
        return f"{sku_sorgente[: 80 - len(SINGLE_SKU_SUFFIX)]}{SINGLE_SKU_SUFFIX}"
    return f"SINGOLA-{prodotto.id}"


def sync_varianti_singole() -> tuple[int, int, int]:
    """Crea o riallinea le unita singole di capsule e cialde.

    Le giacenze partono volutamente da zero: duplicare la disponibilita delle
    confezioni conteggerebbe due volte la stessa merce. L'apertura delle
    confezioni necessarie viene gestita automaticamente durante la vendita.
    """
    categoria_singole = Category.query.filter(
        func.lower(Category.nome) == SINGLE_CATEGORY_NAME.lower()
    ).first()
    if not categoria_singole:
        categoria_singole = Category(
            nome=SINGLE_CATEGORY_NAME,
            descrizione="Unita singole ricavate dalle confezioni di capsule e cialde.",
        )
        db.session.add(categoria_singole)
        db.session.flush()
    else:
        categoria_singole.nome = SINGLE_CATEGORY_NAME
        categoria_singole.descrizione = (
            "Unita singole ricavate dalle confezioni di capsule e cialde."
        )

    sorgenti = (
        Product.query.join(Product.categoria)
        .filter(
            func.lower(Category.nome).in_(["capsule", "cialde"]),
            Product.attivo.is_(True),
        )
        .order_by(Product.id.asc())
        .all()
    )
    punti_vendita = StoreLocation.query.filter_by(attivo=True).all()

    creati = 0
    aggiornati = 0
    ignorati = 0
    for sorgente in sorgenti:
        unita = _unita_per_confezione(sorgente.formato_confezione)
        if not unita:
            ignorati += 1
            continue

        sku = _sku_singola(sorgente)
        singola = Product.query.filter_by(sku_barcode=sku).first()
        nuovi_prezzi = {
            "prezzo_acquisto": (Decimal(sorgente.prezzo_acquisto) / unita).quantize(
                Decimal("0.000001"), rounding=ROUND_HALF_UP
            ),
            "prezzo_vendita": (Decimal(sorgente.prezzo_vendita) / unita).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
        }
        nome_unita = "1 cialda" if sorgente.categoria.nome.lower() == "cialde" else "1 capsula"

        if not singola:
            singola = Product(
                nome=f"{sorgente.nome[:129]} - Singola",
                categoria_id=categoria_singole.id,
                marca_id=sorgente.marca_id,
                vat_rate_id=sorgente.vat_rate_id,
                compatibilita_id=sorgente.compatibilita_id,
                formato_confezione=nome_unita,
                prezzo_acquisto=nuovi_prezzi["prezzo_acquisto"],
                prezzo_vendita=nuovi_prezzi["prezzo_vendita"],
                quantita_disponibile=0,
                quantita_minima_alert=0,
                sku_barcode=sku,
                immagine_url=sorgente.immagine_url,
                fornitore_id=sorgente.fornitore_id,
                confezione_origine_id=sorgente.id,
                unita_per_confezione=unita,
                note=f"Variante singola del prodotto #{sorgente.id} ({unita} unita per confezione).",
                attivo=True,
            )
            db.session.add(singola)
            db.session.flush()
            creati += 1
        else:
            singola.nome = f"{sorgente.nome[:129]} - Singola"
            singola.categoria_id = categoria_singole.id
            singola.marca_id = sorgente.marca_id
            singola.vat_rate_id = sorgente.vat_rate_id
            singola.compatibilita_id = sorgente.compatibilita_id
            singola.formato_confezione = nome_unita
            singola.prezzo_acquisto = nuovi_prezzi["prezzo_acquisto"]
            singola.prezzo_vendita = nuovi_prezzi["prezzo_vendita"]
            singola.immagine_url = sorgente.immagine_url
            singola.fornitore_id = sorgente.fornitore_id
            singola.confezione_origine_id = sorgente.id
            singola.unita_per_confezione = unita
            singola.note = (
                f"Variante singola del prodotto #{sorgente.id} ({unita} unita per confezione)."
            )
            singola.attivo = sorgente.attivo
            aggiornati += 1

        for punto_vendita in punti_vendita:
            giacenza = StoreInventory.query.filter_by(
                punto_vendita_id=punto_vendita.id,
                prodotto_id=singola.id,
            ).first()
            if not giacenza:
                db.session.add(
                    StoreInventory(
                        punto_vendita_id=punto_vendita.id,
                        prodotto_id=singola.id,
                        quantita_disponibile=0,
                        quantita_minima_alert=0,
                    )
                )

    db.session.commit()
    return creati, aggiornati, ignorati


def _ensure_by_name(model, names: set[str]) -> dict:
    found = {}
    for name in names:
        record = model.query.filter_by(nome=name).first()
        if not record:
            record = model(nome=name)
            db.session.add(record)
            db.session.flush()
        found[name] = record
    return found
