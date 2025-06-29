from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import json
import shutil
import time

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
DATA_DIR = "."

# ---------------- PATHS ----------------
ALLOWED_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_FILE = f"pending_ids_{PROGRAM_ID}.json"
TEMPLATE_XLSM = "template.xlsm"
FILES_DIR = "."

# ------------- UTILITIES --------------
def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def calculate_password(machine_id):
    return "PWD" + str(int(machine_id) % 9999 + 12345)

def generate_xlsm(machine_id):
    output_file = f"QTY_Network_2025_{machine_id}.xlsm"
    output_path = os.path.join(FILES_DIR, output_file)
    if not os.path.exists(output_path):
        shutil.copyfile(TEMPLATE_XLSM, output_path)
        time.sleep(1)  # Ensure it's written
    return output_file

# ----------- LICENSE ENDPOINT ----------
@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    if program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Invalid program"}), 403

    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)

    if machine_id in allowed:
        password = calculate_password(machine_id)
        xlsm_file = generate_xlsm(machine_id)
        return jsonify({
            "valid": True,
            "license": f"{machine_id}\n{password}",
            "download_files": ["Launcher.xlsm", "installer_lifetime.exe", xlsm_file]
        })

    if machine_id not in pending:
        pending.append(machine_id)
        save_json(PENDING_FILE, pending)

    return jsonify({"valid": False, "reason": "Pending approval"})

# ----------- FILE DOWNLOAD -------------
@app.route("/files/<path:filename>")
def download_file(filename):
    return send_from_directory(FILES_DIR, filename)

# ----------- ADMIN PANEL ---------------
@app.route("/admin/xlsm_tool")
def admin_panel():
    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)

    html = """
    <h1>🔐 XLSM TOOL LICENSE ADMIN</h1>
    <h2>Pending Approvals:</h2>
    {% for id in pending %}
        <form method="post" action="/admin/xlsm_tool/approve">
            <input type="hidden" name="machine_id" value="{{ id }}">
            <button type="submit">✅ Approve {{ id }}</button>
        </form>
        <form method="post" action="/admin/xlsm_tool/reject">
            <input type="hidden" name="machine_id" value="{{ id }}">
            <button type="submit">❌ Reject {{ id }}</button>
        </form>
        <hr>
    {% endfor %}
    <h2>Approved IDs:</h2>
    <ul>
    {% for id in allowed %}
        <li>{{ id }}</li>
    {% endfor %}
    </ul>
    """
    return render_template_string(html, pending=pending, allowed=allowed)

@app.route("/admin/xlsm_tool/approve", methods=["POST"])
def approve():
    machine_id = request.form.get("machine_id")
    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)
    if machine_id and machine_id not in allowed:
        allowed.append(machine_id)
        save_json(ALLOWED_FILE, allowed)
    if machine_id in pending:
        pending.remove(machine_id)
        save_json(PENDING_FILE, pending)
    return "✅ Approved. <a href='/admin/xlsm_tool'>Back</a>"

@app.route("/admin/xlsm_tool/reject", methods=["POST"])
def reject():
    machine_id = request.form.get("machine_id")
    pending = load_json(PENDING_FILE)
    if machine_id in pending:
        pending.remove(machine_id)
        save_json(PENDING_FILE, pending)
    return "❌ Rejected. <a href='/admin/xlsm_tool'>Back</a>"

# ---------- MAIN RUNNER ---------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
