from datetime import datetime

from app.extensions import db


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True, index=True)
    email = db.Column(db.String(120))
    telefono = db.Column(db.String(40))
    indirizzo = db.Column(db.String(255))
    note = db.Column(db.Text)
    data_creazione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_aggiornamento = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    prodotti = db.relationship("Product", back_populates="fornitore", lazy="selectin")
