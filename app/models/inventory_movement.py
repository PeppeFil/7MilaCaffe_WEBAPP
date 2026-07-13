from datetime import datetime
from decimal import Decimal

from app.extensions import db


class InventoryMovement(db.Model):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        db.Index("ix_inventory_movements_data_tipo", "data_ora", "tipo_movimento"),
        db.Index("ix_inventory_movements_prodotto", "prodotto_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tipo_movimento = db.Column(db.String(40), nullable=False, index=True)
    data_ora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    prodotto_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantita = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(255))
    costo_unitario = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    operatore_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    punto_vendita_id = db.Column(
        db.Integer, db.ForeignKey("store_locations.id"), nullable=True, index=True
    )
    riferimento_entita = db.Column(db.String(80), index=True)
    note = db.Column(db.Text)

    prodotto = db.relationship("Product", back_populates="movimenti_magazzino", lazy="joined")
    operatore = db.relationship("User", back_populates="movimenti", lazy="joined")
    punto_vendita = db.relationship(
        "StoreLocation", back_populates="movimenti", lazy="joined"
    )
