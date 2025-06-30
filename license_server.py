from flask import Flask, request, jsonify, send_file
import os
import json
import shutil
import time

app = Flask(__name__)

DATA_FOLDER = os.path.dirname(os.path.abspath(__file__))
ALLOWED_FILE = os.path.join(DATA_FOLDER, 'allowed_ids_xlsm_tool.json')
PENDING_FILE = os.path.join(DATA_FOLDER, 'pending_ids_xlsm_tool.json')
TEMPLATE_FILE = os.path.join(DATA_FOLDER, 'template.xlsm')

@app.route('/license_xlsm', methods=['POST'])
def license_xlsm():
    data = request.json
    machine_id = data.get('machine_id')
    program_id = data.get('program_id')
    password = data.get('password')

    if not machine_id or not program_id or not password:
        return jsonify({'valid': False, 'reason': 'Missing machine_id or program_id'}), 400

    if program_id != "xlsm_tool":
        return jsonify({'valid': False, 'reason': 'Invalid program ID'}), 400

    # Add to pending list if not present
    with open(PENDING_FILE, 'r') as f:
        pending_ids = json.load(f)
    if machine_id not in pending_ids:
        pending_ids.append(machine_id)
        with open(PENDING_FILE, 'w') as f:
            json.dump(pending_ids, f, indent=2)

    # Load allowed IDs
    with open(ALLOWED_FILE, 'r') as f:
        allowed_ids = json.load(f)

    if machine_id not in allowed_ids:
        return jsonify({'valid': False, 'reason': 'Not allowed'}), 403

    # Prepare licensed XLSM file
    new_file_name = f"QTY_Network_2025_{machine_id}.xlsm"
    new_file_path = os.path.join(DATA_FOLDER, new_file_name)
    if not os.path.exists(new_file_path):
        if os.path.exists(TEMPLATE_FILE):
            shutil.copy(TEMPLATE_FILE, new_file_path)
            time.sleep(1)  # ensure file is saved
        else:
            return jsonify({'valid': False, 'reason': 'Template not found'}), 500

    # Prepare license.txt
    license_file_path = os.path.join(DATA_FOLDER, 'license.txt')
    with open(license_file_path, 'w') as f:
        f.write(machine_id + '\n')
        f.write(password + '\n')

    # Save allowed ID if not already there
    if machine_id not in allowed_ids:
        allowed_ids.append(machine_id)
        with open(ALLOWED_FILE, 'w') as f:
            json.dump(allowed_ids, f, indent=2)

    return jsonify({
        'valid': True,
        'license_file': 'license.txt',
        'xlsm_file': new_file_name,
        'launcher_file': 'Launcher.xlsm'
    })

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(DATA_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

@app.route('/')
def home():
    return 'XLSM License Server is running.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
