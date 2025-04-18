from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False) # Foreign key to User (conceptually)
    room_id = db.Column(db.Integer, nullable=False) # Foreign key to Room (conceptually)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    purpose = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Add constraint to prevent overlapping reservations for the same room
    __table_args__ = (
        db.CheckConstraint('end_time > start_time', name='check_start_end_time'),
        # Overlap check might be better handled in application logic or complex SQL constraint
    )

    def __repr__(self):
        return f'<Reservation {self.id} for Room {self.room_id} by User {self.user_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'room_id': self.room_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'purpose': self.purpose,
            'created_at': self.created_at.isoformat()
        }
