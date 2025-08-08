from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import re
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import sqlite3
import os

app = Flask(__name__)
CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Database setup
def init_db():
    conn = sqlite3.connect('consultations.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS consult_bp (
            consult_id TEXT PRIMARY KEY,
            patient_name TEXT,
            patient_age TEXT,
            bp_measured TEXT,
            pr TEXT,
            rbs TEXT,
            bp_date TEXT,
            date_measures TEXT,
            created_at TEXT,
            complete_data TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "success", "message": "UniDoc Medical Transcription API is running"}), 200

@app.route('/process', methods=['POST', 'OPTIONS'])
def process_medical_text():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        text = data.get('medical_text', '').strip()
        consult_id = data.get('consult_id', '').strip()
        patient_name = data.get('patient_name', '').strip()
        patient_age = data.get('patient_age', '').strip()

        if not text or not consult_id or not patient_name:
            return jsonify({"error": "Missing required fields: medical_text, consult_id, patient_name"}), 400

        print(f"🩺 Processing medical text: {text[:100]}...")
        
        # Enhanced extraction using smart text analysis
        extracted_data = extract_medical_data_smart(text)
        extracted_data['patient_name'] = patient_name
        extracted_data['patient_age'] = patient_age
        extracted_data['consult_id'] = consult_id

        print(f"✅ Extraction completed: {json.dumps(extracted_data, indent=2)}")

        return jsonify({
            "status": "success",
            "message": "Medical text processed successfully",
            "data": extracted_data
        }), 200
    except Exception as e:
        print(f"❌ Processing error: {str(e)}")
        return jsonify({"error": f"Processing error: {str(e)}"}), 500

def extract_medical_data_smart(text):
    """
    Smart medical data extraction that only extracts what's actually present in the text
    """
    print("🔍 Starting smart medical data extraction...")
    
    # Clean text first
    text = clean_and_normalize_text(text)
    print(f"📝 Cleaned text: {text}")
    
    # Extract each component only if present
    result = {
        "chief_complaint": extract_chief_complaint_smart(text),
        "consult_summary": extract_consultation_summary_smart(text),
        "vitals_examination": extract_vitals_smart(text),
        "medication_data": extract_medications_smart(text),
        "investigations": extract_investigations_smart(text),
        "medicine_templates": extract_templates_smart(text, "medicine"),
        "super_templates": extract_templates_smart(text, "super"),
        "advice": extract_advice_smart(text),
        "follow_up_day": extract_follow_up_day_smart(text),
        "follow_up_mode": extract_follow_up_mode_smart(text),
        "visit_type": extract_visit_type_smart(text)
    }
    
    print(f"🎯 Final extraction result: {json.dumps(result, indent=2)}")
    return result

def clean_and_normalize_text(text):
    """Clean and normalize medical text"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Normalize common medical abbreviations
    text = re.sub(r'\bBP\s*[:=]\s*', 'blood pressure is ', text, flags=re.IGNORECASE)
    text = re.sub(r'\bPR\s*[:=]\s*', 'pulse rate is ', text, flags=re.IGNORECASE)
    text = re.sub(r'\bHR\s*[:=]\s*', 'heart rate is ', text, flags=re.IGNORECASE)
    text = re.sub(r'\bRBS\s*[:=]\s*', 'random blood sugar is ', text, flags=re.IGNORECASE)
    text = re.sub(r'\bTemp\s*[:=]\s*', 'temperature is ', text, flags=re.IGNORECASE)
    
    return text

def extract_chief_complaint_smart(text):
    """Extract chief complaint only if explicitly mentioned"""
    patterns = [
        r'complaint(?:s)?\s+of\s+([^.!?]+)[.!?]',
        r'presented?\s+with\s+([^.!?]+)[.!?]',
        r'complain(?:s|ing)?\s+(?:of|about)\s+([^.!?]+)[.!?]',
        r'came\s+with\s+([^.!?]+)[.!?]',
        r'chief\s+complaint\s*[:\-]?\s*([^.!?]+)[.!?]',
        r'main\s+concern\s*[:\-]?\s*([^.!?]+)[.!?]',
        r'primary\s+symptom\s*[:\-]?\s*([^.!?]+)[.!?]',
        r'history\s+of\s+present\s+illness\s*[:\-]?\s*([^.!?]+)[.!?]'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            complaint = match.group(1).strip()
            # Clean up the complaint
            complaint = re.sub(r'^(a|an|the)\s+', '', complaint, flags=re.IGNORECASE)
            complaint = complaint.strip(' .,;')
            
            if len(complaint) > 5:  # Must be meaningful
                print(f"✅ Found chief complaint: {complaint}")
                return complaint
    
    print("❌ No chief complaint found")
    return ""

def extract_consultation_summary_smart(text):
    """Extract consultation summary from examination findings and clinical notes"""
    summary_parts = []
    
    # Look for examination findings
    exam_patterns = [
        r'on\s+(?:physical\s+)?examination[,:]?\s*([^.!?]+)',
        r'examination\s+(?:shows?|reveals?)\s+([^.!?]+)',
        r'physical\s+findings?\s*[:\-]?\s*([^.!?]+)',
        r'clinical\s+(?:examination|findings?)\s*[:\-]?\s*([^.!?]+)',
        r'assessment\s*[:\-]?\s*([^.!?]+)',
        r'impression\s*[:\-]?\s*([^.!?]+)',
        r'(?:he|she|patient)\s+(?:appears?|looks?|seems?)\s+([^.!?]+)'
    ]
    
    for pattern in exam_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            finding = match.strip()
            # Remove vital signs from summary to avoid duplication
            finding = re.sub(r'\b(?:blood\s+pressure|bp)\s+is\s+\d+/\d+', '', finding, flags=re.IGNORECASE)
            finding = re.sub(r'\b(?:pulse|heart\s+rate|pr|hr)\s+is\s+\d+', '', finding, flags=re.IGNORECASE)
            finding = re.sub(r'\b(?:temperature|temp)\s+is\s+\d+', '', finding, flags=re.IGNORECASE)
            finding = re.sub(r'\bsaturation\s+is\s+\d+%?', '', finding, flags=re.IGNORECASE)
            
            finding = re.sub(r'\s+', ' ', finding).strip(' .,;')
            if len(finding) > 10:
                summary_parts.append(finding)
    
    # Look for clinical observations
    observation_patterns = [
        r'(?:patient|he|she)\s+(?:denies?|reports?|has|shows?)\s+([^.!?]+)',
        r'no\s+(?:signs?|symptoms?)\s+of\s+([^.!?]+)',
        r'positive\s+for\s+([^.!?]+)',
        r'negative\s+for\s+([^.!?]+)',
        r'(?:mild|moderate|severe)\s+([^.!?]+)',
        r'normal\s+([^.!?]+)',
        r'abnormal\s+([^.!?]+)'
    ]
    
    for pattern in observation_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            observation = match.strip(' .,;')
            if len(observation) > 5 and not re.search(r'\d+/\d+|\d+\s*bpm|\d+%', observation):
                summary_parts.append(f"Patient {observation}")
    
    if summary_parts:
        # Remove duplicates and combine
        unique_parts = []
        for part in summary_parts:
            if part not in unique_parts:
                unique_parts.append(part)
        
        result = '. '.join(unique_parts[:3])  # Limit to 3 most relevant findings
        if result and not result.endswith('.'):
            result += '.'
        print(f"✅ Found consultation summary: {result}")
        return result
    
    print("❌ No consultation summary found")
    return ""

def extract_vitals_smart(text):
    """Extract vital signs only if explicitly mentioned with values"""
    vitals = {"bp": "", "pr": "", "rbs": ""}
    
    # Blood Pressure patterns - only extract if numbers are present
    bp_patterns = [
        r'blood\s+pressure\s+is\s+(\d{2,3}\/\d{2,3})',
        r'bp\s+(?:is\s+)?(\d{2,3}\/\d{2,3})',
        r'(\d{2,3}\/\d{2,3})\s*mmhg',
        r'systolic\s+\d+\s+diastolic\s+\d+|(\d{2,3}\/\d{2,3})'
    ]
    
    for pattern in bp_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            vitals['bp'] = match.group(1)
            print(f"✅ Found BP: {vitals['bp']}")
            break
    
    # Pulse/Heart Rate patterns
    pr_patterns = [
        r'pulse\s+(?:rate\s+)?is\s+(\d{2,3})',
        r'heart\s+rate\s+is\s+(\d{2,3})',
        r'pr\s+(?:is\s+)?(\d{2,3})',
        r'hr\s+(?:is\s+)?(\d{2,3})',
        r'(\d{2,3})\s*(?:beats?\s*per\s*minute|bpm)'
    ]
    
    for pattern in pr_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            vitals['pr'] = match.group(1)
            print(f"✅ Found PR: {vitals['pr']}")
            break
    
    # Blood Sugar patterns
    rbs_patterns = [
        r'random\s+blood\s+sugar\s+is\s+(\d{2,3})',
        r'blood\s+sugar\s+is\s+(\d{2,3})',
        r'rbs\s+(?:is\s+)?(\d{2,3})',
        r'glucose\s+(?:level\s+)?(?:is\s+)?(\d{2,3})',
        r'(\d{2,3})\s*mg\/dl'
    ]
    
    for pattern in rbs_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            vitals['rbs'] = match.group(1)
            print(f"✅ Found RBS: {vitals['rbs']}")
            break
    
    # Only return vitals if at least one is found
    if any(vitals.values()):
        print(f"✅ Extracted vitals: {vitals}")
        return vitals
    
    print("❌ No vitals found")
    return {"bp": "", "pr": "", "rbs": ""}

def extract_medications_smart(text):
    """Extract medications only if explicitly mentioned"""
    medications = []
    
    # Common medication database
    common_meds = {
        'aspirin': {'dose': '75mg', 'pattern': '0-0-1', 'duration': 'ongoing', 'when': 'after food'},
        'paracetamol': {'dose': '500mg', 'pattern': '1-0-1', 'duration': '5 days', 'when': 'after food'},
        'atorvastatin': {'dose': '20mg', 'pattern': '0-0-1', 'duration': 'ongoing', 'when': 'after dinner'},
        'statin': {'dose': '20mg', 'pattern': '0-0-1', 'duration': 'ongoing', 'when': 'after dinner'},
        'metformin': {'dose': '500mg', 'pattern': '1-0-1', 'duration': 'ongoing', 'when': 'before food'},
        'amlodipine': {'dose': '5mg', 'pattern': '1-0-0', 'duration': 'ongoing', 'when': 'after breakfast'},
        'pantoprazole': {'dose': '40mg', 'pattern': '1-0-0', 'duration': '30 days', 'when': 'before food'},
        'omeprazole': {'dose': '20mg', 'pattern': '1-0-0', 'duration': '30 days', 'when': 'before food'},
        'insulin': {'dose': 'as prescribed', 'pattern': 'as directed', 'duration': 'ongoing', 'when': 'before meals'},
        'lisinopril': {'dose': '10mg', 'pattern': '1-0-0', 'duration': 'ongoing', 'when': 'before food'},
        'losartan': {'dose': '50mg', 'pattern': '1-0-0', 'duration': 'ongoing', 'when': 'before food'},
        'simvastatin': {'dose': '20mg', 'pattern': '0-0-1', 'duration': 'ongoing', 'when': 'after dinner'}
    }
    
    # Medication extraction patterns
    med_patterns = [
        r'(?:started|prescribed|given|ordered)\s+(?:him|her|patient)?\s*(?:on\s+)?([a-z]+(?:\s+\d+mg)?)',
        r'(?:started|prescribed)\s+([a-z]+(?:\s+\d+mg)?)',
        r'(?:tab|tablet)\s+([a-z]+(?:\s+\d+mg)?)',
        r'i\s+have\s+(?:started|prescribed|given)\s+(?:him|her)?\s*(?:on\s+)?([a-z]+)',
        r'put\s+(?:him|her|patient)\s+on\s+([a-z]+)'
    ]
    
    medication_id = 1
    for pattern in med_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            med_name = match.strip().lower()
            
            # Check if it's a known medication
            base_name = re.sub(r'\s*\d+mg', '', med_name)
            
            if base_name in common_meds:
                # Extract dose if mentioned
                dose_match = re.search(r'(\d+\s*mg)', med_name)
                if dose_match:
                    dose = dose_match.group(1)
                else:
                    dose = common_meds[base_name]['dose']
                
                medications.append({
                    "medication": f"{base_name.title()} {dose}",
                    "dose": common_meds[base_name]['pattern'],
                    "duration": common_meds[base_name]['duration'],
                    "medication_when": common_meds[base_name]['when'],
                    "medication_id": str(medication_id)
                })
                medication_id += 1
                print(f"✅ Found medication: {base_name.title()}")
    
    if medications:
        print(f"✅ Extracted medications: {len(medications)} items")
    else:
        print("❌ No medications found")
    
    return medications

def extract_investigations_smart(text):
    """Extract investigations/tests only if explicitly mentioned"""
    investigations = []
    
    # Common investigations database
    common_tests = {
        'ecg': {'name': 'ECG', 'id': '101'},
        'ekg': {'name': 'ECG', 'id': '101'},
        'electrocardiogram': {'name': 'ECG', 'id': '101'},
        'chest x-ray': {'name': 'Chest X-Ray', 'id': '102'},
        'cxr': {'name': 'Chest X-Ray', 'id': '102'},
        'cardiac enzyme': {'name': 'Cardiac Enzyme Panel', 'id': '103'},
        'cardiac enzymes': {'name': 'Cardiac Enzyme Panel', 'id': '103'},
        'enzyme panel': {'name': 'Cardiac Enzyme Panel', 'id': '103'},
        'troponin': {'name': 'Troponin', 'id': '104'},
        'cbc': {'name': 'Complete Blood Count', 'id': '105'},
        'complete blood count': {'name': 'Complete Blood Count', 'id': '105'},
        'lipid profile': {'name': 'Lipid Profile', 'id': '106'},
        'liver function': {'name': 'Liver Function Test', 'id': '107'},
        'lft': {'name': 'Liver Function Test', 'id': '107'},
        'kidney function': {'name': 'Kidney Function Test', 'id': '108'},
        'kft': {'name': 'Kidney Function Test', 'id': '108'},
        'blood sugar': {'name': 'Blood Sugar Test', 'id': '109'},
        'hba1c': {'name': 'HbA1c', 'id': '110'},
        'urine': {'name': 'Urine Analysis', 'id': '111'},
        'urine analysis': {'name': 'Urine Analysis', 'id': '111'},
        'thyroid': {'name': 'Thyroid Function Test', 'id': '112'},
        'tft': {'name': 'Thyroid Function Test', 'id': '112'}
    }
    
    # Investigation extraction patterns
    investigation_patterns = [
        r'(?:ordered|advised|requested|sent\s+for)\s+(?:a\s+)?([a-z\s]+(?:test|panel|profile|analysis)?)',
        r'i\s+have\s+ordered\s+(?:a\s+)?([a-z\s]+)',
        r'(?:test|check|evaluate)\s+(?:for\s+)?([a-z\s]+)',
        r'rule\s+out.*?(?:with\s+)?(?:a\s+)?([a-z\s]+(?:test|panel|analysis)?)'
    ]
    
    investigation_id = 200
    for pattern in investigation_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            test_name = match.strip().lower()
            test_name = re.sub(r'\s+', ' ', test_name)
            
            # Check if it matches known investigations
            for key, test_info in common_tests.items():
                if key in test_name or test_name in key:
                    investigations.append({
                        "investigation": test_info['name'],
                        "investigation_id": test_info['id']
                    })
                    print(f"✅ Found investigation: {test_info['name']}")
                    break
            else:
                # If it's a reasonable test name, add it
                if len(test_name) > 3 and any(word in test_name for word in ['test', 'scan', 'ray', 'panel', 'profile', 'analysis']):
                    investigations.append({
                        "investigation": test_name.title(),
                        "investigation_id": str(investigation_id)
                    })
                    investigation_id += 1
                    print(f"✅ Found custom investigation: {test_name.title()}")
    
    if investigations:
        print(f"✅ Extracted investigations: {len(investigations)} items")
    else:
        print("❌ No investigations found")
    
    return investigations

def extract_templates_smart(text, template_type):
    """Extract medicine or super templates if mentioned"""
    templates = []
    
    if template_type == "medicine":
        patterns = [
            r'(?:medicine\s+)?template\s+([a-z\s]+)',
            r'protocol\s+for\s+([a-z\s]+)',
            r'standard\s+treatment\s+for\s+([a-z\s]+)'
        ]
    else:  # super templates
        patterns = [
            r'super\s+template\s+([a-z\s]+)',
            r'comprehensive\s+protocol\s+([a-z\s]+)',
            r'advanced\s+treatment\s+([a-z\s]+)'
        ]
    
    template_id = 300 if template_type == "medicine" else 400
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            template_name = match.strip().title()
            if len(template_name) > 3:
                key = "medicine_template_id" if template_type == "medicine" else "super_template_id"
                templates.append({
                    "template_name": template_name,
                    key: str(template_id)
                })
                template_id += 1
                print(f"✅ Found {template_type} template: {template_name}")
    
    if not templates:
        print(f"❌ No {template_type} templates found")
    
    return templates

def extract_advice_smart(text):
    """Extract medical advice only if explicitly mentioned"""
    advice_parts = []
    
    # Advice extraction patterns
    advice_patterns = [
        r'(?:advised?|recommended?|suggested?)\s+(?:him|her|patient)?\s*(?:to\s+)?([^.!?]+)',
        r'i\s+(?:would\s+)?(?:advise|recommend|suggest)\s+([^.!?]+)',
        r'patient\s+(?:should|must|needs?\s+to)\s+([^.!?]+)',
        r'instructions?\s*[:\-]?\s*([^.!?]+)',
        r'(?:follow|continue)\s+([^.!?]+)',
        r'avoid\s+([^.!?]+)',
        r'maintain\s+([^.!?]+)'
    ]
    
    for pattern in advice_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            advice = match.strip(' .,;')
            # Filter out medications and vital signs
            if not re.search(r'\d+mg|\d+/\d+|medication|tablet|pill', advice, re.IGNORECASE):
                if len(advice) > 10:
                    advice_parts.append(advice)
    
    if advice_parts:
        # Remove duplicates and combine
        unique_advice = list(dict.fromkeys(advice_parts))
        result = '. '.join(unique_advice[:2])  # Limit to 2 most relevant advice points
        if result and not result.endswith('.'):
            result += '.'
        print(f"✅ Found advice: {result}")
        return result
    
    print("❌ No advice found")
    return ""

def extract_follow_up_day_smart(text):
    """Extract follow-up timing only if explicitly mentioned"""
    patterns = [
        r'follow\s+up\s+in\s+(\d+)\s*(day|week|month)s?',
        r'(?:see|visit)\s+(?:again|back)\s+in\s+(\d+)\s*(day|week|month)s?',
        r'return\s+(?:after|in)\s+(\d+)\s*(day|week|month)s?',
        r'next\s+(?:visit|appointment)\s+in\s+(\d+)\s*(day|week|month)s?',
        r'reassessment\s+in\s+(\d+)\s*(day|week|month)s?',
        r'come\s+back\s+(?:after|in)\s+(\d+)\s*(day|week|month)s?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            number = match.group(1)
            unit = match.group(2).lower()
            
            if unit == 'day':
                result = f"{number} Day{'s' if int(number) > 1 else ''}"
            elif unit == 'week':
                result = f"{number} Week{'s' if int(number) > 1 else ''}"
            elif unit == 'month':
                result = f"{number} Month{'s' if int(number) > 1 else ''}"
            
            print(f"✅ Found follow-up day: {result}")
            return result
    
    print("❌ No follow-up day found")
    return ""

def extract_follow_up_mode_smart(text):
    """Extract follow-up mode only if explicitly mentioned"""
    if re.search(r'tele(?:consultation)?|video\s+call|online|virtual|phone|remote', text, re.IGNORECASE):
        print("✅ Found follow-up mode: Teleconsultation")
        return "Teleconsultation"
    elif re.search(r'clinic|office|in\s*person|visit|come\s+(?:to|back)', text, re.IGNORECASE):
        print("✅ Found follow-up mode: Clinic Visit")
        return "Clinic Visit"
    
    print("❌ No follow-up mode found")
    return ""

def extract_visit_type_smart(text):
    """Extract visit type only if explicitly mentioned"""
    if re.search(r'tele(?:consultation)?|video|online|virtual|remote', text, re.IGNORECASE):
        print("✅ Found visit type: Teleconsultation")
        return "Teleconsultation"
    elif re.search(r'clinic|office|in\s*person|visit|came\s+to|presented\s+to', text, re.IGNORECASE):
        print("✅ Found visit type: In Person")
        return "In Person"
    
    print("❌ No visit type found")
    return ""

@app.route('/save', methods=['POST', 'OPTIONS'])
def save_to_database():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        consult_id = data.get('consult_id')
        patient_name = data.get('patient_name')
        patient_age = data.get('patient_age')
        extracted_data = data.get('extracted_data')

        if not all([consult_id, patient_name, extracted_data]):
            return jsonify({"error": "Missing required fields: consult_id, patient_name, extracted_data"}), 400

        conn = sqlite3.connect('consultations.db')
        c = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle vitals data
        vitals = extracted_data.get('vitals_examination', {})
        
        c.execute('''
            INSERT OR REPLACE INTO consult_bp (
                consult_id, patient_name, patient_age, bp_measured, pr, rbs, 
                bp_date, date_measures, created_at, complete_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            consult_id,
            patient_name,
            patient_age,
            vitals.get('bp', ''),
            vitals.get('pr', ''),
            vitals.get('rbs', ''),
            now.split(' ')[0],
            now.split(' ')[0],
            now,
            json.dumps(extracted_data)
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Data saved successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/generate_pdf', methods=['POST', 'OPTIONS'])
def generate_pdf():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        patient_info = {
            "name": data.get('patient_name', ''),
            "age": data.get('patient_age', ''),
            "consult_id": data.get('consult_id', '')
        }
        extracted_data = data.get('extracted_data', {})

        if not patient_info['name'] or not extracted_data:
            return jsonify({"error": "Missing required data: patient_name, extracted_data"}), 400

        # Generate PDF with enhanced formatting
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', patient_info['name'])
        pdf_filename = f"Medical_Report_{safe_name}_{patient_info['consult_id']}.pdf"
        
        doc = SimpleDocTemplate(pdf_filename, pagesize=letter, 
                              topMargin=0.5*inch, bottomMargin=0.5*inch, 
                              leftMargin=0.75*inch, rightMargin=0.75*inch)
        styles = getSampleStyleSheet()
        
        # Custom styles for professional look
        custom_styles = {
            'Title': ParagraphStyle(
                name='CustomTitle', parent=styles['Title'], 
                fontName='Helvetica-Bold', fontSize=20, spaceAfter=12, 
                textColor=colors.HexColor('#0066CC'), alignment=1
            ),
            'SubTitle': ParagraphStyle(
                name='CustomSubTitle', parent=styles['Normal'], 
                fontName='Helvetica', fontSize=12, spaceAfter=8, 
                textColor=colors.HexColor('#0066CC')
            ),
            'Heading2': ParagraphStyle(
                name='CustomHeading2', parent=styles['Heading2'], 
                fontName='Helvetica-Bold', fontSize=14, spaceAfter=8, 
                textColor=colors.HexColor('#0066CC')
            ),
            'Normal': ParagraphStyle(
                name='CustomNormal', parent=styles['Normal'], 
                fontName='Helvetica', fontSize=11, spaceAfter=6, leading=14
            ),
            'Footer': ParagraphStyle(
                name='CustomFooter', parent=styles['Normal'], 
                fontName='Helvetica-Oblique', fontSize=9, textColor=colors.grey
            )
        }

        elements = []

        # Hospital Header
        elements.append(Paragraph("UNIDOC MEDICAL CENTER", custom_styles['Title']))
        elements.append(Paragraph("Professional Medical Consultation Report", custom_styles['SubTitle']))
        elements.append(Spacer(1, 0.2*inch))

        # Header line
        line_table = Table([[None]], colWidths=[6.5*inch], rowHeights=[2])
        line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#0066CC'))]))
        elements.append(line_table)
        elements.append(Spacer(1, 0.2*inch))

        # Patient Information
        patient_data = [
            ["Patient Name:", patient_info['name']],
            ["Age:", patient_info['age'] or 'Not specified'],
            ["Consultation ID:", patient_info['consult_id']],
            ["Date of Report:", datetime.now().strftime('%Y-%m-%d')],
            ["Time Generated:", datetime.now().strftime('%H:%M:%S')]
        ]
        
        patient_table = Table(patient_data, colWidths=[2*inch, 4.5*inch])
        patient_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#0066CC')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef'))
        ]))
        
        elements.append(Paragraph("PATIENT INFORMATION", custom_styles['Heading2']))
        elements.append(patient_table)
        elements.append(Spacer(1, 0.2*inch))

        # Only add sections that have data
        
        # Chief Complaint
        if extracted_data.get('chief_complaint'):
            elements.append(Paragraph("CHIEF COMPLAINT", custom_styles['Heading2']))
            elements.append(Paragraph(extracted_data['chief_complaint'], custom_styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))

        # Consultation Summary
        if extracted_data.get('consult_summary'):
            elements.append(Paragraph("CLINICAL EXAMINATION", custom_styles['Heading2']))
            elements.append(Paragraph(extracted_data['consult_summary'], custom_styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))

        # Vitals - only if data exists
        vitals = extracted_data.get('vitals_examination', {})
        if vitals and any(vitals.get(key) for key in ['bp', 'pr', 'rbs']):
            vitals_data = [["Parameter", "Value", "Unit"]]
            
            if vitals.get('bp'):
                vitals_data.append(["Blood Pressure", vitals['bp'], 'mmHg'])
            if vitals.get('pr'):
                vitals_data.append(["Pulse Rate", vitals['pr'], 'bpm'])
            if vitals.get('rbs'):
                vitals_data.append(["Random Blood Sugar", vitals['rbs'], 'mg/dL'])
            
            if len(vitals_data) > 1:  # Has data beyond header
                vitals_table = Table(vitals_data, colWidths=[2.5*inch, 2*inch, 2*inch])
                vitals_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066CC')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONT', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef'))
                ]))
                elements.append(Paragraph("VITAL SIGNS", custom_styles['Heading2']))
                elements.append(vitals_table)
                elements.append(Spacer(1, 0.15*inch))

        # Medications - only if data exists
        if extracted_data.get('medication_data') and len(extracted_data['medication_data']) > 0:
            elements.append(Paragraph("PRESCRIBED MEDICATIONS", custom_styles['Heading2']))
            med_data = [["Medication", "Dosage", "Duration", "Instructions"]]
            
            for med in extracted_data['medication_data']:
                med_data.append([
                    med.get('medication', ''),
                    med.get('dose', ''),
                    med.get('duration', ''),
                    med.get('medication_when', '')
                ])
            
            med_table = Table(med_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            med_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066CC')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONT', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef'))
            ]))
            elements.append(med_table)
            elements.append(Spacer(1, 0.15*inch))

        # Investigations - only if data exists
        if extracted_data.get('investigations') and len(extracted_data['investigations']) > 0:
            elements.append(Paragraph("RECOMMENDED INVESTIGATIONS", custom_styles['Heading2']))
            inv_data = [["Investigation", "ID"]]
            
            for inv in extracted_data['investigations']:
                inv_data.append([
                    inv.get('investigation', ''),
                    inv.get('investigation_id', '')
                ])
            
            inv_table = Table(inv_data, colWidths=[4*inch, 2.5*inch])
            inv_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066CC')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONT', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef'))
            ]))
            elements.append(inv_table)
            elements.append(Spacer(1, 0.15*inch))

        # Medicine Templates - only if data exists
        if extracted_data.get('medicine_templates') and len(extracted_data['medicine_templates']) > 0:
            elements.append(Paragraph("MEDICINE TEMPLATES", custom_styles['Heading2']))
            template_data = [["Template Name", "ID"]]
            
            for template in extracted_data['medicine_templates']:
                template_data.append([
                    template.get('template_name', ''),
                    template.get('medicine_template_id', '')
                ])
            
            template_table = Table(template_data, colWidths=[4*inch, 2.5*inch])
            template_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066CC')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONT', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef'))
            ]))
            elements.append(template_table)
            elements.append(Spacer(1, 0.15*inch))

        # Super Templates - only if data exists
        if extracted_data.get('super_templates') and len(extracted_data['super_templates']) > 0:
            elements.append(Paragraph("SUPER TEMPLATES", custom_styles['Heading2']))
            super_template_data = [["Template Name", "ID"]]
            
            for template in extracted_data['super_templates']:
                super_template_data.append([
                    template.get('template_name', ''),
                    template.get('super_template_id', '')
                ])
            
            super_template_table = Table(super_template_data, colWidths=[4*inch, 2.5*inch])
            super_template_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066CC')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONT', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef'))
            ]))
            elements.append(super_template_table)
            elements.append(Spacer(1, 0.15*inch))

        # Medical Advice - only if data exists
        if extracted_data.get('advice'):
            elements.append(Paragraph("MEDICAL ADVICE", custom_styles['Heading2']))
            elements.append(Paragraph(extracted_data['advice'], custom_styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))

        # Follow-up - only if data exists
        follow_up_day = extracted_data.get('follow_up_day', '')
        follow_up_mode = extracted_data.get('follow_up_mode', '')
        if follow_up_day or follow_up_mode:
            elements.append(Paragraph("FOLLOW-UP INSTRUCTIONS", custom_styles['Heading2']))
            follow_up_text = []
            if follow_up_day:
                follow_up_text.append(f"Next consultation: {follow_up_day}")
            if follow_up_mode:
                follow_up_text.append(f"Mode: {follow_up_mode}")
            elements.append(Paragraph('. '.join(follow_up_text) + '.', custom_styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))

        # Visit Type - only if data exists
        if extracted_data.get('visit_type'):
            elements.append(Paragraph("CONSULTATION TYPE", custom_styles['Heading2']))
            elements.append(Paragraph(f"Visit Type: {extracted_data['visit_type']}", custom_styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))

        # Footer
        elements.append(Spacer(1, 0.5*inch))
        footer_line = Table([[None]], colWidths=[6.5*inch], rowHeights=[1])
        footer_line.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, -1), 1, colors.HexColor('#0066CC'))]))
        elements.append(footer_line)
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph("This is a computer-generated medical report based on extracted data.", custom_styles['Footer']))
        elements.append(Paragraph("Generated by UniDoc AI Medical Transcription System", custom_styles['Footer']))
        elements.append(Paragraph(f"Report ID: {patient_info['consult_id']} | Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", custom_styles['Footer']))

        # Build PDF
        doc.build(elements)
        
        print(f"✅ PDF generated successfully: {pdf_filename}")
        return jsonify({"status": "success", "pdf_path": pdf_filename}), 200
        
    except Exception as e:
        print(f"❌ PDF generation error: {str(e)}")
        return jsonify({"error": f"PDF generation error: {str(e)}"}), 500

@app.route('/<path:filename>', methods=['GET'])
def serve_file(filename):
    try:
        if os.path.exists(filename):
            return send_file(filename, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": f"File serving error: {str(e)}"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)