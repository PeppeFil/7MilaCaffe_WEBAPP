from datetime import datetime

from app.extensions import db


class ShopPreference(db.Model):
    __tablename__ = "shop_preferences"

    id = db.Column(db.Integer, primary_key=True)
    chiave = db.Column(db.String(80), nullable=False, unique=True, index=True)
    valore = db.Column(db.String(255), nullable=False, default="")
    descrizione = db.Column(db.String(255))
    data_creazione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_aggiornamento = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
