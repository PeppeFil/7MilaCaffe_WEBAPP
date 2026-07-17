from decimal import Decimal

from app.extensions import db


class SaleItem(db.Model):
    __tablename__ = "sale_items"
    __table_args__ = (
        db.Index("ix_sale_items_sale_prodotto", "vendita_id", "prodotto_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    vendita_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False, index=True)
    prodotto_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantita = db.Column(db.Integer, nullable=False)
    prezzo_unitario = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    subtotale = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    totale_netto = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    aliquota_iva_snapshot = db.Column(
        db.Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )
    totale_iva = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    costo_unitario_snapshot = db.Column(
        db.Numeric(14, 6), nullable=False, default=Decimal("0.00")
    )
    margine_riga = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    vendita = db.relationship("Sale", back_populates="righe", lazy="joined")
    prodotto = db.relationship("Product", back_populates="righe_vendita", lazy="joined")
