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

        # Enhanced extraction using the prompt-based approach
        extracted_data = extract_medical_data_advanced(text)
        extracted_data['patient_name'] = patient_name
        extracted_data['patient_age'] = patient_age
        extracted_data['consult_id'] = consult_id

        return jsonify({
            "status": "success",
            "message": "Medical text processed successfully",
            "data": extracted_data
        }), 200
    except Exception as e:
        return jsonify({"error": f"Processing error: {str(e)}"}), 500

def extract_medical_data_advanced(text):
    """
    Advanced medical data extraction based on the provided prompt logic
    This mimics the sophisticated AI processing from your web application
    """
    
    # Clean and prepare text
    text = clean_medical_text(text)
    
    # Extract vitals FIRST (highest priority as per prompt)
    vitals = extract_vitals_advanced(text)
    
    # Remove vitals from text for consult_summary processing
    text_without_vitals = remove_vitals_from_text(text, vitals)
    
    return {
        "chief_complaint": extract_chief_complaint_advanced(text),
        "consult_summary": extract_consult_summary_advanced(text_without_vitals, vitals),
        "vitals_examination": vitals,
        "medication_data": extract_medications_advanced(text),
        "investigations": extract_investigations_advanced(text),
        "medicine_templates": extract_medicine_templates_advanced(text),
        "super_templates": extract_super_templates_advanced(text),
        "advice": extract_advice_advanced(text),
        "follow_up_day": extract_follow_up_advanced(text),
        "follow_up_mode": extract_follow_up_mode_advanced(text),
        "visit_type": extract_visit_type_advanced(text)
    }

def clean_medical_text(text):
    """Clean and normalize the medical text"""
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Fix common medical abbreviations
    text = re.sub(r'\bBP\b(?!\s*:)', 'BP:', text, flags=re.IGNORECASE)
    text = re.sub(r'\bPR\b(?!\s*:)', 'PR:', text, flags=re.IGNORECASE)
    text = re.sub(r'\bRBS\b(?!\s*:)', 'RBS:', text, flags=re.IGNORECASE)
    
    return text

def extract_vitals_advanced(text):
    """Enhanced vitals extraction with comprehensive pattern matching"""
    vitals = {"bp": "", "pr": "", "rbs": ""}
    
    # Enhanced BP patterns - Extract numerical values only
    bp_patterns = [
        r'BP[:\s]*([0-9]{2,3}/[0-9]{2,3})',
        r'Blood Pressure[:\s]*([0-9]{2,3}/[0-9]{2,3})',
        r'([0-9]{2,3}/[0-9]{2,3})\s*mmHg',
        r'([0-9]{2,3}/[0-9]{2,3})\s*mm\s*Hg',
        r'His BP is ([0-9]{2,3}/[0-9]{2,3})',
        r'Her BP is ([0-9]{2,3}/[0-9]{2,3})',
        r'BP was ([0-9]{2,3}/[0-9]{2,3})',
        r'Blood pressure is ([0-9]{2,3}/[0-9]{2,3})',
        r'systolic[^0-9]*([0-9]{2,3})[^0-9]*diastolic[^0-9]*([0-9]{2,3})',
        r'([0-9]{2,3})\s*/\s*([0-9]{2,3})'
    ]
    
    for pattern in bp_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 1:
                vitals['bp'] = match.group(1)
            elif len(match.groups()) == 2:
                vitals['bp'] = f"{match.group(1)}/{match.group(2)}"
            break

    # Enhanced PR patterns - Extract numerical values only
    pr_patterns = [
        r'PR[:\s]*([0-9]{2,3})',
        r'Pulse Rate[:\s]*([0-9]{2,3})',
        r'Pulse[:\s]*([0-9]{2,3})',
        r'Heart Rate[:\s]*([0-9]{2,3})',
        r'HR[:\s]*([0-9]{2,3})',
        r'([0-9]{2,3})\s*bpm',
        r'Pulse Rate is ([0-9]{2,3})',
        r'His PR is ([0-9]{2,3})',
        r'Her PR is ([0-9]{2,3})',
        r'PR was ([0-9]{2,3})',
        r'pulse.*?([0-9]{2,3})'
    ]
    
    for pattern in pr_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vitals['pr'] = match.group(1)
            break

    # Enhanced RBS patterns - Extract numerical values only
    rbs_patterns = [
        r'RBS[:\s]*([0-9]{2,3})',
        r'Random Blood Sugar[:\s]*([0-9]{2,3})',
        r'Blood Sugar[:\s]*([0-9]{2,3})',
        r'([0-9]{2,3})\s*mg/dL',
        r'([0-9]{2,3})\s*mg\s*/\s*dL',
        r'RBS is ([0-9]{2,3})',
        r'Random Blood Sugar is ([0-9]{2,3})',
        r'Blood glucose[:\s]*([0-9]{2,3})',
        r'glucose level[:\s]*([0-9]{2,3})',
        r'sugar.*?([0-9]{2,3})'
    ]
    
    for pattern in rbs_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vitals['rbs'] = match.group(1)
            break

    return vitals

def remove_vitals_from_text(text, vitals):
    """Remove vital signs from text to prevent duplication in consult_summary"""
    text_clean = text
    
    if vitals['bp']:
        # Remove BP mentions
        text_clean = re.sub(rf"BP[:\s]*{re.escape(vitals['bp'])}", "", text_clean, flags=re.IGNORECASE)
        text_clean = re.sub(rf"Blood Pressure[:\s]*{re.escape(vitals['bp'])}", "", text_clean, flags=re.IGNORECASE)
        text_clean = re.sub(rf"{re.escape(vitals['bp'])}\s*mmHg", "", text_clean, flags=re.IGNORECASE)
    
    if vitals['pr']:
        # Remove PR mentions
        text_clean = re.sub(rf"PR[:\s]*{re.escape(vitals['pr'])}", "", text_clean, flags=re.IGNORECASE)
        text_clean = re.sub(rf"Pulse Rate[:\s]*{re.escape(vitals['pr'])}", "", text_clean, flags=re.IGNORECASE)
        text_clean = re.sub(rf"{re.escape(vitals['pr'])}\s*bpm", "", text_clean, flags=re.IGNORECASE)
    
    if vitals['rbs']:
        # Remove RBS mentions
        text_clean = re.sub(rf"RBS[:\s]*{re.escape(vitals['rbs'])}", "", text_clean, flags=re.IGNORECASE)
        text_clean = re.sub(rf"Random Blood Sugar[:\s]*{re.escape(vitals['rbs'])}", "", text_clean, flags=re.IGNORECASE)
        text_clean = re.sub(rf"{re.escape(vitals['rbs'])}\s*mg/dL", "", text_clean, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    text_clean = re.sub(r'\s+', ' ', text_clean)
    return text_clean.strip()

def extract_chief_complaint_advanced(text):
    """Enhanced chief complaint extraction"""
    patterns = [
        r'complains? of ([^.]+)',
        r'came with complaints? of ([^.]+)',
        r'presents with ([^.]+)',
        r'presented with ([^.]+)',
        r'main concern is ([^.]+)',
        r'chief complaint[:\s]*([^.]+)',
        r'c/o[:\s]*([^.]+)',
        r'presenting complaint[:\s]*([^.]+)',
        r'patient reports ([^.]+)',
        r'suffering from ([^.]+)',
        r'history of ([^.]+)',
        r'came for ([^.]+)',
        r'visited for ([^.]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            complaint = match.group(1).strip()
            # Clean up and normalize
            complaint = re.sub(r'\s+', ' ', complaint)
            complaint = complaint.rstrip('.,')
            # Remove vitals if accidentally captured
            complaint = re.sub(r'BP[^,]*,?|PR[^,]*,?|RBS[^,]*,?', '', complaint, flags=re.IGNORECASE).strip()
            if len(complaint) > 10:  # Ensure meaningful content
                return complaint
    
    return "General medical consultation"

def extract_consult_summary_advanced(text, vitals):
    """Enhanced consultation summary extraction excluding vitals"""
    summary_parts = []
    
    # Look for examination findings
    exam_patterns = [
        r'on examination[^.]*\.([^.]+)',
        r'physical examination[^.]*\.([^.]+)',
        r'clinical findings[^.]*\.([^.]+)',
        r'examination revealed ([^.]+)',
        r'findings include ([^.]+)',
        r'assessment showed ([^.]+)',
        r'tests positive for ([^.]+)',
        r'tests negative for ([^.]+)',
        r'impression[:\s]*([^.]+)',
        r'diagnosis[:\s]*([^.]+)',
        r'likely ([^.]+)',
        r'consistent with ([^.]+)',
        r'appears to have ([^.]+)'
    ]
    
    for pattern in exam_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            finding = match.strip()
            # Exclude vitals and clean
            finding = re.sub(r'BP[^,]*,?|PR[^,]*,?|RBS[^,]*,?', '', finding, flags=re.IGNORECASE).strip()
            finding = re.sub(r'\s+', ' ', finding)
            if len(finding) > 5:
                summary_parts.append(finding)
    
    # Look for specific clinical conditions
    condition_patterns = [
        r'appears?\s+(anxious|nervous|distressed|comfortable|stable)',
        r'(poor|bad|good|adequate)\s+(sleep|appetite)',
        r'(chest pain|chest discomfort|abdominal pain)',
        r'(shortness of breath|breathlessness|dyspnea)',
        r'(nausea|vomiting|diarrhea|constipation)',
        r'(fever|headache|dizziness|fatigue)',
        r'(mild|moderate|severe)\s+([^.]+)',
        r'(positive|negative)\s+for\s+([^.]+)'
    ]
    
    for pattern in condition_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                condition = ' '.join(match).strip()
            else:
                condition = match.strip()
            if len(condition) > 3:
                summary_parts.append(f"Patient {condition}")
    
    if summary_parts:
        # Remove duplicates and combine
        unique_parts = list(dict.fromkeys(summary_parts))
        return '. '.join(unique_parts) + '.'
    
    return "Clinical examination completed. Patient evaluated thoroughly."

def extract_medications_advanced(text):
    """Enhanced medication extraction with comprehensive patterns"""
    medications = []
    
    # Common medications database with enhanced patterns
    medication_db = [
        {"names": ["Paracetamol", "Acetaminophen"], "default_dose": "500mg", "dose_pattern": "1-0-1", "duration": "5 days", "when": "After food"},
        {"names": ["Metformin"], "default_dose": "500mg", "dose_pattern": "1-0-1", "duration": "ongoing", "when": "Before food"},
        {"names": ["Aspirin"], "default_dose": "75mg", "dose_pattern": "0-0-1", "duration": "ongoing", "when": "After food"},
        {"names": ["Atorvastatin"], "default_dose": "10mg", "dose_pattern": "0-0-1", "duration": "ongoing", "when": "After dinner"},
        {"names": ["Amlodipine"], "default_dose": "5mg", "dose_pattern": "1-0-0", "duration": "ongoing", "when": "After breakfast"},
        {"names": ["Pantoprazole", "Omeprazole"], "default_dose": "40mg", "dose_pattern": "1-0-0", "duration": "30 days", "when": "Before food"},
        {"names": ["Insulin"], "default_dose": "As prescribed", "dose_pattern": "As directed", "duration": "ongoing", "when": "Before meals"},
        {"names": ["Ondansetron"], "default_dose": "4mg", "dose_pattern": "1-1-1", "duration": "3 days", "when": "Before food"},
        {"names": ["Azithromycin"], "default_dose": "500mg", "dose_pattern": "1-0-0", "duration": "3 days", "when": "After food"},
        {"names": ["Ciprofloxacin"], "default_dose": "500mg", "dose_pattern": "1-0-1", "duration": "7 days", "when": "After food"},
        {"names": ["Amoxicillin"], "default_dose": "500mg", "dose_pattern": "1-1-1", "duration": "7 days", "when": "After food"},
        {"names": ["Dolo", "Dolo 650"], "default_dose": "650mg", "dose_pattern": "1-1-1", "duration": "3 days", "when": "After food"},
        {"names": ["Telmisartan"], "default_dose": "40mg", "dose_pattern": "1-0-0", "duration": "ongoing", "when": "Before food"},
        {"names": ["Losartan"], "default_dose": "50mg", "dose_pattern": "1-0-0", "duration": "ongoing", "when": "Before food"}
    ]
    
    medication_id = 1
    
    for med in medication_db:
        for name in med["names"]:
            # Enhanced pattern matching
            patterns = [
                rf'\b{re.escape(name)}\s*([0-9]+\s*mg)?',
                rf'Tab\s+{re.escape(name)}\s*([0-9]+\s*mg)?',
                rf'{re.escape(name)}\s+([0-9]+\s*mg)',
                rf'{re.escape(name)}\s+tablet',
                rf'started.*?{re.escape(name)}',
                rf'prescribed.*?{re.escape(name)}',
                rf'given.*?{re.escape(name)}'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    dose_found = match.group(1) if match.groups() and match.group(1) else med["default_dose"]
                    
                    # Look for specific dosage in context
                    context = text[max(0, match.start()-50):match.end()+100]
                    
                    # Extract custom dosage patterns
                    dose_pattern = extract_dosage_pattern(context) or med["dose_pattern"]
                    duration = extract_duration_pattern(context) or med["duration"]
                    when = extract_timing_pattern(context) or med["when"]
                    
                    medications.append({
                        "medication": f"{name} {dose_found}",
                        "dose": dose_pattern,
                        "duration": duration,
                        "medication_when": when,
                        "medication_id": str(medication_id)
                    })
                    medication_id += 1
                    break
    
    # Generic medication extraction for unlisted medications
    generic_patterns = [
        r'Tab\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*([0-9]+\s*mg)?',
        r'Syrup\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)',
        r'Injection\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)',
        r'prescribed\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)',
        r'started on\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)'
    ]
    
    for pattern in generic_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                med_name = match[0].strip()
                dose = match[1] if len(match) > 1 and match[1] else "As prescribed"
            else:
                med_name = match.strip()
                dose = "As prescribed"
            
            # Check if already extracted
            if not any(med_name.lower() in med["medication"].lower() for med in medications):
                medications.append({
                    "medication": f"{med_name} {dose}",
                    "dose": "1-0-1",
                    "duration": "As directed",
                    "medication_when": "After food",
                    "medication_id": str(medication_id)
                })
                medication_id += 1
    
    return medications

def extract_dosage_pattern(text):
    """Extract dosage pattern from context"""
    patterns = [
        r'([0-9])-([0-9])-([0-9])',
        r'([0-9])\s*times?\s*(?:a\s*)?day',
        r'once\s*(?:a\s*)?day',
        r'twice\s*(?:a\s*)?day',
        r'thrice\s*(?:a\s*)?day',
        r'three\s*times\s*(?:a\s*)?day'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if pattern == r'([0-9])-([0-9])-([0-9])':
                return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            elif pattern == r'([0-9])\s*times?\s*(?:a\s*)?day':
                times = int(match.group(1))
                if times == 1:
                    return "1-0-0"
                elif times == 2:
                    return "1-0-1"
                elif times == 3:
                    return "1-1-1"
                else:
                    return f"{times} times daily"
            elif 'once' in match.group(0).lower():
                return "1-0-0"
            elif 'twice' in match.group(0).lower():
                return "1-0-1"
            elif 'thrice' in match.group(0).lower() or 'three times' in match.group(0).lower():
                return "1-1-1"
    
    return None

def extract_duration_pattern(text):
    """Extract duration from context"""
    patterns = [
        r'for\s*([0-9]+)\s*(day|week|month)s?',
        r'([0-9]+)\s*(day|week|month)s?',
        r'ongoing',
        r'continue',
        r'as needed',
        r'indefinitely'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if match.groups() and len(match.groups()) >= 2:
                return f"{match.group(1)} {match.group(2)}s" if int(match.group(1)) > 1 else f"{match.group(1)} {match.group(2)}"
            else:
                return match.group(0)
    
    return None

def extract_timing_pattern(text):
    """Extract timing information from context"""
    patterns = [
        r'before\s*(?:food|meals?|eating)',
        r'after\s*(?:food|meals?|eating)',
        r'with\s*(?:food|meals?)',
        r'empty\s*stomach',
        r'at\s*night',
        r'in\s*the\s*morning',
        r'before\s*breakfast',
        r'after\s*dinner'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).title()
    
    return None

def extract_investigations_advanced(text):
    """Enhanced investigation extraction"""
    investigations = []
    investigation_id = 1
    
    # Comprehensive investigation database
    investigation_db = [
        {"names": ["CBC", "Complete Blood Count", "Complete Blood Picture", "CBP"], "id": "127"},
        {"names": ["HbA1c", "Glycated Hemoglobin"], "id": "1"},
        {"names": ["Lipid Profile", "Lipid Panel"], "id": "329"},
        {"names": ["Liver Function Test", "LFT"], "id": "234"},
        {"names": ["Kidney Function Test", "KFT", "Renal Function Test"], "id": "156"},
        {"names": ["Thyroid Function Test", "TFT"], "id": "89"},
        {"names": ["ECG", "EKG", "Electrocardiogram"], "id": "45"},
        {"names": ["Chest X-Ray", "CXR", "Chest X Ray"], "id": "78"},
        {"names": ["Urine Routine", "Urine Analysis", "Urinalysis"], "id": "12"},
        {"names": ["Blood Sugar", "Fasting Blood Sugar", "FBS"], "id": "23"},
        {"names": ["Postprandial Blood Sugar", "PPBS"], "id": "24"},
        {"names": ["Creatinine", "Serum Creatinine"], "id": "34"},
        {"names": ["Urea", "Blood Urea"], "id": "35"},
        {"names": ["Hemoglobin", "Hb"], "id": "56"},
        {"names": ["ESR", "Erythrocyte Sedimentation Rate"], "id": "67"},
        {"names": ["CRP", "C-Reactive Protein"], "id": "78"},
        {"names": ["Vitamin D", "25-OH Vitamin D"], "id": "89"},
        {"names": ["Vitamin B12"], "id": "90"},
        {"names": ["Iron Studies", "Serum Iron"], "id": "91"},
        {"names": ["Ultrasound", "USG"], "id": "102"},
        {"names": ["CT Scan", "Computed Tomography"], "id": "103"},
        {"names": ["MRI", "Magnetic Resonance Imaging"], "id": "104"},
        {"names": ["Stool Routine", "Stool Examination"], "id": "105"},
        {"names": ["Culture", "Blood Culture", "Urine Culture"], "id": "106"},
        {"names": ["Dengue", "Dengue NS1", "Dengue IgM"], "id": "107"},
        {"names": ["Malaria", "Malaria Test", "MP"], "id": "108"},
        {"names": ["Typhoid", "Widal Test"], "id": "109"},
        {"names": ["HIV", "HIV Test"], "id": "110"},
        {"names": ["HBsAg", "Hepatitis B"], "id": "111"},
        {"names": ["HCV", "Hepatitis C"], "id": "112"}
    ]
    
    # Keywords that indicate investigations
    investigation_keywords = [
        r'ordered?\s*([^.]+)',
        r'advised?\s*([^.]+)',
        r'requested?\s*([^.]+)',
        r'sent for\s*([^.]+)',
        r'refer for\s*([^.]+)',
        r'check\s*([^.]+)',
        r'evaluate\s*([^.]+)',
        r'investigate\s*([^.]+)',
        r'test for\s*([^.]+)',
        r'screening for\s*([^.]+)',
        r'lab work\s*([^.]+)',
        r'blood work\s*([^.]+)'
    ]
    
    for inv in investigation_db:
        for name in inv["names"]:
            pattern = rf'\b{re.escape(name)}\b'
            if re.search(pattern, text, re.IGNORECASE):
                investigations.append({
                    "investigation": inv["names"][0],  # Use primary name
                    "investigation_id": inv["id"]
                })
                break
    
    # Generic investigation extraction
    for keyword_pattern in investigation_keywords:
        matches = re.findall(keyword_pattern, text, re.IGNORECASE)
        for match in matches:
            # Look for medical test names in the match
            potential_tests = re.findall(r'\b[A-Z]{2,}\b|\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', match)
            for test in potential_tests:
                test = test.strip()
                if len(test) > 2 and not any(test.lower() in inv["investigation"].lower() for inv in investigations):
                    investigations.append({
                        "investigation": test,
                        "investigation_id": str(investigation_id)
                    })
                    investigation_id += 1
    
    return investigations

def extract_medicine_templates_advanced(text):
    """Extract medicine templates (macro references)"""
    templates = []
    template_id = 1
    
    # Look for macro keywords
    macro_patterns = [
        r'macro\s*([^.]+)',
        r'template\s*([^.]+)',
        r'protocol\s*for\s*([^.]+)',
        r'management\s*plan\s*for\s*([^.]+)',
        r'standard\s*care\s*for\s*([^.]+)',
        r'follow\s*guidelines\s*for\s*([^.]+)'
    ]
    
    for pattern in macro_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            template_name = match.strip().title()
            if len(template_name) > 3:
                templates.append({
                    "template_name": template_name,
                    "medicine_template_id": str(template_id)
                })
                template_id += 1
    
    return templates

def extract_super_templates_advanced(text):
    """Extract super templates (super macro references)"""
    templates = []
    template_id = 1
    
    # Look for super macro keywords
    super_patterns = [
        r'super\s*macro\s*([^.]+)',
        r'comprehensive\s*protocol\s*([^.]+)',
        r'advanced\s*template\s*([^.]+)',
        r'complete\s*care\s*plan\s*([^.]+)',
        r'integrated\s*management\s*([^.]+)',
        r'master\s*protocol\s*([^.]+)'
    ]
    
    for pattern in super_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            template_name = match.strip().title()
            if len(template_name) > 3:
                templates.append({
                    "template_name": template_name,
                    "super_template_id": str(template_id)
                })
                template_id += 1
    
    return templates

def extract_advice_advanced(text):
    """Enhanced advice extraction"""
    advice_parts = []
    
    # Look for explicit advice sections
    advice_patterns = [
        r'advice[d:]?\s*([^.]+\.)',
        r'recommend[ed]?\s*([^.]+\.)',
        r'suggest[ed]?\s*([^.]+\.)',
        r'patient advised\s*([^.]+\.)',
        r'instructions?\s*([^.]+\.)',
        r'plan[:\s]*([^.]+\.)',
        r'discharge[d]?\s*with\s*([^.]+\.)',
        r'follow[:\s]*([^.]+\.)',
        r'continue\s*([^.]+\.)',
        r'maintain\s*([^.]+\.)',
        r'avoid\s*([^.]+\.)',
        r'take\s*([^.]+\.)'
    ]
    
    for pattern in advice_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            advice = match.strip()
            # Clean advice
            advice = re.sub(r'BP[^,]*,?|PR[^,]*,?|RBS[^,]*,?', '', advice, flags=re.IGNORECASE).strip()
            if len(advice) > 10:
                advice_parts.append(advice)
    
    # Look for common medical advice patterns
    if re.search(r'medication.*(schedule|regularly|as prescribed)', text, re.IGNORECASE):
        advice_parts.append("Follow medication schedule as prescribed.")
    
    if re.search(r'(monitor|check|watch).*symptoms?', text, re.IGNORECASE):
        advice_parts.append("Monitor symptoms closely.")
        
    if re.search(r'(diet|dietary|food|eating)', text, re.IGNORECASE):
        advice_parts.append("Follow dietary recommendations.")
        
    if re.search(r'(exercise|physical activity|walk)', text, re.IGNORECASE):
        advice_parts.append("Maintain regular physical activity.")
    
    if re.search(r'(rest|adequate sleep)', text, re.IGNORECASE):
        advice_parts.append("Take adequate rest and maintain proper sleep.")
    
    if re.search(r'(hydration|fluid)', text, re.IGNORECASE):
        advice_parts.append("Maintain proper hydration.")
    
    if advice_parts:
        # Remove duplicates and combine
        unique_advice = list(dict.fromkeys(advice_parts))
        return ' '.join(unique_advice)
    
    return "Continue current treatment and follow up as scheduled."

def extract_follow_up_advanced(text):
    """Enhanced follow-up day extraction"""
    patterns = [
        r'follow up in ([0-9]+)\s*(day|week|month)s?',
        r'next visit in ([0-9]+)\s*(day|week|month)s?',
        r'return after ([0-9]+)\s*(day|week|month)s?',
        r'see again in ([0-9]+)\s*(day|week|month)s?',
        r'review in ([0-9]+)\s*(day|week|month)s?',
        r'come back in ([0-9]+)\s*(day|week|month)s?',
        r'appointment in ([0-9]+)\s*(day|week|month)s?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            number = match.group(1)
            unit = match.group(2).lower()
            # Proper formatting
            if unit == 'day':
                return f"{number} Days" if int(number) > 1 else f"{number} Day"
            elif unit == 'week':
                return f"{number} Weeks" if int(number) > 1 else f"{number} Week"
            elif unit == 'month':
                return f"{number} Months" if int(number) > 1 else f"{number} Month"
    
    return "As needed"

def extract_follow_up_mode_advanced(text):
    """Enhanced follow-up mode extraction"""
    if re.search(r'teleconsultation|video call|online|virtual|tele|phone call|telephone', text, re.IGNORECASE):
        return "Teleconsultation"
    if re.search(r'clinic visit|in.person|office visit|physical visit|visit clinic', text, re.IGNORECASE):
        return "Clinic Visit"
    return "Clinic Visit"  # Default

def extract_visit_type_advanced(text):
    """Enhanced visit type extraction"""
    if re.search(r'teleconsultation|tele|video|online|virtual|remote', text, re.IGNORECASE):
        return "Teleconsultation"
    if re.search(r'clinic|in.person|office|physical|visited', text, re.IGNORECASE):
        return "In Person"
    return "In Person"  # Default

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

        # Ensure the filename is safe
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', patient_info['name'])
        pdf_filename = f"Medical_Report_{safe_name}_{patient_info['consult_id']}.pdf"
        
        doc = SimpleDocTemplate(pdf_filename, pagesize=letter, 
                              topMargin=0.5*inch, bottomMargin=0.5*inch, 
                              leftMargin=0.75*inch, rightMargin=0.75*inch)
        styles = getSampleStyleSheet()
        
        # Custom styles
        custom_styles = {
            'Title': ParagraphStyle(
                name='CustomTitle', parent=styles['Title'], 
                fontName='Helvetica-Bold', fontSize=20, spaceAfter=12, 
                textColor=colors.HexColor('#003087'), alignment=1
            ),
            'SubTitle': ParagraphStyle(
                name='CustomSubTitle', parent=styles['Normal'], 
                fontName='Helvetica', fontSize=12, spaceAfter=8, 
                textColor=colors.HexColor('#003087')
            ),
            'Heading2': ParagraphStyle(
                name='CustomHeading2', parent=styles['Heading2'], 
                fontName='Helvetica-Bold', fontSize=14, spaceAfter=8, 
                textColor=colors.HexColor('#003087')
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
        elements.append(Paragraph("Advanced Medical Consultation Report", custom_styles['SubTitle']))
        elements.append(Spacer(1, 0.2*inch))

        # Horizontal Line
        line_table = Table([[None]], colWidths=[6.5*inch], rowHeights=[2])
        line_table.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#003087'))]))
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
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#003087')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef'))
        ]))
        
        elements.append(Paragraph("PATIENT INFORMATION", custom_styles['Heading2']))
        elements.append(patient_table)
        elements.append(Spacer(1, 0.2*inch))

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

        # Vitals
        vitals = extracted_data.get('vitals_examination', {})
        if vitals and any(vitals.values()):
            vitals_data = [
                ["Parameter", "Value", "Unit"],
                ["Blood Pressure", vitals.get('bp', 'Not recorded'), 'mmHg' if vitals.get('bp') else ''],
                ["Pulse Rate", vitals.get('pr', 'Not recorded'), 'bpm' if vitals.get('pr') else ''],
                ["Random Blood Sugar", vitals.get('rbs', 'Not recorded'), 'mg/dL' if vitals.get('rbs') else '']
            ]
            
            vitals_table = Table(vitals_data, colWidths=[2.5*inch, 2*inch, 2*inch])
            vitals_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003087')),
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

        # Medications
        if extracted_data.get('medication_data'):
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
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003087')),
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

        # Investigations
        if extracted_data.get('investigations'):
            elements.append(Paragraph("RECOMMENDED INVESTIGATIONS", custom_styles['Heading2']))
            inv_data = [["Investigation", "ID"]]
            
            for inv in extracted_data['investigations']:
                inv_data.append([
                    inv.get('investigation', ''),
                    inv.get('investigation_id', '')
                ])
            
            inv_table = Table(inv_data, colWidths=[4*inch, 2.5*inch])
            inv_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003087')),
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

        # Medicine Templates
        if extracted_data.get('medicine_templates'):
            elements.append(Paragraph("MEDICINE TEMPLATES", custom_styles['Heading2']))
            template_data = [["Template Name", "ID"]]
            
            for template in extracted_data['medicine_templates']:
                template_data.append([
                    template.get('template_name', ''),
                    template.get('medicine_template_id', '')
                ])
            
            template_table = Table(template_data, colWidths=[4*inch, 2.5*inch])
            template_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003087')),
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

        # Super Templates
        if extracted_data.get('super_templates'):
            elements.append(Paragraph("SUPER TEMPLATES", custom_styles['Heading2']))
            super_template_data = [["Template Name", "ID"]]
            
            for template in extracted_data['super_templates']:
                super_template_data.append([
                    template.get('template_name', ''),
                    template.get('super_template_id', '')
                ])
            
            super_template_table = Table(super_template_data, colWidths=[4*inch, 2.5*inch])
            super_template_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003087')),
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

        # Medical Advice
        if extracted_data.get('advice'):
            elements.append(Paragraph("MEDICAL ADVICE", custom_styles['Heading2']))
            elements.append(Paragraph(extracted_data['advice'], custom_styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))

        # Follow-up
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

        # Visit Type
        if extracted_data.get('visit_type'):
            elements.append(Paragraph("CONSULTATION TYPE", custom_styles['Heading2']))
            elements.append(Paragraph(f"Visit Type: {extracted_data['visit_type']}", custom_styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))

        # Footer
        elements.append(Spacer(1, 0.5*inch))
        footer_line = Table([[None]], colWidths=[6.5*inch], rowHeights=[1])
        footer_line.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, -1), 1, colors.HexColor('#003087'))]))
        elements.append(footer_line)
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph("This is a computer-generated medical report.", custom_styles['Footer']))
        elements.append(Paragraph("Generated by UniDoc Medical Transcription System", custom_styles['Footer']))
        elements.append(Paragraph(f"Report ID: {patient_info['consult_id']} | Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", custom_styles['Footer']))

        # Build PDF
        doc.build(elements)
        
        return jsonify({"status": "success", "pdf_path": pdf_filename}), 200
        
    except Exception as e:
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