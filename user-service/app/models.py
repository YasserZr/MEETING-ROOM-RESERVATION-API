from datetime import datetime
from . import db  # Import db from __init__.py
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func

class User(db.Model):
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
