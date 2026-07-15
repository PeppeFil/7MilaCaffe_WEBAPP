from datetime import datetime
from decimal import Decimal

from app.extensions import db


class VatRate(db.Model):
    __tablename__ = "vat_rates"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True, index=True)
    aliquota = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal("22.00"))
    descrizione = db.Column(db.String(255))
    attiva = db.Column(db.Boolean, nullable=False, default=True, index=True)
    predefinita = db.Column(db.Boolean, nullable=False, default=False, index=True)
    data_creazione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_aggiornamento = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    vendite = db.relationship("Sale", back_populates="vat_rate", lazy="select")
    prodotti = db.relationship("Product", back_populates="vat_rate", lazy="select")
