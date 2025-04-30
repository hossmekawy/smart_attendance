import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-face-recognition'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///attendance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ATTENDANCE_COOLDOWN = 3600  # 1 hour in seconds    
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
    COURSE_MATERIALS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/course_materials')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'zip'}
    ATTENDANCE_GRACE_PERIOD = 5  # minutes before/after lecture start time
    
    # Path to wkhtmltopdf executable
    WKHTMLTOPDF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'wkhtmltopdf', 'bin', 'wkhtmltopdf.exe')
    WKHTMLTOIMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'wkhtmltopdf', 'bin', 'wkhtmltoimage.exe')
    TIMEZONE = 'Africa/Cairo'
    TIMEZONE_OFFSET = timedelta(hours=2)  # Egypt is UTC+2
    
    ITEMS_PER_PAGE = 20  # Default number of items per page

