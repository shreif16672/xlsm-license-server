from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import json
import shutil
import time

app = Flask(__name__)

DATA_FOLDER = "./"
PROGRAM_ID = "xlsm_tool"
TEMPLATE_FILE = "template.xlsm"

ALLOWED_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_FILE = f"pending_ids_{PROGRAM_ID}.json"

DOWNLOAD_FILES = [
    "license.txt",
    "Launcher.xlsm",
    "installer_lifetime.exe"
]

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)

    if machine_id in allowed:
        # Generate file if not already present
        xlsm_filename = f"QTY_Network_2025_{machine_id}.xlsm"
        if not os.path.exists(xlsm_filename):
            shutil.copyfile(TEMPLATE_FILE, xlsm_filename)

        # Wait until file is available
        for _ in range(10):
            if os.path.exists(xlsm_filename):
                break
            time.sleep(1)

        return jsonify({
            "valid": True,
            "license": f"{machine_id}\nPWD{machine_id[-5:]}",
            "files": DOWNLOAD_FILES + [xlsm_filename]
        })

    if machine_id not in pending:
        pending.append(machine_id)
        save_json(PENDING_FILE, pending)

    return jsonify({"valid": False, "reason": "Not approved yet"}), 403

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(DATA_FOLDER, filename, as_attachment=True)

@app.route("/admin")
@app.route(f"/admin/{PROGRAM_ID}")
def admin():
    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)

    html = "<h1>Pending Requests</h1>"
    for mid in pending:
        html += f"{mid} ✅ <a href='/approve/{mid}'>Approve</a> ❌ <a href='/reject/{mid}'>Reject</a><br>"

    html += "<h1>Approved IDs</h1>"
    for mid in allowed:
        html += f"{mid}<br>"

    return render_template_string(html)

@app.route("/approve/<machine_id>")
def approve(machine_id):
    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)

    if machine_id not in allowed:
        allowed.append(machine_id)
        save_json(ALLOWED_FILE, allowed)

    if machine_id in pending:
        pending.remove(machine_id)
        save_json(PENDING_FILE, pending)

    return "Approved."

@app.route("/reject/<machine_id>")
def reject(machine_id):
    pending = load_json(PENDING_FILE)
    if machine_id in pending:
        pending.remove(machine_id)
        save_json(PENDING_FILE, pending)
    return "Rejected."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
