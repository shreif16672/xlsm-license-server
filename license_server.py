import os
import json
import shutil
import time
from flask import Flask, request, jsonify, send_from_directory, render_template_string

app = Flask(__name__)

DATA_DIR = "."
PROGRAM_ID = "xlsm_tool"
TEMPLATE_FILE = "template.xlsm"

ALLOWED_FILE = f"{DATA_DIR}/allowed_ids_{PROGRAM_ID}.json"
PENDING_FILE = f"{DATA_DIR}/pending_ids_{PROGRAM_ID}.json"

FILES_TO_SEND = ["Launcher.xlsm", "installer_lifetime.exe"]

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    machine_id = str(data.get("machine_id"))
    program_id = str(data.get("program_id"))

    print(f"📥 Received request: {machine_id} ({program_id})")

    if program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Invalid program ID"}), 400

    allowed_ids = load_json(ALLOWED_FILE)
    if machine_id in allowed_ids:
        filename = f"QTY_Network_2025_{machine_id}.xlsm"
        dst_path = os.path.join(DATA_DIR, filename)

        if not os.path.exists(dst_path):
            print(f"📄 Copying template to {filename}")
            shutil.copyfile(TEMPLATE_FILE, dst_path)

        # Wait until file is written completely
        for _ in range(10):
            if os.path.exists(dst_path):
                break
            time.sleep(0.5)

        return jsonify({
            "valid": True,
            "license": {
                "machine_id": machine_id,
                "password": f"PWD{str(int(machine_id) % 90000 + 10000)}"
            },
            "files": FILES_TO_SEND + [filename]
        })

    # Add to pending if not found
    pending_ids = load_json(PENDING_FILE)
    if machine_id not in pending_ids:
        pending_ids.append(machine_id)
        save_json(PENDING_FILE, pending_ids)
        print(f"🕒 Added to pending: {machine_id}")

    return jsonify({"valid": False, "reason": "Pending approval"}), 403

@app.route("/files/<path:filename>")
def download_file(filename):
    return send_from_directory(DATA_DIR, filename, as_attachment=True)

@app.route("/admin/xlsm_tool")
def admin_view():
    allowed_ids = load_json(ALLOWED_FILE)
    pending_ids = load_json(PENDING_FILE)

    html = """
    <h2>Pending Requests</h2>
    {% for mid in pending %}
      <p>{{ mid }} 
        <a href="/approve/{{ mid }}">✅ Approve</a> 
        <a href="/reject/{{ mid }}">❌ Reject</a>
      </p>
    {% endfor %}

    <h2>Approved IDs</h2>
    {% for mid in allowed %}
      <p>{{ mid }}</p>
    {% endfor %}
    """
    return render_template_string(html, pending=pending_ids, allowed=allowed_ids)

@app.route("/approve/<mid>")
def approve(mid):
    allowed_ids = load_json(ALLOWED_FILE)
    pending_ids = load_json(PENDING_FILE)

    if mid not in allowed_ids:
        allowed_ids.append(mid)
        save_json(ALLOWED_FILE, allowed_ids)

    if mid in pending_ids:
        pending_ids.remove(mid)
        save_json(PENDING_FILE, pending_ids)

    return f"✅ Approved: {mid}<br><a href='/admin/xlsm_tool'>Back</a>"

@app.route("/reject/<mid>")
def reject(mid):
    pending_ids = load_json(PENDING_FILE)
    if mid in pending_ids:
        pending_ids.remove(mid)
        save_json(PENDING_FILE, pending_ids)

    return f"❌ Rejected: {mid}<br><a href='/admin/xlsm_tool'>Back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
