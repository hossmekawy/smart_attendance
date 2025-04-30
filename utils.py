import os
import sys
import pickle
import numpy as np
from werkzeug.security import generate_password_hash
from datetime import datetime
import argparse

# Add the current directory to the path so we can import our app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the database and User model
from models import db, User

def create_admin_user(app, name, email, password, face_encoding=None):
    """
    Create a new admin user in the database.
    
    Args:
        app: Flask application instance
        name: Admin's full name
        email: Admin's email address
        password: Admin's password
        face_encoding: Optional face encoding for facial recognition
    
    Returns:
        The created User object if successful, None otherwise
    """
    with app.app_context():
        # Check if user with this email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"User with email {email} already exists.")
            return None
        
        # Create default face encoding if none provided
        if face_encoding is None:
            # Create a random face encoding (this won't work for actual face recognition)
            # In a real scenario, you'd capture and process a real face
            face_encoding = np.random.rand(128).astype(np.float64)
        
        # Create the new admin user
        admin_user = User(
            name=name,
            email=email,
            is_admin=True,
            created_at=datetime.utcnow()
        )
        
        # Set password and face encoding
        admin_user.set_password(password)
        admin_user.set_face_encoding(face_encoding)
        
        # Add to database and commit
        db.session.add(admin_user)
        db.session.commit()
        
        print(f"Admin user '{name}' created successfully with email: {email}")
        return admin_user

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an admin user for the Smart Attendance system")
    parser.add_argument("--name", required=True, help="Admin's full name")
    parser.add_argument("--email", required=True, help="Admin's email address")
    parser.add_argument("--password", required=True, help="Admin's password")
    parser.add_argument("--face-image", help="Path to admin's face image (optional)")
    
    args = parser.parse_args()
    
    # Import the app here to avoid circular imports
    from app import app
    
    face_encoding = None
    if args.face_image and os.path.exists(args.face_image):
        try:
            # Import face_recognition only if needed
            import face_recognition
            image = face_recognition.load_image_file(args.face_image)
            face_encodings = face_recognition.face_encodings(image)
            if face_encodings:
                face_encoding = face_encodings[0]
                print("Face encoding extracted successfully.")
            else:
                print("No face detected in the provided image. Using random encoding.")
        except ImportError:
            print("face_recognition library not installed. Using random encoding.")
    
    create_admin_user(app, args.name, args.email, args.password, face_encoding)
