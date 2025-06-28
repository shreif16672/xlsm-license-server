import os
import json
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from datetime import datetime
import tempfile
import shutil

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"

PENDING_IDS_FILE = f"pending_ids_{PROGRAM_ID}.json"
ALLOWED_IDS_FILE = f"allowed_ids_{PROGRAM_ID}.json"
LICENSE_TEMPLATE_FILE = "license.txt"
DOWNLOAD_FOLDER = "downloads"

def load_json(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 403

    if program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Invalid program_id"}), 403

    allowed_ids = load_json(ALLOWED_IDS_FILE)
    if machine_id not in allowed_ids:
        # Add to pending if not already in
        pending_ids = load_json(PENDING_IDS_FILE)
        if machine_id not in pending_ids:
            pending_ids.append(machine_id)
            save_json(PENDING_IDS_FILE, pending_ids)
        return jsonify({"valid": False, "reason": "Not allowed"}), 403

    # Build license text
    if not os.path.exists(LICENSE_TEMPLATE_FILE):
        return jsonify({"valid": False, "reason": "No license.txt found"}), 500

    with open(LICENSE_TEMPLATE_FILE, "r") as f:
        base_license = f.read().strip()

    license_data = f"{base_license}\nMachine ID: {machine_id}"

    # Save to local temporary file
    temp_dir = os.path.join(tempfile.gettempdir(), f"license_{machine_id}")
    os.makedirs(temp_dir, exist_ok=True)

    license_path = os.path.join(temp_dir, "license.txt")
    with open(license_path, "w") as f:
        f.write(license_data)

    # Copy extra files to same folder
    download_files = [
        "QTY_Network_2025.xlsm",
        "Launcher.xlsm",
        "installer_lifetime.exe"
    ]
    for file in download_files:
        src = os.path.join(DOWNLOAD_FOLDER, file)
        if os.path.exists(src):
            shutil.copy(src, temp_dir)

    return jsonify({
        "valid": True,
        "license_path": license_path,
        "files": download_files
    })

@app.route("/admin", methods=["GET"])
def view_admin():
    pending_ids = load_json(PENDING_IDS_FILE)
    approved_ids = load_json(ALLOWED_IDS_FILE)

    html = """
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending Requests</h2>
    {% for mid in pending %}
      <li>{{ mid }} 
      <form action="/approve" method="post" style="display:inline;">
        <input type="hidden" name="machine_id" value="{{ mid }}">
        <button type="submit">✅ Approve</button>
      </form>
      <form action="/reject" method="post" style="display:inline;">
        <input type="hidden" name="machine_id" value="{{ mid }}">
        <button type="submit">❌ Reject</button>
      </form>
      </li>
    {% endfor %}

    <h2>Approved Machine IDs</h2>
    {% for mid in approved %}
      <li>{{ mid }}</li>
    {% endfor %}
    """
    return render_template_string(html, pending=pending_ids, approved=approved_ids)

@app.route("/approve", methods=["POST"])
def approve_machine():
    machine_id = request.form.get("machine_id")
    if not machine_id:
        return "Missing machine_id", 400

    allowed_ids = load_json(ALLOWED_IDS_FILE)
    pending_ids = load_json(PENDING_IDS_FILE)

    if machine_id not in allowed_ids:
        allowed_ids.append(machine_id)
        save_json(ALLOWED_IDS_FILE, allowed_ids)

    if machine_id in pending_ids:
        pending_ids.remove(machine_id)
        save_json(PENDING_IDS_FILE, pending_ids)

    return render_template_string("<h1>✅ Approved</h1><a href='/admin'>Back to Admin</a>")

@app.route("/reject", methods=["POST"])
def reject_machine():
    machine_id = request.form.get("machine_id")
    if not machine_id:
        return "Missing machine_id", 400

    pending_ids = load_json(PENDING_IDS_FILE)
    if machine_id in pending_ids:
        pending_ids.remove(machine_id)
        save_json(PENDING_IDS_FILE, pending_ids)

    return render_template_string("<h1>❌ Rejected</h1><a href='/admin'>Back to Admin</a>")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
