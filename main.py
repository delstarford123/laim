import os
import csv
import pandas as pd
from datetime import datetime
from threading import Thread
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from fpdf import FPDF
from dotenv import load_dotenv

# Import local modules
# Ensure src/predict.py exists and works correctly
from src.predict import InseminationPredictor

# --- 1. INITIALIZATION & CONFIGURATION ---
# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_dev_key')  # Required for flash messages

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///farm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'delstarfordisaiah@gmail.com'  # Admin Email
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') # Secure Password from .env
app.config['MAIL_DEFAULT_SENDER'] = ('LAIM Support Bot', 'delstarfordisaiah@gmail.com')

# Initialize Extensions
db = SQLAlchemy(app)
mail = Mail(app)

# Initialize AI Predictor
predictor = InseminationPredictor()


# --- 2. DATABASE MODELS ---

class PredictionHistory(db.Model):
    """Stores the history of all AI predictions made by the user."""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    cow_breed = db.Column(db.String(50))
    bull_code = db.Column(db.String(50))
    probability = db.Column(db.Float)
    recommendation = db.Column(db.String(50))

class FarmSettings(db.Model):
    """Stores configuration for the farm profile and AI sensitivity."""
    id = db.Column(db.Integer, primary_key=True)
    farm_name = db.Column(db.String(100), default="Green Valley Dairy")
    location = db.Column(db.String(100), default="Kakamega")
    ai_threshold = db.Column(db.Float, default=0.65)  # Sensitivity threshold (e.g. 0.65)
    genetic_check = db.Column(db.Boolean, default=True)

class SupportTicket(db.Model):
    """Stores support requests submitted by users."""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    email = db.Column(db.String(100))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default="Open")


# --- 3. HELPER FUNCTIONS ---

def send_async_email(app_obj, msg):
    """Helper function to send emails in a separate thread."""
    with app_obj.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            print(f"❌ Background Email Error: {e}")


# --- 4. CORE ROUTES ---

@app.route('/', methods=['GET'])
def index():
    """Homepage: The Scanner Interface."""
    return render_template('index.html', result=None)


# --- HELPER FUNCTION ---
def get_safe_float(value, default):
    """Safely converts a string to float. Returns default if empty or invalid."""
    try:
        if not value or str(value).strip() == '':
            return float(default)
        return float(value)
    except (ValueError, TypeError):
        return float(default)

# --- THE FULL PREDICT ROUTE ---
@app.route('/predict', methods=['POST'])
def predict():
    """Handles the prediction logic, applies settings, and saves history."""
    try:
        # 1. Get Farm Settings (or defaults)
        settings_db = FarmSettings.query.first()
        threshold = settings_db.ai_threshold if settings_db else 0.65

        # 2. Collect Data SAFELY (Fixes empty string crashes)
        data = {
            'breed': request.form.get('breed', 'Friesian'),
            'parity': request.form.get('parity', '1'),
            'semen_bull_code': request.form.get('semen_bull_code', 'FR_001_KUG'),
            
            # Safe Float Conversions using helper
            'age_months': get_safe_float(request.form.get('age_months'), 36.0),
            'weight_kg': get_safe_float(request.form.get('weight_kg'), 400.0),
            'bcs_score': get_safe_float(request.form.get('bcs_score'), 3.0),
            'days_since_calving': get_safe_float(request.form.get('days_since_calving'), 60.0),
            'activity_index': get_safe_float(request.form.get('activity_index'), 50.0),
            'milk_yield_daily': 20.0  # Hidden default
        }

        # 3. Run AI Prediction
        # (This now calls your updated src/predict.py which handles weather injection)
        result = predictor.predict(data)
        
        # Check for predictor errors (e.g. missing columns)
        if 'error' in result:
            return render_template('index.html', result=result)

        # 4. Apply Custom Sensitivity Logic (Override AI recommendation based on settings)
        raw_score = result.get('raw_score', 0)
        
        if raw_score >= threshold:
            result['recommendation'] = "✅ PROCEED"
        else:
            result['recommendation'] = "❌ DELAY / CHECK HEALTH"
            
            # Add explanation if it failed specifically due to user's high threshold
            if raw_score > 0.50: 
                result['explanation'] += f" (Note: Score {raw_score*100:.1f}% is positive but below your strict threshold of {threshold*100}%)"

        # 5. Save Record to Database
        new_record = PredictionHistory(
            cow_breed=data['breed'],
            bull_code=data['semen_bull_code'],
            probability=result['probability'],
            recommendation=result['recommendation']
        )
        db.session.add(new_record)
        db.session.commit()
        
        # 6. Return Result to User
        return render_template('index.html', result=result)

    except Exception as e:
        print(f"Prediction Route Error: {e}")
        return render_template('index.html', result={'error': f"System Error: {str(e)}"})

@app.route('/history')
def history():
    """Audit Log: View last 50 predictions."""
    records = PredictionHistory.query.order_by(PredictionHistory.date.desc()).limit(50).all()
    return render_template('history.html', records=records)


@app.route('/catalog')
def catalog():
    """Genetics: View the Bull Catalog CSV."""
    bulls = []
    try:
        csv_path = os.path.join('data', 'bull_catalog.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            bulls = df.to_dict(orient='records')
    except Exception as e:
        print(f"Error loading catalog: {e}")

    return render_template('catalog.html', bulls=bulls)


# --- 5. ADMINISTRATIVE ROUTES ---

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Admin Dashboard: Manage Farm Profile and AI Sensitivity."""
    # 1. Fetch existing settings or create defaults
    current_settings = FarmSettings.query.first()
    if not current_settings:
        current_settings = FarmSettings(farm_name="Green Valley Dairy", ai_threshold=0.65)
        db.session.add(current_settings)
        db.session.commit()

    if request.method == 'POST':
        try:
            # 2. Update fields
            current_settings.farm_name = request.form.get('farm_name')
            current_settings.location = request.form.get('location')
            
            # Handle Threshold (Convert "75" -> 0.75)
            threshold_val = request.form.get('threshold')
            if threshold_val:
                current_settings.ai_threshold = int(threshold_val) / 100.0
            
            # Handle Checkbox
            current_settings.genetic_check = True if request.form.get('checkGenetic') else False

            db.session.commit()
            return render_template('settings.html', settings=current_settings, saved=True)
            
        except Exception as e:
            return render_template('settings.html', settings=current_settings, error=str(e))

    return render_template('settings.html', settings=current_settings, saved=False)


@app.route('/admin/bulls', methods=['GET', 'POST'])
def admin_bulls():
    """Knowledge Base: Add/Edit Bulls in CSV."""
    bull_csv_path = os.path.join('data', 'bull_catalog.csv')
    
    # 1. Handle Adding New Bull
    if request.method == 'POST':
        try:
            new_bull = {
                'bull_code': request.form.get('bull_code'),
                'breed': request.form.get('breed'),
                'sire_fertility_score': request.form.get('sire_fertility_score'),
                'straw_motility_percent': request.form.get('straw_motility_percent'),
                'avg_conception_rate': request.form.get('avg_conception_rate'),
                'source': request.form.get('source')
            }

            file_exists = os.path.isfile(bull_csv_path)
            
            with open(bull_csv_path, mode='a', newline='') as csvfile:
                fieldnames = ['bull_code', 'breed', 'sire_fertility_score', 'straw_motility_percent', 'avg_conception_rate', 'source']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()
                writer.writerow(new_bull)

            flash(f"Success! Bull {new_bull['bull_code']} added.", "success")
            
        except Exception as e:
            flash(f"Error adding bull: {str(e)}", "danger")
            
        return redirect('/admin/bulls')

    # 2. Handle Viewing Catalog
    bulls = []
    if os.path.exists(bull_csv_path):
        with open(bull_csv_path, mode='r') as csvfile:
            reader = csv.DictReader(csvfile)
            bulls = list(reader)
    
    return render_template('admin_bulls.html', bulls=bulls)


# --- 6. SUPPORT SYSTEM ---
@app.route('/support', methods=['GET', 'POST'])
def support():
    """Handles support tickets with threaded email notifications."""
    if request.method == 'POST':
        try:
            # 1. Capture Data
            form_data = {
                'fullname': request.form.get('fullname'),
                'phone': request.form.get('phone'),
                'email': request.form.get('email'),
                'location': request.form.get('location'),
                'category': request.form.get('subject'),
                'priority': request.form.get('priority'),
                'message': request.form.get('message')
            }

            # 2. Save to Database
            new_ticket = SupportTicket(email=form_data['email'], subject=form_data['category'], message=form_data['message'])
            db.session.add(new_ticket)
            db.session.commit()
            
            # Generate Logo Link for Email
            logo_link = url_for('static', filename='logo.png', _external=True)

            # 3. Prepare Emails
            # Admin Email
            msg_admin = Message(
                subject=f"[{form_data['priority']}] New Support Ticket #{new_ticket.id}",
                recipients=['delstarfordisaiah@gmail.com'] # Admin Email
            )
            msg_admin.html = render_template('emails/admin_ticket.html', logo_url=logo_link, **form_data, ticket_id=new_ticket.id)

            # User Confirmation Email
            msg_user = Message(
                subject=f"Confirmation: Support Ticket #{new_ticket.id}",
                recipients=[form_data['email']]
            )
            msg_user.html = render_template('emails/user_confirmation.html', logo_url=logo_link, **form_data, ticket_id=new_ticket.id)

            # 4. Send in Background (Threaded)
            # --- THE FIX IS HERE ---
            Thread(target=send_async_email, args=(app, msg_admin)).start()
            Thread(target=send_async_email, args=(app, msg_user)).start()

            return render_template('support.html', success=f"Ticket #{new_ticket.id} Submitted Successfully!")

        except Exception as e:
            return render_template('support.html', error=str(e))

    return render_template('support.html')
# --- 7. UTILITIES & STATIC PAGES ---

@app.route('/download_report/<int:id>')
def download_report(id):
    """Generates a PDF report for a specific prediction."""
    record = PredictionHistory.query.get_or_404(id)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Livestock AI Management Report", ln=1, align='C')
    pdf.line(10, 20, 200, 20)
    pdf.ln(20)
    
    # Details
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Date: {record.date.strftime('%Y-%m-%d')}", ln=1)
    pdf.cell(200, 10, txt=f"Cow Breed: {record.cow_breed}", ln=1)
    pdf.cell(200, 10, txt=f"Bull Code: {record.bull_code}", ln=1)
    pdf.ln(10)
    
    # Result Box
    if 'PROCEED' in record.recommendation:
        pdf.set_fill_color(200, 255, 200) # Green
    else:
        pdf.set_fill_color(255, 200, 200) # Red
        
    pdf.cell(0, 10, txt=f"AI Verdict: {record.recommendation}", ln=1, fill=True)
    pdf.cell(0, 10, txt=f"Success Probability: {record.probability}%", ln=1)
    
    # Save & Redirect
    filename = f"report_{id}.pdf"
    static_folder = os.path.join(app.root_path, 'static')
    os.makedirs(static_folder, exist_ok=True) # Ensure static exists
    
    path = os.path.join(static_folder, filename)
    pdf.output(path)
    
    return redirect(url_for('static', filename=filename))

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

# --- 8. APP EXECUTION ---

# Create tables on startup (if they don't exist)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Use environment port for Render compatibility, default to 5000 local
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)