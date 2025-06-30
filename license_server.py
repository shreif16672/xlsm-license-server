from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import json
import shutil
import time

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
DATA_DIR = "."
TEMPLATE_FILE = "template.xlsm"

def get_json_path(filename):
    return os.path.join(DATA_DIR, filename)

def load_json(filename):
    path = get_json_path(filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_json(filename, data):
    with open(get_json_path(filename), "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = str(data.get("machine_id", "")).strip()
    password = str(data.get("password", "")).strip()
    program_id = str(data.get("program_id", "")).strip()

    if not machine_id or not password or not program_id:
        return jsonify({"valid": False, "reason": "Missing fields"}), 400

    # Always add to pending list
    pending_file = f"pending_ids_{program_id}.json"
    allowed_file = f"allowed_ids_{program_id}.json"
    pending_ids = load_json(pending_file)
    allowed_ids = load_json(allowed_file)

    if machine_id not in pending_ids:
        pending_ids.append(machine_id)
        save_json(pending_file, pending_ids)

    # Not yet approved
    if machine_id not in allowed_ids:
        return jsonify({"valid": False, "reason": "Pending approval"}), 403

    # Approved – Create license file
    license_path = os.path.join(DATA_DIR, "license.txt")
    with open(license_path, "w") as f:
        f.write(machine_id + "\n")
        f.write(password + "\n")

    # Create .xlsm from template
    output_filename = f"QTY_Network_2025_{machine_id}.xlsm"
    if os.path.exists(TEMPLATE_FILE):
        shutil.copy(TEMPLATE_FILE, output_filename)

        # Wait until the file exists
        timeout = 5
        while timeout > 0 and not os.path.exists(output_filename):
            time.sleep(1)
            timeout -= 1

    # Final response
    return jsonify({
        "valid": True,
        "license_file": "license.txt",
        "xlsm_file": output_filename,
        "launcher": "Launcher.xlsm"
    })

@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(DATA_DIR, filename, as_attachment=True)

@app.route("/admin/xlsm_tool")
def admin_panel():
    pending_ids = load_json("pending_ids_xlsm_tool.json")
    allowed_ids = load_json("allowed_ids_xlsm_tool.json")
    return render_template_string("""
    <h1>Admin Panel – XLSM Tool</h1>
    <h2>Pending Requests</h2>
    <ul>
        {% for mid in pending_ids %}
        <li>{{ mid }} — <a href="/approve/{{ mid }}">Approve</a> | <a href="/reject/{{ mid }}">Reject</a></li>
        {% endfor %}
    </ul>
    <h2>Approved</h2>
    <ul>
        {% for mid in allowed_ids %}
        <li>{{ mid }}</li>
        {% endfor %}
    </ul>
    """, pending_ids=pending_ids, allowed_ids=allowed_ids)

@app.route("/approve/<machine_id>")
def approve(machine_id):
    allowed = load_json("allowed_ids_xlsm_tool.json")
    pending = load_json("pending_ids_xlsm_tool.json")

    if machine_id not in allowed:
        allowed.append(machine_id)
    if machine_id in pending:
        pending.remove(machine_id)

    save_json("allowed_ids_xlsm_tool.json", allowed)
    save_json("pending_ids_xlsm_tool.json", pending)
    return "✅ Approved"

@app.route("/reject/<machine_id>")
def reject(machine_id):
    pending = load_json("pending_ids_xlsm_tool.json")
    if machine_id in pending:
        pending.remove(machine_id)
        save_json("pending_ids_xlsm_tool.json", pending)
    return "❌ Rejected"

if __name__ == "__main__":
    app.run(debug=True, port=5000)
