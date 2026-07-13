from datetime import datetime
from decimal import Decimal

from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        db.Index("ix_products_nome_marca", "nome", "marca_id"),
        db.Index("ix_products_categoria_attivo", "categoria_id", "attivo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(140), nullable=False, index=True)
    categoria_id = db.Column(
        db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True
    )
    marca_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False, index=True)
    compatibilita_id = db.Column(
        db.Integer, db.ForeignKey("compatibilities.id"), nullable=True, index=True
    )
    formato_confezione = db.Column(db.String(120))
    prezzo_acquisto = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    prezzo_vendita = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    quantita_disponibile = db.Column(db.Integer, nullable=False, default=0, index=True)
    quantita_minima_alert = db.Column(db.Integer, nullable=False, default=0)
    sku_barcode = db.Column(db.String(80), unique=True, index=True)
    immagine_url = db.Column(db.String(255))
    fornitore_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), index=True)
    note = db.Column(db.Text)
    attivo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    data_creazione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_aggiornamento = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    categoria = db.relationship("Category", back_populates="prodotti", lazy="joined")
    brand = db.relationship("Brand", back_populates="prodotti", lazy="joined")
    compatibility = db.relationship("Compatibility", back_populates="prodotti", lazy="joined")
    fornitore = db.relationship("Supplier", back_populates="prodotti", lazy="joined")
    righe_vendita = db.relationship("SaleItem", back_populates="prodotto", lazy="selectin")
    movimenti_magazzino = db.relationship(
        "InventoryMovement", back_populates="prodotto", lazy="selectin"
    )
    giacenze_punti_vendita = db.relationship(
        "StoreInventory", back_populates="prodotto", lazy="selectin", cascade="all, delete-orphan"
    )

    @property
    def stato_disponibilita(self) -> str:
        if self.quantita_disponibile <= 0:
            return "esaurito"
        if self.quantita_disponibile <= self.quantita_minima_alert:
            return "quasi esaurito"
        return "disponibile"
