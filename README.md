# 🌐 UniFAS - Face Recognition Attendance System

A modern, web-based attendance tracking system powered by **facial recognition technology**. UniFAS offers a sleek and efficient way to register users, track attendance, and manage records with ease — all in a beautiful, responsive interface.

---

## 📚 Table of Contents

- ✨ [Features](#-features)  
- 🔍 [How It Works](#-how-it-works)  
- 🚀 [Installation](#-installation)  
- 🖥️ [Usage Guide](#-usage-guide)  
- 🔧 [Technical Details](#-technical-details)  
- 🗂️ [Project Structure](#-project-structure)  
- 🤝 [Contributing](#-contributing)  
- 📄 [License](#-license)  

---

## ✨ Features

✅ **Facial Registration** – Add users by scanning their face using the webcam  
✅ **Live Recognition** – Detect and mark attendance in real-time  
✅ **Admin Control Panel** – View, update, and manage user records  
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

```
smart_attendance/
├── app.py              # Main Flask app
├── camera.py           # Webcam interface
├── face_utils.py       # Face logic
├── models.py           # DB models
├── config.py           # Settings
├── templates/          # HTML templates
│   ├── base.html
│   ├── register.html
│   ├── attendance.html
│   └── admin.html
├── cert.pem            # SSL cert
├── key.pem             # SSL key
└── requirements.txt    # Dependencies
```

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

