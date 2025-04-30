from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash, Response
from flask_login import LoginManager, login_required, current_user
from models import db, User, Attendance
from config import Config
from camera import camera
from auth.routes import auth_bp
from courses.routes import courses_bp
import numpy as np
from datetime import datetime
import os
import pytz

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)
egypt_timezone = pytz.timezone(Config.TIMEZONE)
app.jinja_env.globals.update(min=min, max=max)

# Helper function to get current time in Egypt timezone
def get_egypt_time():
    """Return current time in Egypt timezone"""
    return datetime.now(egypt_timezone).replace(tzinfo=None)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(courses_bp)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()
    # Load users for face recognition
    camera.update_users(User.query.all())
    if not os.path.exists(app.config['COURSE_MATERIALS_FOLDER']):
        os.makedirs(app.config['COURSE_MATERIALS_FOLDER'])

# Add template filter to format dates in Egypt timezone
@app.template_filter('egypt_time')
def egypt_time_filter(dt):
    """Convert UTC datetime to Egypt timezone"""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        # If datetime has no timezone info, assume it's already in Egypt time
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        # Convert to Egypt timezone
        egypt_dt = dt.astimezone(egypt_timezone)
        return egypt_dt.strftime('%Y-%m-%d %H:%M:%S')

@app.route('/')
def index():
    # Get system statistics for the dashboard
    stats = {}

    # Import models at the function level to avoid circular imports
    from models import User, Course, Lecture, Attendance

    if current_user.is_authenticated:
        # Only admins see full statistics
        if current_user.is_admin:
            stats['users'] = User.query.count()
            stats['courses'] = Course.query.count()
            stats['lectures'] = Lecture.query.count()
            stats['attendances'] = Attendance.query.count()

    return render_template('index.html', stats=stats)

@app.route('/attendance')
@login_required
def attendance():
    # Get active lectures for the current user
    from models import Course, Lecture, Enrollment

    # Use Egypt time
    now = get_egypt_time()

    if current_user.is_admin:
        # Admins see all active lectures
        active_lectures = Lecture.query.filter(
            Lecture.start_time <= now,
            Lecture.end_time >= now
        ).all()
    else:
        # Students see only active lectures for enrolled courses
        enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
        course_ids = [enrollment.course_id for enrollment in enrollments]

        if course_ids:
            active_lectures = Lecture.query.filter(
                Lecture.course_id.in_(course_ids),
                Lecture.start_time <= now,
                Lecture.end_time >= now
            ).all()
        else:
            active_lectures = []

    return render_template('attendance.html', active_lectures=active_lectures)

@app.route('/process_attendance', methods=['POST'])
@login_required
def process_attendance():
    """Process an image from the frontend and check attendance"""
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image provided'})

    # Check if a lecture_id is provided
    lecture_id = request.form.get('lecture_id')
    if lecture_id:
        # Redirect to the course-specific attendance route
        from courses.routes import mark_attendance
        return mark_attendance(int(lecture_id))

    # Legacy attendance processing (not tied to a specific lecture)
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
            # Use Egypt time for timestamp
            attendance = Attendance(user_id=user_id, timestamp=get_egypt_time())
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
                'timestamp': get_egypt_time().strftime('%Y-%m-%d %H:%M:%S')
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

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('You do not have permission to access the admin panel.')
        return redirect(url_for('index'))

    users = User.query.all()
    attendances = Attendance.query.order_by(Attendance.timestamp.desc()).all()

    # Get course statistics
    from models import Course, Lecture, Material, MaterialView, Enrollment

    courses = Course.query.all()
    course_stats = []

    for course in courses:
        enrollments = Enrollment.query.filter_by(course_id=course.id).count()
        lectures = Lecture.query.filter_by(course_id=course.id).count()
        materials = Material.query.filter_by(course_id=course.id).count()

        course_stats.append({
            'course': course,
            'enrollments': enrollments,
            'lectures': lectures,
            'materials': materials
        })

    return render_template(
        'admin.html',
        users=users,
        attendances=attendances,
        course_stats=course_stats
    )

@app.route('/admin/all-attendance')
@login_required
def all_attendance():
    if not current_user.is_admin:
        flash('You do not have permission to access the admin panel.')
        return redirect(url_for('index'))

    users = User.query.all()
    attendances = Attendance.query.order_by(Attendance.timestamp.desc()).all()

    # Get all lectures and courses for reference
    from models import Lecture, Course
    lectures = Lecture.query.all()
    courses = Course.query.all()

    return render_template(
        'all_attendance.html',
        attendances=attendances,
        users=users,
        lectures=lectures,
        courses=courses
    )

@app.route('/admin/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    user_name = user.name  # Store the name before deletion

    # First delete all attendance records for this user
    Attendance.query.filter_by(user_id=user_id).delete()

    # Then delete the user
    db.session.delete(user)
    db.session.commit()

    # Update users list for face recognition
    camera.update_users(User.query.all())

    # Instead of using flash, we'll pass parameters to the URL for our toast system
    return redirect(url_for('admin', deleted=1, name=user_name))

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        try:
            user.name = request.form.get('name')
            user.email = request.form.get('email')
            user.custom_data = request.form.get('custom_data')

            # Update profile picture if provided
            if 'profile_pic' in request.files and request.files['profile_pic'].filename:
                profile_pic = request.files['profile_pic']
                # Read the file data and store it directly in the profile_pic field
                user.profile_pic = profile_pic.read()

            # Update user type if provided
            user_type = request.form.get('user_type')
            if user_type:
                user.is_admin = (user_type == 'admin')

            db.session.commit()

            # Update users list for face recognition
            camera.update_users(User.query.all())

            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Check if profile picture was updated
                profile_pic_updated = 'profile_pic' in request.files and request.files['profile_pic'].filename

                return jsonify({
                    'success': True,
                    'message': f'User {user.name} updated successfully{" with new profile picture" if profile_pic_updated else ""}'
                })

            # For regular form submissions, use flash and redirect
            profile_pic_updated = 'profile_pic' in request.files and request.files['profile_pic'].filename
            flash(f'User {user.name} updated successfully{" with new profile picture" if profile_pic_updated else ""}')
            return redirect(url_for('admin'))
        except Exception as e:
            # Return error as JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': f'Error updating user: {str(e)}'
                }), 400

            # For regular form submissions, use flash and redirect
            flash(f'Error updating user: {str(e)}', 'error')
            return redirect(url_for('edit_user', user_id=user_id))

    return render_template('edit_user.html', user=user)

@app.route('/api/active-lectures')
@login_required
def get_active_lectures():
    """API endpoint to get active lectures for the current user"""
    from models import Course, Lecture, Enrollment
    from datetime import timedelta

    # Get current time in Egypt timezone
    now = get_egypt_time()
    # Consider lectures active if they're starting within 15 minutes or have started but not ended
    active_window = now + timedelta(minutes=15)

    if current_user.is_admin:
        # Admins see all active lectures
        active_lectures = Lecture.query.filter(
            Lecture.start_time <= active_window,
            Lecture.end_time >= now
        ).all()
    else:
        # Students see only active lectures for enrolled courses
        enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
        course_ids = [enrollment.course_id for enrollment in enrollments]

        if course_ids:
            active_lectures = Lecture.query.filter(
                Lecture.course_id.in_(course_ids),
                Lecture.start_time <= active_window,
                Lecture.end_time >= now
            ).all()
        else:
            active_lectures = []

    # Format lectures for the frontend
    lectures_data = []
    for lecture in active_lectures:
        course = Course.query.get(lecture.course_id)
        lectures_data.append({
            'id': lecture.id,
            'title': lecture.title,
            'course_code': course.code,
            'course_name': course.name,
            'location': lecture.location,
            'time': f"{lecture.start_time.strftime('%H:%M')} - {lecture.end_time.strftime('%H:%M')}",
            'url': url_for('courses.view_lecture', lecture_id=lecture.id)
        })

    return jsonify({'lectures': lectures_data})

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
    app.debug = True
    # Run with HTTPS using the generated certificates
    app.run(host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))
