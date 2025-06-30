from flask import Flask, request, jsonify, send_file, render_template_string
import os
import json
import shutil
import time

app = Flask(__name__)

# File paths
PROGRAM_ID = "xlsm_tool"
ALLOWED_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_FILE = f"pending_ids_{PROGRAM_ID}.json"
TEMPLATE_FILE = "template.xlsm"
LICENSE_FOLDER = "generated_files"

# Ensure folders exist
os.makedirs(LICENSE_FOLDER, exist_ok=True)

# Load or initialize ID lists
def load_ids(file_path):
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump([], f)
    with open(file_path, "r") as f:
        return json.load(f)

def save_ids(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    machine_id = data.get("machine_id", "").strip().upper()
    program_id = data.get("program_id", "")

    if program_id != PROGRAM_ID or not machine_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    allowed = load_ids(ALLOWED_FILE)
    pending = load_ids(PENDING_FILE)

    # Auto-approve logic
    if machine_id not in allowed:
        if machine_id not in pending:
            pending.append(machine_id)
            save_ids(PENDING_FILE, pending)
        return jsonify({"valid": False, "reason": "Pending approval"})

    # Create machine-specific xlsm file
    xlsm_name = f"QTY_Network_2025_{machine_id}.xlsm"
    xlsm_path = os.path.join(LICENSE_FOLDER, xlsm_name)
    if not os.path.exists(xlsm_path):
        shutil.copyfile(TEMPLATE_FILE, xlsm_path)

    # Create license.txt contents
    ascii_sum = sum(ord(c) for c in machine_id)
    password = f"PWD{12861 + (ascii_sum % 1000)}"
    license_txt = f"{machine_id}\n{password}"
    license_file = os.path.join(LICENSE_FOLDER, "license.txt")
    with open(license_file, "w") as f:
        f.write(license_txt)

    return jsonify({
        "valid": True,
        "license_file": f"/download/license.txt",
        "xlsm_file": f"/download/{xlsm_name}"
    })

@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join(LICENSE_FOLDER, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "File not found", 404

@app.route("/admin/xlsm_tool")
def admin_page():
    allowed = load_ids(ALLOWED_FILE)
    pending = load_ids(PENDING_FILE)
    return render_template_string("""
    <h2>Pending Approvals</h2>
    <ul>
    {% for mid in pending %}
        <li>{{ mid }} —
            <a href="/admin/approve/{{ mid }}">✅ Approve</a> |
            <a href="/admin/reject/{{ mid }}">❌ Reject</a>
        </li>
    {% endfor %}
    </ul>
    <h2>Approved Machines</h2>
    <ul>
    {% for mid in allowed %}
        <li>{{ mid }}</li>
    {% endfor %}
    </ul>
    """, pending=pending, allowed=allowed)

@app.route("/admin/approve/<machine_id>")
def approve(machine_id):
    machine_id = machine_id.strip().upper()
    allowed = load_ids(ALLOWED_FILE)
    pending = load_ids(PENDING_FILE)

    if machine_id not in allowed:
        allowed.append(machine_id)
    if machine_id in pending:
        pending.remove(machine_id)

    save_ids(ALLOWED_FILE, allowed)
    save_ids(PENDING_FILE, pending)
    return f"✅ {machine_id} approved. <a href='/admin/xlsm_tool'>Return</a>"

@app.route("/admin/reject/<machine_id>")
def reject(machine_id):
    machine_id = machine_id.strip().upper()
    pending = load_ids(PENDING_FILE)
    if machine_id in pending:
        pending.remove(machine_id)
    save_ids(PENDING_FILE, pending)
    return f"❌ {machine_id} rejected. <a href='/admin/xlsm_tool'>Return</a>"

@app.route("/")
def home():
    return "XLSM License Server Running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
