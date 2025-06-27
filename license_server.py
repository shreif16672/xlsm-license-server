from flask import Flask, request, jsonify, send_file, render_template_string
import json
import os
from datetime import datetime
import hashlib

app = Flask(__name__)

ALLOWED_FILE = "allowed_ids_xlsm_tool.json"
PENDING_FILE = "pending_ids_xlsm_tool.json"

DOWNLOAD_FILES = [
    "installer_lifetime.exe",
    "QTY_Network_2025_{machine_id}.xlsm",
    "Launcher.xlsm"
]

# Ensure files exist
for f in [ALLOWED_FILE, PENDING_FILE]:
    if not os.path.exists(f):
        with open(f, "w") as file:
            json.dump({}, file)

# HTML template for admin interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>XLSM Tool License Admin</title></head>
<body>
    <h2>XLSM Tool License Admin</h2>
    <h3>Pending</h3>
    {% if pending_ids %}
        <ul>
        {% for mid in pending_ids %}
            <li>
                {{ mid }}
                <form method="post" action="/admin" style="display:inline;">
                    <input type="hidden" name="machine_id" value="{{ mid }}">
                    <button type="submit" name="action" value="approve">✅ Approve</button>
                    <button type="submit" name="action" value="reject">❌ Reject</button>
                </form>
            </li>
        {% endfor %}
        </ul>
    {% else %}
        <p>No pending requests.</p>
    {% endif %}

    <h3>Approved</h3>
    <ul>
    {% for mid in allowed_ids %}
        <li>{{ mid }}</li>
    {% endfor %}
    </ul>
</body>
</html>
"""

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id", "").strip().upper()
    if not machine_id:
        return jsonify({"valid": False, "reason": "Missing machine ID"}), 400

    # Check if approved
    with open(ALLOWED_FILE) as f:
        allowed = json.load(f)
    if machine_id in allowed:
        # Write license file
        license_content = {
            "machine_id": machine_id,
            "issued": datetime.now().isoformat()
        }
        license_file = f"QTY_Network_2025_{machine_id}.xlsm"
        template_path = "template.xlsm"
        if not os.path.exists(template_path):
            return jsonify({"valid": False, "reason": "Template missing"}), 500
        # Copy template
        with open(template_path, "rb") as src, open(license_file, "wb") as dst:
            dst.write(src.read())
        return jsonify({
            "valid": True,
            "message": "License approved",
            "files": DOWNLOAD_FILES
        })
    else:
        # Add to pending
        with open(PENDING_FILE) as f:
            pending = json.load(f)
        if machine_id not in pending:
            pending[machine_id] = datetime.now().isoformat()
            with open(PENDING_FILE, "w") as f:
                json.dump(pending, f, indent=2)
        return jsonify({"valid": False, "reason": "Not allowed"}), 403

@app.route("/download/<filename>")
def download_file(filename):
    if not os.path.exists(filename):
        return f"File not found: {filename}", 404
    return send_file(filename, as_attachment=True)

@app.route("/admin", methods=["GET", "POST"])
def admin_page():
    # Handle approval actions
    if request.method == "POST":
        action = request.form.get("action")
        machine_id = request.form.get("machine_id", "").strip().upper()

        with open(ALLOWED_FILE) as f:
            allowed = json.load(f)
        with open(PENDING_FILE) as f:
            pending = json.load(f)

        if action == "approve":
            allowed[machine_id] = datetime.now().isoformat()
            if machine_id in pending:
                del pending[machine_id]
        elif action == "reject":
            if machine_id in pending:
                del pending[machine_id]

        with open(ALLOWED_FILE, "w") as f:
            json.dump(allowed, f, indent=2)
        with open(PENDING_FILE, "w") as f:
            json.dump(pending, f, indent=2)

    # Display interface
    with open(ALLOWED_FILE) as f:
        allowed = json.load(f)
    with open(PENDING_FILE) as f:
        pending = json.load(f)

    return render_template_string(
        HTML_TEMPLATE,
        allowed_ids=list(allowed.keys()),
        pending_ids=list(pending.keys())
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
