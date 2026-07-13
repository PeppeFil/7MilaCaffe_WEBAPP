from datetime import datetime

from app.extensions import db


class StoreInventory(db.Model):
    __tablename__ = "store_inventory"
    __table_args__ = (
        db.UniqueConstraint("punto_vendita_id", "prodotto_id", name="uq_store_inventory_store_product"),
        db.Index("ix_store_inventory_store_stock", "punto_vendita_id", "quantita_disponibile"),
    )

    id = db.Column(db.Integer, primary_key=True)
    punto_vendita_id = db.Column(
        db.Integer, db.ForeignKey("store_locations.id"), nullable=False, index=True
    )
    prodotto_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantita_disponibile = db.Column(db.Integer, nullable=False, default=0)
    quantita_minima_alert = db.Column(db.Integer, nullable=False, default=0)
    data_creazione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_aggiornamento = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    punto_vendita = db.relationship("StoreLocation", back_populates="giacenze", lazy="joined")
    prodotto = db.relationship("Product", back_populates="giacenze_punti_vendita", lazy="joined")
