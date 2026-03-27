from datetime import datetime

from app.extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True, index=True)
    descrizione = db.Column(db.String(255))
    data_creazione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_aggiornamento = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    prodotti = db.relationship("Product", back_populates="categoria", lazy="selectin")
