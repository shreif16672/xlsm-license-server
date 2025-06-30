import os
import json
import shutil
import time
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
LICENSE_FOLDER = "licenses"
TEMPLATE_FILE = "template.xlsm"
ALLOWED_IDS_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_IDS_FILE = f"pending_ids_{PROGRAM_ID}.json"

os.makedirs(LICENSE_FOLDER, exist_ok=True)

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return []

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = str(data.get("machine_id")).strip()
    program_id = str(data.get("program_id")).strip()

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    print(f"Received machine_id: {machine_id}")

    allowed_ids = load_json(ALLOWED_IDS_FILE)
    if machine_id not in allowed_ids:
        pending_ids = load_json(PENDING_IDS_FILE)
        if machine_id not in pending_ids:
            pending_ids.append(machine_id)
            save_json(PENDING_IDS_FILE, pending_ids)
        return jsonify({"valid": False, "reason": "Not allowed"}), 403

    # Generate password
    password = f"PWD{int(machine_id) % 100000}"
    license_text = f"{machine_id}\n{password}"

    # Save license.txt
    license_path = os.path.join(LICENSE_FOLDER, f"{machine_id}_license.txt")
    with open(license_path, "w") as f:
        f.write(license_text)

    # Copy and rename template.xlsm
    new_filename = f"QTY_Network_2025_{machine_id}.xlsm"
    new_file_path = os.path.join(LICENSE_FOLDER, new_filename)
    shutil.copyfile(TEMPLATE_FILE, new_file_path)

    return jsonify({
        "valid": True,
        "license_url": f"/download/{machine_id}_license.txt",
        "xlsm_url": f"/download/{new_filename}",
        "launcher_url": "/download/Launcher.xlsm",
        "installer_url": "/download/installer_lifetime.exe"
    })

@app.route("/download/<filename>")
def download_file(filename):
    return app.send_static_file(os.path.join(LICENSE_FOLDER, filename))

@app.route("/admin/xlsm_tool", methods=["GET", "POST"])
def admin_panel():
    pending_ids = load_json(PENDING_IDS_FILE)
    allowed_ids = load_json(ALLOWED_IDS_FILE)

    if request.method == "POST":
        approved_id = request.form.get("approve")
        rejected_id = request.form.get("reject")

        if approved_id:
            approved_id = approved_id.strip()
            if approved_id not in allowed_ids:
                allowed_ids.append(approved_id)
                save_json(ALLOWED_IDS_FILE, allowed_ids)
            pending_ids = [mid for mid in pending_ids if mid != approved_id]
            save_json(PENDING_IDS_FILE, pending_ids)

        elif rejected_id:
            rejected_id = rejected_id.strip()
            pending_ids = [mid for mid in pending_ids if mid != rejected_id]
            save_json(PENDING_IDS_FILE, pending_ids)

    return render_template_string('''
        <h2>📥 Pending Machine IDs for xlsm_tool</h2>
        <form method="POST">
            {% for mid in pending_ids %}
                <div>
                    {{ mid }}
                    <button name="approve" value="{{ mid }}">Approve ✅</button>
                    <button name="reject" value="{{ mid }}">Reject ❌</button>
                </div>
            {% endfor %}
        </form>
        <hr>
        <h2>✅ Approved Machine IDs</h2>
        <ul>
            {% for mid in allowed_ids %}
                <li>{{ mid }}</li>
            {% endfor %}
        </ul>
    ''', pending_ids=pending_ids, allowed_ids=allowed_ids)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
