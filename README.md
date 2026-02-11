# 🗳 Smart Voting System using Face Recognition

> A secure and intelligent voting application that uses biometric face recognition to authenticate voters and prevent duplicate voting.

---

## 📌 Project Overview

The **Smart Voting System** is a web-based application designed to enhance election security using **Face Recognition technology**.  
The system verifies voters through biometric authentication, ensuring that each individual can vote only once.

This project demonstrates practical implementation of:
- Computer Vision
- Biometric Authentication
- Secure Web Application Development
- Database Management

---

## 🚀 Key Features

- 🔐 Face-based voter authentication  
- 🧑 Secure voter registration system  
- 🛑 Duplicate vote prevention  
- 👨‍💼 Admin dashboard with voter management  
- 🔓 Lock / Unlock voter accounts  
- 📊 Real-time voting result tracking  
- 📧 OTP verification system  
- 🗃 SQLite database integration  

---

## 🛠 Tech Stack

### 🔹 Backend
- Python
- Flask
- Flask-SQLAlchemy

### 🔹 Face Recognition & AI
- OpenCV
- face_recognition
- NumPy
- Pillow

### 🔹 Frontend
- HTML5
- CSS3
- Bootstrap

### 🔹 Database
- SQLite

---

## 📂 Project Structure

```
Smart-voting-system-using-Face-Recognition/
│
├── templates/                 # HTML templates
│   ├── index.html
│   ├── register.html
│   ├── vote.html
│   ├── admin_dashboard.html
│   └── ...
│
├── static/                    # CSS and static files
│   ├── style.css
│
├── voting.py                  # Main Flask application
├── requirements.txt           # Project dependencies
└── README.md
```

---

## ⚙️ Installation & Setup (Anaconda)

### 1️⃣ Clone Repository

```
git clone https://github.com/Mahendra-hub961/Smart-voting-system-using-Face-Recognition.git
cd Smart-voting-system-using-Face-Recognition
```

### 2️⃣ Create Virtual Environment

```
conda create -n voting_env python=3.9
conda activate voting_env
```

### 3️⃣ Install Dependencies

```
pip install -r requirements.txt
```

If requirements file is missing:

```
pip install flask opencv-python face-recognition numpy pillow flask_sqlalchemy
```

### 4️⃣ Run Application

```
python voting.py
```

### 5️⃣ Open in Browser

```
http://127.0.0.1:5000/
```

---

## 🔐 Security Implementation

- Biometric face verification
- One-person one-vote mechanism
- Admin-controlled approval system
- Secure session management
- OTP-based verification layer

---

## 🎯 Future Enhancements

- Aadhaar integration
- SMS & Email OTP verification
- Cloud deployment (AWS / Render)
- Blockchain-based vote storage
- AI-based fraud detection
- Real-time analytics dashboard

---

## 📈 Learning Outcomes

Through this project, I gained hands-on experience in:

- Flask web development
- Face recognition using OpenCV
- Database integration using SQLite
- Backend & frontend integration
- Secure authentication mechanisms

---

## 👨‍💻 Author

**Mahendra V**  
Python Developer | Data Science Enthusiast  
GitHub: https://github.com/Mahendra-hub961

---

⭐ If you found this project interesting, feel free to star the repository!
