import os
import json
import shutil
import time
from flask import Flask, request, jsonify, send_from_directory, render_template_string

app = Flask(__name__)

# === Configuration ===
LICENSE_DIR = os.path.join(os.getcwd(), "licenses")
DATA_DIR = os.getcwd()
PROGRAM_ID = "xlsm_tool"

ALLOWED_IDS_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_IDS_FILE = f"pending_ids_{PROGRAM_ID}.json"

# === Utility Functions ===
def load_ids(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

def save_ids(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def is_machine_allowed(machine_id):
    allowed = load_ids(ALLOWED_IDS_FILE)
    return machine_id in allowed

def add_to_pending(machine_id):
    pending = load_ids(PENDING_IDS_FILE)
    if machine_id not in pending:
        pending.append(machine_id)
        save_ids(PENDING_IDS_FILE, pending)

def create_license_file(machine_id):
    if not os.path.exists(LICENSE_DIR):
        os.makedirs(LICENSE_DIR)
    password = f"PWD{str(int(machine_id) % 90000 + 10000)}"
    content = f"{machine_id}\n{password}"
    path = os.path.join(LICENSE_DIR, "license.txt")
    with open(path, "w") as f:
        f.write(content)
    return path

def generate_xlsm(machine_id):
    src = os.path.join(DATA_DIR, "template.xlsm")
    dst_name = f"QTY_Network_2025_{machine_id}.xlsm"
    dst = os.path.join(DATA_DIR, dst_name)
    if not os.path.exists(dst):
        shutil.copyfile(src, dst)
    return dst_name

# === License Generation Endpoint ===
@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id or program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Missing or invalid machine_id/program_id"}), 400

    print(f"[LOG] Request received from machine_id: {machine_id}")

    if not is_machine_allowed(machine_id):
        add_to_pending(machine_id)
        return jsonify({"valid": False, "reason": "Pending approval"}), 403

    # Create license.txt
    license_path = create_license_file(machine_id)

    # Create .xlsm file
    xlsm_filename = generate_xlsm(machine_id)

    # Wait until file exists before sending response
    for _ in range(10):
        if os.path.exists(os.path.join(DATA_DIR, xlsm_filename)):
            break
        time.sleep(0.5)

    # Respond with license and file names
    return jsonify({
        "valid": True,
        "license": open(license_path).read(),
        "files": [
            {"filename": "license.txt", "path": "license.txt"},
            {"filename": "Launcher.xlsm", "path": "Launcher.xlsm"},
            {"filename": xlsm_filename, "path": xlsm_filename}
        ]
    })

# === File Download Endpoint ===
@app.route("/download/<path:filename>", methods=["GET"])
def download_file(filename):
    return send_from_directory(DATA_DIR, filename, as_attachment=True)

# === Admin Panel ===
@app.route("/admin/xlsm_tool", methods=["GET"])
def admin_xlsm_tool():
    allowed = load_ids(ALLOWED_IDS_FILE)
    pending = load_ids(PENDING_IDS_FILE)
    html = """
    <h1>✅ Approved IDs</h1>
    <ul>{% for id in allowed %}<li>{{ id }}</li>{% endfor %}</ul>
    <h1>🕒 Pending Requests</h1>
    <ul>
      {% for id in pending %}
        <li>
          {{ id }}
          <a href='/admin/approve/{{ id }}'>✅ Approve</a>
          <a href='/admin/reject/{{ id }}'>❌ Reject</a>
        </li>
      {% endfor %}
    </ul>
    """
    return render_template_string(html, allowed=allowed, pending=pending)

@app.route("/admin/approve/<machine_id>", methods=["GET"])
def approve_id(machine_id):
    allowed = load_ids(ALLOWED_IDS_FILE)
    pending = load_ids(PENDING_IDS_FILE)

    if machine_id not in allowed:
        allowed.append(machine_id)
        save_ids(ALLOWED_IDS_FILE, allowed)

    if machine_id in pending:
        pending.remove(machine_id)
        save_ids(PENDING_IDS_FILE, pending)

    return f"<h2>✅ Approved {machine_id}</h2><a href='/admin/xlsm_tool'>Back</a>"

@app.route("/admin/reject/<machine_id>", methods=["GET"])
def reject_id(machine_id):
    pending = load_ids(PENDING_IDS_FILE)
    if machine_id in pending:
        pending.remove(machine_id)
        save_ids(PENDING_IDS_FILE, pending)
    return f"<h2>❌ Rejected {machine_id}</h2><a href='/admin/xlsm_tool'>Back</a>"

# === Run Server ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
