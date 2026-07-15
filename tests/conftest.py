import pytest

from app import create_app
from app.extensions import db
from app.models import Brand, Category, Compatibility, Product, Role, Supplier, User, VatRate
from app.models.constants import RUOLO_ADMIN, RUOLO_OPERATORE


@pytest.fixture
def app():
    app = create_app("testing")
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()

        ruolo_admin = Role(nome=RUOLO_ADMIN, descrizione="Admin")
        ruolo_operatore = Role(nome=RUOLO_OPERATORE, descrizione="Operatore")
        db.session.add_all([ruolo_admin, ruolo_operatore])
        db.session.flush()

        admin = User(username="admin", email="admin@test.local", ruolo_id=ruolo_admin.id, attivo=True)
        admin.set_password("admin123")
        operatore = User(
            username="operatore",
            email="operatore@test.local",
            ruolo_id=ruolo_operatore.id,
            attivo=True,
        )
        operatore.set_password("operator123")

        categoria = Category(nome="Capsule")
        marca = Brand(nome="Marca Test")
        compatibilita = Compatibility(nome="Nespresso")
        iva = VatRate(nome="IVA 22%", aliquota=22, attiva=True, predefinita=True)
        fornitore = Supplier(nome="Fornitore Test")
        db.session.add_all([admin, operatore, categoria, marca, compatibilita, iva, fornitore])
        db.session.flush()

        prodotto = Product(
            nome="Capsule Test",
            categoria_id=categoria.id,
            marca_id=marca.id,
            vat_rate_id=iva.id,
            compatibilita_id=compatibilita.id,
            formato_confezione="10 pz",
            prezzo_acquisto=0.2,
            prezzo_vendita=0.4,
            quantita_disponibile=20,
            quantita_minima_alert=5,
            sku_barcode="TEST-001",
            fornitore_id=fornitore.id,
            attivo=True,
        )
        db.session.add(prodotto)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
