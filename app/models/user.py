from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.Index("ix_users_username_email", "username", "email"),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), nullable=False, unique=True, index=True)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    ruolo_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    punto_vendita_predefinito_id = db.Column(
        db.Integer, db.ForeignKey("store_locations.id"), index=True
    )
    attivo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    data_creazione = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_aggiornamento = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    ruolo = db.relationship("Role", back_populates="utenti", lazy="joined")
    punto_vendita_predefinito = db.relationship(
        "StoreLocation", back_populates="utenti_predefiniti", lazy="joined"
    )
    vendite = db.relationship("Sale", back_populates="operatore", lazy="select")
    movimenti = db.relationship(
        "InventoryMovement", back_populates="operatore", lazy="select"
    )
    activity_logs = db.relationship("ActivityLog", back_populates="utente", lazy="select")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def has_role(self, *allowed_roles: str) -> bool:
        return bool(self.ruolo and self.ruolo.nome in allowed_roles)
