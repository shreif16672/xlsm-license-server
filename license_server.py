from flask import Flask, request, jsonify, render_template_string, send_file
import os
import json
import shutil

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
ALLOWED_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_FILE = f"pending_ids_{PROGRAM_ID}.json"

FILES_TO_SEND = [
    "Launcher.xlsm",
    "installer_lifetime.exe"
]

TEMPLATE_FILE = "template.xlsm"
DOWNLOAD_PREFIX = "QTY_Network_2025_"

# Ensure files exist
for file in [ALLOWED_FILE, PENDING_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 403

    # Load allowed list
    with open(ALLOWED_FILE, "r") as f:
        allowed = json.load(f)

    if machine_id in allowed:
        # Generate license file content
        license_data = {
            "machine_id": machine_id,
            "program_id": program_id,
            "license": "Licensed XLSM Tool — Lifetime Access"
        }

        # Save license file
        license_path = "license.txt"
        with open(license_path, "w") as f:
            json.dump(license_data, f)

        # Prepare renamed Excel file
        output_name = f"{DOWNLOAD_PREFIX}{machine_id}.xlsm"
        if os.path.exists(TEMPLATE_FILE):
            shutil.copyfile(TEMPLATE_FILE, output_name)

        return jsonify({
            "valid": True,
            "license_file": license_path,
            "downloads": FILES_TO_SEND + [output_name]
        })

    else:
        # Add to pending list
        with open(PENDING_FILE, "r") as f:
            pending = json.load(f)
        if machine_id not in pending:
            pending.append(machine_id)
            with open(PENDING_FILE, "w") as f:
                json.dump(pending, f)

        return jsonify({
            "valid": False,
            "reason": "Request not allowed",
            "pending": True
        }), 403

@app.route('/admin', methods=['GET'])
def admin():
    with open(PENDING_FILE, "r") as f:
        pending = json.load(f)
    with open(ALLOWED_FILE, "r") as f:
        allowed = json.load(f)

    html = """
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending Machine IDs</h2>
    {% for mid in pending %}
        <li>{{ mid }}
            <form method='post' action='/approve' style='display:inline;'>
                <input type='hidden' name='machine_id' value='{{ mid }}'>
                <button type='submit'>Approve</button>
            </form>
            <form method='post' action='/reject' style='display:inline;'>
                <input type='hidden' name='machine_id' value='{{ mid }}'>
                <button type='submit'>Reject</button>
            </form>
        </li>
    {% endfor %}
    <h2>Approved Machine IDs</h2>
    {% for mid in allowed %}
        <li>{{ mid }}</li>
    {% endfor %}
    """
    return render_template_string(html, pending=pending, allowed=allowed)

@app.route('/approve', methods=['POST'])
def approve():
    machine_id = request.form.get("machine_id")
    if not machine_id:
        return "Missing machine_id", 400

    with open(PENDING_FILE, "r") as f:
        pending = json.load(f)
    with open(ALLOWED_FILE, "r") as f:
        allowed = json.load(f)

    if machine_id in pending:
        pending.remove(machine_id)
        with open(PENDING_FILE, "w") as f:
            json.dump(pending, f)
        if machine_id not in allowed:
            allowed.append(machine_id)
            with open(ALLOWED_FILE, "w") as f:
                json.dump(allowed, f)

    return "Approved successfully.<br><a href='/admin'>Back</a>"

@app.route('/reject', methods=['POST'])
def reject():
    machine_id = request.form.get("machine_id")
    if not machine_id:
        return "Missing machine_id", 400

    with open(PENDING_FILE, "r") as f:
        pending = json.load(f)

    if machine_id in pending:
        pending.remove(machine_id)
        with open(PENDING_FILE, "w") as f:
            json.dump(pending, f)

    return "Rejected successfully.<br><a href='/admin'>Back</a>"

@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return f"File {filename} not found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
