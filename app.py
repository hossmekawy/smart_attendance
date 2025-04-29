from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash
from models import db, User, Attendance
from config import Config
from camera import camera
import numpy as np
from datetime import datetime
import base64
import io

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()
    # Load users for face recognition
    camera.update_users(User.query.all())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if it's a face capture request
        if 'image' in request.files:
            image_file = request.files['image']
            image_data = image_file.read()
            
            result = camera.capture_face_encoding(image_data)
            if result['success']:
                # Store in session
                session['face_encoding'] = result['face_encoding']
                return jsonify({'success': True, 'message': 'Face captured successfully'})
            else:
                return jsonify(result)
        
        # Process the registration form
        name = request.form.get('name')
        email = request.form.get('email')
        custom_data = request.form.get('custom_data')
        
        if not all([name, email]) or 'face_encoding' not in session:
            flash('All fields are required and face must be captured')
            return redirect(url_for('register'))
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered')
            return redirect(url_for('register'))
        
        try:
            # Create new user
            user = User(name=name, email=email, custom_data=custom_data)
            user.set_face_encoding(np.array(session.pop('face_encoding')))
            
            db.session.add(user)
            db.session.commit()
            
            # Update users list for face recognition
            camera.update_users(User.query.all())
            
            flash('Registration successful')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE constraint failed: user.email' in str(e):
                flash('Email already registered')
            else:
                flash(f'Error during registration: {str(e)}')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/attendance')
def attendance():
    return render_template('attendance.html')

@app.route('/process_attendance', methods=['POST'])
def process_attendance():
    """Process an image from the frontend and check attendance"""
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image provided'})
    
    image_file = request.files['image']
    image_data = image_file.read()
    
    # Process the image
    result = camera.process_image(image_data)
    
    if result['recognized']:
        user_id = result['user_id']
        
        # Check if user already has recent attendance
        cooldown = app.config['ATTENDANCE_COOLDOWN']
        if not Attendance.get_recent_attendance(user_id, cooldown):
            # Log new attendance
            user = User.query.get(user_id)
            attendance = Attendance(user_id=user_id)
            db.session.add(attendance)
            db.session.commit()
            
            return jsonify({
                'recognized': True,
                'user': {
                    'id': user_id,
                    'name': result['name'],
                    'email': result['email']
                },
                'message': 'Attendance recorded successfully',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            return jsonify({
                'recognized': True,
                'user': {
                    'id': user_id,
                    'name': result['name'],
                    'email': result['email']
                },
                'message': 'Attendance already recorded recently',
                'timestamp': None
            })
    
    return jsonify({
        'recognized': False,
        'message': 'No recognized user'
    })

@app.route('/check_email')
def check_email():
    email = request.args.get('email')
    if not email:
        return jsonify({'exists': False})
    
    user = User.query.filter_by(email=email).first()
    return jsonify({'exists': user is not None})


@app.route('/admin')
def admin():
    users = User.query.all()
    attendances = Attendance.query.order_by(Attendance.timestamp.desc()).all()
    return render_template('admin.html', users=users, attendances=attendances)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # First delete all attendance records for this user
    Attendance.query.filter_by(user_id=user_id).delete()
    
    # Then delete the user
    db.session.delete(user)
    db.session.commit()
    
    # Update users list for face recognition
    camera.update_users(User.query.all())
    
    flash(f'User {user.name} deleted successfully')
    return redirect(url_for('admin'))


@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.custom_data = request.form.get('custom_data')
        
        db.session.commit()
        
        # Update users list for face recognition
        camera.update_users(User.query.all())
        
        flash(f'User {user.name} updated successfully')
        return redirect(url_for('admin'))
    
    return render_template('edit_user.html', user=user)



@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

@app.after_request
def add_header(response):
    """Add headers to allow camera access"""
    response.headers['Feature-Policy'] = "camera 'self'"
    response.headers['Permissions-Policy'] = "camera=self"
    return response


if __name__ == '__main__':
    # Run with HTTPS using the generated certificates
    app.run(host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))
