from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import numpy as np
import pickle
import os
import pytz
from config import Config
db = SQLAlchemy()

def get_current_time():
    """Return current time in Egypt timezone"""
    return datetime.now(pytz.timezone(Config.TIMEZONE)).replace(tzinfo=None)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(200), nullable=False)
    custom_data = db.Column(db.String(200))
    face_encoding = db.Column(db.LargeBinary, nullable=False)
    profile_pic = db.Column(db.LargeBinary, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_current_time)
    attendances = db.relationship('Attendance', backref='user', lazy=True, cascade="all, delete-orphan")

    # New relationships
    enrollments = db.relationship('Enrollment', backref='student', lazy=True, cascade="all, delete-orphan")
    material_views = db.relationship('MaterialView', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_face_encoding(self, encoding):
        self.face_encoding = pickle.dumps(encoding)

    def get_face_encoding(self):
        return pickle.loads(self.face_encoding)

    def set_profile_pic(self, image_data):
        self.profile_pic = image_data
    def get_profile_pic_base64(self):
        """Return base64-encoded profile picture for template rendering"""
        from base64 import b64encode
        from flask import current_app
        import os
        if self.profile_pic:
            img_data = b64encode(self.profile_pic).decode('utf-8')
            return f"data:image/jpeg;base64,{img_data}"  # Adjust mimetype if needed
        default_img_path = os.path.join(current_app.root_path, 'static', 'images', 'default_profile.png')
        with open(default_img_path, 'rb') as img_file:
            img_data = b64encode(img_file.read()).decode('utf-8')
            return f"data:image/png;base64,{img_data}"
    def get_profile_pic_url(self):
        from flask import url_for
        if self.profile_pic:
            return url_for('auth.profile_pic', user_id=self.id)
        else:
            return url_for('static', filename='images/default_profile.png')


    # Add this method to the User class in models.py

    def is_enrolled_in(self, course_id):
        """Check if the user is enrolled in a specific course"""
        from models import Enrollment
        enrollment = Enrollment.query.filter_by(
            student_id=self.id,
            course_id=course_id
        ).first()
        return enrollment is not None

    def get_last_login(self):
        """Get the user's last login time (using the most recent attendance record as a proxy)"""
        from models import Attendance
        last_attendance = Attendance.query.filter_by(user_id=self.id).order_by(Attendance.timestamp.desc()).first()
        return last_attendance.timestamp if last_attendance else self.created_at

    def get_attendance_percentage(self):
        """Calculate the user's overall attendance percentage"""
        from models import Lecture, Enrollment, Attendance

        # Get all courses the user is enrolled in
        enrollments = Enrollment.query.filter_by(student_id=self.id).all()
        if not enrollments:
            return 0

        total_lectures = 0
        attended_lectures = 0

        for enrollment in enrollments:
            # Get all lectures for this course
            lectures = Lecture.query.filter_by(course_id=enrollment.course_id).all()
            total_lectures += len(lectures)

            # Count attended lectures
            for lecture in lectures:
                if Attendance.query.filter_by(user_id=self.id, lecture_id=lecture.id).first():
                    attended_lectures += 1

        if total_lectures == 0:
            return 100  # No lectures yet, so 100% attendance

        return round((attended_lectures / total_lectures) * 100)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=get_current_time)

    # New field to link attendance to a specific lecture
    lecture_id = db.Column(db.Integer, db.ForeignKey('lecture.id'), nullable=True)

    @classmethod
    def get_recent_attendance(cls, user_id, seconds=300):
        """Check if user has attendance record in the last X seconds"""
        cutoff = get_current_time().timestamp() - seconds
        recent = cls.query.filter(
            cls.user_id == user_id,
            cls.timestamp > datetime.fromtimestamp(cutoff)
        ).first()
        return recent is not None

# New models for lecture management system
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=get_current_time)

    # Relationships
    lectures = db.relationship('Lecture', backref='course', lazy=True, cascade="all, delete-orphan")
    enrollments = db.relationship('Enrollment', backref='course', lazy=True, cascade="all, delete-orphan")
    materials = db.relationship('Material', backref='course', lazy=True, cascade="all, delete-orphan")

    def get_upcoming_lecture(self):
        """Get the next upcoming lecture for this course"""
        now = get_current_time()
        upcoming = Lecture.query.filter(
            Lecture.course_id == self.id,
            Lecture.start_time > now
        ).order_by(Lecture.start_time).first()
        return upcoming

    def get_current_lecture(self):
        """Get the currently ongoing lecture if any"""
        now = get_current_time()
        current = Lecture.query.filter(
            Lecture.course_id == self.id,
            Lecture.start_time <= now,
            Lecture.end_time >= now
        ).first()
        return current

    def get_lectures_by_week(self, week_number):
        """Get all lectures for a specific week"""
        return Lecture.query.filter_by(course_id=self.id, week_number=week_number).all()

    def get_enrollment_count(self):
        """Get the number of students enrolled in this course"""
        return Enrollment.query.filter_by(course_id=self.id).count()

    def get_lecture_count(self):
        """Get the number of lectures in this course"""
        return Lecture.query.filter_by(course_id=self.id).count()

    def get_material_count(self):
        """Get the number of materials in this course"""
        return Material.query.filter_by(course_id=self.id).count()


class Lecture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    week_number = db.Column(db.Integer, nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False)  # Monday, Tuesday, etc.
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=get_current_time)

    # Relationships
    attendances = db.relationship('Attendance', backref='lecture', lazy=True)
    materials = db.relationship('Material', backref='lecture', lazy=True, cascade="all, delete-orphan")

# Add this method to the Lecture class in models.py

    def is_active(self):
        """Check if the lecture is currently active (±5 minutes from start/end time)"""
        from datetime import datetime, timedelta

        now = get_current_time()
        grace_period = timedelta(minutes=5)

        # Lecture is active if current time is within 5 minutes of start time
        # or before end time plus 5 minutes
        return (self.start_time - grace_period <= now <= self.end_time + grace_period)


    def get_attendance_status(self, user_id):
        """Check if a user has marked attendance for this lecture"""
        return Attendance.query.filter_by(lecture_id=self.id, user_id=user_id).first() is not None

    def get_previous_lecture(self):
        """Get the previous lecture in the same course"""
        return Lecture.query.filter(
            Lecture.course_id == self.course_id,
            Lecture.start_time < self.start_time
        ).order_by(Lecture.start_time.desc()).first()

    def get_next_lecture(self):
        """Get the next lecture in the same course"""
        return Lecture.query.filter(
            Lecture.course_id == self.course_id,
            Lecture.start_time > self.start_time
        ).order_by(Lecture.start_time).first()


class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    lecture_id = db.Column(db.Integer, db.ForeignKey('lecture.id'), nullable=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)  # pdf, docx, pptx, etc.
    week_number = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=get_current_time)

    # Relationships
    views = db.relationship('MaterialView', backref='material', lazy=True, cascade="all, delete-orphan")

    def get_view_count(self):
        """Get the number of unique users who viewed this material"""
        return MaterialView.query.filter_by(material_id=self.id).count()

    def is_viewed_by(self, user_id):
        """Check if a specific user has viewed this material"""
        return MaterialView.query.filter_by(material_id=self.id, user_id=user_id).first() is not None

class MaterialView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=get_current_time)
    downloaded = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint('material_id', 'user_id', name='unique_material_view'),
    )

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=get_current_time)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id', name='unique_enrollment'),
    )

    def get_attendance_count(self):
        """Get the number of lectures attended by this student for this course"""
        from models import Lecture, Attendance
        # Get all lectures for this course
        lectures = Lecture.query.filter_by(course_id=self.course_id).all()
        lecture_ids = [lecture.id for lecture in lectures]

        # Count attendances for these lectures
        return Attendance.query.filter(
            Attendance.user_id == self.student_id,
            Attendance.lecture_id.in_(lecture_ids)
        ).count()

    def get_attendance_percentage(self):
        """Calculate attendance percentage for this enrollment"""
        from models import Lecture
        lecture_count = Lecture.query.filter_by(course_id=self.course_id).count()
        if lecture_count == 0:
            return 100  # No lectures yet, so 100% attendance

        attendance_count = self.get_attendance_count()
        return round((attendance_count / lecture_count) * 100)