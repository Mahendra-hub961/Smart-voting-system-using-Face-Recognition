# voting.py
import os
import base64
import random
import string
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import face_recognition
from flask import (
    Flask, render_template, request, jsonify, redirect, session, url_for, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

# ------------------ CONFIG ------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET", "supersecretkey")
app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Upload folders
BASE_UPLOAD = os.path.join('static', 'uploads')
ID_FOLDER = os.path.join(BASE_UPLOAD, 'ids')
AADHAAR_FOLDER = os.path.join(BASE_UPLOAD, 'aadhaar')
PHOTO_FOLDER = os.path.join('static', 'voter_photos')
SYMBOL_FOLDER = os.path.join('static', 'symbols')
os.makedirs(ID_FOLDER, exist_ok=True)
os.makedirs(AADHAAR_FOLDER, exist_ok=True)
os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(SYMBOL_FOLDER, exist_ok=True)

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'pdf'}

# 2Factor API Key
FAST2SMS_API_KEY = "acdfb63b-d89d-11f0-a6b2-0200cd936042"

def allowed_file(filename: str) -> bool:
    if not filename:
        return False
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in ALLOWED_EXT

def rand_str(n=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

# ------------------ CANDIDATES ------------------
candidates = [
    {"name": "BJP", "symbol": "bjp.png"},
    {"name": "Congress", "symbol": "congress.png"},
    {"name": "JDS", "symbol": "jds.png"},
    {"name": "AIDMK", "symbol": "aidmk.png"},
    {"name": "AITC", "symbol": "aitc.png"},
    {"name": "BRS", "symbol": "brs.png"},
    {"name": "BSP", "symbol": "bsp.png"},
    {"name": "AAP", "symbol": "aap.png"},
    {"name": "Shivsena", "symbol": "shivsena.png"},
    {"name": "SP", "symbol": "sp.png"},
    {"name": "OTHERS", "symbol": "others.png"},
    {"name": "NOTA", "symbol": "nota.png"},
]
CANDIDATE_NAMES = [c["name"] for c in candidates]

# ------------------ MODELS ------------------
class Voter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    mobile = db.Column(db.String(10), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    aadhaar = db.Column(db.String(12), unique=True, nullable=False)
    voter_id_number = db.Column(db.String(64), nullable=True)
    voter_id_filename = db.Column(db.String(255), nullable=True)
    aadhaar_filename = db.Column(db.String(255), nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    constituency = db.Column(db.String(100), nullable=True)
    otp = db.Column(db.String(12))
    face_encoding = db.Column(db.PickleType, nullable=True)
    approved = db.Column(db.Boolean, default=False)
    voted = db.Column(db.Boolean, default=False)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('voter.id'), nullable=False, unique=True)
    candidate = db.Column(db.String(100), nullable=False)
    voter = db.relationship('Voter', backref='votes')

# ------------------ DB INIT ------------------
def initialize_db():
    with app.app_context():
        db.create_all()
        print("DB initialized.")

# ------------------ IMAGE / CAPTCHA HELPERS ------------------
def pil_image_from_bytes(img_bytes: bytes) -> Image.Image:
    img = Image.open(BytesIO(img_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img

def numpy_image_from_bytes(img_bytes: bytes) -> np.ndarray:
    img = pil_image_from_bytes(img_bytes)
    return np.array(img)

def save_bytes_to_file(path: str, img_bytes: bytes):
    with open(path, "wb") as f:
        f.write(img_bytes)

def mask_aadhaar(aadhaar: str) -> str:
    if not aadhaar or len(aadhaar) != 12:
        return aadhaar or ''
    return f"XXXX-XXXX-{aadhaar[-4:]}"

def generate_captcha_text(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_captcha_image(text):
    width, height = 200, 70
    img = Image.new('RGB', (width, height), (255,255,255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()
    for _ in range(6):
        start = (random.randint(0,width), random.randint(0,height))
        end = (random.randint(0,width), random.randint(0,height))
        draw.line([start, end], fill=(200,200,200), width=1)
    x = 12
    for ch in text:
        y = random.randint(6, 18)
        draw.text((x, y), ch, font=font, fill=(random.randint(10,80), random.randint(10,80), random.randint(10,80)))
        x += 34
    for _ in range(120):
        draw.point((random.randint(0,width), random.randint(0, height)), fill=(random.randint(0,255), random.randint(0,255), random.randint(0,255)))
    img = img.filter(ImageFilter.SMOOTH)
    return img

# ------------------ ROUTES ------------------
@app.route('/')
def index():
    return render_template('index.html', candidates=candidates)

@app.route('/face_verify')
def face_verify():
    return render_template('face_verify.html')

@app.route('/uploads/ids/<path:filename>')
def serve_id_upload(filename):
    return send_from_directory(ID_FOLDER, filename, as_attachment=False)

@app.route('/uploads/aadhaar/<path:filename>')
def serve_aadhaar_upload(filename):
    return send_from_directory(AADHAAR_FOLDER, filename, as_attachment=False)

@app.route('/voter_photos/<path:filename>')
def serve_voter_photo(filename):
    return send_from_directory(PHOTO_FOLDER, filename, as_attachment=False)

@app.route('/captcha')
def captcha():
    text = generate_captcha_text(5)
    session['captcha_text'] = text
    img = generate_captcha_image(text)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return app.response_class(buf.getvalue(), mimetype='image/png')

# ------------------ REGISTER ------------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        mobile = request.form.get('mobile','').strip()
        age = request.form.get('age','').strip()
        aadhaar = request.form.get('aadhaar','').strip()
        voter_id_number = request.form.get('voter_id_number','').strip()
        country = request.form.get('country','').strip()
        state = request.form.get('state','').strip()
        constituency = request.form.get('constituency','').strip()
        captcha_input = request.form.get('captcha','').strip()
        voter_id_file = request.files.get('voter_id_file')
        aadhaar_file = request.files.get('aadhaar_file')

        # Validation checks
        required_fields = [name,email,mobile,age,aadhaar,voter_id_number,country,state,constituency]
        if not all(required_fields):
            return render_template('register.html', error="All fields are required.",
                                   name=name,email=email,mobile=mobile,
                                   age=age,aadhaar=aadhaar,voter_id_number=voter_id_number,
                                   country=country,state=state,constituency=constituency)
        if not (mobile.isdigit() and len(mobile)==10):
            return render_template('register.html', error="Enter valid 10-digit mobile number",
                                   name=name,email=email,mobile=mobile,age=age,aadhaar=aadhaar,
                                   voter_id_number=voter_id_number,country=country,state=state,constituency=constituency)
        if not (age.isdigit() and int(age)>=18):
            return render_template('register.html', error="You must be 18 or older",
                                   name=name,email=email,mobile=mobile,age=age,aadhaar=aadhaar,
                                   voter_id_number=voter_id_number,country=country,state=state,constituency=constituency)
        if not (aadhaar.isdigit() and len(aadhaar)==12):
            return render_template('register.html', error="Aadhaar must be 12 digits",
                                   name=name,email=email,mobile=mobile,age=age,aadhaar=aadhaar,
                                   voter_id_number=voter_id_number,country=country,state=state,constituency=constituency)
        if captcha_input.upper() != session.get('captcha_text',''):
            return render_template('register.html', error="Invalid CAPTCHA",
                                   name=name,email=email,mobile=mobile,age=age,aadhaar=aadhaar,
                                   voter_id_number=voter_id_number,country=country,state=state,constituency=constituency)
        if Voter.query.filter_by(aadhaar=aadhaar).first():
            return render_template('register.html', error="Aadhaar already registered",
                                   name=name,email=email,mobile=mobile,age=age,aadhaar=aadhaar,
                                   voter_id_number=voter_id_number,country=country,state=state,constituency=constituency)
        if not voter_id_file or voter_id_file.filename=='':
            return render_template('register.html', error="Voter ID document is required",
                                   name=name,email=email,mobile=mobile,age=age,aadhaar=aadhaar,
                                   voter_id_number=voter_id_number,country=country,state=state,constituency=constituency)
        if not aadhaar_file or aadhaar_file.filename=='':
            return render_template('register.html', error="Aadhaar document is required",
                                   name=name,email=email,mobile=mobile,age=age,aadhaar=aadhaar,
                                   voter_id_number=voter_id_number,country=country,state=state,constituency=constituency)
        if not allowed_file(voter_id_file.filename):
            return render_template('register.html', error="Invalid voter ID file type",
                                   name=name,email=email,mobile=mobile,age=age,aadhaar=aadhaar,
                                   voter_id_number=voter_id_number,country=country,state=state,constituency=constituency)
        if not allowed_file(aadhaar_file.filename):
            return render_template('register.html', error="Invalid Aadhaar file type",
                                   name=name,email=email,mobile=mobile,age=age,aadhaar=aadhaar,
                                   voter_id_number=voter_id_number,country=country,state=state,constituency=constituency)

        # Save files
        voter_id_filename = secure_filename(f"{rand_str(6)}id{voter_id_file.filename}")
        aadhaar_filename = secure_filename(f"{rand_str(6)}aad{aadhaar_file.filename}")
        voter_id_file.save(os.path.join(ID_FOLDER, voter_id_filename))
        aadhaar_file.save(os.path.join(AADHAAR_FOLDER, aadhaar_filename))

        # Create voter & OTP
        otp = str(random.randint(100000,999999))
        voter = Voter(
            name=name,email=email,mobile=mobile,age=int(age),
            aadhaar=aadhaar,voter_id_number=voter_id_number,
            voter_id_filename=voter_id_filename,aadhaar_filename=aadhaar_filename,
            country=country,state=state,constituency=constituency,
            otp=otp,approved=False,voted=False
        )
        db.session.add(voter)
        db.session.commit()

        # Send OTP via SMS
        try:
            url = f"https://2factor.in/API/V1/{FAST2SMS_API_KEY}/SMS/+91{mobile}/{otp}/SmartVoting"
            resp = requests.get(url)
            print("SMS OTP response:", resp.text)
            msg = f"OTP sent via SMS to {mobile}"
        except Exception as e:
            print("OTP sending failed:", e)
            msg = "OTP sending failed"

        session.pop('captcha_text', None)
        return render_template('verify_otp.html', email=email, voice_msg=msg)

    return render_template('register.html')

# ------------------ VERIFY OTP ------------------
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    email = request.form.get('email','').strip()
    user_otp = request.form.get('otp','').strip()
    voter = Voter.query.filter_by(email=email).order_by(Voter.id.desc()).first()
    if not voter:
        return render_template('verify_otp.html', email=email, error="No registration found", voice_msg="No registration found")
    if voter.otp == user_otp:
        return render_template('upload_face.html', voter_id=voter.id, voice_msg="OTP verified successfully")
    return render_template('verify_otp.html', email=email, error="Invalid OTP", voice_msg="Invalid OTP")

# ------------------ UPLOAD FACE ------------------
@app.route('/save_face', methods=['POST'])
def save_face():
    voter_id = request.form.get('voter_id')
    captured_image = request.form.get('captured_image','')
    uploaded = request.files.get('photo')

    if not voter_id:
        return "Missing voter id", 400
    voter = db.session.get(Voter,int(voter_id))
    if not voter:
        return "Voter not found", 404

    filename = f"voter_{voter.id}.jpg"
    save_path = os.path.join(PHOTO_FOLDER, filename)

    if uploaded and uploaded.filename:
        save_bytes_to_file(save_path, uploaded.read())
    elif captured_image:
        try:
            header, data = captured_image.split(',',1)
            save_bytes_to_file(save_path, base64.b64decode(data))
        except:
            return "Invalid image",400
    else:
        return "No image provided",400

    # face encoding
    try:
        encs = face_recognition.face_encodings(numpy_image_from_bytes(open(save_path,"rb").read()))
    except Exception as e:
        os.remove(save_path)
        return f"Failed to process image: {e}",500

    if not encs:
        os.remove(save_path)
        return render_template('upload_face.html', voter_id=voter.id, error="No face detected", voice_msg="No face detected")

    encoding = encs[0]
    # check duplicate faces
    for v in Voter.query.filter(Voter.face_encoding.isnot(None)).all():
        try:
            if face_recognition.compare_faces([v.face_encoding], encoding, tolerance=0.45)[0]:
                os.remove(save_path)
                return render_template('upload_face.html', voter_id=voter.id, error="Face already registered", voice_msg="Face already registered")
        except: pass

    voter.photo_filename = filename
    voter.face_encoding = encoding
    db.session.commit()
    return render_template('registered_wait.html', voice_msg="Face registered successfully")

# ------------------ FACE VERIFY FOR VOTING ------------------
@app.route('/verify', methods=['POST'])
def verify():
    if not request.is_json:
        return jsonify({'status':'fail','message':'Invalid request'})

    data = request.get_json()
    image_data = data.get('image')

    if not image_data:
        return jsonify({'status':'fail','message':'No image provided'})

    try:
        header, imgdata = image_data.split(',', 1)
        img_bytes = base64.b64decode(imgdata)
        encs = face_recognition.face_encodings(numpy_image_from_bytes(img_bytes))
    except:
        encs = []

    if not encs:
        return jsonify({'status':'fail','message':'No face detected'})

    encoding = encs[0]
    voters = Voter.query.filter_by(approved=True).all()

    for v in voters:
        if v.face_encoding is None:
            continue
        try:
            match = face_recognition.compare_faces([v.face_encoding], encoding, tolerance=0.45)[0]
        except:
            match = False

        if match:
            # Prevent multiple voting
            existing_vote = Vote.query.filter_by(voter_id=v.id).first()
            if v.voted or existing_vote:
                return jsonify({'status': 'fail', 'message': 'You already voted'})

            session['voter_id'] = v.id
            session['voter_name'] = v.name
            return jsonify({'status': 'success', 'message': 'Face verified'})

    return jsonify({'status':'fail','message':'Face not recognized'})

# ------------------ VOTING ------------------
@app.route('/vote', methods=['GET','POST'])
def vote():
    voter_id = session.get('voter_id')
    if not voter_id:
        return redirect(url_for('face_verify'))

    voter = db.session.get(Voter, voter_id)
    if not voter or not voter.approved:
        session.clear()
        return redirect(url_for('face_verify'))

    # Prevent multiple voting
    existing_vote = Vote.query.filter_by(voter_id=voter.id).first()
    if existing_vote or voter.voted:
        voter.voted = True
        db.session.commit()
        session.clear()
        return render_template('vote.html', candidates=candidates, error="You have already voted")

    if request.method == 'POST':
        candidate = request.form.get('candidate')
        if not candidate or candidate not in CANDIDATE_NAMES:
            return render_template('vote.html', candidates=candidates, error="Invalid candidate")

        # Save vote
        vote = Vote(voter_id=voter.id, candidate=candidate)
        db.session.add(vote)

        # Mark voter as voted
        voter.voted = True
        db.session.commit()

        session.clear()
        return render_template('vote.html', candidates=candidates, message="Thank you for voting")

    return render_template('vote.html', candidates=candidates)

# ------------------ VOTER TRACKING ------------------
@app.route('/track', methods=['GET', 'POST'])
def track_status():
    if request.method == 'POST':
        aadhaar = request.form.get('aadhaar', '').strip()
        if not aadhaar or not aadhaar.isdigit() or len(aadhaar) != 12:
            return render_template('track_status.html', error="Enter valid 12-digit Aadhaar number", voice_msg="Enter valid 12-digit Aadhaar number")
        voter = Voter.query.filter_by(aadhaar=aadhaar).first()
        if not voter:
            return render_template('track_status.html', error="No voter found with this Aadhaar number", voice_msg="No voter found with this Aadhaar number")
        return render_template('track_status.html', voter=voter, masked_aadhaar=mask_aadhaar(voter.aadhaar))
    return render_template('track_status.html')

# ------------------ ADMIN ------------------
@app.route('/admin', methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username=='admin6106' and password=='rulebreakers@123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error="Invalid credentials")
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    pending_voters = Voter.query.filter_by(approved=False).all()
    vote_counts = {c["name"]: Vote.query.filter_by(candidate=c["name"]).count() for c in candidates}
    total_votes = Vote.query.count()
    total_voters = Voter.query.filter_by(approved=True).count()
    votes = Vote.query.all()
    for v in pending_voters:
        v._masked_aadhaar = mask_aadhaar(getattr(v,'aadhaar',''))
    return render_template('admin_dashboard.html',
                           pending_voters=pending_voters,
                           vote_counts=vote_counts,
                           total_votes=total_votes,
                           total_voters=total_voters,
                           candidates=candidates,
                           voters=Voter.query.all(),
                           votes=votes)

@app.route('/admin/approve/<int:voter_id>', methods=['POST'])
def admin_approve(voter_id):
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    v = db.session.get(Voter,voter_id)
    if v:
        v.approved = True
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject/<int:voter_id>', methods=['POST'])
def admin_reject(voter_id):
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    v = db.session.get(Voter,voter_id)
    if v:
        if v.photo_filename: os.remove(os.path.join(PHOTO_FOLDER,v.photo_filename))
        if v.voter_id_filename: os.remove(os.path.join(ID_FOLDER,v.voter_id_filename))
        if v.aadhaar_filename: os.remove(os.path.join(AADHAAR_FOLDER,v.aadhaar_filename))
        db.session.delete(v)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_vote/<int:vote_id>', methods=['POST'])
def admin_delete_vote(vote_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    vote = db.session.get(Vote, vote_id)
    if vote:
        voter = db.session.get(Voter, vote.voter_id)
        if voter:
            voter.voted = False
        db.session.delete(vote)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in',None)
    return redirect(url_for('admin_login'))

# ------------------ RUN ------------------
if __name__=='__main__':
    initialize_db()
    app.run(debug=True)
    