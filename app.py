from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from werkzeug.utils import secure_filename
from flask_migrate import Migrate  # Import Migrate

# Initialize Flask app
app = Flask(__name__)
server= app.server
load_dotenv()  # Load environment variables from .env file
# Setup the PostgreSQL database URI
import os

# Adjust DATABASE_URL for PythonAnywhere deployment
# Configure the database URI (MySQL example)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL','deployment://postgres:1234abcd@127.0.0.1/paycare')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Setup folder to save CV and Cover Letter
app.config['UPLOAD_FOLDER'] = 'C:/Users/benja/pythonvenv/Flask_web_app/Files/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx'}

# Secret key for session management (flash messages)
app.secret_key = 'your_secret_key'  # You can use any secret key

# Initialize the database
db = SQLAlchemy(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)  # Initialize Migrate with app and db

# Define the Applicants model (table)
class Applicants(db.Model):
    __tablename__ = 'applicants'  # Updated table name

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(100), nullable=False)  # Added role/job field
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

    def __repr__(self):
        return f'<Applicants {self.name}>'

# Route to display the form
@app.route('/')
def index():
    success = request.args.get('success', False)
    return render_template('index.html', success=success)

# Route to handle form submission
@app.route('/submit', methods=['POST'])
def submit():
    # Get data from the form
    role = request.form.get('role')  # Added role/job selection
    state = request.form.get('state')
    lga = request.form.get('lga')
    ward = request.form.get('ward')
    name = request.form.get('name')
    country_code = request.form.get('countryCode')
    phone = request.form.get('phone')
    email = request.form.get('email')
    address = request.form.get('address')
    occupation = request.form.get('occupation')

    # Combine country code and phone number
    full_phone = f"{country_code}{phone}"

    # Handle file uploads for CV and Cover Letter
    cv_file = request.files.get('cv')
    cover_letter_file = request.files.get('coverLetter')

    # Check if files are allowed
    if not allowed_file(cv_file.filename) or not allowed_file(cover_letter_file.filename):
        flash('Invalid file type. Only PDF, DOC, DOCX are allowed.', 'danger')
        return redirect(url_for('index'))

    # Securely save file and get file path
    cv_filename = secure_filename(cv_file.filename)
    cover_letter_filename = secure_filename(cover_letter_file.filename)

    # Create folder structure
    role_folder = os.path.join(app.config['UPLOAD_FOLDER'], role)
    state_folder = os.path.join(role_folder, state)
    applicant_folder = os.path.join(state_folder, name)

    # Check if the role folder exists, if not create it
    if not os.path.exists(role_folder):
        os.makedirs(role_folder)
    
    # Check if the state folder exists, if not create it
    if not os.path.exists(state_folder):
        os.makedirs(state_folder)
    
    # Check if the applicant's folder exists, if not create it
    if not os.path.exists(applicant_folder):
        os.makedirs(applicant_folder)

    # Paths for saving the files
    cv_path = os.path.join(applicant_folder, cv_filename)
    cover_letter_path = os.path.join(applicant_folder, cover_letter_filename)

    # Save files to the server (uploads folder)
    cv_file.save(cv_path)
    cover_letter_file.save(cover_letter_path)

    # Check if the phone number or email already exists
    existing_applicant = Applicants.query.filter((Applicants.phone == full_phone) | (Applicants.email == email)).first()
    if existing_applicant:
        flash("You have already applied for this role! Thank you!.", "danger")
        return redirect(url_for('index', already_applied=True))

    # Create new applicant and save to the database
    new_applicant = Applicants(
        role=role,  # Added role/job field
        state=state,
        lga=lga,
        ward=ward,
        name=name,
        phone=full_phone,
        email=email,
        address=address,
        occupation=occupation,
        cv_file=cv_path,
        cover_letter_file=cover_letter_path
    )

    # Add to the database session and commit to save
    db.session.add(new_applicant)
    db.session.commit()

    flash("Your application has been submitted successfully!", "success")
    # Redirect to the home page with success message
    return redirect(url_for('index', success=True))


# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

if __name__ == '__main__':
    # Create the tables if they don't exist
    with app.app_context():
        db.create_all()
    app.run(debug=True)
