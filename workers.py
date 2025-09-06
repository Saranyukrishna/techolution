# flask_app_resources_react.py
from flask import Flask, request, jsonify
import pandas as pd
import pdfplumber
from datetime import datetime
import io
import os

app = Flask(__name__)

def parse_date(value):
    if pd.isna(value):
        return ""
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, str):
        parsed = pd.to_datetime(value, errors='coerce')
        return parsed.isoformat() if pd.notna(parsed) else value
    return str(value)

def excel_to_resources(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    resources = []
    for _, row in df.iterrows():
        availability_start = parse_date(row.get('Availability_start'))
        resources.append({
            "name": str(row.get('Name') or ""),
            "role": str(row.get('Role') or ""),
            "skills": str(row.get('Skills')).split(';') if pd.notna(row.get('Skills')) else [],
            "proficiency": str(row.get('Proficiency') or ""),
            "capacity_hours": int(row.get('Capacity_hours')) if pd.notna(row.get('Capacity_hours')) else 0,
            "availability_start": availability_start,
            "location": str(row.get('Location') or ""),
            "rate_per_hour": float(row.get('Rate_per_hour')) if pd.notna(row.get('Rate_per_hour')) else 0,
            "current_project": str(row.get('Current_project') or ""),
            "import_date": datetime.now().isoformat()
        })
    return resources

def pdf_to_resources(file_bytes):
    resources = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for t in tables:
                if not t or len(t) < 2:
                    continue
                header, *rows = t
                cols = [c.strip().lower() for c in header]
                for r in rows:
                    row_dict = dict(zip(cols, r))
                    if not any(row_dict.values()):
                        continue
                    availability_start = parse_date(row_dict.get('availability_start') or "")
                    resources.append({
                        "name": row_dict.get('name') or "",
                        "role": row_dict.get('role') or "",
                        "skills": row_dict.get('skills').split(';') if row_dict.get('skills') else [],
                        "proficiency": row_dict.get('proficiency') or "",
                        "capacity_hours": int(row_dict.get('capacity_hours')) if (row_dict.get('capacity_hours') and str(row_dict.get('capacity_hours')).isdigit()) else 0,
                        "availability_start": availability_start,
                        "location": row_dict.get('location') or "",
                        "rate_per_hour": float(row_dict.get('rate_per_hour')) if (row_dict.get('rate_per_hour') and str(row_dict.get('rate_per_hour')).replace('.', '', 1).isdigit()) else 0,
                        "current_project": row_dict.get('current_project') or "",
                        "import_date": datetime.now().isoformat()
                    })
    return resources

@app.route('/upload_resource_file', methods=['POST'])
def upload_resource_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    ext = file.filename.split('.')[-1].lower()
    file_bytes = file.read()

    try:
        if ext in ['xlsx', 'xls']:
            resources = excel_to_resources(file_bytes)
        elif ext == 'pdf':
            resources = pdf_to_resources(file_bytes)
        else:
            return jsonify({"error": f"Unsupported file type: {ext}"}), 400

        # JSON response ready for React frontend
        return jsonify({
            "filename": file.filename,
            "resource_count": len(resources),
            "resources": resources
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # CORS is often needed for React frontend
    from flask_cors import CORS
    CORS(app)
    app.run(debug=True, port=5000)
