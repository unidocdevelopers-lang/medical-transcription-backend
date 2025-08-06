from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import sqlite3
import os

app = Flask(__name__)
CORS(app)

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

@app.route('/process', methods=['POST'])
def process_medical_text():
    try:
        data = request.json
        text = data.get('medical_text', '').strip()
        consult_id = data.get('consult_id', '').strip()
        patient_name = data.get('patient_name', '').strip()
        patient_age = data.get('patient_age', '').strip()

        if not text or not consult_id or not patient_name:
            return jsonify({"error": "Missing required fields"}), 400

        extracted_data = extract_medical_data(text)
        extracted_data['patient_name'] = patient_name
        extracted_data['patient_age'] = patient_age
        extracted_data['consult_id'] = consult_id

        return jsonify({
            "status": "success",
            "message": "Medical text processed successfully",
            "data": extracted_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        r'main concern is ([^.]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "Patient consultation"

def extract_consult_summary(text):
    summary = ''
    exam_match = re.search(r'on examination[^.]\.?([^BP|PR|RBS]+)', text, re.IGNORECASE)
    if exam_match:
        summary += re.sub(r'BP[^,],?|PR[^,],?|RBS[^,],?', '', exam_match.group(0)).strip()
    if 'appears anxious' in text.lower(): summary += ' Patient appears anxious.'
    if 'poor sleep' in text.lower(): summary += ' Reports poor sleep.'
    return summary.strip() or "Clinical examination completed."

def extract_vitals(text):
    vitals = {"bp": "", "pr": "", "rbs": ""}
    
    bp_patterns = [
        r'Blood Pressure[^0-9]*([0-9]{2,3}/[0-9]{2,3})',
        r'BP[^0-9]*([0-9]{2,3}/[0-9]{2,3})',
        r'([0-9]{2,3}/[0-9]{2,3})\s*mmHg',
        r'was[^0-9]*([0-9]{2,3}/[0-9]{2,3})',
        r'recorded as[^0-9]*([0-9]{2,3}/[0-9]{2,3})'
    ]
    for pattern in bp_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vitals['bp'] = match.group(1)
            break

    pr_patterns = [
        r'Pulse Rate[^0-9]*([0-9]{2,3})',
        r'PR[^0-9]*([0-9]{2,3})',
        r'([0-9]{2,3})\s*bpm',
        r'Heart Rate[^0-9]*([0-9]{2,3})',
        r'pulse[^0-9]*([0-9]{2,3})'
    ]
    for pattern in pr_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vitals['pr'] = match.group(1)
            break

    rbs_patterns = [
        r'Random Blood Sugar[^0-9]*([0-9]{2,3})',
        r'RBS[^0-9]*([0-9]{2,3})',
        r'Blood Sugar[^0-9]*([0-9]{2,3})',
        r'([0-9]{2,3})\s*mg\/dL',
        r'glucose[^0-9]*([0-9]{2,3})',
        r'sugar[^0-9]*([0-9]{2,3})'
    ]
    for pattern in rbs_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vitals['rbs'] = match.group(1)
            break

    return vitals

def extract_medications(text):
    medications = []
    med_patterns = [
        {"name": "Paracetamol", "pattern": r'Paracetamol\s*([0-9]+mg)?', "dose": "1-0-1", "duration": "5 days", "when": "After food"},
        {"name": "Metformin", "pattern": r'Metformin\s*([0-9]+mg)?', "dose": "1-0-0", "duration": "ongoing", "when": "Before food"}
    ]
    
    for med in med_patterns:
        if re.search(med['pattern'], text, re.IGNORECASE):
            match = re.search(med['pattern'], text, re.IGNORECASE)
            medications.append({
                "medication": f"{med['name']} {match.group(1) if match.group(1) else '500mg'}",
                "dose": med['dose'],
                "duration": med['duration'],
                "medication_when": med['when'],
                "medication_id": len(medications) + 1
            })
    return medications

def extract_investigations(text):
    investigations = []
    test_patterns = [
        {"name": "CBC", "id": "127"},
        {"name": "HbA1c", "id": "0"},
        {"name": "Lipid Profile", "id": "329"},
        {"name": "Urine microalbumin", "id": "16"}
    ]
    
    for test in test_patterns:
        if test['name'].lower() in text.lower():
            investigations.append({
                "investigation": test['name'],
                "investigation_id": test['id']
            })
    return investigations

def extract_advice(text):
    if 'advised' in text.lower() or 'recommend' in text.lower():
        return "Patient advised to follow medication schedule and monitor symptoms."
    return ""

def extract_follow_up(text):
    match = re.search(r'follow up in (\d+)\s*(day|week|month)s?', text, re.IGNORECASE)
    if match:
        return f"{match.group(1)} {match.group(2).capitalize()}{'s' if int(match.group(1)) > 1 else ''}"
    return ""

def extract_follow_up_mode(text):
    if 'clinic visit' in text.lower(): return "Clinic Visit"
    if 'teleconsultation' in text.lower(): return "Teleconsultation"
    return ""

def extract_visit_type(text):
    if 'clinic' in text.lower() or 'in person' in text.lower(): return "In Person"
    if 'tele' in text.lower() or 'video' in text.lower(): return "Tele"
    return "Not Specified"

@app.route('/save', methods=['POST'])
def save_to_database():
    try:
        data = request.json
        consult_id = data.get('consult_id')
        patient_name = data.get('patient_name')
        patient_age = data.get('patient_age')
        extracted_data = data.get('extracted_data')

        if not all([consult_id, patient_name, extracted_data]):
            return jsonify({"error": "Missing required fields"}), 400

        conn = sqlite3.connect('consultations.db')
        c = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        c.execute('''
            INSERT INTO consult_bp (
                consult_id, patient_name, patient_age, bp_measured, pr, rbs, 
                bp_date, date_measures, created_at, complete_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            consult_id,
            patient_name,
            patient_age,
            extracted_data['vitals_examination']['bp'],
            extracted_data['vitals_examination']['pr'],
            extracted_data['vitals_examination']['rbs'],
            now.split(' ')[0],
            now.split(' ')[0],
            now,
            json.dumps(extracted_data)
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Data saved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.json
        patient_info = {
            "name": data.get('patient_name', ''),
            "age": data.get('patient_age', ''),
            "consult_id": data.get('consult_id', '')
        }
        extracted_data = data.get('extracted_data', {})

        if not patient_info['name'] or not extracted_data:
            return jsonify({"error": "Missing required data"}), 400

        pdf_path = f"Medical_Report_{patient_info['name'].replace(' ', '_')}_{patient_info['consult_id']}.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch, leftMargin=0.75*inch, rightMargin=0.75*inch)
        styles = getSampleStyleSheet()
        
        custom_styles = {
            'Title': ParagraphStyle(
                name='Title', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=20, spaceAfter=12, textColor=colors.HexColor('#003087')
            ),
            'SubTitle': ParagraphStyle(
                name='SubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=12, spaceAfter=8, textColor=colors.HexColor('#003087')
            ),
            'Heading2': ParagraphStyle(
                name='Heading2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=14, spaceAfter=8, textColor=colors.HexColor('#003087')
            ),
            'Normal': ParagraphStyle(
                name='Normal', parent=styles['Normal'], fontName='Helvetica', fontSize=11, spaceAfter=6, leading=14
            ),
            'Footer': ParagraphStyle(
                name='Footer', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=9, textColor=colors.grey
            )
        }

        elements = []

        # Hospital Header
        header_table_data = [
            [
                Paragraph("UNIDOC MEDICAL CENTER", custom_styles['Title']),
                Paragraph(f"Consultation Report - ID: {patient_info['consult_id']}", custom_styles['SubTitle'])
            ],
            [
                Paragraph("123 Health St, Wellness City, Country | Phone: (123) 456-7890 | Email: info@unidoc.org", custom_styles['Normal']),
                Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", custom_styles['Normal'])
            ]
        ]
        header_table = Table(header_table_data, colWidths=[4*inch, 2.5*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('ALIGN', (1, 1), (1, 1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 6),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.2*inch))

        # Horizontal Line
        elements.append(Table([[None]], colWidths=[6.5*inch], rowHeights=[2], style=[('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#003087'))]))

        # Patient Information
        patient_data = [
            ["Patient Name:", patient_info['name']],
            ["Age:", patient_info['age']],
            ["Consultation ID:", patient_info['consult_id']],
            ["Date of Visit:", datetime.now().strftime('%Y-%m-%d')],
            ["Time:", datetime.now().strftime('%H:%M:%S')]
        ]
        patient_table = Table(patient_data, colWidths=[2*inch, 4.5*inch])
        patient_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#003087')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
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

        # Vitals
        vitals = extracted_data.get('vitals_examination', {})
        vitals_data = [
            ["Blood Pressure:", f"{vitals.get('bp', 'Not recorded')} {'mmHg' if vitals.get('bp') else ''}"],
            ["Pulse Rate:", f"{vitals.get('pr', 'Not recorded')} {'bpm' if vitals.get('pr') else ''}"],
            ["Blood Sugar:", f"{vitals.get('rbs', 'Not recorded')} {'mg/dL' if vitals.get('rbs') else ''}"]
        ]
        vitals_table = Table(vitals_data, colWidths=[2*inch, 4.5*inch])
        vitals_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#003087')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef'))
        ]))
        elements.append(Paragraph("VITAL SIGNS", custom_styles['Heading2']))
        elements.append(vitals_table)
        elements.append(Spacer(1, 0.15*inch))

        # Other Sections
        if extracted_data.get('consult_summary'):
            elements.append(Paragraph("CLINICAL EXAMINATION", custom_styles['Heading2']))
            elements.append(Paragraph(extracted_data['consult_summary'], custom_styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))

        if extracted_data.get('medication_data'):
            elements.append(Paragraph("PRESCRIBED MEDICATIONS", custom_styles['Heading2']))
            med_data = [["Medication", "Dosage", "Duration", "When"]]
            for med in extracted_data['medication_data']:
                med_data.append([
                    med['medication'],
                    med['dose'],
                    med['duration'],
                    med['medication_when']
                ])
            med_table = Table(med_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            med_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003087')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONT', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef'))
            ]))
            elements.append(med_table)
            elements.append(Spacer(1, 0.15*inch))

        if extracted_data.get('investigations'):
            elements.append(Paragraph("RECOMMENDED INVESTIGATIONS", custom_styles['Heading2']))
            inv_data = [["Investigation", "ID"]]
            for inv in extracted_data['investigations']:
                inv_data.append([inv['investigation'], inv['investigation_id']])
            inv_table = Table(inv_data, colWidths=[3.5*inch, 3*inch])
            inv_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003087')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONT', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef'))
            ]))
            elements.append(inv_table)
            elements.append(Spacer(1, 0.15*inch))

        if extracted_data.get('advice'):
            elements.append(Paragraph("MEDICAL ADVICE", custom_styles['Heading2']))
            elements.append(Paragraph(extracted_data['advice'], custom_styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))

        if extracted_data.get('follow_up_day'):
            elements.append(Paragraph("FOLLOW-UP", custom_styles['Heading2']))
            follow_up_text = f"Next visit: {extracted_data['follow_up_day']}"
            if extracted_data.get('follow_up_mode'):
                follow_up_text += f" via {extracted_data['follow_up_mode']}"
            elements.append(Paragraph(follow_up_text, custom_styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))

        # Footer
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Table([[None]], colWidths=[6.5*inch], rowHeights=[2], style=[('LINEABOVE', (0, 0), (-1, -1), 1, colors.HexColor('#003087'))]))
        elements.append(Paragraph("Confidential: This document contains sensitive medical information.", custom_styles['Footer']))
        elements.append(Paragraph("Generated by UniDoc Clinical Text Processing System", custom_styles['Footer']))

        doc.build(elements)
        return jsonify({"status": "success", "pdf_path": pdf_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/<path:filename>', methods=['GET'])
def serve_file(filename):
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)