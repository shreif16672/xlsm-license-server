from flask import Flask, request, jsonify, send_from_directory
import json
import os

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ALLOWED_IDS_FILE = os.path.join(BASE_DIR, f"allowed_ids_{PROGRAM_ID}.json")
PENDING_IDS_FILE = os.path.join(BASE_DIR, f"pending_ids_{PROGRAM_ID}.json")

FILES_FOLDER = BASE_DIR  # All files (xlsm, exe) are in the repo root
LICENSE_KEY = "ENJAZ2025"  # The key expected by the xlsm logic

# Load JSON
def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

# Save JSON
def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    try:
        data = request.get_json()
        machine_id = data.get("machine_id")
        if not machine_id:
            return jsonify({"valid": False, "reason": "No machine ID provided"}), 400

        allowed_ids = load_json(ALLOWED_IDS_FILE)

        if machine_id not in allowed_ids:
            pending_ids = load_json(PENDING_IDS_FILE)
            if machine_id not in pending_ids:
                pending_ids.append(machine_id)
                save_json(PENDING_IDS_FILE, pending_ids)
            return jsonify({"valid": False, "reason": "Not allowed"}), 403

        # Approved license
        license_data = {
            "machine_id": machine_id,
            "program_id": PROGRAM_ID,
            "license": LICENSE_KEY
        }

        # File paths (generic fallback filename is template.xlsm)
        files = {
            "installer": "installer_lifetime.exe",
            "launcher": "Launcher.xlsm",
            "xlsm": f"QTY_Network_2025_{machine_id}.xlsm" if os.path.exists(os.path.join(FILES_FOLDER, f"QTY_Network_2025_{machine_id}.xlsm")) else "template.xlsm"
        }

        return jsonify({
            "valid": True,
            "license": license_data,
            "files": files
        })

    except Exception as e:
        return jsonify({"valid": False, "reason": str(e)}), 500

@app.route("/files/<filename>", methods=["GET"])
def download_file(filename):
    return send_from_directory(FILES_FOLDER, filename, as_attachment=True)

@app.route("/admin")
def admin_panel():
    allowed_ids = load_json(ALLOWED_IDS_FILE)
    pending_ids = load_json(PENDING_IDS_FILE)

    html = "<h2>XLSM Tool License Admin</h2><h3>Pending Requests</h3><ul>"
    for mid in pending_ids:
        html += f"<li>{mid} <form action='/approve' method='post' style='display:inline;'><input type='hidden' name='id' value='{mid}'><button type='submit'>✅ Approve</button></form> <form action='/reject' method='post' style='display:inline;'><input type='hidden' name='id' value='{mid}'><button type='submit'>❌ Reject</button></form></li>"
    html += "</ul><h3>Approved Machine IDs</h3><ul>"
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
