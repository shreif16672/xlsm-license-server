from flask import Flask, request, jsonify, send_from_directory
import json
import os

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ALLOWED_IDS_FILE = os.path.join(BASE_DIR, f"allowed_ids_{PROGRAM_ID}.json")
PENDING_IDS_FILE = os.path.join(BASE_DIR, f"pending_ids_{PROGRAM_ID}.json")

FILES_FOLDER = BASE_DIR  # all files are in root folder (e.g., Launcher.xlsm)

LICENSE_KEY = "ENJAZ2025"  # hardcoded key used by .xlsm for validation

# Load JSON data helper
def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

# Save JSON data helper
def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    if not machine_id:
        return jsonify({"valid": False, "reason": "No machine ID provided"}), 400

    allowed_ids = load_json(ALLOWED_IDS_FILE)

    if machine_id not in allowed_ids:
        # Add to pending
        pending_ids = load_json(PENDING_IDS_FILE)
        if machine_id not in pending_ids:
            pending_ids.append(machine_id)
            save_json(PENDING_IDS_FILE, pending_ids)
        return jsonify({"valid": False, "reason": "Not allowed"}), 403

    # License is valid
    license_data = {
        "machine_id": machine_id,
        "program_id": PROGRAM_ID,
        "license": LICENSE_KEY
    }

    # Determine filenames
    xlsm_file = f"QTY_Network_2025_{machine_id}.xlsm"
    files = {
        "installer": "installer_lifetime.exe",
        "launcher": "Launcher.xlsm",
        "xlsm": xlsm_file
    }

    return jsonify({
        "status": "approved",
        "license": license_data,
        "files": files
    })

@app.route("/files/<filename>", methods=["GET"])
def download_file(filename):
    return send_from_directory(FILES_FOLDER, filename, as_attachment=True)

@app.route("/admin")
def admin_panel():
    allowed_ids = load_json(ALLOWED_IDS_FILE)
    pending_ids = load_json(PENDING_IDS_FILE)

    html = "<h2>XLSM Tool License Admin</h2>"
    html += "<h3>Pending Requests</h3><ul>"
    for mid in pending_ids:
        html += f"<li>{mid} <form action='/approve' method='post' style='display:inline;'><input type='hidden' name='id' value='{mid}'><button type='submit'>✅ Approve</button></form> <form action='/reject' method='post' style='display:inline;'><input type='hidden' name='id' value='{mid}'><button type='submit'>❌ Reject</button></form></li>"
    html += "</ul>"

    html += "<h3>Approved Machine IDs</h3><ul>"
    for mid in allowed_ids:
        html += f"<li>{mid}</li>"
    html += "</ul>"

    return html

@app.route("/approve", methods=["POST"])
def approve_id():
    mid = request.form.get("id")
    allowed = load_json(ALLOWED_IDS_FILE)
    pending = load_json(PENDING_IDS_FILE)

    if mid and mid not in allowed:
        allowed.append(mid)
        save_json(ALLOWED_IDS_FILE, allowed)

    if mid in pending:
        pending.remove(mid)
        save_json(PENDING_IDS_FILE, pending)

    return '<script>window.location.href="/admin";</script>'

@app.route("/reject", methods=["POST"])
def reject_id():
    mid = request.form.get("id")
    pending = load_json(PENDING_IDS_FILE)

    if mid in pending:
        pending.remove(mid)
        save_json(PENDING_IDS_FILE, pending)

    return '<script>window.location.href="/admin";</script>'

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
