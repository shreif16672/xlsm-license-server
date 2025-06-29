# license_server.py — FINAL version with xlwings and correct Drive Serial logic

import os
import json
import shutil
import subprocess
import time
from flask import Flask, request, jsonify, send_from_directory, render_template_string
import xlwings as xw

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_XLSM = os.path.join(BASE_DIR, "template.xlsm")

FILES_TO_SEND = [
    "Launcher.xlsm",
    "installer_lifetime.exe"
]

JSON_PATHS = {
    "allowed": os.path.join(BASE_DIR, f"allowed_ids_{PROGRAM_ID}.json"),
    "pending": os.path.join(BASE_DIR, f"pending_ids_{PROGRAM_ID}.json"),
    "rejected": os.path.join(BASE_DIR, f"rejected_ids_{PROGRAM_ID}.json"),
}

os.makedirs(BASE_DIR, exist_ok=True)
for path in JSON_PATHS.values():
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump([], f)

def get_drive_serial():
    try:
        output = subprocess.check_output('vol C:', shell=True, text=True)
        for line in output.splitlines():
            if "Serial Number is" in line:
                return line.strip().split("is")[-1].strip().replace("-", "")
    except Exception as e:
        return "UNKNOWN"

def generate_password(machine_id):
    seed = 12345
    for ch in machine_id:
        seed += ord(ch)
    return "PWD" + str(seed)

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id", "").strip().upper()
    program_id = data.get("program_id", "")

    if not machine_id or program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 403

    allowed = load_json(JSON_PATHS["allowed"])
    pending = load_json(JSON_PATHS["pending"])
    rejected = load_json(JSON_PATHS["rejected"])

    if machine_id in rejected:
        return jsonify({"valid": False, "reason": "License rejected"}), 403

    if machine_id not in allowed:
        if machine_id not in pending:
            pending.append(machine_id)
            save_json(JSON_PATHS["pending"], pending)
        return jsonify({"valid": False, "reason": "Pending approval"}), 403

    # Create licensed .xlsm
    target_file = os.path.join(BASE_DIR, f"QTY_Network_2025_{machine_id}.xlsm")
    if not os.path.exists(target_file):
        shutil.copyfile(TEMPLATE_XLSM, target_file)

        try:
            app_xl = xw.App(visible=False)
            wb = app_xl.books.open(target_file)
            try:
                sheet = wb.sheets["LicenseData"]
            except:
                sheet = wb.sheets.add(name="LicenseData", after=wb.sheets[-1])
            sheet["A1"].value = machine_id
            sheet["A2"].value = generate_password(machine_id)
            sheet.api.Visible = 2  # xlSheetVeryHidden
            wb.save()
            wb.close()
            app_xl.quit()
        except Exception as e:
            return jsonify({"valid": False, "reason": f"Excel write error: {e}"}), 500

    return jsonify({
        "valid": True,
        "machine_id": machine_id,
        "download_files": FILES_TO_SEND + [f"QTY_Network_2025_{machine_id}.xlsm"]
    })

@app.route("/files/<filename>")
def download_file(filename):
    return send_from_directory(BASE_DIR, filename, as_attachment=True)

@app.route("/admin")
def admin_panel():
    allowed = load_json(JSON_PATHS["allowed"])
    pending = load_json(JSON_PATHS["pending"])
    rejected = load_json(JSON_PATHS["rejected"])
    html = """
    <h1>Admin Panel — XLSM Tool</h1>
    <h2>Pending</h2>
    <ul>{% for mid in pending %}
        <li>{{ mid }} <a href="/admin/approve/{{ mid }}">✅ Approve</a> | <a href="/admin/reject/{{ mid }}">❌ Reject</a></li>
    {% endfor %}</ul>
    <h2>Approved</h2><ul>{% for mid in allowed %}<li>{{ mid }}</li>{% endfor %}</ul>
    <h2>Rejected</h2><ul>{% for mid in rejected %}<li>{{ mid }}</li>{% endfor %}</ul>
    """
    return render_template_string(html, pending=pending, allowed=allowed, rejected=rejected)

@app.route("/admin/approve/<machine_id>")
def approve(machine_id):
    mid = machine_id.upper()
    allowed = load_json(JSON_PATHS["allowed"])
    pending = load_json(JSON_PATHS["pending"])
    if mid not in allowed:
        allowed.append(mid)
    if mid in pending:
        pending.remove(mid)
    save_json(JSON_PATHS["allowed"], allowed)
    save_json(JSON_PATHS["pending"], pending)
    return f"✅ Approved {mid}. <a href='/admin'>Back</a>"

@app.route("/admin/reject/<machine_id>")
def reject(machine_id):
    mid = machine_id.upper()
    rejected = load_json(JSON_PATHS["rejected"])
    pending = load_json(JSON_PATHS["pending"])
    if mid not in rejected:
        rejected.append(mid)
    if mid in pending:
        pending.remove(mid)
    save_json(JSON_PATHS["rejected"], rejected)
    save_json(JSON_PATHS["pending"], pending)
    return f"❌ Rejected {mid}. <a href='/admin'>Back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
