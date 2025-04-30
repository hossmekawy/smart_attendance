import os
import sys
import random
import numpy as np
import pickle
from datetime import datetime
import cv2
import face_recognition

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, User
from werkzeug.security import generate_password_hash

# List of Arabic/Muslim male first names
first_names = [
    "Mohamed", "Ahmed", "Mahmoud", "Ali", "Omar", "Khaled", "Ibrahim", "Mostafa", 
    "Yousef", "Zeyad", "Abdelrahman", "Wael", "Tarek", "Amr", "Hossam", "Karim", 
    "Ayman", "Hesham", "Sherif", "Osama", "Hamza", "Yasser", "Walid", "Sayed", 
    "Nasser", "Adel", "Magdy", "Sameh", "Tamer", "Ashraf", "Hany", "Shady", 
    "Ramy", "Fady", "Ehab", "Hatem", "Medhat", "Nabil", "Samir", "Essam", 
    "Akram", "Emad", "Hisham", "Kareem", "Maher", "Mounir", "Nader", "Ramadan", 
    "Sami", "Tariq"
]

# List of Arabic/Muslim female first names
female_first_names = [
    "Fatima", "Aisha", "Mariam", "Nour", "Sara", "Heba", "Rana", "Amira",
    "Layla", "Dina", "Reem", "Yasmin", "Maha", "Hala", "Salma", "Nada",
    "Rania", "Dalia", "Aya", "Noura", "Ghada", "Manal", "Sahar", "Hanan",
    "Basma", "Esraa", "Mona", "Nahla", "Safaa", "Zeinab"
]
# List of Arabic/Muslim last names
last_names = [
    "Mohamed", "Ahmed", "Mahmoud", "Ali", "Hassan", "Hussein", "Ibrahim", "Mostafa", 
    "Yousef", "Abdelrahman", "Elsayed", "Elsherbiny", "Elmasry", "Abdelaziz", "Abdelfattah", 
    "Abdelhamid", "Abdelkader", "Abdelwahab", "Amin", "Fawzy", "Gaber", "Hamed", 
    "Kamal", "Mansour", "Morsy", "Nour", "Osman", "Ramadan", "Salah", "Shawky", 
    "Soliman", "Zaki", "Fahmy", "Fathy", "Fouad", "Ghaly", "Habib", "Hakim", 
    "Halim", "Hamdy", "Hasan", "Helmy", "Hosny", "Ismail", "Khalil", "Lotfy", 
    "Mabrouk", "Mahfouz", "Mourad", "Naguib", "Rashid", "Saad", "Sabry", "Sadek", 
    "Saleh", "Selim", "Shafik", "Sherif", "Taha", "Wahba", "Yehia", "Zaher"
]

# Admin users (first name, last name)
admin_users = [
    ("Mohamed", "Mekawy"),
    ("Ahmed", "Elmasry"),
    ("Mahmoud", "Ibrahim"),
    ("Ali", "Hassan"),
    ("Omar", "Abdelaziz")
]

def generate_random_face_encoding():
    """Generate a random face encoding (128-dimensional vector)"""
    # Generate a random 128-dimensional vector
    encoding = np.random.normal(0, 0.5, 128)
    # Normalize it to have unit length (like real face encodings)
    encoding = encoding / np.linalg.norm(encoding)
    return encoding

def create_users():
    """Create 1000 users (995 normal + 5 admin)"""
    with app.app_context():
        print("Starting user creation...")
        
        # Create admin users first
        for i, (first_name, last_name) in enumerate(admin_users):
            full_name = f"{first_name} {last_name}"
            email = f"{first_name.lower()}.{last_name.lower()}@admin.com"
            
            # Check if user already exists
            if User.query.filter_by(email=email).first():
                print(f"Admin user {email} already exists, skipping...")
                continue
                
            # Create admin user
            user = User(
                name=full_name,
                email=email,
                custom_data=f"Admin ID: A{i+1000}",
                is_admin=True
            )
            
            # Set password (same as email for simplicity)
            user.set_password(email)
            
            # Generate and set face encoding
            face_encoding = generate_random_face_encoding()
            user.set_face_encoding(face_encoding)
            
            db.session.add(user)
            print(f"Created admin user: {full_name} ({email})")
        
        # Commit admin users
        db.session.commit()
        
        # Create normal users
        for i in range(10):
            # Generate random name with random gender
            if random.choice([True, False]):  # Randomly choose male or female
                first_name = random.choice(first_names)
            else:
                first_name = random.choice(female_first_names)
            last_name = random.choice(last_names)
            full_name = f"{first_name} {last_name}"
            
            # Generate email with a random number to avoid duplicates
            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}@student.com"
            
            # Create student ID
            student_id = f"S{i+1000}"
            
            # Create user
            user = User(
                name=full_name,
                email=email,
                custom_data=f"Student ID: {student_id}",
                is_admin=False
            )
            
            # Set password (same as email for simplicity)
            user.set_password(email)
            
            # Generate and set face encoding
            face_encoding = generate_random_face_encoding()
            user.set_face_encoding(face_encoding)
            
            db.session.add(user)
            
            # Commit in batches to avoid memory issues
            if i % 100 == 0:
                db.session.commit()
                print(f"Created {i+1} normal users so far...")
        
        # Final commit
        db.session.commit()
        print("User creation complete!")
        print(f"Created 5 admin users and 10 normal users.")

if __name__ == "__main__":
    create_users()