from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import shutil
import json
import random
import time

app = Flask(__name__)

# JSON files
ALLOWED_FILE = "allowed_ids_xlsm_tool.json"
PENDING_FILE = "pending_ids_xlsm_tool.json"

# Home
@app.route("/")
def home():
    return "✅ XLSM License Server Running"

# License route
@app.route("/license_xlsm", methods=["POST"])
def license_xlsm():
    data = request.json
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    if program_id != "xlsm_tool":
        return jsonify({"valid": False, "reason": "Unknown program_id"}), 400

    # Load allowed list
    if os.path.exists(ALLOWED_FILE):
        with open(ALLOWED_FILE, "r") as f:
            allowed_ids = json.load(f)
    else:
        allowed_ids = []

    # ✅ Auto-approve: Add to allowed list
    if machine_id not in allowed_ids:
        allowed_ids.append(machine_id)
        with open(ALLOWED_FILE, "w") as f:
            json.dump(allowed_ids, f, indent=2)

    # ✅ Generate license content
    password = f"PWD{random.randint(10000, 99999)}"
    license_content = f"{machine_id}\n{password}"

    # Save license.txt
    with open("license.txt", "w") as f:
        f.write(license_content)

    # ✅ Generate QTY_Network_2025_xxxx.xlsm from template.xlsm
    xlsm_name = f"QTY_Network_2025_{machine_id}.xlsm"
    if not os.path.exists(xlsm_name):
        shutil.copy("template.xlsm", xlsm_name)

    # ✅ Return file download links
    response = {
        "valid": True,
        "license": license_content,
        "files": [
            {"filename": "license.txt"},
            {"filename": "Launcher.xlsm"},
            {"filename": xlsm_name}
        ]
    }

    return jsonify(response)

# Download route
@app.route("/download/<filename>")
def download(filename):
    folder = os.getcwd()
    return send_from_directory(folder, filename, as_attachment=True)

# Admin page (all approved and pending)
@app.route("/admin")
def admin():
    with open(ALLOWED_FILE, "r") as f:
        allowed_ids = json.load(f)
    with open(PENDING_FILE, "r") as f:
        pending_ids = json.load(f)

    html = """
    <h2>✅ Approved Machine IDs</h2>
    <ul>{% for id in allowed %}<li>{{ id }}</li>{% endfor %}</ul>
    <h2>⏳ Pending Requests</h2>
    <ul>{% for id in pending %}<li>{{ id }}</li>{% endfor %}</ul>
    """
    return render_template_string(html, allowed=allowed_ids, pending=pending_ids)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
