import os

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import Role, User
from .models.constants import RUOLO_ADMIN
from .services.catalog_service import sync_catalogo_reale, sync_varianti_singole


def register_commands(app) -> None:
    app.cli.add_command(create_admin)
    app.cli.add_command(import_catalogo_reale)


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
