from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import numpy as np
import pickle

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    custom_data = db.Column(db.String(200))
    face_encoding = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    attendances = db.relationship('Attendance', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_face_encoding(self, encoding):
        self.face_encoding = pickle.dumps(encoding)
    
    def get_face_encoding(self):
        return pickle.loads(self.face_encoding)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    @classmethod
    def get_recent_attendance(cls, user_id, seconds=300):
        """Check if user has attendance record in the last X seconds"""
        cutoff = datetime.utcnow().timestamp() - seconds
        recent = cls.query.filter(
            cls.user_id == user_id,
            cls.timestamp > datetime.fromtimestamp(cutoff)
        ).first()
        return recent is not None
