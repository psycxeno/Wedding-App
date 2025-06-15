from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import pandas as pd
from flask_mail import Mail, Message
import io
from flask_migrate import Migrate
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure database
if 'DATABASE_URL' in os.environ:
    # Heroku PostgreSQL
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL'].replace('postgres://', 'postgresql://')
else:
    # Local SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wedding.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))

# Log template folder path
logger.debug(f"Template folder: {app.template_folder}")
logger.debug(f"Template folder exists: {os.path.exists(app.template_folder)}")
logger.debug(f"Template folder contents: {os.listdir(app.template_folder) if os.path.exists(app.template_folder) else 'N/A'}")

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Migration commands (run these in terminal):
# flask db init
# flask db migrate -m "Initial migration"
# flask db upgrade

# User Model for Admin Authentication
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# RSVP Model
class RSVP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=True)
    attending = db.Column(db.Boolean, nullable=False)
    guests = db.Column(db.Integer, default=0)
    dietary_restrictions = db.Column(db.String(200))
    message = db.Column(db.Text)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'attending': self.attending,
            'guests': self.guests,
            'dietary_restrictions': self.dietary_restrictions,
            'message': self.message,
            'submission_date': self.submission_date.isoformat()
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Enhanced Admin interface with statistics
@app.route('/admin')
@login_required
def admin():
    total_rsvps = RSVP.query.count()
    attending = RSVP.query.filter_by(attending=True).count()
    not_attending = RSVP.query.filter_by(attending=False).count()
    total_guests = db.session.query(db.func.sum(RSVP.guests)).filter_by(attending=True).scalar() or 0
    
    rsvps = RSVP.query.all()
    return render_template('admin.html', 
                         rsvps=rsvps,
                         total_rsvps=total_rsvps,
                         attending=attending,
                         not_attending=not_attending,
                         total_guests=total_guests)

# Export RSVPs to CSV
@app.route('/export/csv')
@login_required
def export_csv():
    rsvps = RSVP.query.all()
    data = [rsvp.to_dict() for rsvp in rsvps]
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'rsvps_{datetime.now().strftime("%Y%m%d")}.csv'
    )

# Edit RSVP
@app.route('/api/rsvp/<int:rsvp_id>', methods=['PUT'])
@login_required
def edit_rsvp(rsvp_id):
    rsvp = RSVP.query.get_or_404(rsvp_id)
    data = request.json
    
    try:
        rsvp.name = data.get('name', rsvp.name)
        rsvp.email = data.get('email', rsvp.email)
        rsvp.attending = data.get('attending', rsvp.attending)
        rsvp.guests = data.get('guests', rsvp.guests)
        rsvp.dietary_restrictions = data.get('dietary_restrictions', rsvp.dietary_restrictions)
        rsvp.message = data.get('message', rsvp.message)
        
        db.session.commit()
        return jsonify({'message': 'RSVP updated successfully', 'rsvp': rsvp.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Delete RSVP
@app.route('/api/rsvp/<int:rsvp_id>', methods=['DELETE'])
@login_required
def delete_rsvp(rsvp_id):
    rsvp = RSVP.query.get_or_404(rsvp_id)
    try:
        db.session.delete(rsvp)
        db.session.commit()
        return jsonify({'message': 'RSVP deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Modified submit_rsvp to include better error handling
@app.route('/api/rsvp', methods=['POST'])
def submit_rsvp():
    try:
        # Check if request has JSON data
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'attending']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create RSVP
        rsvp = RSVP(
            name=data['name'],
            email=data.get('email', ''),
            attending=data['attending'],
            guests=data.get('guests', 0),
            dietary_restrictions=data.get('dietary_restrictions', ''),
            message=data.get('message', '')
        )
        
        # Add to database
        db.session.add(rsvp)
        db.session.commit()
        
        # Send email notification
        try:
            msg = Message(
                'New RSVP Received',
                sender=app.config['MAIL_USERNAME'],
                recipients=[app.config['MAIL_USERNAME']]
            )
            msg.body = f"""
            New RSVP received:
            Name: {rsvp.name}
            Email: {rsvp.email}
            Attending: {'Yes' if rsvp.attending else 'No'}
            Guests: {rsvp.guests}
            Dietary Restrictions: {rsvp.dietary_restrictions}
            Message: {rsvp.message}
            """
            mail.send(msg)
        except Exception as email_error:
            print(f"Email sending failed: {str(email_error)}")
            # Continue even if email fails
        
        return jsonify({
            'message': 'RSVP submitted successfully',
            'rsvp': rsvp.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        print(f"Error in submit_rsvp: {str(e)}")  # Print error for debugging
        return jsonify({'error': str(e)}), 400

# Update static file serving
@app.route('/')
def home():
    logger.debug("Attempting to render index.html")
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        raise

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Add a route for the map
@app.route('/map')
def map():
    return redirect('https://maps.app.goo.gl/pEro2gBK8Z8FWbwu6')

# Create database tables
# db.create_all()  # Commented out to prevent duplicate table creation in production

@app.route('/api/check-name/<name>')
def check_name(name):
    exists = RSVP.query.filter_by(name=name).first() is not None
    return jsonify({'exists': exists})

if __name__ == '__main__':
    app.run(debug=True)
