import csv
import io
from decimal import Decimal

from sqlalchemy import or_

from app.extensions import db
from app.models import Brand, Compatibility, Product
from app.utils.parsers import to_decimal, to_int


def cerca_prodotti(filtri: dict):
    query = (
        Product.query.join(Product.brand)
        .outerjoin(Product.compatibility)
    )

    testo = (filtri.get("q") or "").strip()
    if testo:
        like_value = f"%{testo}%"
        query = query.filter(
            or_(
                Product.nome.ilike(like_value),
                Brand.nome.ilike(like_value),
                Compatibility.nome.ilike(like_value),
                Product.sku_barcode.ilike(like_value),
            )
        )

    categoria_id = filtri.get("categoria_id")
    if categoria_id:
        query = query.filter(Product.categoria_id == to_int(categoria_id))

    marca_id = to_int(filtri.get("marca_id"), default=0)
    if marca_id:
        query = query.filter(Product.marca_id == marca_id)

    compatibilita_id = to_int(filtri.get("compatibilita_id"), default=0)
    if compatibilita_id:
        query = query.filter(Product.compatibilita_id == compatibilita_id)

    sku = (filtri.get("sku") or "").strip()
    if sku:
        query = query.filter(Product.sku_barcode.ilike(f"%{sku}%"))

    attivo = filtri.get("attivo")
    if attivo == "1":
        query = query.filter(Product.attivo.is_(True))
    elif attivo == "0":
        query = query.filter(Product.attivo.is_(False))

    return query.order_by(Product.nome.asc())


def crea_prodotto(data: dict) -> Product:
    prodotto = Product()
    _apply_product_data(prodotto, data)
    db.session.add(prodotto)
    db.session.commit()
    return prodotto


def aggiorna_prodotto(prodotto: Product, data: dict) -> Product:
    _apply_product_data(prodotto, data)
    db.session.commit()
    return prodotto


def elimina_prodotto_logico(prodotto: Product) -> Product:
    prodotto.attivo = False
    db.session.commit()
    return prodotto


def duplica_prodotto(prodotto: Product) -> Product:
    clone = Product(
        nome=f"{prodotto.nome} (Copia)",
        categoria_id=prodotto.categoria_id,
        marca_id=prodotto.marca_id,
        compatibilita_id=prodotto.compatibilita_id,
        formato_confezione=prodotto.formato_confezione,
        prezzo_acquisto=prodotto.prezzo_acquisto,
        prezzo_vendita=prodotto.prezzo_vendita,
        quantita_disponibile=prodotto.quantita_disponibile,
        quantita_minima_alert=prodotto.quantita_minima_alert,
        sku_barcode=None,
        fornitore_id=prodotto.fornitore_id,
        note=prodotto.note,
        attivo=True,
    )
    db.session.add(clone)
    db.session.commit()
    return clone


def esporta_prodotti_csv(prodotti) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        [
            "id",
            "nome",
            "categoria",
            "marca_id",
            "marca",
            "compatibilita_id",
            "compatibilita",
            "formato_confezione",
            "prezzo_acquisto",
            "prezzo_vendita",
            "quantita_disponibile",
            "quantita_minima_alert",
            "sku_barcode",
            "fornitore",
            "attivo",
        ]
    )
    for p in prodotti:
        writer.writerow(
            [
                p.id,
                p.nome,
                p.categoria.nome if p.categoria else "",
                p.marca_id,
                p.brand.nome if p.brand else "",
                p.compatibilita_id or "",
                p.compatibility.nome if p.compatibility else "",
                p.formato_confezione or "",
                p.prezzo_acquisto,
                p.prezzo_vendita,
                p.quantita_disponibile,
                p.quantita_minima_alert,
                p.sku_barcode or "",
                p.fornitore.nome if p.fornitore else "",
                "1" if p.attivo else "0",
            ]
        )
    return stream.getvalue()


def importa_prodotti_csv(file_storage) -> tuple[int, int]:
    content = file_storage.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    created = 0
    updated = 0

    for row in reader:
        sku = (row.get("sku_barcode") or "").strip() or None
        prodotto = None
        if sku:
            prodotto = Product.query.filter_by(sku_barcode=sku).first()

        data = {
            "nome": row.get("nome"),
            "categoria_id": row.get("categoria_id"),
            "marca_id": _resolve_brand_id(row.get("marca_id"), row.get("marca")),
            "compatibilita_id": _resolve_compatibility_id(
                row.get("compatibilita_id"), row.get("compatibilita")
            ),
            "formato_confezione": row.get("formato_confezione"),
            "prezzo_acquisto": row.get("prezzo_acquisto"),
            "prezzo_vendita": row.get("prezzo_vendita"),
            "quantita_disponibile": row.get("quantita_disponibile"),
            "quantita_minima_alert": row.get("quantita_minima_alert"),
            "sku_barcode": sku,
            "fornitore_id": row.get("fornitore_id"),
            "note": row.get("note"),
            "attivo": row.get("attivo", "1"),
        }

        if prodotto:
            _apply_product_data(prodotto, data)
            updated += 1
        else:
            prodotto = Product()
            _apply_product_data(prodotto, data)
            db.session.add(prodotto)
            created += 1

    db.session.commit()
    return created, updated


def _apply_product_data(prodotto: Product, data: dict) -> None:
    prodotto.nome = (data.get("nome") or "").strip()
    prodotto.categoria_id = to_int(data.get("categoria_id"))
    prodotto.marca_id = to_int(data.get("marca_id"))
    prodotto.compatibilita_id = to_int(data.get("compatibilita_id"), default=0) or None
    prodotto.formato_confezione = (data.get("formato_confezione") or "").strip() or None
    prodotto.prezzo_acquisto = to_decimal(data.get("prezzo_acquisto"), Decimal("0.00"))
    prodotto.prezzo_vendita = to_decimal(data.get("prezzo_vendita"), Decimal("0.00"))
    prodotto.quantita_disponibile = to_int(data.get("quantita_disponibile"))
    prodotto.quantita_minima_alert = to_int(data.get("quantita_minima_alert"))
    prodotto.sku_barcode = (data.get("sku_barcode") or "").strip() or None

    if not prodotto.marca_id:
        raise ValueError("Marca obbligatoria.")

    fornitore_id = to_int(data.get("fornitore_id"), default=0)
    prodotto.fornitore_id = fornitore_id or None

    prodotto.note = (data.get("note") or "").strip() or None
    prodotto.attivo = str(data.get("attivo", "1")) in {"1", "true", "True", "on"}


def _resolve_brand_id(raw_id, raw_name) -> int:
    brand_id = to_int(raw_id, default=0)
    if brand_id:
        return brand_id
    nome = (raw_name or "").strip()
    if not nome:
        return 0
    brand = Brand.query.filter(Brand.nome.ilike(nome)).first()
    if brand:
        return brand.id
    brand = Brand(nome=nome)
    db.session.add(brand)
    db.session.flush()
    return brand.id


def _resolve_compatibility_id(raw_id, raw_name) -> int | None:
    compatibility_id = to_int(raw_id, default=0)
    if compatibility_id:
        return compatibility_id
    nome = (raw_name or "").strip()
    if not nome:
        return None
    compatibility = Compatibility.query.filter(Compatibility.nome.ilike(nome)).first()
    if compatibility:
        return compatibility.id
    compatibility = Compatibility(nome=nome)
    db.session.add(compatibility)
    db.session.flush()
    return compatibility.id
