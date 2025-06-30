from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import json
import shutil
import random

app = Flask(__name__)

# Filenames
ALLOWED_FILE = "allowed_ids_xlsm_tool.json"
PENDING_FILE = "pending_ids_xlsm_tool.json"
TEMPLATE_FILE = "template.xlsm"

@app.route("/")
def home():
    return "✅ XLSM license server is running."

@app.route("/license_xlsm", methods=["POST"])
def license_xlsm():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or program_id != "xlsm_tool":
        return jsonify({"valid": False, "reason": "Missing or invalid data"}), 400

    # Load allowed and pending lists
    allowed = []
    if os.path.exists(ALLOWED_FILE):
        with open(ALLOWED_FILE, "r") as f:
            allowed = json.load(f)

    # Auto-approve
    if machine_id not in allowed:
        allowed.append(machine_id)
        with open(ALLOWED_FILE, "w") as f:
            json.dump(allowed, f, indent=2)

    # Generate license.txt content
    password = f"PWD{random.randint(10000, 99999)}"
    license_content = f"{machine_id}\n{password}"
    with open("license.txt", "w") as f:
        f.write(license_content)

    # Generate QTY_Network_2025_[machine_id].xlsm
    output_file = f"QTY_Network_2025_{machine_id}.xlsm"
    if not os.path.exists(output_file):
        shutil.copy(TEMPLATE_FILE, output_file)

    # Return license + files
    return jsonify({
        "valid": True,
        "license": license_content,
        "files": [
            {"filename": "license.txt"},
            {"filename": "Launcher.xlsm"},
            {"filename": output_file}
        ]
    })

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(os.getcwd(), filename, as_attachment=True)

@app.route("/admin")
def admin():
    with open(ALLOWED_FILE, "r") as f:
        allowed = json.load(f)
    with open(PENDING_FILE, "r") as f:
        pending = json.load(f)
    html = """
    <h2>✅ Approved Machines</h2>
    <ul>{% for id in allowed %}<li>{{ id }}</li>{% endfor %}</ul>
    <h2>⏳ Pending Machines</h2>
    <ul>{% for id in pending %}<li>{{ id }}</li>{% endfor %}</ul>
    """
    return render_template_string(html, allowed=allowed, pending=pending)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
