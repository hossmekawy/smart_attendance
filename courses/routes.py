import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Course, Lecture, Material, MaterialView, Enrollment, Attendance, User, get_current_time
from datetime import datetime, timedelta
import calendar
from flask import send_file
import pandas as pd
from io import BytesIO

courses_bp = Blueprint('courses', __name__, url_prefix='/courses')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@courses_bp.route('/')
@login_required
def index():
    """Show all courses for the current user"""
    if current_user.is_admin:
        # Admins see all courses
        courses = Course.query.all()
    else:
        # Students see only enrolled courses
        enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
        courses = [enrollment.course for enrollment in enrollments]
    
    # Create a dummy course object with all required attributes for the base template
    dummy_course = {
        "id": None,
        "name": "All Courses",
        "code": "",
        "instructor_id": None
    }
    
    return render_template('courses/index.html', courses=courses, course=dummy_course)


@courses_bp.route('/<int:course_id>')
@login_required
def view_course(course_id):
    """View a specific course and its lectures"""
    course = Course.query.get_or_404(course_id)
    
    # Check if user is enrolled or is admin
    if not current_user.is_admin and not current_user.is_enrolled_in(course_id):
        flash('You are not enrolled in this course', 'error')
        return redirect(url_for('courses.index'))
    
    # Get all lectures grouped by week
    lectures_by_week = {}
    for lecture in course.lectures:
        if lecture.week_number not in lectures_by_week:
            lectures_by_week[lecture.week_number] = []
        lectures_by_week[lecture.week_number].append(lecture)
    
    # Get all materials grouped by week
    materials_by_week = {}
    for material in course.materials:
        if material.week_number not in materials_by_week:
            materials_by_week[material.week_number] = []
        materials_by_week[material.week_number].append(material)
    
    return render_template(
        'courses/view_course.html', 
        course=course, 
        lectures_by_week=lectures_by_week,
        materials_by_week=materials_by_week
    )

@courses_bp.route('/schedule')
@login_required
def schedule():
    """Show the user's course schedule"""
    if current_user.is_admin:
        # Admins see all lectures
        lectures = Lecture.query.all()
    else:
        # Students see only lectures for enrolled courses
        enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
        course_ids = [enrollment.course_id for enrollment in enrollments]
        lectures = Lecture.query.filter(Lecture.course_id.in_(course_ids)).all()
    
    # Group lectures by day of week
    schedule_by_day = {day: [] for day in calendar.day_name}
    for lecture in lectures:
        schedule_by_day[lecture.day_of_week].append(lecture)
    
    # Sort lectures within each day by start time
    for day in schedule_by_day:
        schedule_by_day[day].sort(key=lambda x: x.start_time.time())
    
    # Create a dummy course object for the base template
    dummy_course = {
        "id": None,
        "name": "Weekly Schedule",
        "code": "",
        "instructor_id": None
    }
    
    return render_template('courses/schedule.html', schedule_by_day=schedule_by_day, course=dummy_course)

@courses_bp.route('/calendar')
@login_required
def calendar_view():
    """Show the user's course schedule in a calendar format"""
    if current_user.is_admin:
        # Admins see all lectures
        lectures = Lecture.query.all()
    else:
        # Students see only lectures for enrolled courses
        enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
        course_ids = [enrollment.course_id for enrollment in enrollments]
        lectures = Lecture.query.filter(Lecture.course_id.in_(course_ids)).all()
    
    # Format lectures for calendar
    events = []
    for lecture in lectures:
        course = Course.query.get(lecture.course_id)
        events.append({
            'id': lecture.id,
            'title': f"{course.code}: {lecture.title}",
            'start': lecture.start_time.isoformat(),
            'end': lecture.end_time.isoformat(),
            'url': url_for('courses.view_lecture', lecture_id=lecture.id)
        })
    
    # Create a dummy course object for the base template
    dummy_course = {
        "id": None,
        "name": "Calendar View",
        "code": "",
        "instructor_id": None
    }
    
    return render_template('courses/calendar.html', events=events, course=dummy_course)

@courses_bp.route('/lecture/<int:lecture_id>')
@login_required
def view_lecture(lecture_id):
    """View a specific lecture and its materials"""
    # Get the lecture and associated course
    lecture = Lecture.query.get_or_404(lecture_id)
    course = Course.query.get(lecture.course_id)
    
    # Check if user is enrolled or is admin
    if not current_user.is_admin and not current_user.is_enrolled_in(course.id):
        flash('You are not enrolled in this course', 'error')
        return redirect(url_for('courses.index'))
    
    # Get all lectures for this course (for navigation)
    lectures = Lecture.query.filter_by(course_id=course.id).order_by(Lecture.start_time).all()
    
    # Get materials for this lecture
    materials = Material.query.filter_by(lecture_id=lecture_id).all()
    
    # Check if the user has marked attendance for this lecture
    attendance_marked = Attendance.query.filter_by(
        user_id=current_user.id, 
        lecture_id=lecture_id
    ).first() is not None
    
    # Check if lecture is currently active
    is_active = lecture.is_active()
    
    # Get current datetime for template comparisons
    from datetime import datetime
    current_time = get_current_time()
    
    # Debug information
    print(f"Lecture ID: {lecture_id}")
    print(f"Course ID: {course.id}")
    print(f"Number of lectures: {len(lectures)}")
    print(f"Number of materials: {len(materials)}")
    
    # Render the template with all necessary data
    return render_template(
        'courses/view_lecture.html',
        lecture=lecture,
        lectures=lectures,
        course=course,
        materials=materials,
        attendance_marked=attendance_marked,
        is_active=is_active,
        now=current_time  # Pass current time for template comparisons
    )

@courses_bp.route('/material/<int:material_id>')
@login_required
def view_material(material_id):
    """View or download a specific material"""
    material = Material.query.get_or_404(material_id)
    course = Course.query.get(material.course_id)
    
    # Check if user is enrolled or is admin
    if not current_user.is_admin and not current_user.is_enrolled_in(course.id):
        flash('You are not enrolled in this course', 'error')
        return redirect(url_for('courses.index'))
    
    # Record that the user has viewed this material
    existing_view = MaterialView.query.filter_by(
        material_id=material_id,
        user_id=current_user.id
    ).first()
    
    if not existing_view:
        view = MaterialView(
            material_id=material_id,
            user_id=current_user.id,
            downloaded=True  # Since they're downloading it
        )
        db.session.add(view)
        db.session.commit()
    elif not existing_view.downloaded:
        existing_view.downloaded = True
        db.session.commit()
    
    # Serve the file
    directory = os.path.join(
        current_app.config['COURSE_MATERIALS_FOLDER'],
        str(course.id),
        str(material.week_number)
    )
    filename = os.path.basename(material.file_path)
    
    return send_from_directory(directory, filename, as_attachment=True)

@courses_bp.route('/mark_attendance/<int:lecture_id>', methods=['POST'])
@login_required
def mark_attendance(lecture_id):
    """Mark attendance for a specific lecture using face recognition"""
    lecture = Lecture.query.get_or_404(lecture_id)
    course = Course.query.get(lecture.course_id)
    
    # Check if user is enrolled
    if not current_user.is_enrolled_in(course.id):
        return jsonify({
            'success': False,
            'message': 'You are not enrolled in this course'
        })
    
    # Check if lecture is active
    if not lecture.is_active():
        return jsonify({
            'success': False,
            'message': 'Attendance can only be marked during the lecture time (±5 minutes)'
        })
    
    # Check if attendance already marked
    existing_attendance = Attendance.query.filter_by(
        user_id=current_user.id,
        lecture_id=lecture_id
    ).first()
    
    if existing_attendance:
        return jsonify({
            'success': False,
            'message': 'Attendance already marked for this lecture'
        })
    
    # Process face recognition
    if 'image' not in request.files:
        return jsonify({
            'success': False,
            'message': 'No image provided'
        })
    
    image_file = request.files['image']
    image_data = image_file.read()
    
    # Use the existing camera module to process the image
    from camera import camera
    result = camera.process_image(image_data)
    
    if result['recognized'] and result['user_id'] == current_user.id:
        # Create attendance record
        attendance = Attendance(
            user_id=current_user.id,
            lecture_id=lecture_id,
            timestamp=datetime.utcnow()
        )
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Attendance marked successfully',
            'timestamp': attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Face not recognized or does not match your profile'
        })

# Admin routes for course management
@courses_bp.route('/admin/courses')
@login_required
def admin_courses():
    """Admin view for managing courses"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    courses = Course.query.all()
    
    # Create a dummy course object for the base template
    class DummyCourse:
        id = None
        name = "Course Management"
        code = ""
        instructor_id = None
        
        def get_enrollment_count(self):
            return 0
            
        def get_lecture_count(self):
            return 0
            
        def get_material_count(self):
            return 0
    
    dummy_course = DummyCourse()
    
    return render_template('courses/admin/courses.html', courses=courses, course=dummy_course)

@courses_bp.route('/admin/course/new', methods=['GET', 'POST'])
@login_required
def new_course():
    """Create a new course"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    # Create a dummy course object for the base template
    dummy_course = {
        "id": None,
        "name": "New Course",
        "code": "",
        "instructor_id": None
    }
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        description = request.form.get('description')
        
        if not name or not code:
            flash('Course name and code are required', 'error')
            return redirect(url_for('courses.new_course'))
        
        # Check if course code already exists
        existing_course = Course.query.filter_by(code=code).first()
        if existing_course:
            flash('A course with this code already exists', 'error')
            return redirect(url_for('courses.new_course'))
        
        course = Course(
            name=name,
            code=code,
            description=description
        )
        db.session.add(course)
        db.session.commit()
        
        # Create course materials directory
        course_dir = os.path.join(current_app.config['COURSE_MATERIALS_FOLDER'], str(course.id))
        if not os.path.exists(course_dir):
            os.makedirs(course_dir)
        
        flash(f'Course "{name}" created successfully', 'success')
        return redirect(url_for('courses.admin_courses'))
    
    return render_template('courses/admin/new_course.html', course=dummy_course)

@courses_bp.route('/admin/course/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    """Edit an existing course"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        description = request.form.get('description')
        
        if not name or not code:
            flash('Course name and code are required', 'error')
            return redirect(url_for('courses.edit_course', course_id=course_id))
        
        # Check if course code already exists (excluding this course)
        existing_course = Course.query.filter(Course.code == code, Course.id != course_id).first()
        if existing_course:
            flash('A course with this code already exists', 'error')
            return redirect(url_for('courses.edit_course', course_id=course_id))
        
        course.name = name
        course.code = code
        course.description = description
        db.session.commit()
        
        flash(f'Course "{name}" updated successfully', 'success')
        return redirect(url_for('courses.admin_courses'))
    
    return render_template('courses/admin/edit_course.html', course=course)

@courses_bp.route('/admin/course/<int:course_id>/delete', methods=['POST'])
@login_required
def delete_course(course_id):
    """Delete a course"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    course = Course.query.get_or_404(course_id)
    
    # Delete course materials directory
    course_dir = os.path.join(current_app.config['COURSE_MATERIALS_FOLDER'], str(course.id))
    if os.path.exists(course_dir):
        import shutil
        shutil.rmtree(course_dir)
    
    db.session.delete(course)
    db.session.commit()
    
    flash(f'Course "{course.name}" deleted successfully', 'success')
    return redirect(url_for('courses.admin_courses'))

@courses_bp.route('/admin/course/<int:course_id>/lectures', methods=['GET'])
@login_required
def course_lectures(course_id):
    """Manage lectures for a course"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    course = Course.query.get_or_404(course_id)
    lectures = Lecture.query.filter_by(course_id=course_id).order_by(Lecture.week_number, Lecture.start_time).all()
    
    # Group lectures by week
    lectures_by_week = {}
    for lecture in lectures:
        if lecture.week_number not in lectures_by_week:
            lectures_by_week[lecture.week_number] = []
        lectures_by_week[lecture.week_number].append(lecture)
    
    # Get current datetime for template comparisons
    from datetime import datetime
    current_time = get_current_time()
    
    return render_template(
        'courses/admin/lectures.html', 
        course=course, 
        lectures=lectures,
        lectures_by_week=lectures_by_week,
        now=lambda: current_time  # Pass a function that returns current time
    )

@courses_bp.route('/admin/course/<int:course_id>/lecture/new', methods=['GET', 'POST'])
@login_required
def new_lecture(course_id):
    """Create a new lecture for a course"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        week_number = request.form.get('week_number')
        location = request.form.get('location')
        date = request.form.get('date')  # This is new
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')  # This is new
        
        if not all([title, week_number, date, start_time, end_time]):
            flash('All required fields must be filled out', 'error')
            return render_template('courses/admin/new_lecture.html', course=course)
        
        try:
            # Parse date and times
            start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
            
            # Get day of week
            day_of_week = start_datetime.strftime('%A')  # Monday, Tuesday, etc.
            
            lecture = Lecture(
                course_id=course_id,
                title=title,
                week_number=int(week_number),
                day_of_week=day_of_week,
                start_time=start_datetime,
                end_time=end_datetime,
                location=location
            )
            db.session.add(lecture)
            db.session.commit()
            
            # Create week directory if it doesn't exist
            week_dir = os.path.join(
                current_app.config['COURSE_MATERIALS_FOLDER'],
                str(course_id),
                str(week_number)
            )
            if not os.path.exists(week_dir):
                os.makedirs(week_dir)
            
            flash(f'Lecture "{title}" created successfully', 'success')
            return redirect(url_for('courses.course_lectures', course_id=course_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating lecture: {str(e)}', 'error')
            return render_template('courses/admin/new_lecture.html', course=course)
    
    return render_template('courses/admin/new_lecture.html', course=course)

@courses_bp.route('/admin/lecture/<int:lecture_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lecture(lecture_id):
    """Edit an existing lecture"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    lecture = Lecture.query.get_or_404(lecture_id)
    course = Course.query.get(lecture.course_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        week_number = request.form.get('week_number')
        date = request.form.get('date')  # Changed from start_date to date
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')  # Changed from duration to end_time
        location = request.form.get('location')
        
        if not all([title, week_number, date, start_time, end_time]):  # Updated required fields
            flash('All fields are required', 'error')
            return redirect(url_for('courses.edit_lecture', lecture_id=lecture_id))
        
        try:
            # Parse date and times
            start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
            
            # Get day of week
            day_of_week = start_datetime.strftime('%A')  # Monday, Tuesday, etc.
            
            # Check if week number changed
            old_week = lecture.week_number
            new_week = int(week_number)
            
            lecture.title = title
            lecture.week_number = new_week
            lecture.day_of_week = day_of_week
            lecture.start_time = start_datetime
            lecture.end_time = end_datetime
            lecture.location = location
            
            db.session.commit()
            
            # If week changed, create new week directory if needed
            if old_week != new_week:
                week_dir = os.path.join(
                    current_app.config['COURSE_MATERIALS_FOLDER'],
                    str(course.id),
                    str(new_week)
                )
                if not os.path.exists(week_dir):
                    os.makedirs(week_dir)
            
            flash(f'Lecture "{title}" updated successfully', 'success')
            return redirect(url_for('courses.course_lectures', course_id=course.id))
        except Exception as e:
            flash(f'Error updating lecture: {str(e)}', 'error')
            return redirect(url_for('courses.edit_lecture', lecture_id=lecture_id))
    
    # Format date and time for the form
    start_date = lecture.start_time.strftime('%Y-%m-%d')
    start_time = lecture.start_time.strftime('%H:%M')
    end_time = lecture.end_time.strftime('%H:%M')  # Added end_time instead of duration
    
    return render_template(
        'courses/admin/edit_lecture.html', 
        course=course, 
        lecture=lecture,
        start_date=start_date,
        start_time=start_time,
        end_time=end_time  # Pass end_time to the template
    )

@courses_bp.route('/admin/lecture/<int:lecture_id>/delete', methods=['POST'])
@login_required
def delete_lecture(lecture_id):
    """Delete a lecture"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    lecture = Lecture.query.get_or_404(lecture_id)
    course_id = lecture.course_id
    
    db.session.delete(lecture)
    db.session.commit()
    
    flash(f'Lecture "{lecture.title}" deleted successfully', 'success')
    return redirect(url_for('courses.course_lectures', course_id=course_id))

@courses_bp.route('/admin/course/<int:course_id>/materials', methods=['GET'])
@login_required
def course_materials(course_id):
    """Manage materials for a course"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    course = Course.query.get_or_404(course_id)
    materials = Material.query.filter_by(course_id=course_id).order_by(Material.week_number, Material.title).all()
    
    # Group materials by week
    materials_by_week = {}
    for material in materials:
        if material.week_number not in materials_by_week:
            materials_by_week[material.week_number] = []
        materials_by_week[material.week_number].append(material)
    
    return render_template(
        'courses/admin/materials.html', 
        course=course, 
        materials=materials,
        materials_by_week=materials_by_week
    )

@courses_bp.route('/admin/material/<int:material_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_material(material_id):
    """Edit an existing material"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    material = Material.query.get_or_404(material_id)
    course = Course.query.get(material.course_id)
    lectures = Lecture.query.filter_by(course_id=course.id).order_by(Lecture.week_number, Lecture.start_time).all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        week_number = request.form.get('week_number')
        lecture_id = request.form.get('lecture_id')
        
        if not title or not week_number:
            flash('Title and week number are required', 'error')
            return redirect(url_for('courses.edit_material', material_id=material_id))
        
        # Update material details
        material.title = title
        material.description = description
        material.week_number = int(week_number)
        material.lecture_id = lecture_id if lecture_id and lecture_id != 'none' else None
        
        # Check if a new file was uploaded
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            
            if file and allowed_file(file.filename):
                try:
                    # Delete old file if it exists
                    if os.path.exists(material.file_path):
                        os.remove(material.file_path)
                    
                    # Secure the filename
                    filename = secure_filename(file.filename)
                    
                    # Create directory structure
                    week_dir = os.path.join(
                        current_app.config['COURSE_MATERIALS_FOLDER'],
                        str(course.id),
                        str(week_number)
                    )
                    if not os.path.exists(week_dir):
                        os.makedirs(week_dir)
                    
                    # Save the file
                    file_path = os.path.join(week_dir, filename)
                    file.save(file_path)
                    
                    # Update file path and type
                    material.file_path = file_path
                    material.file_type = filename.rsplit('.', 1)[1].lower()
                except Exception as e:
                    flash(f'Error updating file: {str(e)}', 'error')
                    return redirect(url_for('courses.edit_material', material_id=material_id))
            else:
                flash(f'File type not allowed. Allowed types: {", ".join(current_app.config["ALLOWED_EXTENSIONS"])}', 'error')
                return redirect(url_for('courses.edit_material', material_id=material_id))
        
        db.session.commit()
        flash(f'Material "{title}" updated successfully', 'success')
        return redirect(url_for('courses.course_materials', course_id=course.id))
    
    return render_template(
        'courses/admin/edit_material.html', 
        course=course,
        material=material,
        lectures=lectures
    )


@courses_bp.route('/admin/course/<int:course_id>/material/new', methods=['GET', 'POST'])
@login_required
def new_material(course_id):
    """Upload a new material for a course"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    course = Course.query.get_or_404(course_id)
    lectures = Lecture.query.filter_by(course_id=course_id).order_by(Lecture.week_number, Lecture.start_time).all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        week_number = request.form.get('week_number')
        lecture_id = request.form.get('lecture_id')
        
        if not title or not week_number:
            flash('Title and week number are required', 'error')
            return redirect(url_for('courses.new_material', course_id=course_id))
        
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(url_for('courses.new_material', course_id=course_id))
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(url_for('courses.new_material', course_id=course_id))
        
        if file and allowed_file(file.filename):
            try:
                # Secure the filename
                filename = secure_filename(file.filename)
                
                # Create directory structure
                week_dir = os.path.join(
                    current_app.config['COURSE_MATERIALS_FOLDER'],
                    str(course_id),
                    str(week_number)
                )
                if not os.path.exists(week_dir):
                    os.makedirs(week_dir)
                
                # Save the file
                file_path = os.path.join(week_dir, filename)
                file.save(file_path)
                
                # Get file extension for file type
                file_type = filename.rsplit('.', 1)[1].lower()
                
                # Create material record
                material = Material(
                    course_id=course_id,
                    lecture_id=lecture_id if lecture_id and lecture_id != 'none' else None,
                    title=title,
                    description=description,
                    file_path=file_path,
                    file_type=file_type,
                    week_number=int(week_number)
                )
                db.session.add(material)
                db.session.commit()
                
                flash(f'Material "{title}" uploaded successfully', 'success')
                return redirect(url_for('courses.course_materials', course_id=course_id))
            except Exception as e:
                flash(f'Error uploading material: {str(e)}', 'error')
                return redirect(url_for('courses.new_material', course_id=course_id))
        else:
            flash(f'File type not allowed. Allowed types: {", ".join(current_app.config["ALLOWED_EXTENSIONS"])}', 'error')
            return redirect(url_for('courses.new_material', course_id=course_id))
    
    return render_template('courses/admin/new_material.html', course=course, lectures=lectures)

@courses_bp.route('/admin/material/<int:material_id>/delete', methods=['POST'])
@login_required
def delete_material(material_id):
    """Delete a material"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    material = Material.query.get_or_404(material_id)
    course_id = material.course_id
    
    # Delete the file
    if os.path.exists(material.file_path):
        os.remove(material.file_path)
    
    db.session.delete(material)
    db.session.commit()
    
    flash(f'Material "{material.title}" deleted successfully', 'success')
    return redirect(url_for('courses.course_materials', course_id=course_id))

@courses_bp.route('/admin/course/<int:course_id>/enrollments', methods=['GET'])
@login_required
def course_enrollments(course_id):
    """Manage enrollments for a course"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    course = Course.query.get_or_404(course_id)
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    
    # Get all users who are not enrolled in this course
    enrolled_user_ids = [e.student_id for e in enrollments]
    available_users = User.query.filter(User.id.notin_(enrolled_user_ids), User.is_admin == False).all()
    
    # Get lecture count for attendance percentage calculation
    lecture_count = Lecture.query.filter_by(course_id=course_id).count()
    
    return render_template(
        'courses/admin/enrollments.html', 
        course=course, 
        enrollments=enrollments,
        available_users=available_users,
        lecture_count=lecture_count
    )

@courses_bp.route('/admin/course/<int:course_id>/enroll', methods=['POST'])
@login_required
def add_enrollment(course_id):
    """Enroll a student in a course"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    course = Course.query.get_or_404(course_id)
    
    # Check if it's individual enrollment or bulk enrollment
    enrollment_type = request.form.get('enrollment_type')
    
    if enrollment_type == 'individual':
        # Get selected user IDs (can be multiple)
        user_ids = request.form.getlist('user_ids')
        
        if not user_ids:
            flash('Please select at least one student to enroll', 'error')
            return redirect(url_for('courses.course_enrollments', course_id=course_id))
        
        # Enroll each selected student
        enrolled_count = 0
        for user_id in user_ids:
            # Check if student is already enrolled
            existing_enrollment = Enrollment.query.filter_by(
                student_id=user_id,
                course_id=course_id
            ).first()
            
            if not existing_enrollment:
                # Create enrollment
                enrollment = Enrollment(
                    student_id=user_id,
                    course_id=course_id
                )
                db.session.add(enrollment)
                enrolled_count += 1
        
        db.session.commit()
        
        if enrolled_count > 0:
            flash(f'Successfully enrolled {enrolled_count} student(s)', 'success')
        else:
            flash('No new students were enrolled (they may already be enrolled)', 'info')
            
    elif enrollment_type == 'bulk':
        # Process bulk enrollment by email
        email_list = request.form.get('email_list', '').strip()
        
        if not email_list:
            flash('Please provide at least one email address', 'error')
            return redirect(url_for('courses.course_enrollments', course_id=course_id))
        
        # Split the email list by line breaks
        emails = [email.strip() for email in email_list.split('\n') if email.strip()]
        
        # Enroll each student by email
        enrolled_count = 0
        not_found_count = 0
        
        for email in emails:
            # Find user by email
            user = User.query.filter_by(email=email).first()
            
            if user:
                # Check if already enrolled
                existing_enrollment = Enrollment.query.filter_by(
                    student_id=user.id,
                    course_id=course_id
                ).first()
                
                if not existing_enrollment:
                    # Create enrollment
                    enrollment = Enrollment(
                        student_id=user.id,
                        course_id=course_id
                    )
                    db.session.add(enrollment)
                    enrolled_count += 1
            else:
                not_found_count += 1
        
        db.session.commit()
        
        if enrolled_count > 0:
            flash(f'Successfully enrolled {enrolled_count} student(s)', 'success')
        if not_found_count > 0:
            flash(f'{not_found_count} email(s) could not be found in the system', 'warning')
    
    return redirect(url_for('courses.course_enrollments', course_id=course_id))

@courses_bp.route('/admin/enrollment/<int:enrollment_id>/delete', methods=['POST'])
@login_required
def delete_enrollment(enrollment_id):
    """Remove a student from a course"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    course_id = enrollment.course_id
    student = User.query.get(enrollment.student_id)
    
    db.session.delete(enrollment)
    db.session.commit()
    
    flash(f'Student "{student.name}" removed from course', 'success')
    return redirect(url_for('courses.course_enrollments', course_id=course_id))

@courses_bp.route('/admin/material/<int:material_id>/views')
@login_required
def material_views(material_id):
    """View statistics for a material"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    material = Material.query.get_or_404(material_id)
    course = Course.query.get(material.course_id)
    
    # Get all enrollments for this course
    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    students = [User.query.get(e.student_id) for e in enrollments]
    
    # Get view data for each student
    student_views = []
    for student in students:
        view = MaterialView.query.filter_by(
            material_id=material_id,
            user_id=student.id
        ).first()
        
        student_views.append({
            'student': student,
            'viewed': view is not None,
            'downloaded': view.downloaded if view else False,
            'viewed_at': view.viewed_at if view else None
        })
    
    return render_template(
        'courses/admin/material_views.html',
        material=material,
        course=course,
        student_views=student_views
    )

@courses_bp.route('/admin/lecture/<int:lecture_id>/attendance')
@login_required
def lecture_attendance(lecture_id):
    """View attendance for a lecture"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    lecture = Lecture.query.get_or_404(lecture_id)
    course = Course.query.get(lecture.course_id)
    
    # Get all enrollments for this course
    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    students = [User.query.get(e.student_id) for e in enrollments]
    
    # Get attendance data for each student
    student_attendance = []
    attendance_count = 0  # Initialize attendance count
    
    for student in students:
        attendance = Attendance.query.filter_by(
            lecture_id=lecture_id,
            user_id=student.id
        ).first()
        
        is_present = attendance is not None
        if is_present:
            attendance_count += 1  # Increment attendance count
            
        student_attendance.append({
            'student': student,
            'present': is_present,
            'timestamp': attendance.timestamp if attendance else None,
            'attendance_id': attendance.id if attendance else None
        })
    
    # Calculate the enrolled count
    enrolled_count = len(students)
    
    return render_template(
        'courses/admin/lecture_attendance.html',
        lecture=lecture,
        course=course,
        student_attendance=student_attendance,
        attendance_count=attendance_count,
        enrolled_count=enrolled_count
    )

@courses_bp.route('/admin/student/<int:student_id>/activity')
@login_required
def student_activity(student_id):
    """View activity timeline for a student"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    student = User.query.get_or_404(student_id)
    
    # Get all attendance records
    attendances = Attendance.query.filter_by(user_id=student_id).order_by(Attendance.timestamp.desc()).all()
    
    # Get all material views
    material_views = MaterialView.query.filter_by(user_id=student_id).order_by(MaterialView.viewed_at.desc()).all()
    
    # Combine into a timeline
    timeline = []
    
    for attendance in attendances:
        lecture = Lecture.query.get(attendance.lecture_id) if attendance.lecture_id else None
        course = Course.query.get(lecture.course_id) if lecture else None
        
        timeline.append({
            'type': 'attendance',
            'timestamp': attendance.timestamp,
            'lecture': lecture,
            'course': course
        })
    
    for view in material_views:
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
    
    return render_template(
        'courses/admin/student_activity.html',
        student=student,
        timeline=timeline
    )

@courses_bp.route('/admin/course/<int:course_id>/attendance')
@login_required
def course_attendance(course_id):
    """View attendance statistics for a course"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    course = Course.query.get_or_404(course_id)
    lectures = Lecture.query.filter_by(course_id=course_id).order_by(Lecture.start_time).all()
    
    # Get all enrollments for this course
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    students = [User.query.get(e.student_id) for e in enrollments]
    
    # Build attendance matrix
    attendance_data = []
    for student in students:
        student_attendance = {
            'student': student,
            'attendance': [],
            'total_present': 0,
            'percentage': 0
        }
        
        for lecture in lectures:
            attendance = Attendance.query.filter_by(
                lecture_id=lecture.id,
                user_id=student.id
            ).first()
            
            present = attendance is not None
            student_attendance['attendance'].append({
                'lecture': lecture,
                'present': present,
                'timestamp': attendance.timestamp if attendance else None
            })
            
            if present:
                student_attendance['total_present'] += 1
        
        # Calculate attendance percentage
        if lectures:
            student_attendance['percentage'] = (student_attendance['total_present'] / len(lectures)) * 100
        
        attendance_data.append(student_attendance)
    
    return render_template(
        'courses/admin/course_attendance.html',
        course=course,
        lectures=lectures,
        attendance_data=attendance_data
    )

@courses_bp.route('/admin/lecture/<int:lecture_id>/export', methods=['GET'])
@login_required
def export_attendance(lecture_id):
    """Export attendance data for a lecture to Excel"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    lecture = Lecture.query.get_or_404(lecture_id)
    course = Course.query.get(lecture.course_id)
    
    # Get all enrollments for this course
    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    students = [User.query.get(e.student_id) for e in enrollments]
    
    # Create a pandas DataFrame for the attendance data
    import pandas as pd
    from io import BytesIO
    
    data = []
    for student in students:
        attendance = Attendance.query.filter_by(
            lecture_id=lecture_id,
            user_id=student.id
        ).first()
        
        data.append({
            'Student ID': student.custom_data or '',
            'Name': student.name,
            'Email': student.email,
            'Status': 'Present' if attendance else 'Absent',
            'Time': attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S') if attendance else ''
        })
    
    df = pd.DataFrame(data)
    
    # Create an Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Attendance', index=False)
        
        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Attendance']
        
        # Add a header format
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # Write the column headers with the defined format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        # Set column widths
        worksheet.set_column('A:A', 15)  # Student ID
        worksheet.set_column('B:B', 25)  # Name
        worksheet.set_column('C:C', 30)  # Email
        worksheet.set_column('D:D', 10)  # Status
        worksheet.set_column('E:E', 20)  # Time
    
    # Set up the response
    output.seek(0)
    
    filename = f"attendance_{course.code}_{lecture.start_time.strftime('%Y-%m-%d')}.xlsx"
    
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@courses_bp.route('/admin/lecture/<int:lecture_id>/print', methods=['GET'])
@login_required
def print_attendance(lecture_id):
    """Generate a printable PDF of attendance for a lecture using wkhtmltopdf"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    lecture = Lecture.query.get_or_404(lecture_id)
    course = Course.query.get(lecture.course_id)
    
    # Get current time for the report
    current_time = get_current_time()
    
    # Get all enrollments for this course
    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    students = [User.query.get(e.student_id) for e in enrollments]
    
    # Get attendance data for each student
    student_attendance = []
    attendance_count = 0
    
    for student in students:
        attendance = Attendance.query.filter_by(
            lecture_id=lecture_id,
            user_id=student.id
        ).first()
        
        is_present = attendance is not None
        if is_present:
            attendance_count += 1
            
        student_attendance.append({
            'student': student,
            'present': is_present,
            'timestamp': attendance.timestamp if attendance else None
        })
    
    # Calculate attendance percentage
    enrolled_count = len(students)
    attendance_percentage = (attendance_count / enrolled_count * 100) if enrolled_count > 0 else 0
    
    # Render the attendance data to an HTML template
    html = render_template(
        'courses/admin/print_attendance.html',
        lecture=lecture,
        course=course,
        student_attendance=student_attendance,
        attendance_count=attendance_count,
        enrolled_count=enrolled_count,
        attendance_percentage=attendance_percentage,
        current_time=current_time,
        print_view=True
    )
    
    # Use wkhtmltopdf to convert HTML to PDF
    import pdfkit
    import tempfile
    import os
    
    # Create a temporary file for the HTML
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
        f.write(html.encode('utf-8'))
        html_path = f.name
    
    # Define PDF options
    options = {
        'page-size': 'A4',
        'margin-top': '1cm',
        'margin-right': '1cm',
        'margin-bottom': '1cm',
        'margin-left': '1cm',
        'encoding': 'UTF-8',
        'no-outline': None,
        'enable-local-file-access': None  # Important for loading local images
    }
    
    # Create a temporary file for the PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        pdf_path = f.name
    
    try:
        # Configure pdfkit to use the wkhtmltopdf path from config
        config = pdfkit.configuration(wkhtmltopdf=current_app.config['WKHTMLTOPDF_PATH'])
        
        # Generate PDF with the configured path
        pdfkit.from_file(html_path, pdf_path, options=options, configuration=config)
        
        # Prepare the response
        filename = f"attendance_{course.code}_{lecture.start_time.strftime('%Y-%m-%d')}.pdf"
        
        # Send the PDF file
        response = send_file(
            pdf_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
        # Delete the PDF file after sending
        @response.call_on_close
        def cleanup():
            os.unlink(pdf_path)
            os.unlink(html_path)
        
        return response
    
    except Exception as e:
        # Clean up files in case of error
        os.unlink(html_path)
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('courses.lecture_attendance', lecture_id=lecture_id))


@courses_bp.route('/admin/course/<int:course_id>/print_summary', methods=['GET'])
@login_required
def print_course_attendance_summary(course_id):
    """Generate a printable PDF summary of attendance for an entire course using wkhtmltopdf"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    course = Course.query.get_or_404(course_id)
    lectures = Lecture.query.filter_by(course_id=course_id).order_by(Lecture.start_time).all()
    
    # Get current time for the report
    current_time = get_current_time()
    
    # Get all enrollments for this course
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    students = [User.query.get(e.student_id) for e in enrollments]
    
    # Build attendance matrix
    attendance_data = []
    for student in students:
        student_attendance = {
            'student': student,
            'attendance': [],
            'total_present': 0,
            'percentage': 0
        }
        
        for lecture in lectures:
            attendance = Attendance.query.filter_by(
                lecture_id=lecture.id,
                user_id=student.id
            ).first()
            
            present = attendance is not None
            student_attendance['attendance'].append({
                'lecture': lecture,
                'present': present,
                'timestamp': attendance.timestamp if attendance else None
            })
            
            if present:
                student_attendance['total_present'] += 1
        
        # Calculate attendance percentage
        if lectures:
            student_attendance['percentage'] = (student_attendance['total_present'] / len(lectures)) * 100
        
        attendance_data.append(student_attendance)
    
    # Render the attendance data to an HTML template
    html = render_template(
        'courses/admin/print_course_summary.html',
        course=course,
        lectures=lectures,
        attendance_data=attendance_data,
        current_time=current_time
    )
    
    # Use wkhtmltopdf to convert HTML to PDF
    import pdfkit
    import tempfile
    import os
    
    # Create a temporary file for the HTML
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
        f.write(html.encode('utf-8'))
        html_path = f.name
    
    # Define PDF options
    options = {
        'page-size': 'A4',
        'orientation': 'Landscape',  # Use landscape for wide tables
        'margin-top': '1cm',
        'margin-right': '1cm',
        'margin-bottom': '1cm',
        'margin-left': '1cm',
        'encoding': 'UTF-8',
        'no-outline': None,
        'enable-local-file-access': None  # Important for loading local images
    }
    
    # Create a temporary file for the PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        pdf_path = f.name
    
    try:
        # Configure pdfkit to use the wkhtmltopdf path from config
        config = pdfkit.configuration(wkhtmltopdf=current_app.config['WKHTMLTOPDF_PATH'])
        
        # Generate PDF with the configured path
        pdfkit.from_file(html_path, pdf_path, options=options, configuration=config)
        
        # Prepare the response
        filename = f"attendance_summary_{course.code}.pdf"
        
        # Send the PDF file
        response = send_file(
            pdf_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
        # Delete the PDF file after sending
        @response.call_on_close
        def cleanup():
            os.unlink(pdf_path)
            os.unlink(html_path)
        
        return response
    
    except Exception as e:
        # Clean up files in case of error
        os.unlink(html_path)
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('courses.course_attendance', course_id=course_id))


@courses_bp.route('/debug/lectures/<int:course_id>')
@login_required
def debug_lectures(course_id):
    """Debug view to check lecture data"""
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    course = Course.query.get_or_404(course_id)
    lectures = Lecture.query.filter_by(course_id=course_id).all()
    
    lecture_data = []
    for lecture in lectures:
        lecture_data.append({
            'id': lecture.id,
            'title': lecture.title,
            'week_number': lecture.week_number,
            'day_of_week': lecture.day_of_week,
            'start_time': lecture.start_time,
            'end_time': lecture.end_time,
            'location': lecture.location
        })
    
    return render_template(
        'courses/admin/debug_lectures.html',
        course=course,
        lectures=lecture_data
    )


@courses_bp.route('/get_active_lectures')
@login_required
def get_active_lectures():
    """API endpoint to get active lectures for the current user"""
    from datetime import datetime, timedelta
    
    # Get current time
    now = get_current_time()
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
        
        if course_ids:  # Only query if there are enrolled courses
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



@courses_bp.route('/admin/lecture/<int:lecture_id>/mark_attendance/<int:student_id>', methods=['POST'])
@login_required
def admin_mark_attendance(lecture_id, student_id):
    """Mark a student as present for a lecture (admin only)"""
    if not current_user.is_admin:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Permission denied'})
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    lecture = Lecture.query.get_or_404(lecture_id)
    student = User.query.get_or_404(student_id)
    
    # Check if attendance already exists
    existing_attendance = Attendance.query.filter_by(
        lecture_id=lecture_id,
        user_id=student_id
    ).first()
    
    if existing_attendance:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Attendance already marked'})
        flash('Attendance already marked for this student', 'warning')
        return redirect(url_for('courses.lecture_attendance', lecture_id=lecture_id))
    
    # Create new attendance record
    attendance = Attendance(
        lecture_id=lecture_id,
        user_id=student_id,
        timestamp=datetime.utcnow()
    )
    db.session.add(attendance)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True, 
            'message': 'Attendance marked successfully',
            'attendance_id': attendance.id,
            'timestamp': attendance.timestamp.strftime('%H:%M:%S')
        })
    
    flash('Attendance marked successfully', 'success')
    return redirect(url_for('courses.lecture_attendance', lecture_id=lecture_id))

@courses_bp.route('/admin/attendance/<int:attendance_id>/remove', methods=['POST'])
@login_required
def admin_remove_attendance(attendance_id):
    """Remove an attendance record (admin only)"""
    if not current_user.is_admin:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Permission denied'})
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('courses.index'))
    
    attendance = Attendance.query.get_or_404(attendance_id)
    lecture_id = attendance.lecture_id
    
    db.session.delete(attendance)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Attendance removed successfully'})
    
    flash('Attendance removed successfully', 'success')
    return redirect(url_for('courses.lecture_attendance', lecture_id=lecture_id))

