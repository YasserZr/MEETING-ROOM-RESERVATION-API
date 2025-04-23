from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from . import db  # Import db at the top to avoid delayed initialization issues

class User(db.Model):  # Ensure User inherits from db.Model
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    email = Column(String(128), nullable=False, unique=True)
    username = Column(String(128), nullable=False, unique=True)
    password = Column(String(256), nullable=False)  # Updated length to 256
    full_name = Column(String(128), nullable=True)
    role = Column(String(128), nullable=False, default="user")
    created_at = Column(DateTime, nullable=False, server_default=func.now())  # Automatically set current timestamp

    def __repr__(self):
        return f'<User {self.username}>'
        
    def to_dict(self):
        """Convert User object to a dictionary for JSON serialization."""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'full_name': self.full_name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
