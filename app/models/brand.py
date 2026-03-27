from datetime import datetime

from app.extensions import db


class Brand(db.Model):
    __tablename__ = "brands"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True, index=True)
    descrizione = db.Column(db.String(255))
    data_creazione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_aggiornamento = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    prodotti = db.relationship("Product", back_populates="brand", lazy="selectin")
