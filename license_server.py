import os
import json
import shutil
from flask import Flask, request, jsonify, send_from_directory, render_template_string

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
ALLOWED_IDS_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_IDS_FILE = f"pending_ids_{PROGRAM_ID}.json"
REJECTED_IDS_FILE = f"rejected_ids_{PROGRAM_ID}.json"
TEMPLATE_FILE = "template.xlsm"

STATIC_FILES = [
    "Launcher.xlsm",
    "installer_lifetime.exe"
]

# Ensure files exist
for file in [ALLOWED_IDS_FILE, PENDING_IDS_FILE, REJECTED_IDS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

@app.route('/generate', methods=['POST'])
def generate_license():
    try:
        data = request.get_json()
        machine_id = data.get("machine_id")
        program_id = data.get("program_id")

        if not machine_id or not program_id or program_id != PROGRAM_ID:
            return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

        # Check rejection list
        with open(REJECTED_IDS_FILE) as f:
            rejected_ids = json.load(f)
        if machine_id in rejected_ids:
            return jsonify({"valid": False, "reason": "Rejected"}), 403

        # Check approval list
        with open(ALLOWED_IDS_FILE) as f:
            allowed_ids = json.load(f)

        if machine_id in allowed_ids:
            # Build and send license JSON
            license_data = {
                "machine_id": machine_id,
                "program_id": program_id,
                "license_type": "lifetime"
            }

            license_path = os.path.join("licenses", f"{machine_id}.json")
            os.makedirs("licenses", exist_ok=True)
            with open(license_path, "w") as f:
                json.dump(license_data, f)

            # Copy template.xlsm to named file
            if os.path.exists(TEMPLATE_FILE):
                target_xlsm = f"QTY_Network_2025_{machine_id}.xlsm"
                shutil.copyfile(TEMPLATE_FILE, target_xlsm)

            return jsonify({
                "valid": True,
                "license": license_data
            })

        # Else: Not approved
        with open(PENDING_IDS_FILE) as f:
            pending_ids = json.load(f)
        if machine_id not in pending_ids:
            pending_ids.append(machine_id)
            with open(PENDING_IDS_FILE, "w") as f:
                json.dump(pending_ids, f)

        return jsonify({"valid": False, "reason": "Pending"}), 403

    except Exception as e:
        return jsonify({"valid": False, "reason": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    directory = os.getcwd()
    filepath = os.path.join(directory, filename)
    if os.path.exists(filepath):
        return send_from_directory(directory, filename, as_attachment=True)
    return "File not found", 404

@app.route("/admin", methods=["GET"])
def admin_page():
    def read_ids(path):
        try:
            with open(path) as f:
                return json.load(f)
        except:
            return []

    pending_ids = read_ids(PENDING_IDS_FILE)
    approved_ids = read_ids(ALLOWED_IDS_FILE)
    rejected_ids = read_ids(REJECTED_IDS_FILE)

    html = "<h1>XLSM Tool License Admin</h1>"

    def render_ids(title, ids, actions=False):
        result = f"<h2>{title}</h2><ul>"
        for mid in ids:
            result += f"<li>{mid}"
            if actions:
                result += f' ✅ <a href="/admin/approve/{mid}">Approve</a>'
                result += f' ❌ <a href="/admin/reject/{mid}">Reject</a>'
            result += "</li>"
        return result + "</ul>"

    html += render_ids("Pending Machine IDs", pending_ids, actions=True)
    html += render_ids("Approved Machine IDs", approved_ids)
    html += render_ids("Rejected Machine IDs", rejected_ids)

    return render_template_string(html)

@app.route("/admin/approve/<machine_id>")
def approve_id(machine_id):
    with open(ALLOWED_IDS_FILE) as f:
        allowed = json.load(f)
    with open(PENDING_IDS_FILE) as f:
        pending = json.load(f)

    if machine_id not in allowed:
        allowed.append(machine_id)
    if machine_id in pending:
        pending.remove(machine_id)

    with open(ALLOWED_IDS_FILE, "w") as f:
        json.dump(allowed, f)
    with open(PENDING_IDS_FILE, "w") as f:
        json.dump(pending, f)

    return "✅ Approved. <a href='/admin'>Return</a>"

@app.route("/admin/reject/<machine_id>")
def reject_id(machine_id):
    with open(REJECTED_IDS_FILE) as f:
        rejected = json.load(f)
    with open(PENDING_IDS_FILE) as f:
        pending = json.load(f)

    if machine_id not in rejected:
        rejected.append(machine_id)
    if machine_id in pending:
        pending.remove(machine_id)

    with open(REJECTED_IDS_FILE, "w") as f:
        json.dump(rejected, f)
    with open(PENDING_IDS_FILE, "w") as f:
        json.dump(pending, f)

    return "❌ Rejected. <a href='/admin'>Return</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
