import os
import json
import shutil
import time
from flask import Flask, request, jsonify, send_file, render_template_string

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
DATA_FOLDER = "."
TEMPLATE_FILE = "template.xlsm"

# File paths
allowed_path = os.path.join(DATA_FOLDER, f"allowed_ids_{PROGRAM_ID}.json")
pending_path = os.path.join(DATA_FOLDER, f"pending_ids_{PROGRAM_ID}.json")

# Ensure JSON files exist
for path in [allowed_path, pending_path]:
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump([], f)

# HTML template for admin panel
HTML_TEMPLATE = """
<h2>✅ Approved Machine IDs</h2>
<ul>
{% for mid in approved %}
  <li>{{ mid }}</li>
{% endfor %}
</ul>

<h2>🕒 Pending Machine IDs</h2>
<ul>
{% for mid in pending %}
  <li>
    {{ mid }}
    <a href="/approve/{{ mid }}">[Approve]</a>
    <a href="/reject/{{ mid }}">[Reject]</a>
  </li>
{% endfor %}
</ul>
"""

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if program_id != PROGRAM_ID or not machine_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    # Load allowed and pending
    with open(allowed_path, "r") as f:
        allowed_ids = json.load(f)

    with open(pending_path, "r") as f:
        pending_ids = json.load(f)

    if machine_id not in allowed_ids:
        if machine_id not in pending_ids:
            pending_ids.append(machine_id)
            with open(pending_path, "w") as f:
                json.dump(pending_ids, f)
        return jsonify({"valid": False, "reason": "Pending approval"})

    # Prepare license content
    ascii_sum = sum(ord(c) for c in machine_id)
    password = f"PWD{12800 + (ascii_sum % 100)}"
    license_text = f"{machine_id}\n{password}"

    license_dir = os.path.join(os.getenv("APPDATA", "/tmp"), "DynamoLicense")
    os.makedirs(license_dir, exist_ok=True)
    license_path = os.path.join(license_dir, "license.txt")
    with open(license_path, "w") as f:
        f.write(license_text)

    # Create XLSM file dynamically
    output_filename = f"QTY_Network_2025_{machine_id}.xlsm"
    output_path = os.path.join(DATA_FOLDER, output_filename)
    if not os.path.exists(output_path):
        shutil.copy(TEMPLATE_FILE, output_path)
        time.sleep(1)  # Ensure file write completes

    return jsonify({
        "valid": True,
        "license": license_text,
        "files": {
            "license": "license.txt",
            "xlsm": output_filename,
            "launcher": "Launcher.xlsm"
        }
    })

@app.route("/download/<filename>")
def download_file(filename):
    return send_file(os.path.join(DATA_FOLDER, filename), as_attachment=True)

@app.route("/admin")
def admin_panel():
    with open(allowed_path, "r") as f:
        approved = json.load(f)
    with open(pending_path, "r") as f:
        pending = json.load(f)
    return render_template_string(HTML_TEMPLATE, approved=approved, pending=pending)

@app.route("/approve/<machine_id>")
def approve(machine_id):
    with open(allowed_path, "r") as f:
        allowed = json.load(f)
    with open(pending_path, "r") as f:
        pending = json.load(f)

    if machine_id not in allowed:
        allowed.append(machine_id)
        with open(allowed_path, "w") as f:
            json.dump(allowed, f)

    if machine_id in pending:
        pending.remove(machine_id)
        with open(pending_path, "w") as f:
            json.dump(pending, f)

    return "✅ Approved. <a href='/admin'>Back</a>"

@app.route("/reject/<machine_id>")
def reject(machine_id):
    with open(pending_path, "r") as f:
        pending = json.load(f)

    if machine_id in pending:
        pending.remove(machine_id)
        with open(pending_path, "w") as f:
            json.dump(pending, f)

    return "❌ Rejected. <a href='/admin'>Back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
