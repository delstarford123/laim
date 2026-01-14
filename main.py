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
    if request.method == 'POST':
        # In a real app, you would save these to the database here
        # For now, we just acknowledge the save
        return render_template('settings.html', saved=True)
    return render_template('settings.html', saved=False)
@app.route('/support')
def support():
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
        # Extract Data
        data = {
            'breed': request.form.get('breed', 'Friesian'),
            'age_months': float(request.form.get('age_months', 36)),
            'weight_kg': float(request.form.get('weight_kg', 400)),
            'bcs_score': float(request.form.get('bcs_score', 3.0)),
            'days_since_calving': float(request.form.get('days_since_calving', 60)),
            'activity_index': float(request.form.get('activity_index', 50)),
            'parity': request.form.get('parity', '1'),
            'semen_bull_code': request.form.get('semen_bull_code', 'BULL_A'),
            # Defaults
            'milk_yield_daily': 20.0
        }

        # Predict
        result = predictor.predict(data)

        # 3. SAVE to Database
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