
from flask import Flask, request, jsonify, send_file, render_template_string
import os
import json
import shutil
import time

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
DATA_FOLDER = "."
TEMPLATE_FILE = "template.xlsm"
LICENSE_FOLDER = os.path.join(DATA_FOLDER, "licenses")
ALLOWED_FILE = os.path.join(DATA_FOLDER, f"allowed_ids_{PROGRAM_ID}.json")
PENDING_FILE = os.path.join(DATA_FOLDER, f"pending_ids_{PROGRAM_ID}.json")
REJECTED_FILE = os.path.join(DATA_FOLDER, f"rejected_ids_{PROGRAM_ID}.json")

os.makedirs(LICENSE_FOLDER, exist_ok=True)

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def generate_password(machine_id):
    seed = 12345
    for c in machine_id:
        seed += ord(c)
    return f"PWD{seed}"

def get_license_file_path(machine_id):
    return os.path.join(LICENSE_FOLDER, f"license_{machine_id}.txt")

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.json
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")
    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400
    if program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Invalid program ID"}), 403

    allowed_ids = load_json(ALLOWED_FILE)
    pending_ids = load_json(PENDING_FILE)
    rejected_ids = load_json(REJECTED_FILE)

    if machine_id in rejected_ids:
        return jsonify({"valid": False, "reason": "Rejected"}), 403

    if machine_id not in allowed_ids:
        if machine_id not in pending_ids:
            pending_ids.append(machine_id)
            save_json(PENDING_FILE, pending_ids)
        return jsonify({"valid": False, "reason": "Pending approval"}), 403

    # Write license file
    password = generate_password(machine_id)
    license_path = get_license_file_path(machine_id)
    with open(license_path, "w") as f:
        f.write(f"{machine_id}\n{password}")

    # Copy XLSM file based on template
    target_xlsm = f"QTY_Network_2025_{machine_id}.xlsm"
    if not os.path.exists(target_xlsm):
        shutil.copyfile(TEMPLATE_FILE, target_xlsm)
        time.sleep(1)  # Ensure file is ready

    return jsonify({
        "valid": True,
        "license_url": f"/download_license/{machine_id}",
        "xlsm_url": f"/download_xlsm/{machine_id}",
        "installer_url": "/download/installer_lifetime.exe",
        "launcher_url": "/download/Launcher.xlsm"
    })

@app.route("/download_license/<machine_id>")
def download_license(machine_id):
    return send_file(get_license_file_path(machine_id), as_attachment=True)

@app.route("/download_xlsm/<machine_id>")
def download_xlsm(machine_id):
    filename = f"QTY_Network_2025_{machine_id}.xlsm"
    return send_file(filename, as_attachment=True)

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_file(filename, as_attachment=True)

@app.route("/admin")
def admin():
    pending_ids = load_json(PENDING_FILE)
    approved_ids = load_json(ALLOWED_FILE)
    rejected_ids = load_json(REJECTED_FILE)

    html = "<h1>XLSM Tool License Admin</h1>"
    html += "<h2>Pending Machine IDs</h2>"
    for mid in pending_ids:
        html += f"<li>{mid} ✅ <a href='/approve/{mid}'>Approve</a> ❌ <a href='/reject/{mid}'>Reject</a></li>"
    html += "<h2>Approved Machine IDs</h2><ul>"
    for mid in approved_ids:
        html += f"<li>{mid}</li>"
    html += "</ul><h2>Rejected Machine IDs</h2><ul>"
    for mid in rejected_ids:
        html += f"<li>{mid}</li>"
    html += "</ul>"
    return render_template_string(html)

@app.route("/approve/<machine_id>")
def approve_id(machine_id):
    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)
    if machine_id not in allowed:
        allowed.append(machine_id)
    if machine_id in pending:
        pending.remove(machine_id)
    save_json(ALLOWED_FILE, allowed)
    save_json(PENDING_FILE, pending)
    return "✅ Approved. <a href='/admin'>Back</a>"

@app.route("/reject/<machine_id>")
def reject_id(machine_id):
    rejected = load_json(REJECTED_FILE)
    pending = load_json(PENDING_FILE)
    if machine_id not in rejected:
        rejected.append(machine_id)
    if machine_id in pending:
        pending.remove(machine_id)
    save_json(REJECTED_FILE, rejected)
    save_json(PENDING_FILE, pending)
    return "❌ Rejected. <a href='/admin'>Back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
