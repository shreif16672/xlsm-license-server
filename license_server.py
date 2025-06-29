from flask import Flask, request, jsonify, render_template_string, send_file
import os
import json
import shutil

app = Flask(__name__)
PROGRAM_ID = "xlsm_tool"

# File paths
ALLOWED_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_FILE = f"pending_ids_{PROGRAM_ID}.json"
TEMPLATE_FILE = "template.xlsm"
INSTALLER_FILE = "installer_lifetime.exe"
LAUNCHER_FILE = "Launcher.xlsm"

# Ensure JSON storage exists
for file_path in [ALLOWED_FILE, PENDING_FILE]:
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump([], f)

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 403

    if program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Invalid program_id"}), 403

    allowed_ids = load_json(ALLOWED_FILE)
    pending_ids = load_json(PENDING_FILE)

    if machine_id in allowed_ids:
        license_data = {
            "machine_id": machine_id,
            "license": "Licensed XLSM Tool — Lifetime Access"
        }
        with open(os.path.expanduser("~\\AppData\\Roaming\\DynamoLicense\\license.txt"), "w") as f:
            f.write(json.dumps(license_data))

        # Copy template.xlsm and rename
        new_file = f"QTY_Network_2025_{machine_id}.xlsm"
        try:
            shutil.copyfile(TEMPLATE_FILE, new_file)
        except Exception as e:
            return jsonify({"valid": False, "reason": str(e)}), 500

        return jsonify({
            "valid": True,
            "files": {
                "launcher": LAUNCHER_FILE,
                "installer": INSTALLER_FILE,
                "xlsm": new_file
            }
        })

    # Not yet approved → add to pending if not already
    if machine_id not in pending_ids:
        pending_ids.append(machine_id)
        save_json(PENDING_FILE, pending_ids)

    return jsonify({"valid": False, "reason": "Pending approval"}), 403

@app.route("/admin", methods=["GET", "POST"])
def admin():
    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)

    if request.method == "POST":
        action = request.form.get("action")
        machine_id = request.form.get("machine_id")
        if action == "approve" and machine_id not in allowed:
            allowed.append(machine_id)
            save_json(ALLOWED_FILE, allowed)
            if machine_id in pending:
                pending.remove(machine_id)
                save_json(PENDING_FILE, pending)
        elif action == "reject" and machine_id in pending:
            pending.remove(machine_id)
            save_json(PENDING_FILE, pending)

    html = """<!DOCTYPE html><html><body>
    <h2>Pending Approvals</h2>
    {% for mid in pending %}
        <form method='post'>
            <input type='hidden' name='machine_id' value='{{ mid }}'>
            {{ mid }}
            <button name='action' value='approve'>Approve</button>
            <button name='action' value='reject'>Reject</button>
        </form>
    {% endfor %}
    <h2>Approved Machine IDs</h2>
    <ul>
    {% for mid in allowed %}
        <li>{{ mid }}</li>
    {% endfor %}
    </ul></body></html>
    """
    return render_template_string(html, pending=pending, allowed=allowed)

@app.route("/download/<filename>")
def download(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
