from flask import Flask, request, jsonify, send_file, render_template_string
import os
import json
import shutil
import time

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
DATA_DIR = "."
TEMPLATE_FILE = "template.xlsm"

def get_json_path(file_type):
    return os.path.join(DATA_DIR, f"{file_type}_{PROGRAM_ID}.json")

def load_json(file_type):
    path = get_json_path(file_type)
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_json(file_type, data):
    path = get_json_path(file_type)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id", "").strip()
    program_id = data.get("program_id", "").strip()

    if program_id != PROGRAM_ID or not machine_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    allowed = load_json("allowed_ids")
    pending = load_json("pending_ids")

    if machine_id in allowed:
        license_path = os.path.join("licenses", f"{machine_id}.txt")
        os.makedirs("licenses", exist_ok=True)
        with open(license_path, "w") as f:
            f.write(f"{machine_id}\nPWD17610")

        # Create .xlsm file if not already
        new_file = f"QTY_Network_2025_{machine_id}.xlsm"
        new_file_path = os.path.join(DATA_DIR, new_file)
        if not os.path.exists(new_file_path):
            shutil.copyfile(TEMPLATE_FILE, new_file_path)

        return jsonify({
            "valid": True,
            "license_path": license_path,
            "download_files": {
                "license.txt": license_path,
                "Launcher.xlsm": os.path.join(DATA_DIR, "Launcher.xlsm"),
                "QTY_Network_2025": new_file_path
            }
        })

    # Add to pending if not already
    if machine_id not in pending:
        pending.append(machine_id)
        save_json("pending_ids", pending)

    return jsonify({"valid": False, "reason": "Pending approval"})

@app.route("/admin/xlsm_tool")
def admin_view():
    allowed = load_json("allowed_ids")
    pending = load_json("pending_ids")
    template = """
    <h2>✅ Approved Machine IDs</h2>
    <ul>
    {% for id in allowed %}
      <li>{{ id }}</li>
    {% endfor %}
    </ul>
    <h2>⏳ Pending Approvals</h2>
    <ul>
    {% for id in pending %}
      <li>
        {{ id }}
        <form action="/approve" method="post" style="display:inline;">
          <input type="hidden" name="machine_id" value="{{ id }}">
          <button type="submit">Approve</button>
        </form>
        <form action="/reject" method="post" style="display:inline;">
          <input type="hidden" name="machine_id" value="{{ id }}">
          <button type="submit">Reject</button>
        </form>
      </li>
    {% endfor %}
    </ul>
    """
    return render_template_string(template, allowed=allowed, pending=pending)

@app.route("/approve", methods=["POST"])
def approve():
    machine_id = request.form.get("machine_id", "").strip()
    allowed = load_json("allowed_ids")
    pending = load_json("pending_ids")

    if machine_id not in allowed:
        allowed.append(machine_id)
        save_json("allowed_ids", allowed)

    if machine_id in pending:
        pending.remove(machine_id)
        save_json("pending_ids", pending)

    return "Approved. <a href='/admin/xlsm_tool'>Back</a>"

@app.route("/reject", methods=["POST"])
def reject():
    machine_id = request.form.get("machine_id", "").strip()
    pending = load_json("pending_ids")
    if machine_id in pending:
        pending.remove(machine_id)
        save_json("pending_ids", pending)
    return "Rejected. <a href='/admin/xlsm_tool'>Back</a>"

@app.route("/")
def home():
    return "XLSM License Server is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
