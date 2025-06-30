import os
import json
import time
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
DATA_FOLDER = "."
FILES_FOLDER = "."

ALLOWED_IDS_FILE = os.path.join(DATA_FOLDER, "allowed_ids_xlsm_tool.json")
PENDING_IDS_FILE = os.path.join(DATA_FOLDER, "pending_ids_xlsm_tool.json")
TEMPLATE_FILE = os.path.join(FILES_FOLDER, "template.xlsm")

def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def generate_filename(machine_id):
    return f"QTY_Network_2025_{machine_id}.xlsm"

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = str(data.get("machine_id", "")).strip()
    program_id = str(data.get("program_id", "")).strip()

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    allowed_ids = load_json(ALLOWED_IDS_FILE)
      print(f"Received machine_id: {machine_id}")
      print(f"Allowed: {allowed_ids}")
    if machine_id not in allowed_ids:
        # Add to pending list if not already there
        pending = load_json(PENDING_IDS_FILE)
        if machine_id not in pending:
            pending.append(machine_id)
            save_json(PENDING_IDS_FILE, pending)
        return jsonify({"valid": False, "reason": "Not allowed"}), 403

    # Generate target XLSM file if not exists
    target_xlsm = generate_filename(machine_id)
    target_path = os.path.join(FILES_FOLDER, target_xlsm)
    if not os.path.exists(target_path):
        if os.path.exists(TEMPLATE_FILE):
            import shutil
            shutil.copyfile(TEMPLATE_FILE, target_path)
            time.sleep(1)  # Allow time for file to be saved

    response = {
        "valid": True,
        "license": f"{machine_id}\nPWD{int(machine_id) % 9999 + 12345}",
        "download_files": [
            {"filename": "Launcher.xlsm", "path": "Launcher.xlsm"},
            {"filename": target_xlsm, "path": target_xlsm},
        ]
    }
    return jsonify(response)

@app.route("/files/<path:filename>", methods=["GET"])
def download_file(filename):
    try:
        return send_from_directory(FILES_FOLDER, filename, as_attachment=True)
    except Exception as e:
        return f"Error: {str(e)}", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
