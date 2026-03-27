from datetime import datetime
from decimal import Decimal

from app.extensions import db


class Sale(db.Model):
    __tablename__ = "sales"
    __table_args__ = (
        db.Index("ix_sales_data_ora_stato", "data_ora", "stato"),
        db.Index("ix_sales_pagamento", "metodo_pagamento"),
    )

    id = db.Column(db.Integer, primary_key=True)
    data_ora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    totale_lordo = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    sconto_tipo = db.Column(db.String(20), nullable=False, default="nessuno")
    sconto_valore = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    totale_netto = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    metodo_pagamento = db.Column(db.String(30), nullable=False, default="contanti")
    note_cliente = db.Column(db.String(255))
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), index=True)
    vat_rate_id = db.Column(db.Integer, db.ForeignKey("vat_rates.id"), index=True)
    aliquota_iva_snapshot = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    totale_iva = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    operatore_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    stato = db.Column(db.String(20), nullable=False, default="completata", index=True)
    margine_stimato = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    operatore = db.relationship("User", back_populates="vendite", lazy="joined")
    customer = db.relationship("Customer", back_populates="vendite", lazy="joined")
    vat_rate = db.relationship("VatRate", back_populates="vendite", lazy="joined")
    righe = db.relationship(
        "SaleItem",
        back_populates="vendita",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
