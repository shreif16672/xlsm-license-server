import os
import json
import shutil
from flask import Flask, request, jsonify, send_file, render_template_string, redirect

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
TEMPLATE_FILE = "template.xlsm"
LICENSE_FOLDER = os.path.expandvars(r"%APPDATA%\DynamoLicense")
LICENSE_FILE_NAME = "license.txt"

PENDING_FILE = f"pending_ids_{PROGRAM_ID}.json"
ALLOWED_FILE = f"allowed_ids_{PROGRAM_ID}.json"

DOWNLOAD_FOLDER = "."  # All downloadable files must be in same folder as .exe

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Approval</title>
</head>
<body>
    <h1>Pending Requests for {{ program_id }}</h1>
    {% for item in pending %}
        <p>{{ item }} 
        <a href="/approve?program_id={{ program_id }}&machine_id={{ item }}">✅ Approve</a> | 
        <a href="/reject?program_id={{ program_id }}&machine_id={{ item }}">❌ Reject</a></p>
    {% endfor %}
    
    <h2>✅ Approved IDs</h2>
    {% for item in allowed %}
        <p>{{ item }}</p>
    {% endfor %}
</body>
</html>
"""

def generate_password(machine_id):
    seed = 12345
    for c in machine_id:
        seed += ord(c)
    return f"PWD{seed}"

def read_json(file):
    if not os.path.exists(file):
        return []
    with open(file, "r") as f:
        return json.load(f)

def write_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json(force=True)
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"reason": "Missing machine_id or program_id", "valid": False}), 403

    if program_id != PROGRAM_ID:
        return jsonify({"reason": "Invalid program ID", "valid": False}), 403

    allowed_ids = read_json(ALLOWED_FILE)
    if machine_id not in allowed_ids:
        pending = read_json(PENDING_FILE)
        if machine_id not in pending:
            pending.append(machine_id)
            write_json(PENDING_FILE, pending)
        return jsonify({"reason": "Pending approval", "valid": False}), 403

    password = generate_password(machine_id)
    license_text = f"{machine_id}\n{password}"

    # Write license file in AppData
    os.makedirs(LICENSE_FOLDER, exist_ok=True)
    license_path = os.path.join(LICENSE_FOLDER, LICENSE_FILE_NAME)
    with open(license_path, "w") as f:
        f.write(license_text)

    # Generate QTY_Network_2025_[MachineID].xlsm
    if not os.path.exists(TEMPLATE_FILE):
        return jsonify({"reason": f"{TEMPLATE_FILE} not found", "valid": False}), 500

    output_file = f"QTY_Network_2025_{machine_id}.xlsm"
    output_path = os.path.join(DOWNLOAD_FOLDER, output_file)
    shutil.copyfile(TEMPLATE_FILE, output_path)

    return jsonify({
        "valid": True,
        "license": license_text,
        "files": [
            output_file,
            "Launcher.xlsm",
            "installer_lifetime.exe"
        ]
    })

@app.route("/admin")
def admin():
    pending = read_json(PENDING_FILE)
    allowed = read_json(ALLOWED_FILE)
    return render_template_string(HTML_TEMPLATE, program_id=PROGRAM_ID, pending=pending, allowed=allowed)

@app.route("/approve")
def approve():
    machine_id = request.args.get("machine_id")
    program_id = request.args.get("program_id")

    if program_id != PROGRAM_ID:
        return redirect("/admin")

    pending = read_json(PENDING_FILE)
    allowed = read_json(ALLOWED_FILE)

    if machine_id in pending:
        pending.remove(machine_id)
        write_json(PENDING_FILE, pending)

    if machine_id not in allowed:
        allowed.append(machine_id)
        write_json(ALLOWED_FILE, allowed)

    return redirect("/admin")

@app.route("/reject")
def reject():
    machine_id = request.args.get("machine_id")
    program_id = request.args.get("program_id")

    if program_id != PROGRAM_ID:
        return redirect("/admin")

    pending = read_json(PENDING_FILE)
    if machine_id in pending:
        pending.remove(machine_id)
        write_json(PENDING_FILE, pending)

    return redirect("/admin")

@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return f"File {filename} not found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
