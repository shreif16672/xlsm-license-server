# license_server.py (final version for xlsm tool)

import os
import json
import shutil
import uuid
import time
from flask import Flask, request, jsonify, send_from_directory, render_template_string

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LICENSES_DIR = os.path.join(BASE_DIR, "licenses")
TEMPLATE_XLSM = os.path.join(BASE_DIR, "template.xlsm")

FILES_TO_SEND = [
    "Launcher.xlsm",
    "installer_lifetime.exe"
]

JSON_PATHS = {
    "allowed": os.path.join(BASE_DIR, f"allowed_ids_{PROGRAM_ID}.json"),
    "pending": os.path.join(BASE_DIR, f"pending_ids_{PROGRAM_ID}.json"),
    "rejected": os.path.join(BASE_DIR, f"rejected_ids_{PROGRAM_ID}.json"),
}

os.makedirs(LICENSES_DIR, exist_ok=True)
for path in JSON_PATHS.values():
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump([], f)

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id", "").strip().upper()
    program_id = data.get("program_id", "")

    if not machine_id or program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 403

    allowed = load_json(JSON_PATHS["allowed"])
    pending = load_json(JSON_PATHS["pending"])
    rejected = load_json(JSON_PATHS["rejected"])

    if machine_id in rejected:
        return jsonify({"valid": False, "reason": "License rejected"}), 403

    if machine_id not in allowed:
        if machine_id not in pending:
            pending.append(machine_id)
            save_json(JSON_PATHS["pending"], pending)
        return jsonify({"valid": False, "reason": "Pending approval"}), 403

    # Generate machine-specific xlsm
    new_file = os.path.join(BASE_DIR, f"QTY_Network_2025_{machine_id}.xlsm")
    if not os.path.exists(new_file):
        shutil.copyfile(TEMPLATE_XLSM, new_file)

        # Write license content
        license_path = os.path.join(LICENSES_DIR, f"license_{machine_id}.txt")
        password = "PWD" + str(uuid.uuid4().int)[-5:]
        with open(license_path, "w") as f:
            f.write(machine_id + "\n" + password)

    # Wait until file exists
    timeout = 10
    while not os.path.exists(new_file) and timeout > 0:
        time.sleep(1)
        timeout -= 1

    if not os.path.exists(new_file):
        return jsonify({"valid": False, "reason": "File not ready"}), 500

    return jsonify({
        "valid": True,
        "machine_id": machine_id,
        "download_files": FILES_TO_SEND + [f"QTY_Network_2025_{machine_id}.xlsm"]
    })

@app.route("/files/<filename>")
def download_file(filename):
    return send_from_directory(BASE_DIR, filename, as_attachment=True)

@app.route("/admin")
def admin_panel():
    allowed = load_json(JSON_PATHS["allowed"])
    pending = load_json(JSON_PATHS["pending"])
    rejected = load_json(JSON_PATHS["rejected"])

    html = """
    <h1>Admin Panel — XLSM Tool</h1>
    <h2>Pending IDs</h2>
    <ul>
        {% for mid in pending %}
            <li>{{ mid }} 
                <a href="/admin/approve/{{ mid }}">✅ Approve</a> | 
                <a href="/admin/reject/{{ mid }}">❌ Reject</a>
            </li>
        {% endfor %}
    </ul>
    <h2>Approved IDs</h2>
    <ul>{% for mid in allowed %}<li>{{ mid }}</li>{% endfor %}</ul>
    <h2>Rejected IDs</h2>
    <ul>{% for mid in rejected %}<li>{{ mid }}</li>{% endfor %}</ul>
    """
    return render_template_string(html, pending=pending, allowed=allowed, rejected=rejected)

@app.route("/admin/approve/<machine_id>")
def approve(machine_id):
    machine_id = machine_id.upper()
    allowed = load_json(JSON_PATHS["allowed"])
    pending = load_json(JSON_PATHS["pending"])
    if machine_id not in allowed:
        allowed.append(machine_id)
    if machine_id in pending:
        pending.remove(machine_id)
    save_json(JSON_PATHS["allowed"], allowed)
    save_json(JSON_PATHS["pending"], pending)
    return f"✅ Approved {machine_id}. <a href='/admin'>Back</a>"

@app.route("/admin/reject/<machine_id>")
def reject(machine_id):
    machine_id = machine_id.upper()
    rejected = load_json(JSON_PATHS["rejected"])
    pending = load_json(JSON_PATHS["pending"])
    if machine_id not in rejected:
        rejected.append(machine_id)
    if machine_id in pending:
        pending.remove(machine_id)
    save_json(JSON_PATHS["rejected"], rejected)
    save_json(JSON_PATHS["pending"], pending)
    return f"❌ Rejected {machine_id}. <a href='/admin'>Back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
