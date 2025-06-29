from flask import Flask, request, jsonify, send_from_directory, render_template_string
import json
import os
import shutil

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
LICENSE_FILE = "license.txt"
TEMPLATE_FILE = "template.xlsm"
LAUNCHER_FILE = "Launcher.xlsm"
INSTALLER_FILE = "installer_lifetime.exe"

ALLOWED_IDS_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_IDS_FILE = f"pending_ids_{PROGRAM_ID}.json"

DOWNLOAD_FOLDER = os.path.dirname(os.path.abspath(__file__))

# Ensure storage files exist
for file in [ALLOWED_IDS_FILE, PENDING_IDS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json()
        machine_id = data.get("machine_id")
        program_id = data.get("program_id")
        if not machine_id or not program_id:
            return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 403
        if program_id != PROGRAM_ID:
            return jsonify({"valid": False, "reason": "Invalid program_id"}), 403

        # Load allowed machine IDs
        with open(ALLOWED_IDS_FILE, "r") as f:
            allowed_ids = json.load(f)

        if machine_id in allowed_ids:
            # Copy template.xlsm → QTY_Network_2025_[machine_id].xlsm
            renamed_file = f"QTY_Network_2025_{machine_id}.xlsm"
            renamed_path = os.path.join(DOWNLOAD_FOLDER, renamed_file)
            if os.path.exists(TEMPLATE_FILE):
                shutil.copy(TEMPLATE_FILE, renamed_path)
            else:
                return jsonify({"valid": False, "reason": f"Missing {TEMPLATE_FILE}"}), 403

            # Write license file content
            with open(os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "DynamoLicense", LICENSE_FILE), "w") as lic:
                lic.write(f"Licensed XLSM Tool — Lifetime Access\nMachine ID: {machine_id}")

            return jsonify({
                "valid": True,
                "status": "approved",
                "files": {
                    "launcher": LAUNCHER_FILE,
                    "installer": INSTALLER_FILE,
                    "xlsm": renamed_file
                }
            })

        # If not approved yet, store as pending
        with open(PENDING_IDS_FILE, "r") as f:
            pending_ids = json.load(f)
        if machine_id not in pending_ids:
            pending_ids.append(machine_id)
            with open(PENDING_IDS_FILE, "w") as f:
                json.dump(pending_ids, f)

        return jsonify({"valid": False, "status": "pending", "reason": "Your request is pending approval."})

    except Exception as e:
        return jsonify({"valid": False, "reason": str(e)}), 403

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

@app.route("/admin")
def admin():
    with open(PENDING_IDS_FILE, "r") as f:
        pending_ids = json.load(f)
    with open(ALLOWED_IDS_FILE, "r") as f:
        approved_ids = json.load(f)
    return render_template_string("""
        <h2>Pending Machine IDs</h2>
        <ul>
        {% for mid in pending %}
            <li>{{ mid }}
                <form action="/approve" method="post" style="display:inline;">
                    <input type="hidden" name="machine_id" value="{{ mid }}">
                    <button type="submit">Approve</button>
                </form>
            </li>
        {% endfor %}
        </ul>
        <h2>Approved Machine IDs</h2>
        <ul>
        {% for mid in approved %}
            <li>{{ mid }}</li>
        {% endfor %}
        </ul>
    """, pending=pending_ids, approved=approved_ids)

@app.route("/approve", methods=["POST"])
def approve():
    machine_id = request.form.get("machine_id")
    if not machine_id:
        return "Missing machine_id", 400
    with open(ALLOWED_IDS_FILE, "r") as f:
        allowed_ids = json.load(f)
    if machine_id not in allowed_ids:
        allowed_ids.append(machine_id)
        with open(ALLOWED_IDS_FILE, "w") as f:
            json.dump(allowed_ids, f)
    # Remove from pending
    with open(PENDING_IDS_FILE, "r") as f:
        pending_ids = json.load(f)
    if machine_id in pending_ids:
        pending_ids.remove(machine_id)
        with open(PENDING_IDS_FILE, "w") as f:
            json.dump(pending_ids, f)
    return "Approved and updated."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
