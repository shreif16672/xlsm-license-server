from flask import Flask, request, send_file, jsonify, render_template_string
import os
import json
import shutil
import time

app = Flask(__name__)

# Constants
PROGRAM_ID = "xlsm_tool"
LICENSE_FOLDER = "xlsm_licenses"
TEMPLATE_FILE = "template.xlsm"

# Ensure folders exist
os.makedirs(LICENSE_FOLDER, exist_ok=True)

# JSON storage files
allowed_file = f"allowed_ids_{PROGRAM_ID}.json"
pending_file = f"pending_ids_{PROGRAM_ID}.json"
rejected_file = f"rejected_ids_{PROGRAM_ID}.json"

def load_json(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump([], f)
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.json
    machine_id = data.get("machine_id", "").strip().upper()
    program_id = data.get("program_id", "")

    if not machine_id or program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 403

    allowed = load_json(allowed_file)
    pending = load_json(pending_file)
    rejected = load_json(rejected_file)

    if machine_id in rejected:
        return jsonify({"valid": False, "reason": "Rejected"}), 403

    if machine_id not in allowed:
        if machine_id not in pending:
            pending.append(machine_id)
            save_json(pending_file, pending)
        return jsonify({"valid": False, "reason": "Pending approval"}), 403

    # Generate password format (PWDxxxxx)
    seed = 12345 + sum(ord(char) for char in machine_id)
    password = f"PWD{seed}"

    # Save license.txt format
    license_path = os.path.join(LICENSE_FOLDER, f"{machine_id}_license.txt")
    with open(license_path, "w") as f:
        f.write(f"{machine_id}\n{password}")

    # Copy and rename XLSM file
    new_xlsm_name = f"QTY_Network_2025_{machine_id}.xlsm"
    new_xlsm_path = os.path.join(LICENSE_FOLDER, new_xlsm_name)
    if not os.path.exists(new_xlsm_path):
        shutil.copyfile(TEMPLATE_FILE, new_xlsm_path)

    # Wait until file is available
    for _ in range(10):
        if os.path.exists(new_xlsm_path):
            break
        time.sleep(0.5)

    if not os.path.exists(new_xlsm_path):
        return jsonify({"valid": False, "reason": "XLSM generation failed"}), 500

    return jsonify({
        "valid": True,
        "license_path": license_path,
        "download_files": {
            "installer_lifetime.exe": "installer_lifetime.exe",
            "Launcher.xlsm": "Launcher.xlsm",
            new_xlsm_name: new_xlsm_path
        }
    })

@app.route("/admin")
def admin():
    pending = load_json(pending_file)
    allowed = load_json(allowed_file)
    rejected = load_json(rejected_file)

    html = """
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending Machine IDs</h2>
    <ul>
    {% for mid in pending %}
        <li>{{ mid }} ✅<a href="/approve/{{ mid }}">Approve</a> ❌<a href="/reject/{{ mid }}">Reject</a></li>
    {% endfor %}
    </ul>
    <h2>Approved Machine IDs</h2>
    <ul>
    {% for mid in allowed %}
        <li>{{ mid }}</li>
    {% endfor %}
    </ul>
    <h2>Rejected Machine IDs</h2>
    <ul>
    {% for mid in rejected %}
        <li>{{ mid }}</li>
    {% endfor %}
    </ul>
    """
    return render_template_string(html, pending=pending, allowed=allowed, rejected=rejected)

@app.route("/approve/<machine_id>")
def approve(machine_id):
    allowed = load_json(allowed_file)
    pending = load_json(pending_file)
    if machine_id not in allowed:
        allowed.append(machine_id)
        save_json(allowed_file, allowed)
    if machine_id in pending:
        pending.remove(machine_id)
        save_json(pending_file, pending)
    return f"✅ Approved {machine_id}. <a href='/admin'>Back</a>"

@app.route("/reject/<machine_id>")
def reject(machine_id):
    rejected = load_json(rejected_file)
    pending = load_json(pending_file)
    if machine_id not in rejected:
        rejected.append(machine_id)
        save_json(rejected_file, rejected)
    if machine_id in pending:
        pending.remove(machine_id)
        save_json(pending_file, pending)
    return f"❌ Rejected {machine_id}. <a href='/admin'>Back</a>"

@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(LICENSE_FOLDER, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
