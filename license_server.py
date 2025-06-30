
from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import json
import shutil

app = Flask(__name__)

DATA_FOLDER = os.path.dirname(os.path.abspath(__file__))
LICENSE_FOLDER = DATA_FOLDER
STATIC_FILES = ["license.txt", "Launcher.xlsm", "installer_lifetime.exe"]
PROGRAM_ID = "xlsm_tool"
ALLOWED_IDS_FILE = os.path.join(DATA_FOLDER, f"allowed_ids_{PROGRAM_ID}.json")
PENDING_IDS_FILE = os.path.join(DATA_FOLDER, f"pending_ids_{PROGRAM_ID}.json")
TEMPLATE_FILE = os.path.join(DATA_FOLDER, "template.xlsm")

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/", methods=["GET"])
def home():
    return "License server is running."

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = str(data.get("machine_id"))
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    allowed_ids = load_json(ALLOWED_IDS_FILE)
    if machine_id not in allowed_ids:
        pending = load_json(PENDING_IDS_FILE)
        if machine_id not in pending:
            pending.append(machine_id)
            save_json(PENDING_IDS_FILE, pending)
        return jsonify({"valid": False, "reason": "Not allowed"}), 403

    filename = f"QTY_Network_2025_{machine_id}.xlsm"
    target_path = os.path.join(DATA_FOLDER, filename)
    if not os.path.exists(target_path):
        shutil.copyfile(TEMPLATE_FILE, target_path)

    return jsonify({
        "valid": True,
        "license": f"{machine_id}\nPWD17610",
        "files": [
            {"filename": "license.txt", "path": "license.txt"},
            {"filename": "Launcher.xlsm", "path": "Launcher.xlsm"},
            {"filename": filename, "path": filename}
        ]
    })

@app.route("/download/<path:filename>", methods=["GET"])
def download_file(filename):
    return send_from_directory(DATA_FOLDER, filename, as_attachment=True)

@app.route("/admin/xlsm_tool", methods=["GET"])
def admin_page():
    allowed_ids = load_json(ALLOWED_IDS_FILE)
    pending_ids = load_json(PENDING_IDS_FILE)
    html = """
    <h1>Admin Panel - xlsm_tool</h1>
    <h2>Pending IDs</h2>
    <ul>
    {% for mid in pending %}
      <li>{{ mid }} - <a href='/approve/{{ mid }}'>[Approve]</a></li>
    {% endfor %}
    </ul>
    <h2>Approved IDs</h2>
    <ul>
    {% for mid in allowed %}
      <li>{{ mid }}</li>
    {% endfor %}
    </ul>
    """
    return render_template_string(html, allowed=allowed_ids, pending=pending_ids)

@app.route("/approve/<machine_id>", methods=["GET"])
def approve(machine_id):
    allowed = load_json(ALLOWED_IDS_FILE)
    pending = load_json(PENDING_IDS_FILE)
    if machine_id not in allowed:
        allowed.append(machine_id)
    if machine_id in pending:
        pending.remove(machine_id)
    save_json(ALLOWED_IDS_FILE, allowed)
    save_json(PENDING_IDS_FILE, pending)
    return f"Machine ID {machine_id} approved."

@app.route("/reject/<machine_id>", methods=["GET"])
def reject(machine_id):
    pending = load_json(PENDING_IDS_FILE)
    if machine_id in pending:
        pending.remove(machine_id)
        save_json(PENDING_IDS_FILE, pending)
    return f"Machine ID {machine_id} rejected."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
