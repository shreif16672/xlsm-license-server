from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import json
import shutil

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(BASE_DIR, "files")
os.makedirs(FILES_DIR, exist_ok=True)

TEMPLATE_FILE = os.path.join(BASE_DIR, "template.xlsm")
ALLOWED_IDS_FILE = os.path.join(BASE_DIR, "allowed_ids_xlsm_tool.json")
PENDING_IDS_FILE = os.path.join(BASE_DIR, "pending_ids_xlsm_tool.json")

def load_json(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r") as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

def calculate_password(machine_id):
    ascii_sum = sum(ord(char) for char in machine_id)
    return "PWD" + str(ascii_sum + 12345)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id or program_id != "xlsm_tool":
        return jsonify({"valid": False, "reason": "Missing or invalid request"}), 403

    allowed_ids = load_json(ALLOWED_IDS_FILE)
    pending_ids = load_json(PENDING_IDS_FILE)

    if machine_id in allowed_ids:
        # Generate license file
        password = calculate_password(machine_id)
        license_filename = f"license_{machine_id}.txt"
        license_path = os.path.join(FILES_DIR, license_filename)
        with open(license_path, "w") as f:
            f.write(f"{machine_id}\n{password}")

        # Generate Excel file
        output_filename = f"QTY_Network_2025_{machine_id}.xlsm"
        output_path = os.path.join(FILES_DIR, output_filename)
        if not os.path.exists(output_path):
            shutil.copyfile(TEMPLATE_FILE, output_path)

        return jsonify({
            "valid": True,
            "download_files": [
                license_filename,
                "Launcher.xlsm",
                "installer_lifetime.exe",
                output_filename
            ]
        })

    if machine_id not in pending_ids:
        pending_ids.append(machine_id)
        save_json(PENDING_IDS_FILE, pending_ids)

    return jsonify({"valid": False, "reason": "Pending approval"})

@app.route("/files/<path:filename>")
def download_file(filename):
    return send_from_directory(FILES_DIR, filename, as_attachment=True)

@app.route("/admin/xlsm_tool", methods=["GET", "POST"])
def admin_panel():
    allowed = load_json(ALLOWED_IDS_FILE)
    pending = load_json(PENDING_IDS_FILE)

    if request.method == "POST":
        action = request.form.get("action")
        machine_id = request.form.get("machine_id")
        if action == "approve" and machine_id not in allowed:
            allowed.append(machine_id)
            save_json(ALLOWED_IDS_FILE, allowed)
            pending = [mid for mid in pending if mid != machine_id]
            save_json(PENDING_IDS_FILE, pending)
        elif action == "reject" and machine_id in pending:
            pending = [mid for mid in pending if mid != machine_id]
            save_json(PENDING_IDS_FILE, pending)

    html = """
    <h2>🧾 Pending IDs</h2>
    {% for mid in pending %}
      <form method="post" style="margin-bottom:10px;">
        <b>{{ mid }}</b>
        <input type="hidden" name="machine_id" value="{{ mid }}">
        <button name="action" value="approve">✅ Approve</button>
        <button name="action" value="reject">❌ Reject</button>
      </form>
    {% endfor %}
    <h2>✅ Approved IDs</h2>
    <ul>{% for mid in allowed %}<li>{{ mid }}</li>{% endfor %}</ul>
    """
    return render_template_string(html, pending=pending, allowed=allowed)

@app.route("/")
def home():
    return "<h3>📦 XLSM License Server Running</h3>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
