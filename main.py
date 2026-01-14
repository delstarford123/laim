from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.predict import InseminationPredictor

app = Flask(__name__)
# 1. Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///farm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. Define the 'PredictionHistory' Table
class PredictionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    cow_breed = db.Column(db.String(50))
    bull_code = db.Column(db.String(50))
    probability = db.Column(db.Float)
    recommendation = db.Column(db.String(50))

# Initialize DB (Run this once)
with app.app_context():
    db.create_all()

predictor = InseminationPredictor()
# --- ADD THESE TO YOUR EXISTING MODELS ---

class FarmSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    farm_name = db.Column(db.String(100), default="My Dairy Farm")
    location = db.Column(db.String(100), default="Kenya")
    ai_threshold = db.Column(db.Float, default=0.65)  # The sensitivity (e.g., 0.65)
    genetic_check = db.Column(db.Boolean, default=True)

class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    email = db.Column(db.String(100))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default="Open")

# Ensure you create these tables (run this once or keep in main block)
with app.app_context():
    db.create_all()
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', result=None)
from fpdf import FPDF
import os
# --- ADD THESE TO main.py ---

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    # 1. Fetch existing settings or create defaults if they don't exist
    current_settings = FarmSettings.query.first()
    if not current_settings:
        current_settings = FarmSettings(farm_name="Green Valley Dairy", ai_threshold=0.65)
        db.session.add(current_settings)
        db.session.commit()

    if request.method == 'POST':
        try:
            # 2. Update fields from the form
            current_settings.farm_name = request.form.get('farm_name')
            current_settings.location = request.form.get('location')
            
            # Convert percentage (e.g. "75") to float (0.75)
            threshold_val = int(request.form.get('threshold')) / 100.0
            current_settings.ai_threshold = threshold_val
            
            # Checkbox handling (HTML checkboxes send 'on' if checked, nothing if unchecked)
            current_settings.genetic_check = True if request.form.get('checkGenetic') else False

            db.session.commit()
            
            # 3. Reload with success flag
            return render_template('settings.html', settings=current_settings, saved=True)
            
        except Exception as e:
            return render_template('settings.html', settings=current_settings, error=str(e))

    # GET request: Just show current settings
    return render_template('settings.html', settings=current_settings, saved=False)

@app.route('/support', methods=['GET', 'POST'])
def support():
    if request.method == 'POST':
        try:
            # 1. Extract data
            email = request.form.get('email')
            subject = request.form.get('subject')
            message = request.form.get('message')

            # 2. Create Ticket
            new_ticket = SupportTicket(email=email, subject=subject, message=message)
            db.session.add(new_ticket)
            db.session.commit()

            # 3. Show Success Message
            flash_message = "Ticket Submitted! Reference ID: #{}".format(new_ticket.id)
            return render_template('support.html', success=flash_message)

        except Exception as e:
            return render_template('support.html', error="Failed to submit: " + str(e))

    return render_template('support.html')
@app.route('/download_report/<int:id>')
def download_report(id):
    # 1. Fetch record from DB
    record = PredictionHistory.query.get_or_404(id)
    
    # 2. Create PDF
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
    pdf.set_fill_color(200, 255, 200) if 'PROCEED' in record.recommendation else pdf.set_fill_color(255, 200, 200)
    pdf.cell(0, 10, txt=f"AI Verdict: {record.recommendation}", ln=1, fill=True)
    pdf.cell(0, 10, txt=f"Success Probability: {record.probability}%", ln=1)
    
    # Save & Return
    filename = f"report_{id}.pdf"
    path = os.path.join('static', filename)
    pdf.output(path)
    
    return redirect(url_for('static', filename=filename))
import pandas as pd

@app.route('/catalog')
def catalog():
    # Load the CSV to display on the web
    try:
        # Read the CSV file
        df = pd.read_csv('data/bull_catalog.csv')
        # Convert to a list of dictionaries (easy to loop in HTML)
        bulls = df.to_dict(orient='records')
    except Exception as e:
        bulls = []
        print(f"Error loading catalog: {e}")

    return render_template('catalog.html', bulls=bulls)
@app.route('/predict', methods=['POST'])
def predict():
    try:
        # --- NEW: Get Farm Settings ---
        settings_db = FarmSettings.query.first()
        # Default to 0.65 if database is empty
        threshold = settings_db.ai_threshold if settings_db else 0.65
        # -----------------------------

        data = {
            # ... (your existing inputs) ...
            'breed': request.form.get('breed', 'Friesian'),
            'age_months': float(request.form.get('age_months', 36)),
            'weight_kg': float(request.form.get('weight_kg', 400)),
            'bcs_score': float(request.form.get('bcs_score', 3.0)),
            'days_since_calving': float(request.form.get('days_since_calving', 60)),
            'activity_index': float(request.form.get('activity_index', 50)),
            'parity': request.form.get('parity', '1'),
            'semen_bull_code': request.form.get('semen_bull_code', 'FR_001_KUG'),
            'milk_yield_daily': 20.0
        }

        # Run Prediction
        result = predictor.predict(data)
        
        # --- NEW: Apply Custom Sensitivity Logic ---
        # The AI gives a raw score (e.g., 0.70). 
        # If User set settings to 0.75, this should now be a "DELAY"
        raw_score = result['raw_score'] 
        
        if raw_score >= threshold:
            result['recommendation'] = "✅ PROCEED"
        else:
            result['recommendation'] = "❌ DELAY / CHECK HEALTH"
            # Add explanation if it failed due to high threshold
            if raw_score > 0.50: 
                result['explanation'] += f" (Score {raw_score*100:.1f}% is below your strict threshold of {threshold*100}%)"
        # -------------------------------------------

        # Save to History (Same as before)
        new_record = PredictionHistory(
            cow_breed=data['breed'],
            bull_code=data['semen_bull_code'],
            probability=result['probability'],
            recommendation=result['recommendation']
        )
        db.session.add(new_record)
        db.session.commit()
        
        return render_template('index.html', result=result)

    except Exception as e:
        return render_template('index.html', result={'error': str(e)})
# 4. New Page: View History
@app.route('/history')
def history():
    # Fetch last 50 records, newest first
    records = PredictionHistory.query.order_by(PredictionHistory.date.desc()).limit(50).all()
    return render_template('history.html', records=records)

if __name__ == '__main__':
    app.run(debug=True, port=5000)