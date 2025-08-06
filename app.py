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

        extracted_data = extract_medical_data(text)
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

def extract_medical_data(text):
    return {
        "chief_complaint": extract_chief_complaint(text),
        "consult_summary": extract_consult_summary(text),
        "vitals_examination": extract_vitals(text),
        "medication_data": extract_medications(text),
        "investigations": extract_investigations(text),
        "advice": extract_advice(text),
        "follow_up_day": extract_follow_up(text),
        "follow_up_mode": extract_follow_up_mode(text),
        "visit_type": extract_visit_type(text)
    }

def extract_chief_complaint(text):
    patterns = [
        r'came with complaints? of ([^.]+)',
        r'presents with ([^.]+)',
        r'complains of ([^.]+)',
        r'main concern is ([^.]+)',
        r'chief complaint[:\s]*([^.]+)',
        r'c/o[:\s]*([^.]+)',
        r'presenting complaint[:\s]*([^.]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            complaint = match.group(1).strip()
            # Clean up common artifacts
            complaint = re.sub(r'\s+', ' ', complaint)
            complaint = complaint.rstrip(',.')
            return complaint
    return "General medical consultation"

def extract_consult_summary(text):
    summary_parts = []
    
    # Look for examination findings
    exam_patterns = [
        r'on examination[^.]*\.([^BP|PR|RBS]+)',
        r'physical examination[^.]*\.([^BP|PR|RBS]+)',
        r'clinical findings[^.]*\.([^BP|PR|RBS]+)'
    ]
    
    for pattern in exam_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            finding = match.group(1).strip()
            finding = re.sub(r'BP[^,],?|PR[^,],?|RBS[^,],?', '', finding).strip()
            if finding:
                summary_parts.append(finding)
    
    # Look for specific conditions
    conditions = []
    if re.search(r'appears?\s+(anxious|nervous|distressed)', text, re.IGNORECASE):
        conditions.append('Patient appears anxious')
    if re.search(r'(poor|bad|inadequate)\s+sleep', text, re.IGNORECASE):
        conditions.append('Reports poor sleep quality')
    if re.search(r'(chest pain|chest discomfort)', text, re.IGNORECASE):
        conditions.append('Complaints of chest discomfort')
    if re.search(r'(shortness of breath|breathlessness|dyspnea)', text, re.IGNORECASE):
        conditions.append('Experiencing breathing difficulties')
    
    summary_parts.extend(conditions)
    
    if summary_parts:
        return '. '.join(summary_parts) + '.'
    
    return "Clinical examination completed. Patient evaluated thoroughly."

def extract_vitals(text):
    vitals = {"bp": "", "pr": "", "rbs": ""}
    
    # Enhanced BP patterns
    bp_patterns = [
        r'Blood Pressure[:\s]*([0-9]{2,3}\/[0-9]{2,3})',
        r'BP[:\s]*([0-9]{2,3}\/[0-9]{2,3})',
        r'([0-9]{2,3}\/[0-9]{2,3})\s*mmHg',
        r'was[^0-9]*([0-9]{2,3}\/[0-9]{2,3})',
        r'recorded as[^0-9]*([0-9]{2,3}\/[0-9]{2,3})',
        r'([0-9]{2,3})\s*\/\s*([0-9]{2,3})',
        r'systolic[^0-9]*([0-9]{2,3})[^0-9]*diastolic[^0-9]*([0-9]{2,3})'
    ]
    
    for pattern in bp_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 1:
                vitals['bp'] = match.group(1)
            else:
                vitals['bp'] = f"{match.group(1)}/{match.group(2)}"
            break

    # Enhanced PR patterns
    pr_patterns = [
        r'Pulse Rate[:\s]*([0-9]{2,3})',
        r'PR[:\s]*([0-9]{2,3})',
        r'([0-9]{2,3})\s*bpm',
        r'Heart Rate[:\s]*([0-9]{2,3})',
        r'pulse[:\s]*([0-9]{2,3})',
        r'HR[:\s]*([0-9]{2,3})'
    ]
    
    for pattern in pr_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vitals['pr'] = match.group(1)
            break

    # Enhanced RBS patterns
    rbs_patterns = [
        r'Random Blood Sugar[:\s]*([0-9]{2,3})',
        r'RBS[:\s]*([0-9]{2,3})',
        r'Blood Sugar[:\s]*([0-9]{2,3})',
        r'([0-9]{2,3})\s*mg\/dL',
        r'glucose[:\s]*([0-9]{2,3})',
        r'sugar level[:\s]*([0-9]{2,3})',
        r'blood glucose[:\s]*([0-9]{2,3})'
    ]
    
    for pattern in rbs_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vitals['rbs'] = match.group(1)
            break

    return vitals

def extract_medications(text):
    medications = []
    
    # Common medications with their patterns
    med_patterns = [
        {"name": "Paracetamol", "pattern": r'Paracetamol\s*([0-9]+\s*mg)?', 
         "dose": "1-0-1", "duration": "5 days", "when": "After food"},
        {"name": "Metformin", "pattern": r'Metformin\s*([0-9]+\s*mg)?', 
         "dose": "1-0-0", "duration": "ongoing", "when": "Before food"},
        {"name": "Aspirin", "pattern": r'Aspirin\s*([0-9]+\s*mg)?', 
         "dose": "0-0-1", "duration": "ongoing", "when": "After food"},
        {"name": "Atorvastatin", "pattern": r'Atorvastatin\s*([0-9]+\s*mg)?', 
         "dose": "0-0-1", "duration": "ongoing", "when": "After dinner"},
        {"name": "Amlodipine", "pattern": r'Amlodipine\s*([0-9]+\s*mg)?', 
         "dose": "1-0-0", "duration": "ongoing", "when": "After breakfast"},
        {"name": "Pantoprazole", "pattern": r'Pantoprazole\s*([0-9]+\s*mg)?', 
         "dose": "1-0-0", "duration": "30 days", "when": "Before food"},
        {"name": "Insulin", "pattern": r'Insulin\s*([0-9]+\s*units?)?', 
         "dose": "As directed", "duration": "ongoing", "when": "Before meals"}
    ]
    
    for med in med_patterns:
        match = re.search(med['pattern'], text, re.IGNORECASE)
        if match:
            dose_match = match.group(1) if match.group(1) else "500mg"
            medications.append({
                "medication": f"{med['name']} {dose_match}",
                "dose": med['dose'],
                "duration": med['duration'],
                "medication_when": med['when'],
                "medication_id": len(medications) + 1
            })
    
    return medications

def extract_investigations(text):
    investigations = []
    
    test_patterns = [
        {"name": "Complete Blood Count", "short": "CBC", "id": "127"},
        {"name": "HbA1c", "short": "HbA1c", "id": "0"},
        {"name": "Lipid Profile", "short": "Lipid", "id": "329"},
        {"name": "Urine Microalbumin", "short": "Microalbumin", "id": "16"},
        {"name": "ECG", "short": "ECG", "id": "45"},
        {"name": "Chest X-Ray", "short": "CXR", "id": "78"},
        {"name": "Thyroid Function Test", "short": "TFT", "id": "89"},
        {"name": "Kidney Function Test", "short": "KFT", "id": "156"},
        {"name": "Liver Function Test", "short": "LFT", "id": "234"}
    ]
    
    text_lower = text.lower()
    for test in test_patterns:
        if (test['name'].lower() in text_lower or 
            test['short'].lower() in text_lower):
            investigations.append({
                "investigation": test['name'],
                "investigation_id": test['id']
            })
    
    return investigations

def extract_advice(text):
    advice_parts = []
    
    # Look for explicit advice sections
    advice_patterns = [
        r'advice[d:]?\s*([^.]+\.)',
        r'recommend[ed]?\s*([^.]+\.)',
        r'suggest[ed]?\s*([^.]+\.)',
        r'patient advised\s*([^.]+\.)'
    ]
    
    for pattern in advice_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        advice_parts.extend(matches)
    
    # Common medical advice
    if re.search(r'medication.*(schedule|regularly|as prescribed)', text, re.IGNORECASE):
        advice_parts.append("Follow medication schedule as prescribed")
    
    if re.search(r'(monitor|check|watch).*symptoms?', text, re.IGNORECASE):
        advice_parts.append("Monitor symptoms closely")
        
    if re.search(r'(diet|food|eating)', text, re.IGNORECASE):
        advice_parts.append("Follow dietary recommendations")
        
    if re.search(r'(exercise|physical activity)', text, re.IGNORECASE):
        advice_parts.append("Maintain regular physical activity")
    
    if advice_parts:
        return '. '.join(advice_parts) + '.'
    
    return "Continue current treatment and follow up as scheduled."

def extract_follow_up(text):
    patterns = [
        r'follow up in (\d+)\s*(day|week|month)s?',
        r'next visit in (\d+)\s*(day|week|month)s?',
        r'return after (\d+)\s*(day|week|month)s?',
        r'see again in (\d+)\s*(day|week|month)s?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            number = match.group(1)
            unit = match.group(2).lower()
            plural = 's' if int(number) > 1 else ''
            return f"{number} {unit.capitalize()}{plural}"
    
    return "As needed"

def extract_follow_up_mode(text):
    if re.search(r'clinic visit|in.person|office visit', text, re.IGNORECASE):
        return "Clinic Visit"
    if re.search(r'teleconsultation|video call|online|virtual', text, re.IGNORECASE):
        return "Teleconsultation"
    if re.search(r'phone call|telephone', text, re.IGNORECASE):
        return "Phone Call"
    return "Clinic Visit"

def extract_visit_type(text):
    if re.search(r'clinic|in.person|office|physical', text, re.IGNORECASE):
        return "In Person"
    if re.search(r'tele|video|online|virtual|remote', text, re.IGNORECASE):
        return "Teleconsultation"
    return "In Person"

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