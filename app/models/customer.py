from datetime import datetime

from app.extensions import db


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    cognome = db.Column(db.String(100), index=True)
    ragione_sociale = db.Column(db.String(140), index=True)
    email = db.Column(db.String(120), index=True)
    telefono = db.Column(db.String(40), index=True)
    codice_fiscale = db.Column(db.String(20), unique=True, index=True)
    partita_iva = db.Column(db.String(20), unique=True, index=True)
    indirizzo = db.Column(db.String(255))
    citta = db.Column(db.String(100), index=True)
    compatibilita_preferita_id = db.Column(
        db.Integer,
        db.ForeignKey("compatibilities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    note = db.Column(db.Text)
    attivo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    data_creazione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_aggiornamento = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    vendite = db.relationship("Sale", back_populates="customer", lazy="select")
    compatibilita_preferita = db.relationship("Compatibility", lazy="joined")

    @property
    def display_name(self) -> str:
        if self.ragione_sociale:
            return self.ragione_sociale
        full_name = f"{self.nome} {self.cognome or ''}".strip()
        return full_name or self.nome
