from flask import Flask, request, jsonify, send_from_directory, render_template_string
import json
import os
import shutil
import time

app = Flask(__name__)

DATA_DIR = "."
PROGRAM_ID = "xlsm_tool"

FILES = {
    "xlsm_tool": {
        "template": "template.xlsm",
        "launcher": "Launcher.xlsm",
        "allowed": "allowed_ids_xlsm_tool.json",
        "pending": "pending_ids_xlsm_tool.json"
    }
}

def load_json(path):
    return json.load(open(path)) if os.path.exists(path) else []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/request_license", methods=["POST"])
def request_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id or program_id not in FILES:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    f = FILES[program_id]
    allowed = load_json(f["allowed"])
    pending = load_json(f["pending"])

    if machine_id in allowed:
        xlsm_name = f"QTY_Network_2025_{machine_id}.xlsm"
        xlsm_path = os.path.join(DATA_DIR, xlsm_name)
        if not os.path.exists(xlsm_path):
            shutil.copyfile(f["template"], xlsm_path)

        timeout = 10
        while not os.path.exists(xlsm_path) and timeout > 0:
            time.sleep(1)
            timeout -= 1

        return jsonify({
            "valid": True,
            "machine_id": machine_id,
            "launcher_url": f"https://xlsm-license-server.onrender.com/download/Launcher.xlsm",
            "xlsm_url": f"https://xlsm-license-server.onrender.com/download/{xlsm_name}"
        })
    else:
        if machine_id not in pending:
            pending.append(machine_id)
            save_json(f["pending"], pending)
        return jsonify({"valid": False, "reason": "Pending approval"}), 202

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(DATA_DIR, filename, as_attachment=True)

@app.route("/admin/<program>")
def admin_view(program):
    if program not in FILES:
        return f"Invalid program: {program}", 404

    f = FILES[program]
    allowed = load_json(f["allowed"])
    pending = load_json(f["pending"])

    html = f"""
    <h2>Admin Panel: {program}</h2>
    <h3>Pending Approvals</h3>
    <ul>
    {''.join([f'<li>{mid} <a href="/approve/{program}/{mid}">Approve</a> | <a href="/reject/{program}/{mid}">Reject</a></li>' for mid in pending])}
    </ul>
    <h3>Approved Machines</h3>
    <ul>
    {''.join(f"<li>{mid}</li>" for mid in allowed)}
    </ul>
    """
    return render_template_string(html)

@app.route("/approve/<program>/<machine_id>")
def approve(program, machine_id):
    if program not in FILES:
        return "Invalid program", 404
    f = FILES[program]
    allowed = load_json(f["allowed"])
    pending = load_json(f["pending"])
    if machine_id not in allowed:
        allowed.append(machine_id)
        save_json(f["allowed"], allowed)
    if machine_id in pending:
        pending.remove(machine_id)
        save_json(f["pending"], pending)
    return f"✅ Approved {machine_id} for {program}. <a href='/admin/{program}'>Back</a>"

@app.route("/reject/<program>/<machine_id>")
def reject(program, machine_id):
    if program not in FILES:
        return "Invalid program", 404
    f = FILES[program]
    pending = load_json(f["pending"])
    if machine_id in pending:
        pending.remove(machine_id)
        save_json(f["pending"], pending)
    return f"❌ Rejected {machine_id} for {program}. <a href='/admin/{program}'>Back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
