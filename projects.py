# flask_app_projects.py
from flask import Flask, request, jsonify
import pandas as pd
import pdfplumber
from datetime import datetime
import io
import os

app = Flask(__name__)

def normalize_cols(df_cols):
    return [str(c).strip().lower().replace(" ", "_") for c in df_cols]

def parse_date(value):
    if pd.isna(value):
        return ""
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, str):
        parsed = pd.to_datetime(value, errors='coerce')
        return parsed.isoformat() if pd.notna(parsed) else value
    return str(value)

def excel_to_projects(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    df.columns = normalize_cols(df.columns)
    projects = []
    for _, row in df.iterrows():
        projects.append({
            "name": str(row.get('name', '')).strip(),
            "description": str(row.get('description', '')).strip(),
            "required_skills": [s.strip() for s in str(row.get('required_skills', '')).split(',') if s.strip()],
            "start_date": parse_date(row.get('start_date')),
            "end_date": parse_date(row.get('end_date')),
            "budget": float(row.get('budget', 0)) if pd.notna(row.get('budget')) else 0,
            "resources": [],
            "status": str(row.get('status', '')).strip(),
            "client_name": str(row.get('client_name', '')).strip(),
            "location": str(row.get('location', '')).strip(),
            "import_date": datetime.now().isoformat()
        })
    return projects

def pdf_to_projects(file_bytes):
    projects = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for t in tables:
                if not t or len(t) < 2:
                    continue
                header, *rows = t
                cols = normalize_cols(header)
                for r in rows:
                    row_dict = dict(zip(cols, r))
                    if not any(row_dict.values()):
                        continue
                    projects.append({
                        "name": str(row_dict.get('name', '')).strip(),
                        "description": str(row_dict.get('description', '')).strip(),
                        "required_skills": [s.strip() for s in str(row_dict.get('required_skills', '')).split(',') if s.strip()],
                        "start_date": parse_date(row_dict.get('start_date')),
                        "end_date": parse_date(row_dict.get('end_date')),
                        "budget": float(row_dict.get('budget', 0)) if row_dict.get('budget') and str(row_dict.get('budget')).replace('.', '', 1).isdigit() else 0,
                        "resources": [],
                        "status": str(row_dict.get('status', '')).strip(),
                        "client_name": str(row_dict.get('client_name', '')).strip(),
                        "location": str(row_dict.get('location', '')).strip(),
                        "import_date": datetime.now().isoformat()
                    })
    return projects

@app.route('/upload_project_file', methods=['POST'])
def upload_project_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    ext = file.filename.split('.')[-1].lower()
    file_bytes = file.read()

    try:
        if ext in ['xlsx', 'xls']:
            projects = excel_to_projects(file_bytes)
        elif ext == 'pdf':
            projects = pdf_to_projects(file_bytes)
        else:
            return jsonify({"error": f"Unsupported file type: {ext}"}), 400

        return jsonify({
            "filename": file.filename,
            "project_count": len(projects),
            "projects": projects
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    from flask_cors import CORS
    CORS(app)
    app.run(debug=True, port=8000)
