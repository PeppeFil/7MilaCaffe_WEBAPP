from datetime import datetime

from app.extensions import db


class StoreLocation(db.Model):
    __tablename__ = "store_locations"

    id = db.Column(db.Integer, primary_key=True)
    codice = db.Column(db.String(40), nullable=False, unique=True, index=True)
    nome = db.Column(db.String(120), nullable=False)
    indirizzo = db.Column(db.String(255), nullable=False)
    cap = db.Column(db.String(10), nullable=False)
    comune = db.Column(db.String(100), nullable=False)
    provincia = db.Column(db.String(10), nullable=False)
    ragione_sociale = db.Column(db.String(160), nullable=False)
    partita_iva = db.Column(db.String(20), nullable=False, unique=True)
    attivo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    data_creazione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_aggiornamento = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    utenti_predefiniti = db.relationship(
        "User", back_populates="punto_vendita_predefinito", lazy="selectin"
    )
    giacenze = db.relationship("StoreInventory", back_populates="punto_vendita", lazy="noload")
    vendite = db.relationship("Sale", back_populates="punto_vendita", lazy="selectin")
    movimenti = db.relationship(
        "InventoryMovement", back_populates="punto_vendita", lazy="selectin"
    )

    @property
    def indirizzo_completo(self) -> str:
        return f"{self.indirizzo}, {self.cap} {self.comune} ({self.provincia})"
