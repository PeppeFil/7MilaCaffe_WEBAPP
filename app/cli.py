import os

import click
from flask.cli import with_appcontext
from sqlalchemy import func

from .extensions import db
from .models import Product, Role, StoreLocation, User
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
