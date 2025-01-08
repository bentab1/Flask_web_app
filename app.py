from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from werkzeug.exceptions import RequestEntityTooLarge
from functools import wraps
from datetime import datetime, timedelta
import random
import string

# Initialize Flask app
app = Flask(__name__)
load_dotenv()  # Load environment variables from .env file

# Configure the database URI (PostgreSQL example)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:Ubmc1987#$@127.0.0.1/paycare')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Setup folder to save CV and Cover Letter
app.config['UPLOAD_FOLDER'] = 'C:/Users/benja/pythonvenv/Flask_web_app/Files/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx'}

# Set maximum content length (2MB)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit

# Secret key for session management (flash messages)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_default_secret_key')

# Initialize the database
db = SQLAlchemy(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Default status values (These can be updated by admin in the backend)
FORM_OPEN = True  # True if form is open, False if closed
ROLE_OPEN_STATUS = {
    'Aggregator': True,
    'Agent': True,
    'Sales': False,
    'Customer Care': True,
    'Finance': False
}

class AccessCode(db.Model):
    __tablename__ = 'access_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(255), nullable=False)
    expiration_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Created at field

    def __init__(self, code, expiration_date):
        self.code = code
        self.expiration_date = expiration_date
# Define the Applicants model (table)
class Applicants(db.Model):
    __tablename__ = 'applicants'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    lga = db.Column(db.String(100), nullable=False)
    ward = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    address = db.Column(db.Text, nullable=False)
    occupation = db.Column(db.String(100), nullable=False)
    cv_file = db.Column(db.String(200), nullable=False)
    cover_letter_file = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')

    def __repr__(self):
        return f'<Applicants {self.name}>'

# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Error handler for file size exceeding the 2MB limit
@app.errorhandler(RequestEntityTooLarge)
def handle_file_size_error(error):
    flash("File size exceeds the 2MB limit. Please upload a smaller file.", "danger")
    return redirect(url_for('index'))

# Mock login check
def is_admin():
    return 'is_admin' in session and session['is_admin']

# Decorator for admin login required
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            return redirect(url_for('login'))  # Redirect to login if not admin
        return f(*args, **kwargs)
    return decorated_function

# Function to generate a random access code
def generate_random_code(length=10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@app.route('/', methods=['GET', 'POST'])
def index():
    error_message = None
    role = None  # Initialize role variable to avoid undefined errors

    # Filter the active roles only
    active_roles = [role_name for role_name, status in ROLE_OPEN_STATUS.items() if status]

    if request.method == 'POST':
        role = request.form.get('role')
        access_code = request.form.get('access_code')

        # Check if access code is entered and valid
        valid_code = AccessCode.query.filter_by(code=access_code).first()
        if valid_code and valid_code.expiration_date > datetime.now():
            if ROLE_OPEN_STATUS.get(role) == False:
                error_message = "This role is closed, please check back some other time."
            else:
                access_code = 'ROLE_OPEN123'  # This can be passed to applicant form for role selection
        else:
            error_message = "Invalid or expired access code. Please try again later."

    return render_template('index.html', 
                           role_open_status=ROLE_OPEN_STATUS, 
                           error_message=error_message, 
                           role=role,
                           active_roles=active_roles)  # Pass active roles to the template


# Route to handle form submission
@app.route('/submit', methods=['POST'])
def submit():
    role = request.form.get('role')
    access_code = request.form.get('access_code')

    # Validate if form is open
    if not FORM_OPEN:
        flash("The application form is closed, please check back some other time.", "danger")
        return redirect(url_for('index'))

    # Check access code validity
    valid_code = AccessCode.query.filter_by(code=access_code).first()
    if not valid_code or valid_code.expiration_date < datetime.now():
        flash("This application has closed, please come back some other time.", "danger")
        return redirect(url_for('index'))

    if ROLE_OPEN_STATUS.get(role) == False:
        flash("This role is closed, please check back some other time.", "danger")
        return redirect(url_for('index'))

    # Collect other form data
    name = request.form.get('name')
    phone = request.form.get('phone')
    email = request.form.get('email')
    address = request.form.get('address')
    occupation = request.form.get('occupation')
    state = request.form.get('state')
    lga = request.form.get('lga')
    ward = request.form.get('ward')

    existing_applicant = Applicants.query.filter((Applicants.phone == phone) | (Applicants.email == email)).first()
    if existing_applicant:
        flash("You have already applied for this role! Thank you!", "danger")
        return redirect(url_for('index', already_applied=True))

    cv_file = request.files.get('cv_file')
    if cv_file and allowed_file(cv_file.filename):
        cv_filename = secure_filename(cv_file.filename)
    else:
        flash("Invalid file for CV. Only PDF, DOC, DOCX are allowed.", "danger")
        return redirect(url_for('index'))

    cover_letter_file = request.files.get('cover_letter_file')
    if cover_letter_file and allowed_file(cover_letter_file.filename):
        cover_letter_filename = secure_filename(cover_letter_file.filename)
    else:
        flash("Invalid file for Cover Letter. Only PDF, DOC, DOCX are allowed.", "danger")
        return redirect(url_for('index'))

    role_folder = os.path.join(app.config['UPLOAD_FOLDER'], role)
    state_folder = os.path.join(role_folder, state)
    applicant_folder = os.path.join(state_folder, name)

    if not os.path.exists(role_folder):
        os.makedirs(role_folder)
    if not os.path.exists(state_folder):
        os.makedirs(state_folder)
    if not os.path.exists(applicant_folder):
        os.makedirs(applicant_folder)

    cv_path = os.path.join(applicant_folder, cv_filename)
    cover_letter_path = os.path.join(applicant_folder, cover_letter_filename)

    cv_file.save(cv_path)
    cover_letter_file.save(cover_letter_path)

    new_applicant = Applicants(
        role=role,
        state=state,
        lga=lga,
        ward=ward,
        name=name,
        phone=phone,
        email=email,
        address=address,
        occupation=occupation,
        cv_file=cv_filename,
        cover_letter_file=cover_letter_filename,
        status='pending'
    )

    try:
        db.session.add(new_applicant)
        db.session.commit()
        flash("Your application has been submitted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {e}", "danger")

    return redirect(url_for('index', success=True))

# Admin panel route
@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin_panel():
    global FORM_OPEN, ROLE_OPEN_STATUS

    if request.method == 'POST':
        FORM_OPEN = 'form_open' in request.form
        for role in ROLE_OPEN_STATUS:
            ROLE_OPEN_STATUS[role] = role in request.form

        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin_panel'))

    # Convert ROLE_OPEN_STATUS dictionary to a list of roles with names and statuses
    roles = [{'id': role, 'name': role, 'status': 'active' if ROLE_OPEN_STATUS[role] else 'inactive'} for role in ROLE_OPEN_STATUS]

    # Fetch access codes along with created_at field for display in admin panel
    all_codes = AccessCode.query.order_by(AccessCode.expiration_date.desc()).all()

    return render_template('admin_panel.html', form_open=FORM_OPEN, roles=roles, all_codes=all_codes)

# Admin route to generate access code
# Route to handle form submission
@app.route('/generate_code', methods=['GET', 'POST'])
@admin_required
def generate_code():
    if request.method == 'POST':
        expiration_date_str = request.form.get('expiration_date')
        try:
            # Convert expiration date from string to datetime object
            expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%dT%H:%M')
            generated_code = generate_random_code()
            new_code = AccessCode(code=generated_code, expiration_date=expiration_date)
            db.session.add(new_code)
            db.session.commit()
            
            # Store generated code and formatted expiration date in session
            session['generated_code'] = generated_code
            session['expiration_date'] = expiration_date.strftime('%Y-%m-%dT%H:%M')  # Ensure correct format

            flash("Access code generated successfully", "success")
        except ValueError:
            flash("Invalid expiration date format", "danger")

    all_codes = AccessCode.query.order_by(AccessCode.expiration_date.desc()).all()
    return render_template('generate_code.html', all_codes=all_codes)

# Admin toggle role status route
@app.route('/admin/toggle_status/<string:role_name>', methods=['POST'])
@admin_required
def admin_toggle_status(role_name):
    if role_name in ROLE_OPEN_STATUS:
        # Toggle the status of the role
        ROLE_OPEN_STATUS[role_name] = not ROLE_OPEN_STATUS[role_name]

        flash(f"Role '{role_name}' status updated successfully!", 'success')
    else:
        flash(f"Invalid role name: '{role_name}'", 'danger')

    return redirect(url_for('admin_panel'))


# Admin login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['is_admin'] = True
            return redirect(url_for('admin_panel'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

# Admin logout route
@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

