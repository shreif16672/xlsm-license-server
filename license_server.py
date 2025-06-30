from flask import Flask, request, send_file, jsonify, render_template_string
import json
import os
import shutil
import time

app = Flask(__name__)

LICENSE_DIR = "."
PROGRAM_ID = "xlsm_tool"

ALLOWED_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_FILE = f"pending_ids_{PROGRAM_ID}.json"
TEMPLATE_FILE = "template.xlsm"


def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return []


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


def add_to_pending(machine_id):
    pending = load_json(PENDING_FILE)
    if machine_id not in pending:
        pending.append(machine_id)
        save_json(PENDING_FILE, pending)


@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    print(f"Received machine_id: {machine_id}")
    print(f"Program ID: {program_id}")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    if program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Invalid program_id"}), 403

    allowed = load_json(ALLOWED_FILE)
    if machine_id not in allowed:
        add_to_pending(machine_id)
        return jsonify({"valid": False, "reason": "Not allowed"}), 403

    # Copy template to machine-specific XLSM
    output_filename = f"QTY_Network_2025_{machine_id}.xlsm"
    output_path = os.path.join(LICENSE_DIR, output_filename)

    try:
        shutil.copyfile(TEMPLATE_FILE, output_path)
    except Exception as e:
        return jsonify({"valid": False, "reason": f"Copy failed: {e}"}), 500

    # Write license.txt (machine ID and password)
    password = f"PWD{str(int(machine_id) % 90000 + 10000)}"
    license_txt_path = "license.txt"
    with open(license_txt_path, "w") as f:
        f.write(machine_id + "\n" + password)

    # Wait until file exists
    for _ in range(20):
        if os.path.exists(output_path):
            break
        time.sleep(0.2)

    response = {
        "valid": True,
        "license_file": "license.txt",
        "excel_file": output_filename,
        "launcher_file": "Launcher.xlsm",
        "installer_file": "installer_lifetime.exe",
        "license": {
            "machine_id": machine_id,
            "password": password
        }
    }
    return jsonify(response)


@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@app.route("/admin/xlsm_tool")
def admin_xlsm():
    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)

    html = f"""
    <h1>Admin Panel - {PROGRAM_ID}</h1>
    <h2>Pending Requests</h2>
    <ul>
        {''.join([f"<li>{mid} <a href='/approve/{mid}'>[Approve]</a> <a href='/reject/{mid}'>[Reject]</a></li>" for mid in pending])}
    </ul>
    <h2>Approved Machines</h2>
    <ul>
        {''.join([f"<li>{mid}</li>" for mid in allowed])}
    </ul>
    """
    return render_template_string(html)


@app.route("/approve/<machine_id>")
def approve(machine_id):
    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)
    if machine_id not in allowed:
        allowed.append(machine_id)
    if machine_id in pending:
        pending.remove(machine_id)
    save_json(ALLOWED_FILE, allowed)
    save_json(PENDING_FILE, pending)
    return f"✅ Approved {machine_id}. <a href='/admin/xlsm_tool'>Back</a>"


@app.route("/reject/<machine_id>")
def reject(machine_id):
    pending = load_json(PENDING_FILE)
    if machine_id in pending:
        pending.remove(machine_id)
        save_json(PENDING_FILE, pending)
    return f"❌ Rejected {machine_id}. <a href='/admin/xlsm_tool'>Back</a>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
