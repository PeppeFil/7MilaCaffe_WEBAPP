from datetime import datetime

from app.extensions import db


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"
    __table_args__ = (
        db.Index("ix_activity_logs_data_azione", "data_ora", "azione"),
    )

    id = db.Column(db.Integer, primary_key=True)
    utente_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    azione = db.Column(db.String(120), nullable=False)
    entita_tipo = db.Column(db.String(60), nullable=False)
    entita_id = db.Column(db.String(60), nullable=True)
    dettagli = db.Column(db.Text)
    data_ora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    utente = db.relationship("User", back_populates="activity_logs", lazy="joined")
