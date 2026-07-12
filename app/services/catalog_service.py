"""Catalogo iniziale ricavato dalle fatture di acquisto di giugno 2026."""

from decimal import Decimal, ROUND_HALF_UP

from app.extensions import db
from app.models import Brand, Category, Compatibility, Product, Supplier, User
from app.services.inventory_service import registra_movimento


# Foto reali di prodotto cercate online. Sono volutamente URL esterni, come richiesto:
# il fallback grafico della cassa entra in funzione se un fornitore rimuove una foto.
IMG_CAPSULE = "https://www.casacialde.it/upload/prodotti/1732878053.webp"
IMG_CIALDE = "https://www.casacialde.it/upload/prodotti/1732698493.webp"
IMG_DOLCE_GUSTO = "https://www.zicaffe.com/361-large_default/gustosa-dolce-gusto-caps.jpg"
IMG_MODO_MIO = "https://www.zicaffe.com/364-large_default/capsula-gustosa-a-modo-mio.jpg"
IMG_DON_CARLO = "https://www.galloenrico.com/shop/78-large_default/capsula-doncarlo-100-pz-nera.jpg"

# Immagini della confezione realmente associata al codice articolo.  I primi
# undici URL sono le foto frontali individuate tramite gli EAN corrispondenti;
# per Lollo/Golosita' e Zicaffe sono immagini dei rispettivi cataloghi online.
IMMAGINI_PRODOTTI = {
    "8034028330636": "https://images.openfoodfacts.org/images/products/803/402/833/0636/front_it.3.400.jpg",
    "8034028336706": "https://images.openfoodfacts.org/images/products/803/402/833/6706/front_it.3.400.jpg",
    "8034028330476": "https://images.openfoodfacts.org/images/products/803/402/833/0476/front_it.13.400.jpg",
    "8034028330643": "https://images.openfoodfacts.org/images/products/803/402/833/0643/front_it.5.400.jpg",
    "8034028330674": "https://images.openfoodfacts.org/images/products/803/402/833/0674/front_fr.10.400.jpg",
    "8034028330698": "https://images.openfoodfacts.org/images/products/803/402/833/0698/front_it.3.400.jpg",
    "8034028330483": "https://images.openfoodfacts.org/images/products/803/402/833/0483/front_fr.3.400.jpg",
    "8034028338014": "https://images.openfoodfacts.org/images/products/803/402/833/8014/front_it.3.400.jpg",
    "8034028330780": "https://images.openfoodfacts.org/images/products/803/402/833/0780/front_it.16.400.jpg",
    "8034028330827": "https://images.openfoodfacts.org/images/products/803/402/833/0827/front_it.3.400.jpg",
    "8034028330506": "https://images.openfoodfacts.org/images/products/803/402/833/0506/front_it.3.400.jpg",
    "8055176432317": "https://www.cialdeitalia.it/images/prodotti/BOR-NDG-BLU-0050-01.jpg",
    "8034028333880": "https://images.openfoodfacts.org/images/products/803/402/833/3880/front_it.3.400.jpg",
    "032415800016": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_amm_amazon_2026_copertina_3.jpg",
    "032415800017": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_amm_amazon_2026_copertina_4.jpg",
    "032415800018": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_amm_amazon_2026_copertina_5.jpg",
    "032416202882": "https://lollocaffeonline.it/media/catalog/product/l/o/lollo-dolce-gusto_1_1.jpg",
    "032415900030": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_nespresso_amazon_2026_2.jpg",
    "032415900032": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_nespresso_amazon_2026_4.jpg",
    "032315200058": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_cialda_amazon_2026_10.jpg",
    "032315200057": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_cialda_amazon_2026_9.jpg",
    "032315200059": "https://lollocaffeonline.it/media/catalog/product/m/o/mockup_cialda_amazon_2026.jpg",
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
    "8029804009776": "https://coffeeshopitalia.com/cdn/shop/files/Screenshot_2023-08-27_alle_11.31.29.png?height=628&pad_color=ffffff&v=1693128703&width=1200",
    "DOG48G": "https://www.zicaffe.com/361-large_default/capsula-gustosa-dolce-gusto.jpg",
    "CLA50G": "https://www.zicaffe.com/364-large_default/capsula-gustosa-a-modo-mio.jpg",
    "CNE50G": "https://www.zicaffe.com/358-large_default/capsula-gustosa-nespresso.jpg",
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
    "8034028330780": Decimal("24.00"),  # Cialde Borbone Nera
    "8034028330827": Decimal("26.00"),  # Cialde Borbone Red
    "8034028330506": Decimal("28.00"),  # Cialde Borbone Blu
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
        "costo": Decimal(costo),
        "quantita": quantita,
        "image": IMMAGINI_PRODOTTI.get(barcode, image),
    }


CATALOGO_REALE = [
    # Caffe Borbone - fattura 17/06/2026
    _product("8034028330636", "Respresso Borbone Nera", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Nespresso", "100 capsule", "11.49", 16, IMG_CAPSULE),
    _product("8034028336706", "Respresso Borbone Red", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Nespresso", "110 capsule", "12.31", 16, IMG_CAPSULE),
    _product("8034028330476", "Respresso Borbone Blu", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Nespresso", "100 capsule", "12.50", 32, IMG_CAPSULE),
    _product("8034028330643", "Respresso Borbone Oro", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Nespresso", "100 capsule", "13.49", 16, IMG_CAPSULE),
    _product("8034028330674", "Don Carlo Borbone Nera", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Lavazza A Modo Mio", "100 capsule", "12.35", 32, IMG_DON_CARLO),
    _product("8034028330698", "Don Carlo Borbone Red", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Lavazza A Modo Mio", "100 capsule", "12.96", 32, IMG_DON_CARLO),
    _product("8034028330483", "Don Carlo Borbone Blu", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Lavazza A Modo Mio", "100 capsule", "13.44", 64, IMG_DON_CARLO),
    _product("8034028338014", "Don Carlo Borbone Oro Compostabile", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Lavazza A Modo Mio", "100 capsule", "14.51", 16, IMG_DON_CARLO),
    _product("8034028330780", "Cialde Borbone Nera", "Caffe Borbone", "Caffe Borbone SRL", "Cialde", "ESE 44 mm", "150 cialde", "14.67", 20, IMG_CIALDE),
    _product("8034028330827", "Cialde Borbone Red", "Caffe Borbone", "Caffe Borbone SRL", "Cialde", "ESE 44 mm", "150 cialde", "15.91", 20, IMG_CIALDE),
    _product("8034028330506", "Cialde Borbone Blu", "Caffe Borbone", "Caffe Borbone SRL", "Cialde", "ESE 44 mm", "150 cialde", "17.83", 20, IMG_CIALDE),
    _product("8055176432317", "Borbone Dolce Gusto Blu", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Dolce Gusto", "50 capsule", "7.03", 20, IMG_DOLCE_GUSTO),
    _product("8055176432348", "Borbone Dolce Gusto Red", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Dolce Gusto", "50 capsule", "7.03", 20, IMG_DOLCE_GUSTO),
    _product("8055176432744", "Respresso Borbone 100% Arabica Compostabile", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Nespresso", "50 capsule", "7.41", 5, IMG_CAPSULE),
    _product("8055176432751", "Don Carlo Borbone 100% Arabica Compostabile", "Caffe Borbone", "Caffe Borbone SRL", "Capsule", "Lavazza A Modo Mio", "50 capsule", "7.41", 5, IMG_DON_CARLO),
    _product("8034028333880", "Caffe Borbone Ginseng", "Caffe Borbone", "Caffe Borbone SRL", "Capsule solubili", "Sistema Borbone", "4 x 18 capsule", "13.57", 3, IMG_CAPSULE),
    # Dical - fattura 22/06/2026. I costi includono sconti e omaggi ripartiti sulla giacenza ricevuta.
    _product("032415800016", "Passione Mito Classica", "Passione Mito", "Dical SRL", "Capsule", "Lavazza A Modo Mio", "100 capsule", "10.58", 148, IMG_MODO_MIO),
    _product("032415800017", "Passione Mito Oro", "Passione Mito", "Dical SRL", "Capsule", "Lavazza A Modo Mio", "100 capsule", "11.02", 33, IMG_MODO_MIO),
    _product("032415800018", "Passione Mito Dek", "Passione Mito", "Dical SRL", "Capsule", "Lavazza A Modo Mio", "100 capsule", "12.34", 30, IMG_MODO_MIO),
    _product("032416202882", "Passione Dolcissima Classica", "Passione Mito", "Dical SRL", "Capsule", "Dolce Gusto", "96 capsule", "13.52", 33, IMG_DOLCE_GUSTO),
    _product("032415900030", "Passione Espresso Classica", "Passione Mito", "Dical SRL", "Capsule", "Nespresso", "100 capsule", "11.52", 66, IMG_CAPSULE),
    _product("032415900032", "Passione Espresso Dek", "Passione Mito", "Dical SRL", "Capsule", "Nespresso", "100 capsule", "12.34", 10, IMG_CAPSULE),
    _product("032315200058", "Cialde Lollo Oro", "Caffe Lollo", "Dical SRL", "Cialde", "ESE 44 mm", "150 cialde", "15.26", 22, IMG_CIALDE),
    _product("032315200057", "Cialde Lollo Classico", "Caffe Lollo", "Dical SRL", "Cialde", "ESE 44 mm", "150 cialde", "14.28", 33, IMG_CIALDE),
    _product("032315200059", "Cialde Lollo Dek", "Caffe Lollo", "Dical SRL", "Cialde", "ESE 44 mm", "150 cialde", "16.68", 20, IMG_CIALDE),
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
    _product("032423401923", "Passionesse Lollo Nera", "Caffe Lollo", "Dical SRL", "Capsule", "Esse Caffe", "100 capsule", "10.43", 10, IMG_CAPSULE),
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
    operatore = User.query.filter_by(attivo=True).order_by(User.id.asc()).first()

    creati = 0
    presenti = 0
    for row in CATALOGO_REALE:
        esistente = Product.query.filter_by(sku_barcode=row["barcode"]).first()
        if esistente:
            # Manteniamo invariati prezzi e giacenze, ma correggiamo le schede
            # importate in precedenza con foto o descrizioni troppo generiche.
            esistente.nome = row["nome"]
            esistente.immagine_url = row["image"]
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
            compatibilita_id=compatibilita[row["compatibility"]].id,
            formato_confezione=row["formato"],
            prezzo_acquisto=row["costo"],
            prezzo_vendita=prezzo_vendita,
            quantita_disponibile=0,
            quantita_minima_alert=max(2, min(10, row["quantita"] // 10)),
            sku_barcode=row["barcode"],
            immagine_url=row["image"],
            fornitore_id=fornitori[row["supplier"]].id,
            note="Importato dai listini di acquisto di giugno 2026.",
            attivo=True,
        )
        db.session.add(product)
        db.session.flush()
        if operatore:
            registra_movimento(
                prodotto=product,
                tipo_movimento="carico",
                quantita=row["quantita"],
                operatore_id=operatore.id,
                motivo="Carico iniziale da listino giugno 2026",
                riferimento_entita=row["supplier"],
            )
        else:
            product.quantita_disponibile = row["quantita"]
        creati += 1

    db.session.commit()
    return creati, presenti


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
