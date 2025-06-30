from flask import Flask, request, jsonify, send_file, render_template_string
import json
import os
import shutil
import time

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
ALLOWED_IDS_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_IDS_FILE = f"pending_ids_{PROGRAM_ID}.json"

LICENSE_FOLDER = os.path.expanduser("~")
TEMPLATE_FILE = "template.xlsm"
LAUNCHER_FILE = "Launcher.xlsm"
INSTALLER_FILE = "installer_lifetime.exe"

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = str(data.get("machine_id")).strip()
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    if program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Invalid program_id"}), 403

    # Load allowed IDs
    try:
        with open(ALLOWED_IDS_FILE, "r") as f:
            allowed_ids = json.load(f)
    except:
        allowed_ids = []

    if machine_id not in allowed_ids:
        return jsonify({"valid": False, "reason": "Not allowed"}), 403

    # Prepare license content
    license_text = f"{machine_id}\nPWD17610"
    license_path = os.path.join(LICENSE_FOLDER, "license.txt")
    with open(license_path, "w") as f:
        f.write(license_text)

    # Generate .xlsm file
    output_xlsm = f"QTY_Network_2025_{machine_id}.xlsm"
    if not os.path.exists(output_xlsm):
        try:
            shutil.copyfile(TEMPLATE_FILE, output_xlsm)
        except Exception as e:
            return jsonify({"valid": False, "reason": f"Error copying XLSM: {e}"}), 500

    # Wait until the file is confirmed to exist
    timeout = 5
    while not os.path.exists(output_xlsm) and timeout > 0:
        time.sleep(0.5)
        timeout -= 0.5

    if not os.path.exists(output_xlsm):
        return jsonify({"valid": False, "reason": "XLSM generation failed"}), 500

    return jsonify({
        "valid": True,
        "license": license_text,
        "download_files": [
            {"filename": "license.txt", "path": license_path},
            {"filename": "Launcher.xlsm", "path": LAUNCHER_FILE},
            {"filename": output_xlsm, "path": output_xlsm}
        ]
    })

@app.route("/admin")
def admin_panel():
    try:
        with open(ALLOWED_IDS_FILE, "r") as f:
            allowed_ids = json.load(f)
    except:
        allowed_ids = []

    try:
        with open(PENDING_IDS_FILE, "r") as f:
            pending_ids = json.load(f)
    except:
        pending_ids = []

    html = """
    <h1>Admin Panel - XLSM Tool</h1>
    <h2>Pending Approvals</h2>
    <ul>
    {% for id in pending %}
        <li>{{ id }}
            <a href="/approve/{{ id }}">✅ Approve</a>
            <a href="/reject/{{ id }}">❌ Reject</a>
        </li>
    {% endfor %}
    </ul>
    <h2>Approved IDs</h2>
    <ul>
    {% for id in approved %}
        <li>{{ id }}</li>
    {% endfor %}
    </ul>
    """
    return render_template_string(html, pending=pending_ids, approved=allowed_ids)

@app.route("/approve/<machine_id>")
def approve_id(machine_id):
    machine_id = str(machine_id).strip()

    try:
        with open(PENDING_IDS_FILE, "r") as f:
            pending_ids = json.load(f)
    except:
        pending_ids = []

    try:
        with open(ALLOWED_IDS_FILE, "r") as f:
            allowed_ids = json.load(f)
    except:
        allowed_ids = []

    if machine_id not in allowed_ids:
        allowed_ids.append(machine_id)
    if machine_id in pending_ids:
        pending_ids.remove(machine_id)

    with open(ALLOWED_IDS_FILE, "w") as f:
        json.dump(allowed_ids, f, indent=2)
    with open(PENDING_IDS_FILE, "w") as f:
        json.dump(pending_ids, f, indent=2)

    return f"✅ {machine_id} approved."

@app.route("/reject/<machine_id>")
def reject_id(machine_id):
    try:
        with open(PENDING_IDS_FILE, "r") as f:
            pending_ids = json.load(f)
    except:
        pending_ids = []

    if machine_id in pending_ids:
        pending_ids.remove(machine_id)

    with open(PENDING_IDS_FILE, "w") as f:
        json.dump(pending_ids, f, indent=2)

    return f"❌ {machine_id} rejected."

@app.route("/download/<filename>")
def download_file(filename):
    try:
        return send_file(filename, as_attachment=True)
    except:
        return "File not found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
