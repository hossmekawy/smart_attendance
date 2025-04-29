import face_recognition
import numpy as np
import cv2

def get_face_encoding(frame):
    """Extract face encoding from a frame"""
    # Convert BGR to RGB (face_recognition uses RGB)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Resize image to 1/4 size for faster face detection
    small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)
    
    # Find face locations
    face_locations = face_recognition.face_locations(small_frame)
    
    if not face_locations:
        return None
    
    # Get face encodings
    face_encodings = face_recognition.face_encodings(small_frame, face_locations)
    
    if not face_encodings:
        return None
    
    # Scale back up face locations
    face_locations = [(top * 4, right * 4, bottom * 4, left * 4) 
                      for (top, right, bottom, left) in face_locations]
    
    # Return the first face encoding and location
    return face_encodings[0], face_locations[0]

def recognize_face(frame, users):
    """Recognize faces in the frame against registered users"""
    if not users:
        return None, None
        
    # Convert BGR to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Resize image to 1/4 size for faster face detection
    small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)
    
    # Find face locations
    face_locations = face_recognition.face_locations(small_frame)
    
    if not face_locations:
        return None, None
    
    # Get face encodings
    face_encodings = face_recognition.face_encodings(small_frame, face_locations)
    
    if not face_encodings:
        return None, None
    
    # Scale back up face locations
    face_locations = [(top * 4, right * 4, bottom * 4, left * 4) 
                      for (top, right, bottom, left) in face_locations]
    
    # Check each face in the frame
    for face_encoding, face_location in zip(face_encodings, face_locations):
        # Compare with known faces
        known_encodings = [user.get_face_encoding() for user in users]
        
        # Compare faces
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.6)
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        
        if True in matches:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                return users[best_match_index], face_location
    
    return None, None

def draw_face_box(frame, location, name=None):
    """Draw a box around the face and display name"""
    top, right, bottom, left = location
    
    # Draw a box around the face
    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
    
    # Draw a label with a name below the face
    if name:
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.8, (255, 255, 255), 1)
    
    return frame
