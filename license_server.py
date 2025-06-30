import os
import json
import shutil
import time
from flask import Flask, request, jsonify, send_from_directory, render_template_string

app = Flask(__name__)
PROGRAM_ID = "xlsm_tool"
TEMPLATE_FILE = "template.xlsm"
LICENSE_FOLDER = "./"

def get_file_path(file):
    return os.path.join(LICENSE_FOLDER, file)

def load_json(file):
    path = get_file_path(file)
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(get_file_path(file), "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = str(data.get("machine_id", ""))
    program_id = data.get("program_id", "")

    if not machine_id or program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    allowed_file = f"allowed_ids_{program_id}.json"
    pending_file = f"pending_ids_{program_id}.json"

    allowed_ids = load_json(allowed_file)
    pending_ids = load_json(pending_file)

    if machine_id in allowed_ids:
        # Approved - generate license + file
        license_path = os.path.join(LICENSE_FOLDER, f"license_{machine_id}.txt")
        with open(license_path, "w") as f:
            f.write(f"{machine_id}\nPWD{17610 + int(machine_id[-3:], 10) % 1000}")

        # Copy laptop.xlsm and rename
        new_file = f"QTY_Network_2025_{machine_id}.xlsm"
        template_path = get_file_path(TEMPLATE_FILE)
        new_file_path = get_file_path(new_file)
        if not os.path.exists(new_file_path):
            shutil.copyfile(template_path, new_file_path)
            time.sleep(1)

        return jsonify({
            "valid": True,
            "license_url": f"/download/license_{machine_id}.txt",
            "xlsm_url": f"/download/{new_file}",
            "launcher_url": f"/download/Launcher.xlsm"
        })

    elif machine_id not in pending_ids:
        pending_ids.append(machine_id)
        save_json(pending_file, pending_ids)
        return jsonify({"valid": False, "reason": "Pending approval"}), 403

    else:
        return jsonify({"valid": False, "reason": "Pending approval"}), 403

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(LICENSE_FOLDER, filename, as_attachment=True)

@app.route("/admin/xlsm_tool")
def admin_panel():
    allowed = load_json("allowed_ids_xlsm_tool.json")
    pending = load_json("pending_ids_xlsm_tool.json")

    html = """
    <h1>XLSM License Admin Panel</h1>
    <h2>Pending Approvals</h2>
    <ul>
        {% for id in pending %}
            <li>{{ id }} <a href="/approve/{{ id }}">[Approve]</a> <a href="/reject/{{ id }}">[Reject]</a></li>
        {% endfor %}
    </ul>
    <h2>Approved IDs</h2>
    <ul>
        {% for id in allowed %}
            <li>{{ id }}</li>
        {% endfor %}
    </ul>
    """
    return render_template_string(html, pending=pending, allowed=allowed)

@app.route("/approve/<machine_id>")
def approve(machine_id):
    machine_id = str(machine_id)
    allowed = load_json("allowed_ids_xlsm_tool.json")
    pending = load_json("pending_ids_xlsm_tool.json")
    if machine_id not in allowed:
        allowed.append(machine_id)
    if machine_id in pending:
        pending.remove(machine_id)
    save_json("allowed_ids_xlsm_tool.json", allowed)
    save_json("pending_ids_xlsm_tool.json", pending)
    return f"✅ Approved {machine_id}. <a href='/admin/xlsm_tool'>Back</a>"

@app.route("/reject/<machine_id>")
def reject(machine_id):
    machine_id = str(machine_id)
    pending = load_json("pending_ids_xlsm_tool.json")
    if machine_id in pending:
        pending.remove(machine_id)
    save_json("pending_ids_xlsm_tool.json", pending)
    return f"❌ Rejected {machine_id}. <a href='/admin/xlsm_tool'>Back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
