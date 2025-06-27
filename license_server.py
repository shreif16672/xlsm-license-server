import os
import json
from flask import Flask, request, send_file

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
ALLOWED_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_FILE = f"pending_ids_{PROGRAM_ID}.json"

def load_json(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    if not machine_id:
        return {"valid": False, "reason": "Missing machine_id"}, 400

    allowed_ids = load_json(ALLOWED_FILE)
    pending_ids = load_json(PENDING_FILE)

    if machine_id in allowed_ids:
        print(f"✅ Approved Machine: {machine_id}")
        # Prepare downloadable files
        return {
            "valid": True,
            "message": "License granted",
            "files": [
                {"name": f"QTY_Network_2025_{machine_id}.xlsm", "path": "template.xlsm"},
                {"name": "Launcher.xlsm", "path": "Launcher.xlsm"},
                {"name": "installer_lifetime.exe", "path": "installer_lifetime.exe"}
            ]
        }

    # Add to pending
    if machine_id not in pending_ids:
        pending_ids[machine_id] = True
        save_json(PENDING_FILE, pending_ids)
        print(f"🕒 New Pending Machine: {machine_id}")

    return {"valid": False, "reason": "Not allowed"}, 403

@app.route("/admin", methods=["GET"])
def admin_page():
    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)

    pending_html = ""
    for mid in pending:
        pending_html += f"<li>{mid} " \
                        f"<form method='post' action='/approve' style='display:inline'>" \
                        f"<input type='hidden' name='machine_id' value='{mid}'>" \
                        f"<button type='submit'>✅ Approve</button></form> " \
                        f"<form method='post' action='/reject' style='display:inline'>" \
                        f"<input type='hidden' name='machine_id' value='{mid}'>" \
                        f"<button type='submit'>❌ Reject</button></form></li>"

    approved_html = ""
    for mid in allowed:
        approved_html += f"<li>{mid}</li>"

    return f"""
        <h1>XLSM Tool License Admin</h1>
        <h2>Pending</h2>
        <ul>{pending_html or '<p>No pending requests.</p>'}</ul>
        <h2>Approved</h2>
        <ul>{approved_html or '<p>No approved machines.</p>'}</ul>
    """

@app.route("/approve", methods=["POST"])
def approve():
    machine_id = request.form.get("machine_id")
    if not machine_id:
        return "Invalid request", 400

    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)

    allowed[machine_id] = True
    if machine_id in pending:
        del pending[machine_id]

    save_json(ALLOWED_FILE, allowed)
    save_json(PENDING_FILE, pending)

    return "<script>window.location.href = '/admin';</script>"

@app.route("/reject", methods=["POST"])
def reject():
    machine_id = request.form.get("machine_id")
    if not machine_id:
        return "Invalid request", 400

    pending = load_json(PENDING_FILE)
    if machine_id in pending:
        del pending[machine_id]
        save_json(PENDING_FILE, pending)

    return "<script>window.location.href = '/admin';</script>"

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    filepath = os.path.join(".", filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return f"File not found: {filename}", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
