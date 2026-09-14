import os

import click
from flask.cli import with_appcontext
from sqlalchemy import func

from .extensions import db
from .models import InventoryMovement, Product, Role, StoreLocation, User
from .models.constants import RUOLO_ADMIN
from .services.audit_service import registra_attivita
from .services.catalog_service import (
    ULTIMO_IMPORT_BORBONE_SKU,
    sync_catalogo_reale,
    sync_varianti_singole,
)
from .services.inventory_service import registra_movimento
from .services.store_service import quantita_fisica


def register_commands(app) -> None:
    app.cli.add_command(create_admin)
    app.cli.add_command(import_catalogo_reale)
    app.cli.add_command(imposta_giacenza_ultimo_import)
    app.cli.add_command(riconcilia_giacenze_20_luglio)
    app.cli.add_command(carica_ordini_borbone_luglio_2026)
    app.cli.add_command(carica_fatture_borbone_settembre_2026)


GIACENZE_20_LUGLIO = {
    "via-pepoli": {
        "8034028330636": 34,
        "8034028336706": 5,
        "8034028330476": 46,
        "REBDEK100N": 9,
        "8034028330643": 19,
        "8034028330780": 34,
        "8034028330827": 15,
        "8034028330506": 16,
        "44BDEK150N": 18,
        "44BORO150N": 30,
        "8034028330698": 24,
        "8034028330674": 23,
        "8034028330483": 20,
        "8034028338014": 15,
        "AMSDEK100NDONCARLO": 27,
        "DONNAREGINA170": 11,
        "BLTBBLU100N": 14,
        "BLTBDEK100N": 8,
        "BLTBRED100N": 5,
        "LVBROSSA100N": 4,
        "DGBDEK90N": 26,
        "DGBRED90N": 0,
        "DGBBLU90N": 0,
        "GRBRED006REDVENDING": 12,
        "GRBBLU006SUPERVENDIN": 16,
    },
    "via-vespri": {
        "8034028330780": 41,
        "8034028330827": 10,
        "8034028330506": 6,
        "44BORO150N": 8,
        "44BDEK150N": 9,
        "8034028330674": 23,
        "8034028330698": 22,
        "8034028330483": 4,
        "AMSDEK100NDONCARLO": 9,
        "8034028338014": 2,
        "8034028330636": 1,
        "8034028336706": 29,
        "8034028330476": 2,
        "8034028330643": 17,
        "REBDEK100N": 22,
        "DGBBLU90N": 4,
        "DONNAREGINA170": 25,
        "BLTBRED100N": 8,
        "BLTBBLU100N": 8,
        "BLTBDEK100N": 3,
    },
}


# Ogni riga contiene: SKU del documento, SKU interno, colli ricevuti e
# confezioni vendibili contenute in ciascun collo. Le quantità registrate a
# magazzino sono sempre espresse nell'unità venduta dall'applicazione.
ORDINI_BORBONE_LUGLIO_2026 = {
    "283447": {
        "punto_vendita": "via-pepoli",
        "righe": (
            ("REBRED100N", "8034028336706", 16, 1),
            ("AMSNERA100NDONCARLO", "8034028330674", 64, 1),
            ("AMSRED100NDONCARLO", "8034028330698", 64, 1),
            ("AMSBLU100NDONCARLO", "8034028330483", 64, 1),
            ("44BBLU150N", "8034028330506", 20, 1),
            ("DGBBLU90N", "DGBBLU90N", 10, 1),
            ("DGBBLU4X16N", "DGBBLU4X16N", 10, 4),
            ("DGBRED90N", "DGBRED90N", 10, 1),
            ("DGBROSSA4X16N", "DGBROSSA4X16N", 10, 4),
            ("44SRED150+20NDREGIN", "DONNAREGINA170", 20, 1),
            ("DGSUPERGIN4X16", "DGSUPERGIN4X16", 4, 4),
            ("GINSENGWEB4X18", "8034028333880", 3, 1),
            ("AMGINSENG6X16", "AMGINSENG6X16", 15, 6),
        ),
    },
    "283449": {
        "punto_vendita": "via-vespri",
        "righe": (
            ("44BRED150N", "8034028330827", 20, 1),
            ("44BBLU150N", "8034028330506", 20, 1),
            ("REBNERA100N", "8034028330636", 16, 1),
            ("REBBLU100N", "8034028330476", 16, 1),
            ("AMSNERA100NDONCARLO", "8034028330674", 48, 1),
            ("AMSRED100NDONCARLO", "8034028330698", 48, 1),
            ("AMSBLU100NDONCARLO", "8034028330483", 48, 1),
            ("AMSDEK100NDONCARLO", "AMSDEK100NDONCARLO", 16, 1),
            ("AMCOMPOSTABORO100N", "8034028338014", 16, 1),
            ("DGSUPERGIN4X16", "DGSUPERGIN4X16", 4, 4),
            ("DGNOCCIOLONE4X16", "DGNOCCIOLONE4X16", 4, 4),
            ("GINSENGWEB4X18", "8034028333880", 4, 1),
            ("AMGINSENG6X16", "AMGINSENG6X16", 15, 6),
        ),
    },
}


# Ogni riga contiene: SKU del documento, SKU interno, colli ricevuti e
# confezioni vendibili per collo. Le macchine omaggio e le pedane non sono
# articoli di magazzino e sono quindi escluse.
FATTURE_BORBONE_SETTEMBRE_2026 = {
    "1000022858": {
        "punto_vendita": "via-pepoli",
        "sostituisci_se_almeno": None,
        "righe": (
            ("REBRED100N", "8034028336706", 32, 1),
            ("REBBLU100N", "8034028330476", 16, 1),
            ("REBNERA100N", "8034028330636", 16, 1),
            ("REBDEK100N", "REBDEK100N", 16, 1),
            ("AMSNERA100NDONCARLO", "8034028330674", 16, 1),
            ("AMSRED100NDONCARLO", "8034028330698", 16, 1),
            ("AMSBLU100NDONCARLO", "8034028330483", 64, 1),
            ("AMCOMPOSTABORO100N", "8034028338014", 16, 1),
            ("44BBLU150N", "8034028330506", 50, 1),
            ("44BRED150N", "8034028330827", 30, 1),
            ("44BDEK150N", "44BDEK150N", 26, 1),
            ("DGBBLU50N", "8055176432317", 40, 1),
            ("DGBRED50N", "8055176432348", 20, 1),
            ("BLTBBLU100N", "BLTBBLU100N", 20, 1),
            ("BLTBRED100N", "BLTBRED100N", 20, 1),
            ("LVBROSSA100N", "LVBROSSA100N", 5, 1),
            ("THELIMON4X16DOLCEGUS", "THELIMON4X16DOLCEGUS", 4, 4),
            ("DGCAMOMILLA4X16", "DGCAMOMILLA4X16", 4, 4),
            ("44SRED150+20NDREGIN", "DONNAREGINA170", 20, 1),
        ),
    },
    "1000022859": {
        "punto_vendita": "via-vespri",
        # Il conteggio presente a Valderice contiene vecchi valori provvisori
        # molto alti. Per i soli pacchi con almeno 70 unita, la quantita della
        # fattura sostituisce la giacenza anziche sommarsi ad essa.
        "sostituisci_se_almeno": 70,
        "righe": (
            ("44BNERA150N", "8034028330780", 30, 1),
            ("44BRED150N", "8034028330827", 25, 1),
            ("44BBLU150N", "8034028330506", 45, 1),
            ("44BDEK150N", "44BDEK150N", 26, 1),
            ("REBNERA100N", "8034028330636", 16, 1),
            ("REBBLU100N", "8034028330476", 16, 1),
            ("AMSNERA100NDONCARLO", "8034028330674", 16, 1),
            ("AMSRED100NDONCARLO", "8034028330698", 16, 1),
            ("AMSBLU100NDONCARLO", "8034028330483", 32, 1),
            ("AMSDEK100NDONCARLO", "AMSDEK100NDONCARLO", 16, 1),
            ("AMCOMPOSTABORO100N", "8034028338014", 16, 1),
            ("DGBBLU50N", "8055176432317", 20, 1),
            ("DGBRED50N", "8055176432348", 10, 1),
            ("BLTBBLU100N", "BLTBBLU100N", 20, 1),
            ("BLTBRED100N", "BLTBRED100N", 10, 1),
            ("DGSUPERGIN4X16", "DGSUPERGIN4X16", 4, 4),
            ("DGNOCCIOLONE4X16", "DGNOCCIOLONE4X16", 4, 4),
            ("GINSENGWEB4X18", "8034028333880", 4, 1),
            ("44SRED150+20NDREGIN", "DONNAREGINA170", 20, 1),
        ),
    },
}


@click.command("create-admin")
@with_appcontext
def create_admin() -> None:
    """Crea l'amministratore iniziale leggendo le variabili ADMIN_* dall'ambiente."""
    admin_role = Role.query.filter_by(nome=RUOLO_ADMIN).first()
    if admin_role and User.query.filter_by(ruolo_id=admin_role.id).first():
        click.echo("Esiste già almeno un amministratore.")
        return

    username = os.getenv("ADMIN_USERNAME")

    if username and User.query.filter_by(username=username).first():
        click.echo("L'amministratore iniziale esiste già.")
        return

    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    missing = [
        name
        for name, value in {
            "ADMIN_USERNAME": username,
            "ADMIN_EMAIL": email,
            "ADMIN_PASSWORD": password,
        }.items()
        if not value
    ]
    if missing:
        raise click.ClickException(
            "Imposta " + ", ".join(missing) + " prima di creare il primo amministratore."
        )

    if User.query.filter_by(email=email).first():
        raise click.ClickException("Esiste già un utente con questa email.")

    if not admin_role:
        admin_role = Role(nome=RUOLO_ADMIN, descrizione="Accesso completo")
        db.session.add(admin_role)
        db.session.flush()

    admin = User(username=username, email=email, ruolo_id=admin_role.id, attivo=True)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Amministratore '{username}' creato.")


@click.command("import-catalogo-reale")
@with_appcontext
def import_catalogo_reale() -> None:
    """Importa una sola volta il catalogo iniziale dai listini forniti."""
    creati, presenti = sync_catalogo_reale()
    click.echo(f"Catalogo reale: {creati} prodotti creati, {presenti} gia presenti.")
    singole_create, singole_aggiornate, singole_ignorate = sync_varianti_singole()
    click.echo(
        "Varianti singole: "
        f"{singole_create} create, {singole_aggiornate} aggiornate, "
        f"{singole_ignorate} ignorate."
    )


@click.command("imposta-giacenza-ultimo-import")
@click.option(
    "--quantita",
    type=click.IntRange(min=0),
    default=30,
    show_default=True,
    help="Giacenza obiettivo per articolo e punto vendita.",
)
@with_appcontext
def imposta_giacenza_ultimo_import(quantita: int) -> None:
    """Rettifica in modo tracciato gli articoli dell'ultimo import Borbone."""
    prodotti = Product.query.filter(
        Product.sku_barcode.in_(ULTIMO_IMPORT_BORBONE_SKU)
    ).all()
    prodotti_per_sku = {prodotto.sku_barcode: prodotto for prodotto in prodotti}
    mancanti = [
        sku for sku in ULTIMO_IMPORT_BORBONE_SKU if sku not in prodotti_per_sku
    ]
    if mancanti:
        raise click.ClickException(
            "Articoli non trovati: " + ", ".join(mancanti)
        )

    punti_vendita = StoreLocation.query.filter_by(attivo=True).order_by(
        StoreLocation.id.asc()
    ).all()
    if not punti_vendita:
        raise click.ClickException("Nessun punto vendita attivo configurato.")

    operatore = User.query.filter(
        func.lower(User.username) == "admin", User.attivo.is_(True)
    ).first()
    if not operatore:
        operatore = User.query.filter_by(attivo=True).order_by(User.id.asc()).first()
    if not operatore:
        raise click.ClickException("Nessun operatore attivo disponibile per la rettifica.")

    movimenti_creati = 0
    for punto_vendita in punti_vendita:
        for sku in ULTIMO_IMPORT_BORBONE_SKU:
            prodotto = prodotti_per_sku[sku]
            delta = quantita - quantita_fisica(prodotto, punto_vendita.id)
            if delta == 0:
                continue
            registra_movimento(
                prodotto=prodotto,
                tipo_movimento="rettifica",
                quantita=delta,
                operatore_id=operatore.id,
                motivo=f"Impostazione giacenza ultimo import a {quantita}",
                riferimento_entita="ultimo-import-borbone-2026",
                punto_vendita_id=punto_vendita.id,
            )
            movimenti_creati += 1

    registra_attivita(
        utente_id=operatore.id,
        azione="rettifica_ultimo_import",
        entita_tipo="catalogo",
        dettagli=(
            f"{len(prodotti)} articoli impostati a {quantita} in "
            f"{len(punti_vendita)} punti vendita; {movimenti_creati} rettifiche."
        ),
    )
    db.session.commit()
    click.echo(
        f"Giacenza {quantita}: {len(prodotti)} articoli, "
        f"{len(punti_vendita)} punti vendita, {movimenti_creati} rettifiche."
    )


@click.command("riconcilia-giacenze-20-luglio")
@with_appcontext
def riconcilia_giacenze_20_luglio() -> None:
    """Allinea alle conte fisiche del 20/07/2026 lasciando una traccia movimenti."""
    punti_vendita = {
        punto.codice: punto
        for punto in StoreLocation.query.filter(
            StoreLocation.codice.in_(GIACENZE_20_LUGLIO)
        ).all()
    }
    negozi_mancanti = sorted(set(GIACENZE_20_LUGLIO) - set(punti_vendita))
    if negozi_mancanti:
        raise click.ClickException(
            "Punti vendita non trovati: " + ", ".join(negozi_mancanti)
        )

    sku_richiesti = {
        riferimento
        for conteggio in GIACENZE_20_LUGLIO.values()
        for riferimento in conteggio
    }
    prodotti = Product.query.filter(Product.sku_barcode.in_(sku_richiesti)).all()
    prodotti_per_riferimento = {
        prodotto.sku_barcode: prodotto for prodotto in prodotti
    }
    riferimenti_richiesti = {
        riferimento
        for conteggio in GIACENZE_20_LUGLIO.values()
        for riferimento in conteggio
    }
    articoli_mancanti = sorted(
        riferimenti_richiesti - set(prodotti_per_riferimento)
    )
    if articoli_mancanti:
        raise click.ClickException(
            "Articoli non trovati: " + ", ".join(articoli_mancanti)
        )

    operatore = User.query.filter(
        func.lower(User.username) == "admin", User.attivo.is_(True)
    ).first()
    if not operatore:
        raise click.ClickException("Utente admin attivo non disponibile.")

    movimenti_creati = 0
    articoli_invariati = 0
    for codice_negozio, conteggio in GIACENZE_20_LUGLIO.items():
        punto_vendita = punti_vendita[codice_negozio]
        for riferimento, quantita_obiettivo in conteggio.items():
            prodotto = prodotti_per_riferimento[riferimento]
            delta = quantita_obiettivo - quantita_fisica(
                prodotto, punto_vendita.id
            )
            if delta == 0:
                articoli_invariati += 1
                continue
            registra_movimento(
                prodotto=prodotto,
                tipo_movimento="rettifica",
                quantita=delta,
                operatore_id=operatore.id,
                motivo=(
                    "Riconciliazione con conteggio fisico del 20/07/2026 "
                    f"(obiettivo {quantita_obiettivo})"
                ),
                riferimento_entita="inventario-fisico:2026-07-20",
                punto_vendita_id=punto_vendita.id,
            )
            movimenti_creati += 1

    registra_attivita(
        utente_id=operatore.id,
        azione="riconciliazione_inventario",
        entita_tipo="magazzino",
        entita_id="2026-07-20",
        dettagli=(
            f"{len(riferimenti_richiesti)} prodotti conteggiati in "
            f"{len(GIACENZE_20_LUGLIO)} punti vendita; "
            f"{movimenti_creati} rettifiche, {articoli_invariati} invariati."
        ),
    )
    db.session.commit()
    click.echo(
        f"Riconciliazione completata: {movimenti_creati} rettifiche, "
        f"{articoli_invariati} articoli gia corretti."
    )


@click.command("carica-ordini-borbone-luglio-2026")
@with_appcontext
def carica_ordini_borbone_luglio_2026() -> None:
    """Carica in modo idempotente gli ordini Borbone 283447 e 283449."""
    sync_catalogo_reale()
    sync_varianti_singole()

    punti_vendita = {
        punto.codice: punto
        for punto in StoreLocation.query.filter(
            StoreLocation.codice.in_(
                {
                    ordine["punto_vendita"]
                    for ordine in ORDINI_BORBONE_LUGLIO_2026.values()
                }
            )
        ).all()
    }
    negozi_mancanti = sorted(
        {
            ordine["punto_vendita"]
            for ordine in ORDINI_BORBONE_LUGLIO_2026.values()
        }
        - set(punti_vendita)
    )
    if negozi_mancanti:
        raise click.ClickException(
            "Punti vendita non trovati: " + ", ".join(negozi_mancanti)
        )

    sku_richiesti = {
        sku_interno
        for ordine in ORDINI_BORBONE_LUGLIO_2026.values()
        for _, sku_interno, _, _ in ordine["righe"]
    }
    prodotti = Product.query.filter(Product.sku_barcode.in_(sku_richiesti)).all()
    prodotti_per_sku = {prodotto.sku_barcode: prodotto for prodotto in prodotti}
    articoli_mancanti = sorted(sku_richiesti - set(prodotti_per_sku))
    if articoli_mancanti:
        raise click.ClickException(
            "Articoli non trovati: " + ", ".join(articoli_mancanti)
        )

    operatore = User.query.filter(
        func.lower(User.username) == "admin", User.attivo.is_(True)
    ).first()
    if not operatore:
        raise click.ClickException("Utente admin attivo non disponibile.")

    movimenti_creati = 0
    righe_gia_caricate = 0
    for numero_documento, ordine in ORDINI_BORBONE_LUGLIO_2026.items():
        punto_vendita = punti_vendita[ordine["punto_vendita"]]
        riferimento = f"ordine-borbone:{numero_documento}"
        movimenti_documento = 0
        for sku_documento, sku_interno, colli, confezioni_per_collo in ordine["righe"]:
            prodotto = prodotti_per_sku[sku_interno]
            gia_caricato = InventoryMovement.query.filter_by(
                tipo_movimento="carico",
                prodotto_id=prodotto.id,
                punto_vendita_id=punto_vendita.id,
                riferimento_entita=riferimento,
            ).first()
            if gia_caricato:
                righe_gia_caricate += 1
                continue

            quantita_vendibile = colli * confezioni_per_collo
            registra_movimento(
                prodotto=prodotto,
                tipo_movimento="carico",
                quantita=quantita_vendibile,
                operatore_id=operatore.id,
                motivo=f"Carico ordine Caffe Borbone n. {numero_documento}",
                riferimento_entita=riferimento,
                note=(
                    f"SKU documento {sku_documento}: {colli} CT x "
                    f"{confezioni_per_collo} confezione/i vendibili"
                ),
                punto_vendita_id=punto_vendita.id,
            )
            movimenti_creati += 1
            movimenti_documento += 1

        if movimenti_documento:
            registra_attivita(
                utente_id=operatore.id,
                azione="carico_ordine_fornitore",
                entita_tipo="ordine_fornitore",
                entita_id=numero_documento,
                dettagli=(
                    f"Ordine Borbone {numero_documento}: "
                    f"{movimenti_documento} righe caricate in "
                    f"{punto_vendita.nome}."
                ),
            )

    db.session.commit()
    click.echo(
        f"Ordini Borbone caricati: {movimenti_creati} movimenti creati, "
        f"{righe_gia_caricate} righe gia presenti."
    )


@click.command("carica-fatture-borbone-settembre-2026")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Mostra le variazioni previste senza modificare il database.",
)
@click.option(
    "--skip-catalog-sync",
    is_flag=True,
    hidden=True,
)
@with_appcontext
def carica_fatture_borbone_settembre_2026(
    dry_run: bool, skip_catalog_sync: bool
) -> None:
    """Carica in modo idempotente le fatture Borbone del 09/09/2026."""
    if not skip_catalog_sync and not dry_run:
        sync_catalogo_reale()
        sync_varianti_singole()

    punti_vendita = {
        punto.codice: punto
        for punto in StoreLocation.query.filter(
            StoreLocation.codice.in_(
                {
                    fattura["punto_vendita"]
                    for fattura in FATTURE_BORBONE_SETTEMBRE_2026.values()
                }
            )
        ).all()
    }
    negozi_mancanti = sorted(
        {
            fattura["punto_vendita"]
            for fattura in FATTURE_BORBONE_SETTEMBRE_2026.values()
        }
        - set(punti_vendita)
    )
    if negozi_mancanti:
        raise click.ClickException(
            "Punti vendita non trovati: " + ", ".join(negozi_mancanti)
        )

    sku_richiesti = {
        sku_interno
        for fattura in FATTURE_BORBONE_SETTEMBRE_2026.values()
        for _, sku_interno, _, _ in fattura["righe"]
    }
    prodotti = Product.query.filter(Product.sku_barcode.in_(sku_richiesti)).all()
    prodotti_per_sku = {prodotto.sku_barcode: prodotto for prodotto in prodotti}
    articoli_mancanti = sorted(sku_richiesti - set(prodotti_per_sku))
    if articoli_mancanti:
        raise click.ClickException(
            "Articoli non trovati: " + ", ".join(articoli_mancanti)
        )

    singole_non_ammesse = sorted(
        prodotto.sku_barcode
        for prodotto in prodotti
        if prodotto.is_variante_singola
    )
    if singole_non_ammesse:
        raise click.ClickException(
            "Le fatture contengono varianti singole non caricabili: "
            + ", ".join(singole_non_ammesse)
        )

    operatore = User.query.filter(
        func.lower(User.username) == "admin", User.attivo.is_(True)
    ).first()
    if not operatore:
        raise click.ClickException("Utente admin attivo non disponibile.")

    movimenti_creati = 0
    righe_gia_caricate = 0
    rettifiche_create = 0
    try:
        for numero_documento, fattura in FATTURE_BORBONE_SETTEMBRE_2026.items():
            punto_vendita = punti_vendita[fattura["punto_vendita"]]
            riferimento = f"fattura-borbone:{numero_documento}"
            soglia_sostituzione = fattura["sostituisci_se_almeno"]
            movimenti_documento = 0

            click.echo(
                f"Fattura {numero_documento} - {punto_vendita.nome}:"
            )
            for sku_documento, sku_interno, colli, confezioni_per_collo in fattura["righe"]:
                prodotto = prodotti_per_sku[sku_interno]
                gia_caricato = InventoryMovement.query.filter_by(
                    prodotto_id=prodotto.id,
                    punto_vendita_id=punto_vendita.id,
                    riferimento_entita=riferimento,
                ).first()
                if gia_caricato:
                    righe_gia_caricate += 1
                    click.echo(f"  GIA CARICATO {prodotto.nome}")
                    continue

                quantita_fattura = colli * confezioni_per_collo
                quantita_corrente = quantita_fisica(prodotto, punto_vendita.id)
                sostituisci = (
                    soglia_sostituzione is not None
                    and quantita_corrente >= soglia_sostituzione
                )
                if sostituisci:
                    tipo_movimento = "rettifica"
                    quantita_movimento = quantita_fattura - quantita_corrente
                    quantita_finale = quantita_fattura
                    azione = (
                        f"RETTIFICA {quantita_corrente} -> {quantita_finale}"
                    )
                else:
                    tipo_movimento = "carico"
                    quantita_movimento = quantita_fattura
                    quantita_finale = quantita_corrente + quantita_fattura
                    azione = (
                        f"CARICO +{quantita_fattura}: "
                        f"{quantita_corrente} -> {quantita_finale}"
                    )

                click.echo(f"  {azione} - {prodotto.nome}")
                if dry_run:
                    continue

                registra_movimento(
                    prodotto=prodotto,
                    tipo_movimento=tipo_movimento,
                    quantita=quantita_movimento,
                    operatore_id=operatore.id,
                    motivo=(
                        f"Rettifica da fattura Caffe Borbone n. {numero_documento}"
                        if sostituisci
                        else f"Carico fattura Caffe Borbone n. {numero_documento}"
                    ),
                    riferimento_entita=riferimento,
                    note=(
                        f"SKU documento {sku_documento}: {colli} CT x "
                        f"{confezioni_per_collo} confezione/i vendibili; "
                        f"giacenza precedente {quantita_corrente}, "
                        f"giacenza finale {quantita_finale}."
                    ),
                    punto_vendita_id=punto_vendita.id,
                )
                movimenti_creati += 1
                movimenti_documento += 1
                if sostituisci:
                    rettifiche_create += 1

            if movimenti_documento:
                registra_attivita(
                    utente_id=operatore.id,
                    azione="carico_fattura_fornitore",
                    entita_tipo="fattura_fornitore",
                    entita_id=numero_documento,
                    dettagli=(
                        f"Fattura Borbone {numero_documento}: "
                        f"{movimenti_documento} righe registrate in "
                        f"{punto_vendita.nome}."
                    ),
                )

        if dry_run:
            db.session.rollback()
            click.echo(
                "Anteprima completata: il database non e stato modificato."
            )
            return

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    click.echo(
        "Fatture Borbone settembre caricate: "
        f"{movimenti_creati} movimenti creati "
        f"({rettifiche_create} rettifiche), "
        f"{righe_gia_caricate} righe gia presenti."
    )
