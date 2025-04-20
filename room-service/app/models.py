from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON  # Import JSON type for PostgreSQL

db = SQLAlchemy()

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    amenities = db.Column(JSON, nullable=True)  # New column for amenities
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Room {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'capacity': self.capacity,
            'description': self.description,
            'amenities': self.amenities,  # Include amenities in the dictionary
            'created_at': self.created_at.isoformat()
        }

class BlackoutPeriod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'reason': self.reason
        }
