import subprocess
import cv2
import face_recognition
import numpy as np
import os
import qrcode
import base64
from io import BytesIO
from flask import Blueprint, jsonify, render_template, redirect, url_for, request, flash, session, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User
from camera import camera
import pdfkit
import tempfile
from flask import current_app, send_file
from PIL import Image, ImageDraw

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Check if it's a face recognition login
        if 'image' in request.files:
            image_file = request.files['image']
            image_data = image_file.read()

            result = camera.process_image(image_data)

            if result['recognized']:
                user = User.query.get(result['user_id'])
                if user:
                    login_user(user)
                    flash(f'Welcome back, {user.name}!')
                    return redirect(url_for('index'))

            flash('Face not recognized. Please try again or use email login.')
            return redirect(url_for('auth.login'))

        # Regular email/password login
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('auth.login'))

        login_user(user)
        flash(f'Welcome back, {user.name}!')
        return redirect(url_for('index'))

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if it's a face capture request
        if 'image' in request.files:
            image_file = request.files['image']
            image_data = image_file.read()

            # First, check if this face already exists in the system
            result = camera.process_image(image_data)
            if result.get('recognized', False):
                return jsonify({
                    'success': False,
                    'message': 'This face is already registered in the system.',
                    'user_exists': True,
                    'email': result.get('email', '')
                })

            # If face not recognized, proceed with capturing
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
        password = request.form.get('password')
        custom_data = request.form.get('custom_data')
        user_type = request.form.get('user_type', 'normal')  # Default to normal user

        if not all([name, email, password]) or 'face_encoding' not in session:
            flash('All fields are required and face must be captured', 'error')
            return redirect(url_for('auth.register'))

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))

        try:
            # Create new user
            user = User(
                name=name,
                email=email,
                custom_data=custom_data,
                is_admin=(user_type == 'admin')
            )
            user.set_password(password)
            user.set_face_encoding(np.array(session.pop('face_encoding')))

            db.session.add(user)
            db.session.commit()

            # Update users list for face recognition
            camera.update_users(User.query.all())

            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}', 'error')
            return redirect(url_for('auth.register'))

    return render_template('auth/register.html')

@auth_bp.route('/detect_face', methods=['POST'])
def detect_face():
    """Detect if a face is present in the uploaded image and check if it's already registered"""
    if 'image' not in request.files:
        return jsonify({'face_detected': False})

    image_file = request.files['image']
    image_data = image_file.read()

    try:
        # Decode the image data
        nparr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Convert BGR to RGB (face_recognition uses RGB)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Find face locations
        face_locations = face_recognition.face_locations(rgb_frame)

        # Check if face is already registered
        if len(face_locations) > 0:
            # Process the image to see if it matches any existing user
            result = camera.process_image(image_data)
            if result.get('recognized', False):
                return jsonify({
                    'face_detected': True,
                    'user_exists': True,
                    'user_email': result.get('email', '')
                })

        return jsonify({
            'face_detected': len(face_locations) > 0,
            'user_exists': False
        })
    except Exception as e:
        print(f"Error detecting face: {e}")
        return jsonify({'face_detected': False, 'error': str(e)})

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def profile():
    # Get recent attendance records
    from models import Attendance, Lecture, Course, MaterialView, Material

    # Get the 5 most recent attendance records
    recent_attendances = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.timestamp.desc()).limit(5).all()

    # Get the 5 most recent material views
    recent_material_views = MaterialView.query.filter_by(user_id=current_user.id).order_by(MaterialView.viewed_at.desc()).limit(5).all()

    # Combine into a timeline
    timeline = []

    for attendance in recent_attendances:
        lecture = Lecture.query.get(attendance.lecture_id) if attendance.lecture_id else None
        course = Course.query.get(lecture.course_id) if lecture else None

        timeline.append({
            'type': 'attendance',
            'timestamp': attendance.timestamp,
            'lecture': lecture,
            'course': course
        })

    for view in recent_material_views:
        material = Material.query.get(view.material_id)
        course = Course.query.get(material.course_id) if material else None

        timeline.append({
            'type': 'material_view',
            'timestamp': view.viewed_at,
            'material': material,
            'downloaded': view.downloaded,
            'course': course
        })

    # Sort timeline by timestamp (newest first)
    timeline.sort(key=lambda x: x['timestamp'], reverse=True)

    # Limit to 10 most recent activities
    timeline = timeline[:10]

    return render_template('auth/profile.html', timeline=timeline)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Check if it's a face update request
        if 'face_update' in request.form and 'image' in request.files:
            image_file = request.files['image']
            image_data = image_file.read()

            result = camera.capture_face_encoding(image_data)
            if result['success']:
                current_user.set_face_encoding(np.array(result['face_encoding']))
                db.session.commit()

                # Update users list for face recognition
                camera.update_users(User.query.all())

                return jsonify({'success': True, 'message': 'Face data updated successfully'})
            else:
                return jsonify({'success': False, 'message': result['message']})

        # Regular form submission
        current_user.name = request.form.get('name')
        current_user.custom_data = request.form.get('custom_data')

        # Update profile picture if provided
        if 'profile_pic' in request.files and request.files['profile_pic'].filename:
            profile_pic = request.files['profile_pic']
            # Read the file data and store it directly in the profile_pic field
            current_user.profile_pic = profile_pic.read()
            # Make sure to flush the session to ensure the data is saved
            db.session.flush()

        # Update password if provided
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')

        if current_password and new_password:
            if current_user.check_password(current_password):
                current_user.set_password(new_password)
                flash('Password updated successfully')
            else:
                flash('Current password is incorrect')
                return redirect(url_for('auth.edit_profile'))

        # Commit all changes to the database
        db.session.commit()

        # Update users list for face recognition if name changed
        camera.update_users(User.query.all())

        flash('Profile updated successfully!')
        return redirect(url_for('auth.profile'))

    return render_template('auth/edit_profile.html')

@auth_bp.route('/profile_pic/<int:user_id>')
def profile_pic(user_id):
    """Serve the profile picture for a user"""
    user = User.query.get_or_404(user_id)

    if user.profile_pic:
        return send_file(
            BytesIO(user.profile_pic),
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=f'profile_{user.id}.jpg'
        )

    # Return a default profile picture if none exists
    return redirect(url_for('static', filename='default_profile.png'))

@auth_bp.route('/check_email')
def check_email():
    """Check if an email is already registered"""
    email = request.args.get('email')
    if not email:
        return jsonify({'exists': False})

    user = User.query.filter_by(email=email).first()
    return jsonify({'exists': user is not None})



def generate_qr_code(user):
    """Generate a QR code for the user with name, email, ID and message"""
    try:
        # Create a very simple QR code content - just the ID number
        # This is guaranteed to be scannable by all QR code readers
        qr_content = f"{user.id:06d}"

        # Create QR code instance with minimal settings
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,  # Use L for better compatibility
            box_size=10,
            border=2,
        )

        # Add data to QR code
        qr.add_data(qr_content)
        qr.make(fit=True)

        # Create an image from the QR code with blue color
        img = qr.make_image(fill_color="#1E40AF", back_color="white")

        # Convert to base64 for embedding in HTML
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        qr_code_base64 = f"data:image/png;base64,{img_str}"

        print(f"Generated QR code with content: {qr_content}")
        return qr_code_base64
    except Exception as e:
        print(f"Error generating QR code: {e}")
        # Return a fallback QR code or empty string
        return ""

@auth_bp.route('/qr_code/<int:user_id>')
def get_qr_code(user_id):
    """Generate and return a QR code for a user"""
    user = User.query.get_or_404(user_id)
    qr_code_base64 = generate_qr_code(user)

    # Remove the data:image/png;base64, prefix
    img_data = qr_code_base64.split(',')[1]

    # Decode the base64 string
    img_bytes = base64.b64decode(img_data)

    # Return the image
    return send_file(
        BytesIO(img_bytes),
        mimetype='image/png',
        as_attachment=False
    )

@auth_bp.route('/profile/download_card')
@login_required
def download_profile_card():
    """Generate and download a PNG card of the user's profile"""
    user = current_user

    # Get base64-encoded profile picture
    profile_pic_base64 = user.get_profile_pic_base64()

    # Generate QR code
    qr_code_base64 = generate_qr_code(user)

    # Render the profile card template
    html = render_template('auth/profile_card.html', user=user, profile_pic_base64=profile_pic_base64, qr_code_base64=qr_code_base64)

    # Use wkhtmltoimage to convert HTML to PNG
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as html_file:
        html_file.write(html.encode('utf-8'))
        html_path = html_file.name

    # Define the PNG path
    png_path = html_path.replace('.html', '.png')

    try:
        # Get wkhtmltoimage path from config
        wkhtmltoimage_path = current_app.config.get('WKHTMLTOIMAGE_PATH', 'wkhtmltoimage')

        # Run wkhtmltoimage with specific options for better rendering
        command = [
            wkhtmltoimage_path,
            '--enable-local-file-access',
            '--width', '800',
            '--height', '400',
            '--quality', '100',
            '--format', 'png',
            '--encoding', 'UTF-8',
            '--javascript-delay', '5000',  # Increased delay to ensure QR code rendering
            html_path,
            png_path
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True)

        # Prepare the response
        filename = f"profile_card_{user.name.replace(' ', '_')}.png"

        # Send the PNG file
        response = send_file(
            png_path,
            as_attachment=True,
            download_name=filename,
            mimetype='image/png'
        )

        # Delete the temporary files after sending
        @response.call_on_close
        def cleanup():
            if os.path.exists(html_path):
                os.unlink(html_path)
            if os.path.exists(png_path):
                os.unlink(png_path)

        return response

    except subprocess.CalledProcessError as e:
        flash(f'Error generating profile card: {e}, Stderr: {e.stderr}', 'error')
        print(f"Command: {' '.join(command)}")
        print(f"Subprocess error: {e}, Stderr: {e.stderr}")
        if os.path.exists(html_path):
            os.unlink(html_path)
        if os.path.exists(png_path) and os.path.isfile(png_path):
            os.unlink(png_path)
        return redirect(url_for('auth.profile'))

    except Exception as e:
        flash(f'Error generating profile card: {str(e)}', 'error')
        if os.path.exists(html_path):
            os.unlink(html_path)
        if os.path.exists(png_path) and os.path.isfile(png_path):
            os.unlink(png_path)
        return redirect(url_for('auth.profile'))

@auth_bp.route('/admin/user/<int:user_id>/download_card')
@login_required
def download_user_card(user_id):
    """Generate and download a PNG card of a user's profile (admin only)"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)

    # Get base64-encoded profile picture
    profile_pic_base64 = user.get_profile_pic_base64()

    # Generate QR code
    qr_code_base64 = generate_qr_code(user)

    # Render the profile card template
    html = render_template('auth/profile_card.html', user=user, profile_pic_base64=profile_pic_base64, qr_code_base64=qr_code_base64)

    # Use wkhtmltoimage to convert HTML to PNG
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as html_file:
        html_file.write(html.encode('utf-8'))
        html_path = html_file.name

    # Define the PNG path
    png_path = html_path.replace('.html', '.png')

    try:
        # Get wkhtmltoimage path from config
        wkhtmltoimage_path = current_app.config.get('WKHTMLTOIMAGE_PATH', 'wkhtmltoimage')

        # Run wkhtmltoimage with specific options for better rendering
        command = [
            wkhtmltoimage_path,
            '--enable-local-file-access',
            '--width', '800',
            '--height', '400',
            '--quality', '100',
            '--format', 'png',
            '--encoding', 'UTF-8',
            '--javascript-delay', '5000',  # Increased delay to ensure QR code rendering
            html_path,
            png_path
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True)

        # Prepare the response
        filename = f"user_card_{user.name.replace(' ', '_')}.png"

        # Send the PNG file
        response = send_file(
            png_path,
            as_attachment=True,
            download_name=filename,
            mimetype='image/png'
        )

        # Delete the temporary files after sending
        @response.call_on_close
        def cleanup():
            if os.path.exists(html_path):
                os.unlink(html_path)
            if os.path.exists(png_path):
                os.unlink(png_path)

        return response

    except subprocess.CalledProcessError as e:
        flash(f'Error generating user card: {e}, Stderr: {e.stderr}', 'error')
        print(f"Command: {' '.join(command)}")
        print(f"Subprocess error: {e}, Stderr: {e.stderr}")
        if os.path.exists(html_path):
            os.unlink(html_path)
        if os.path.exists(png_path) and os.path.isfile(png_path):
            os.unlink(png_path)
        return redirect(url_for('admin'))

    except Exception as e:
        flash(f'Error generating user card: {str(e)}', 'error')
        if os.path.exists(html_path):
            os.unlink(html_path)
        if os.path.exists(png_path) and os.path.isfile(png_path):
            os.unlink(png_path)
        return redirect(url_for('admin'))
