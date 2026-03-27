from datetime import datetime, timedelta
from decimal import Decimal
from random import Random
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import create_app
from app.extensions import db
from app.models import (
    CATEGORIE_BASE,
    Brand,
    Category,
    Compatibility,
    Customer,
    Product,
    Role,
    ShopPreference,
    Supplier,
    User,
    VatRate,
)
from app.models.constants import RUOLO_ADMIN, RUOLO_OPERATORE
from app.services.inventory_service import registra_movimento
from app.services.sale_service import annulla_vendita, crea_vendita


RND = Random(7)


def esegui_seed(reset: bool = True) -> None:
    if reset:
        db.drop_all()
        db.create_all()

    ruolo_admin = _ensure_role(RUOLO_ADMIN, "Accesso completo")
    ruolo_operatore = _ensure_role(RUOLO_OPERATORE, "Vendite e consultazione")

    admin = _ensure_user("admin", "admin@7milacaffe.local", "admin123", ruolo_admin.id)
    operatore = _ensure_user("operatore", "operatore@7milacaffe.local", "operator123", ruolo_operatore.id)

    categorie = {nome: _ensure_category(nome) for nome in CATEGORIE_BASE}
    marche = {
        "7Mila Selection": _ensure_brand("7Mila Selection"),
        "Napoli Espresso": _ensure_brand("Napoli Espresso"),
        "CapsulaLab": _ensure_brand("CapsulaLab"),
        "Torrefazione Vesuvio": _ensure_brand("Torrefazione Vesuvio"),
        "Coffee Machines": _ensure_brand("Coffee Machines"),
        "Barista Tools": _ensure_brand("Barista Tools"),
    }
    compatibilita = {
        "Universale": _ensure_compatibility("Universale"),
        "Nespresso": _ensure_compatibility("Nespresso"),
        "DolceGusto": _ensure_compatibility("DolceGusto"),
        "Lavazza A Modo Mio": _ensure_compatibility("Lavazza A Modo Mio"),
        "Multi": _ensure_compatibility("Multi"),
        "Misto": _ensure_compatibility("Misto"),
    }
    fornitori = {
        "Torrefazione Vesuvio": _ensure_supplier("Torrefazione Vesuvio"),
        "CapsulaLab Italia": _ensure_supplier("CapsulaLab Italia"),
        "Coffee Machines SRL": _ensure_supplier("Coffee Machines SRL"),
        "Barista Tools Group": _ensure_supplier("Barista Tools Group"),
    }

    _ensure_vat_rate("IVA 4%", Decimal("4.00"), predefinita=False)
    _ensure_vat_rate("IVA 10%", Decimal("10.00"), predefinita=False)
    _ensure_vat_rate("IVA 22%", Decimal("22.00"), predefinita=True)

    _ensure_customer("Mario", "Rossi", telefono="333000111")
    _ensure_customer("Luca", "Bianchi", email="luca.bianchi@example.com")
    _ensure_customer("", "", ragione_sociale="Bar Centrale SRL", partita_iva="IT12345678901")

    _ensure_shop_preference("shop_name", "7MilaCaffe", "Nome negozio")
    _ensure_shop_preference("shop_address", "", "Indirizzo")
    _ensure_shop_preference("shop_phone", "", "Telefono")
    _ensure_shop_preference("shop_email", "", "Email")
    _ensure_shop_preference("shop_vat_number", "", "Partita IVA")

    db.session.commit()

    prodotti = _seed_prodotti(categorie, marche, compatibilita, fornitori)
    db.session.commit()

    for p, qty in prodotti:
        registra_movimento(
            prodotto=p,
            tipo_movimento="carico",
            quantita=qty,
            operatore_id=admin.id,
            motivo="Carico iniziale demo",
            data_ora=datetime.now() - timedelta(days=35),
        )

    db.session.commit()
    _seed_movimenti_extra(admin.id)
    _seed_vendite(admin.id, operatore.id)
    db.session.commit()


def _seed_prodotti(categorie, marche, compatibilita, fornitori):
    items = [
        ("Cialde Arabica 44mm 150pz", "Cialde", "7Mila Selection", "Universale", "150 pz", "0.15", "0.28", 60),
        ("Cialde Intenso 44mm 100pz", "Cialde", "Napoli Espresso", "Universale", "100 pz", "0.13", "0.25", 50),
        ("Capsule Compatibili Nespresso Classico", "Capsule", "CapsulaLab", "Nespresso", "50 pz", "0.20", "0.38", 70),
        ("Capsule Compatibili DolceGusto Crema", "Capsule", "CapsulaLab", "DolceGusto", "30 pz", "0.24", "0.45", 45),
        ("Capsule Compatibili Lavazza A Modo Mio", "Capsule", "Torrefazione Vesuvio", "Lavazza A Modo Mio", "36 pz", "0.23", "0.41", 40),
        ("Macchinetta Espresso Slim 15bar", "Macchinette da caffe", "Coffee Machines", "Nespresso", "1 unita", "52.00", "89.00", 4),
        ("Macchinetta MultiCaps Pro", "Macchinette da caffe", "Coffee Machines", "Multi", "1 unita", "79.00", "129.00", 3),
        ("Montalatte Elettrico 400ml", "Accessori", "Barista Tools", "Universale", "1 unita", "14.00", "24.90", 10),
        ("Bicchierini biodegradabili 80cc", "Accessori", "Barista Tools", "Universale", "100 pz", "2.90", "5.90", 30),
        ("Palette legno caffe", "Accessori", "Barista Tools", "Universale", "200 pz", "1.40", "3.20", 20),
        ("Kit Degustazione Arabica Premium", "Kit degustazione", "7Mila Selection", "Misto", "24 pz", "5.00", "11.90", 25),
        ("Kit Degustazione Intenso e Decaf", "Kit degustazione", "7Mila Selection", "Misto", "24 pz", "5.20", "12.50", 18),
        ("Capsule Decaf Compatibili Nespresso", "Capsule", "CapsulaLab", "Nespresso", "40 pz", "0.21", "0.39", 35),
        ("Cialde Orzo 44mm", "Cialde", "Napoli Espresso", "Universale", "50 pz", "0.10", "0.21", 20),
        ("Detergente decalcificante 250ml", "Accessori", "Barista Tools", "Universale", "1 unita", "3.50", "7.50", 16),
    ]

    created = []
    for nome, categoria_nome, marca_nome, compat_nome, formato, acq, ven, min_alert in items:
        existing = Product.query.filter_by(nome=nome).first()
        if existing:
            created.append((existing, 0))
            continue

        categoria_key = categoria_nome if categoria_nome in categorie else _resolve_categoria_key(categorie, categoria_nome)

        qta_iniziale = RND.randint(min_alert + 10, min_alert + 120)
        prodotto = Product(
            nome=nome,
            categoria_id=categorie[categoria_key].id,
            marca_id=marche[marca_nome].id,
            compatibilita_id=compatibilita[compat_nome].id,
            formato_confezione=formato,
            prezzo_acquisto=Decimal(acq),
            prezzo_vendita=Decimal(ven),
            quantita_disponibile=0,
            quantita_minima_alert=min_alert,
            sku_barcode=f"SKU-{RND.randint(100000, 999999)}",
            fornitore_id=fornitori[_pick_supplier(categoria_key)].id,
            note="Prodotto demo",
            attivo=True,
        )
        db.session.add(prodotto)
        db.session.flush()
        created.append((prodotto, qta_iniziale))

    return created


def _seed_vendite(admin_id: int, operatore_id: int):
    prodotti = Product.query.filter_by(attivo=True).all()
    clienti = Customer.query.filter_by(attivo=True).all()
    vat_rates = VatRate.query.filter_by(attiva=True).all()
    now = datetime.now().replace(minute=0, second=0, microsecond=0)

    for i in range(30):
        giorno = now - timedelta(days=i)
        vendite_n = RND.randint(2, 8)
        for _ in range(vendite_n):
            disponibili = [p for p in prodotti if p.quantita_disponibile > 0]
            if len(disponibili) < 2:
                break

            RND.shuffle(disponibili)
            num_righe = RND.randint(1, min(4, len(disponibili)))
            righe = []
            for p in disponibili[:num_righe]:
                qta = RND.randint(1, 4)
                if qta <= p.quantita_disponibile:
                    righe.append({"prodotto_id": p.id, "quantita": qta})

            if not righe:
                continue

            sconto_tipo = RND.choice(["nessuno", "percentuale", "fisso"])
            sconto_valore = 0
            if sconto_tipo == "percentuale":
                sconto_valore = RND.choice([5, 10, 15])
            elif sconto_tipo == "fisso":
                sconto_valore = RND.choice([0.5, 1, 2, 3])

            try:
                vendita = crea_vendita(
                    operatore_id=RND.choice([admin_id, operatore_id]),
                    items=righe,
                    sconto_tipo=sconto_tipo,
                    sconto_valore=sconto_valore,
                    metodo_pagamento=RND.choice(["contanti", "carta", "bonifico", "altro"]),
                    note_cliente="Vendita demo simulata",
                    customer_id=RND.choice(clienti).id if clienti and RND.random() < 0.4 else None,
                    vat_rate_id=RND.choice(vat_rates).id if vat_rates else None,
                    data_ora=giorno + timedelta(hours=RND.randint(9, 19), minutes=RND.randint(0, 59)),
                    commit=True,
                )

                if RND.random() < 0.08:
                    annulla_vendita(
                        vendita_id=vendita.id,
                        operatore_id=admin_id,
                        motivo="Annullamento demo casuale",
                        data_ora=vendita.data_ora + timedelta(minutes=10),
                    )
            except ValueError:
                db.session.rollback()


def _seed_movimenti_extra(admin_id: int):
    prodotti = Product.query.filter_by(attivo=True).all()
    for _ in range(20):
        prodotto = RND.choice(prodotti)
        tipo = RND.choice(["reso", "omaggio", "danneggiato", "rettifica"])
        if tipo == "rettifica":
            qta = RND.choice([-2, -1, 1, 2, 3])
        else:
            qta = RND.randint(1, 4)

        try:
            registra_movimento(
                prodotto=prodotto,
                tipo_movimento=tipo,
                quantita=qta,
                operatore_id=admin_id,
                motivo="Movimento demo",
                data_ora=datetime.now() - timedelta(days=RND.randint(1, 25)),
            )
        except ValueError:
            db.session.rollback()
            continue


def _ensure_role(nome: str, descrizione: str) -> Role:
    role = Role.query.filter_by(nome=nome).first()
    if role:
        return role
    role = Role(nome=nome, descrizione=descrizione)
    db.session.add(role)
    db.session.flush()
    return role


def _ensure_user(username: str, email: str, password: str, ruolo_id: int) -> User:
    user = User.query.filter_by(username=username).first()
    if user:
        return user
    user = User(username=username, email=email, ruolo_id=ruolo_id, attivo=True)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user


def _ensure_category(nome: str) -> Category:
    category = Category.query.filter_by(nome=nome).first()
    if category:
        return category
    category = Category(nome=nome)
    db.session.add(category)
    db.session.flush()
    return category


def _ensure_brand(nome: str) -> Brand:
    brand = Brand.query.filter_by(nome=nome).first()
    if brand:
        return brand
    brand = Brand(nome=nome)
    db.session.add(brand)
    db.session.flush()
    return brand


def _ensure_compatibility(nome: str) -> Compatibility:
    compatibility = Compatibility.query.filter_by(nome=nome).first()
    if compatibility:
        return compatibility
    compatibility = Compatibility(nome=nome)
    db.session.add(compatibility)
    db.session.flush()
    return compatibility


def _ensure_supplier(nome: str) -> Supplier:
    supplier = Supplier.query.filter_by(nome=nome).first()
    if supplier:
        return supplier
    supplier = Supplier(nome=nome)
    db.session.add(supplier)
    db.session.flush()
    return supplier


def _ensure_vat_rate(nome: str, aliquota: Decimal, predefinita: bool = False) -> VatRate:
    vat_rate = VatRate.query.filter_by(nome=nome).first()
    if vat_rate:
        if predefinita and not vat_rate.predefinita:
            VatRate.query.update({"predefinita": False})
            vat_rate.predefinita = True
        return vat_rate

    if predefinita:
        VatRate.query.update({"predefinita": False})

    vat_rate = VatRate(nome=nome, aliquota=aliquota, attiva=True, predefinita=predefinita)
    db.session.add(vat_rate)
    db.session.flush()
    return vat_rate


def _ensure_customer(
    nome: str,
    cognome: str,
    ragione_sociale: str | None = None,
    email: str | None = None,
    telefono: str | None = None,
    partita_iva: str | None = None,
) -> Customer:
    if ragione_sociale:
        existing = Customer.query.filter_by(ragione_sociale=ragione_sociale).first()
    else:
        existing = Customer.query.filter_by(nome=nome, cognome=cognome).first()

    if existing:
        return existing

    customer = Customer(
        nome=nome or ragione_sociale,
        cognome=cognome or None,
        ragione_sociale=ragione_sociale,
        email=email,
        telefono=telefono,
        partita_iva=partita_iva,
        attivo=True,
    )
    db.session.add(customer)
    db.session.flush()
    return customer


def _ensure_shop_preference(chiave: str, valore: str, descrizione: str) -> ShopPreference:
    pref = ShopPreference.query.filter_by(chiave=chiave).first()
    if pref:
        return pref
    pref = ShopPreference(chiave=chiave, valore=valore, descrizione=descrizione)
    db.session.add(pref)
    db.session.flush()
    return pref


def _pick_supplier(categoria_nome: str) -> str:
    categoria_lower = categoria_nome.lower()
    if categoria_nome in {"Cialde", "Capsule"}:
        return "Torrefazione Vesuvio"
    if "macchinette" in categoria_lower:
        return "Coffee Machines SRL"
    if categoria_nome == "Accessori":
        return "Barista Tools Group"
    return "CapsulaLab Italia"


def _resolve_categoria_key(categorie: dict, categoria_nome: str) -> str:
    if categoria_nome in categorie:
        return categoria_nome

    check = categoria_nome.lower()
    for key in categorie:
        key_l = key.lower()
        if check == key_l:
            return key
        if "macchinette" in check and "macchinette" in key_l:
            return key

    return next(iter(categorie.keys()))


if __name__ == "__main__":
    app = create_app("development")
    with app.app_context():
        esegui_seed(reset=True)
        print("Seed completato.")
