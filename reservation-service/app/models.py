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
    num_attendees = db.Column(db.Integer, nullable=False)  # New column for number of attendees
    description = db.Column(db.String(255), nullable=True)  # Add description field
    attendees = db.Column(db.ARRAY(db.String), nullable=True)  # Add attendees field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Add constraint to prevent overlapping reservations for the same room
    __table_args__ = (
        db.CheckConstraint('end_time > start_time', name='check_start_end_time'),
        db.CheckConstraint('num_attendees > 0', name='check_positive_num_attendees'),  # Ensure positive attendees
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
            'num_attendees': self.num_attendees,  # Include in the dictionary
            'description': self.description,  # Include description in the dictionary
            'attendees': self.attendees,  # Include attendees in the dictionary
            'created_at': self.created_at.isoformat()
        }
