from flask import Flask, request, jsonify, send_file, render_template_string
import os
import json
import shutil
import time

app = Flask(__name__)
TEMPLATE_FILE = "template.xlsm"
DOWNLOAD_FOLDER = "."

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")
    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    allowed_file = f"allowed_ids_{program_id}.json"
    pending_file = f"pending_ids_{program_id}.json"
    allowed = load_json(allowed_file)
    pending = load_json(pending_file)

    if machine_id not in allowed:
        if machine_id not in pending:
            pending[machine_id] = True
            save_json(pending_file, pending)
        return jsonify({"valid": False, "reason": "Pending approval"}), 403

    filename = f"QTY_Network_2025_{machine_id}.xlsm"
    dest_path = os.path.join(DOWNLOAD_FOLDER, filename)

    if not os.path.exists(dest_path):
        shutil.copy(TEMPLATE_FILE, dest_path)

    timeout = 15
    while not os.path.exists(dest_path) and timeout > 0:
        time.sleep(1)
        timeout -= 1

    if not os.path.exists(dest_path):
        return jsonify({"valid": False, "reason": "File generation timeout"}), 500

    return jsonify({
        "valid": True,
        "license": f"{machine_id}\nPWD{machine_id[-5:]}",
        "download_files": {
            "license": "license.txt",
            "xlsm": filename,
            "launcher": "Launcher.xlsm",
            "installer": "installer_lifetime.exe"
        }
    })

@app.route("/download/<filename>")
def download(filename):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "File not found", 404

@app.route("/admin/xlsm_tool")
def admin_panel():
    program_id = "xlsm_tool"
    pending_file = f"pending_ids_{program_id}.json"
    allowed_file = f"allowed_ids_{program_id}.json"
    pending = load_json(pending_file)
    allowed = load_json(allowed_file)

    html = "<h2>Pending Requests</h2>"
    for mid in pending:
        html += f"{mid} ✅ <a href='/approve/{program_id}/{mid}'>Approve</a> ❌ <a href='/reject/{program_id}/{mid}'>Reject</a><br>"

    html += "<h2>Approved IDs</h2>"
    for mid in allowed:
        html += f"{mid}<br>"

    return render_template_string(html)

@app.route("/approve/<program_id>/<machine_id>")
def approve(program_id, machine_id):
    pending = load_json(f"pending_ids_{program_id}.json")
    allowed = load_json(f"allowed_ids_{program_id}.json")

    if machine_id in pending:
        pending.pop(machine_id)
        allowed[machine_id] = True
        save_json(f"pending_ids_{program_id}.json", pending)
        save_json(f"allowed_ids_{program_id}.json", allowed)

    return f"✅ Approved {machine_id}<br><a href='/admin/{program_id}'>Back</a>"

@app.route("/reject/<program_id>/<machine_id>")
def reject(program_id, machine_id):
    pending = load_json(f"pending_ids_{program_id}.json")
    if machine_id in pending:
        pending.pop(machine_id)
        save_json(f"pending_ids_{program_id}.json", pending)
    return f"❌ Rejected {machine_id}<br><a href='/admin/{program_id}'>Back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
