# 🌐 UniFAS - Face Recognition Attendance System v2.0

A modern, web-based attendance tracking system powered by **facial recognition technology**. UniFAS offers a sleek and efficient way to register users, track attendance, and manage records with ease — all in a beautiful, responsive interface. Now with enhanced course management, user profiles, and interactive features!

---

## 📚 Table of Contents

- ✨ [Features](#features)
- 🔍 [How It Works](#how-it-works)
- 🚀 [Installation](#installation)
- 🖥️ [Usage Guide](#usage-guide)
- 🔧 [Technical Details](#technical-details)
- 🗂️ [Project Structure](#project-structure)
- 📱 [New in Version 2.0](#new-in-version-20)
- 🤝 [Contributing](#contributing)
- 📄 [License](#license)

---

## ✨ Features

✅ **Facial Registration** – Add users by scanning their face using the webcam
✅ **Live Recognition** – Detect and mark attendance in real-time
✅ **Admin Control Panel** – View, update, and manage user records
✅ **Course Management** – Create and manage courses, lectures, and materials
✅ **User Profiles** – Enhanced profiles with activity tracking and statistics
✅ **QR Code Integration** – Generate and download user ID cards with QR codes
✅ **Interactive Calendar** – View schedule and attendance in calendar format
✅ **Toast Notifications** – Modern notification system for better user experience
✅ **Responsive Design** – Works on all screen sizes (desktop + mobile)
✅ **SSL-Ready** – Enable secure access using HTTPS
✅ **Modern Frontend** – Powered by TailwindCSS + AlpineJS

---

## 🔍 How It Works

🎥 **UniFAS** leverages advanced face recognition algorithms to automate attendance in 3 easy steps:

1. **Register** – Capture facial data + personal info
2. **Recognize** – Scan faces live via webcam
3. **Record** – System matches face and logs attendance

---

## 🚀 Installation

### ✅ Prerequisites
- Python **3.8 only** (required for compatibility)
- pip
- Git

### 📦 Step-by-Step Setup

```bash
# 1. Clone the repo
git clone https://github.com/hossmekawy/smart_attendance.git
cd smart_attendance

# 2. Create virtual environment using Python 3.8
python3.8 -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/macOS)
source venv/bin/activate

# 3. Upgrade pip
pip install --upgrade pip

# 4. Install dependencies
pip install numpy==1.22.3
pip install Flask==2.0.1 Werkzeug==2.0.1 Jinja2==3.0.1 itsdangerous==2.0.1 MarkupSafe==2.0.1
pip install opencv-python-headless==4.5.5.64
pip install face_recognition==1.3.0 dlib Flask-SQLAlchemy==2.5.1

# (Optional) Fix for dlib - Windows
pip install https://github.com/jloh02/dlib/releases/download/v19.22/dlib-19.22.99-cp310-cp310-win_amd64.whl

# 5. Generate HTTPS certificate
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# 6. Run the server
python app.py
```

🚀 App will be available at: [https://localhost:5000](https://localhost:5000)
or it will be available with your ipv4

---

## 🖥️ Usage Guide

### 👤 Register a User
- Go to **Register Page**
- Allow camera access
- Position face ➔ Click **Capture Face**
- Fill form ➔ Submit

### 📸 Mark Attendance
- Go to **Attendance Page**
- Camera will auto-detect and mark attendance

### 🛠️ Admin Dashboard
- View all users and records
- Edit / Delete / Audit users

---

## 🔧 Technical Details

### 🧠 Face Recognition Flow
```python
# 1. Detect Face
face_locations = face_recognition.face_locations(image)

# 2. Encode Face
face_encodings = face_recognition.face_encodings(image, face_locations)

# 3. Compare & Match
matches = face_recognition.compare_faces(known_encodings, face_encoding)

# 4. Best Match
face_distances = face_recognition.face_distance(known_encodings, face_encoding)
best_match_index = np.argmin(face_distances)
```

### 🗃️ Database (SQLAlchemy + SQLite)
- `User` model ➔ stores info + face encoding
- `Attendance` model ➔ logs timestamped presence

### 💅 Frontend Stack
- **TailwindCSS** – for responsive UI
- **AlpineJS** – for dynamic interactivity
- **Jinja2** – for template rendering

---

## 🗂️ Project Structure

```python
smart_attendance/
├── app.py              # Main Flask app
├── camera.py           # Webcam interface
├── models.py           # DB models
├── config.py           # Settings
├── auth/               # Authentication module
│   ├── routes.py       # Auth routes
│   └── utils.py        # Auth utilities
├── courses/            # Course management module
│   ├── routes.py       # Course routes
│   └── utils.py        # Course utilities
├── templates/          # HTML templates
│   ├── base.html       # Base template with layout
│   ├── index.html      # Homepage
│   ├── admin.html      # Admin dashboard
│   ├── attendance.html # Attendance page
│   ├── auth/           # Auth templates
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── profile.html
│   │   └── edit_profile.html
│   └── courses/        # Course templates
│       ├── index.html
│       ├── view.html
│       ├── calendar.html
│       └── admin/      # Course admin templates
├── static/             # Static assets
│   ├── css/
│   ├── js/
│   └── images/
├── cert.pem            # SSL cert
├── key.pem             # SSL key
└── requirements.txt    # Dependencies
```

---

## 📱 New in Version 2.0

### 🎉 Major Enhancements

#### 1. Course Management System
- Create and manage courses with detailed information
- Schedule lectures and track attendance for specific sessions
- Upload and share course materials with students
- View course statistics and student engagement

#### 2. Enhanced User Profiles
- Comprehensive activity timeline showing recent actions
- Visual statistics with attendance rates and course engagement
- Personalized QR code ID cards for quick attendance
- Improved profile editing with image upload

#### 3. Modern UI Improvements
- Toast notification system replacing traditional alerts
- Interactive calendar for viewing schedule and attendance
- Improved mobile responsiveness and accessibility
- Enhanced admin dashboard with better data visualization

#### 4. Technical Improvements
- Modular code structure with blueprints
- Improved error handling and user feedback
- Enhanced security features
- Better performance and reliability

---

## 🤝 Contributing

We ❤️ contributions!

```bash
# 1. Fork the repo
# 2. Create a branch
  git checkout -b my-feature
# 3. Make your edits
# 4. Commit & push
  git commit -m "Added awesome feature"
  git push origin my-feature
# 5. Create a Pull Request 🚀
```

---

## 📄 License

Licensed under the [MIT License](LICENSE). Use it, modify it, share it!