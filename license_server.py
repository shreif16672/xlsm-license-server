import os
import json
import time
import shutil
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from openpyxl import load_workbook

app = Flask(__name__)

DATA_FOLDER = "data"
DOWNLOAD_FOLDER = "downloads"
TEMPLATE_FILE = "template.xlsm"
PROGRAM_ID = "xlsm_tool"

ALLOWED_IDS_FILE = os.path.join(DATA_FOLDER, f"allowed_ids_{PROGRAM_ID}.json")
PENDING_IDS_FILE = os.path.join(DATA_FOLDER, f"pending_ids_{PROGRAM_ID}.json")

os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Ensure allowed and pending ID files exist
for file_path in [ALLOWED_IDS_FILE, PENDING_IDS_FILE]:
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump([], f)

def load_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def is_allowed(machine_id):
    return machine_id in load_json(ALLOWED_IDS_FILE)

def is_pending(machine_id):
    return machine_id in load_json(PENDING_IDS_FILE)

def add_to_pending(machine_id):
    data = load_json(PENDING_IDS_FILE)
    if machine_id not in data:
        data.append(machine_id)
        save_json(PENDING_IDS_FILE, data)

def move_to_allowed(machine_id):
    allowed = load_json(ALLOWED_IDS_FILE)
    if machine_id not in allowed:
        allowed.append(machine_id)
        save_json(ALLOWED_IDS_FILE, allowed)
    pending = load_json(PENDING_IDS_FILE)
    if machine_id in pending:
        pending.remove(machine_id)
        save_json(PENDING_IDS_FILE, pending)

def generate_password(machine_id):
    try:
        seed = 12345
        for i in range(len(machine_id)):
            seed += ord(machine_id[i])
        return f"PWD{seed}"
    except Exception as e:
        print(f"[ERROR] Password generation failed: {e}")
        return None

@app.route("/request_license", methods=["POST"])
def request_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Invalid program ID"}), 403

    if not machine_id:
        return jsonify({"valid": False, "reason": "Missing machine ID"}), 400

    print(f"[INFO] Received request: {data}")

    if not is_allowed(machine_id):
        add_to_pending(machine_id)
        return jsonify({"valid": False, "reason": "Pending approval"}), 403

    password = generate_password(machine_id)
    if not password:
        return jsonify({"valid": False, "reason": "License password generation failed"}), 500

    license_text = f"{machine_id}\n{password}"
    license_path = os.path.join(DOWNLOAD_FOLDER, "license.txt")
    with open(license_path, 'w') as f:
        f.write(license_text)

    new_file = f"QTY_Network_2025_{machine_id}.xlsm"
    new_path = os.path.join(DOWNLOAD_FOLDER, new_file)

    if not os.path.exists(new_path):
        shutil.copy(TEMPLATE_FILE, new_path)
        print(f"[INFO] Created file: {new_path}")

    for _ in range(10):
        if os.path.exists(new_path):
            break
        time.sleep(1)

    return jsonify({
        "valid": True,
        "license_url": "/download/license.txt",
        "xlsm_url": "/download/QTY_Network_2025_EE0FFC25.xlsm",
        "launcher_url": "/download/Launcher.xlsm",
        "license": license_text
    })

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

@app.route("/admin/xlsm_tool")
def admin_panel():
    pending = load_json(PENDING_IDS_FILE)
    allowed = load_json(ALLOWED_IDS_FILE)
    html = """
    <h1>Admin Panel: xlsm_tool</h1>
    <h2>Pending Approvals</h2>
    <ul>
    {% for mid in pending %}
      <li>{{ mid }} <a href='/approve/{{ mid }}'>Approve</a> | <a href='/reject/{{ mid }}'>Reject</a></li>
    {% endfor %}
    </ul>
    <h2>Approved Machines</h2>
    <ul>
    {% for mid in allowed %}
      <li>{{ mid }}</li>
    {% endfor %}
    </ul>
    """
    return render_template_string(html, pending=pending, allowed=allowed)

@app.route("/approve/<machine_id>")
def approve(machine_id):
    move_to_allowed(machine_id)
    return f"Approved {machine_id}. <a href='/admin/xlsm_tool'>Back</a>"

@app.route("/reject/<machine_id>")
def reject(machine_id):
    pending = load_json(PENDING_IDS_FILE)
    if machine_id in pending:
        pending.remove(machine_id)
        save_json(PENDING_IDS_FILE, pending)
    return f"Rejected {machine_id}. <a href='/admin/xlsm_tool'>Back</a>"

if __name__ == '__main__':
    print("\U0001F680 Flask license server is starting... [VERSION: 2025-07-01]")
    app.run(host='0.0.0.0', port=10000)
