import cv2
import numpy as np
from face_utils import recognize_face, get_face_encoding

class Camera:
    def __init__(self):
        self.recognized_user = None
        self.users = []
    
    def update_users(self, users):
        """Update the list of users for recognition"""
        self.users = users
    
    def process_image(self, image_data):
        """Process an image from the frontend and recognize faces"""
        # Convert base64 image to numpy array
        try:
            # Decode the image data
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Try to recognize faces
            user, face_location = recognize_face(frame, self.users)
            
            if user:
                return {
                    'recognized': True,
                    'user_id': user.id,
                    'name': user.name,
                    'email': user.email
                }
            else:
                return {
                    'recognized': False
                }
        except Exception as e:
            print(f"Error processing image: {e}")
            return {
                'recognized': False,
                'error': str(e)
            }
    
    def capture_face_encoding(self, image_data):
        """Extract face encoding from uploaded image"""
        try:
            # Decode the image data
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Get face encoding
            result = get_face_encoding(frame)
            if result:
                face_encoding, face_location = result
                return {
                    'success': True,
                    'face_encoding': face_encoding.tolist()
                }
            else:
                return {
                    'success': False,
                    'message': 'No face detected in the image'
                }
        except Exception as e:
            print(f"Error capturing face: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }

# Global camera instance
camera = Camera()
