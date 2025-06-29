from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import json
import shutil
import time

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LICENSE_DIR = os.path.join(BASE_DIR, "licenses")

if not os.path.exists(LICENSE_DIR):
    os.makedirs(LICENSE_DIR)

# Storage files
PENDING_FILE = os.path.join(BASE_DIR, "pending_ids_xlsm_tool.json")
ALLOWED_FILE = os.path.join(BASE_DIR, "allowed_ids_xlsm_tool.json")
REJECTED_FILE = os.path.join(BASE_DIR, "rejected_ids_xlsm_tool.json")

# Load or initialize JSON files
for file in [PENDING_FILE, ALLOWED_FILE, REJECTED_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

def load_ids(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def save_ids(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

def generate_password(machine_id):
    seed = 12345
    for char in machine_id:
        seed += ord(char)
    return f"PWD{seed}"

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    machine_id = data.get("machine_id")

    if not machine_id:
        return jsonify({"error": "Missing machine_id"}), 403

    allowed_ids = load_ids(ALLOWED_FILE)
    rejected_ids = load_ids(REJECTED_FILE)
    pending_ids = load_ids(PENDING_FILE)

    if machine_id in rejected_ids:
        return jsonify({"error": "Rejected"}), 403

    if machine_id not in allowed_ids:
        if machine_id not in pending_ids:
            pending_ids.append(machine_id)
            save_ids(PENDING_FILE, pending_ids)
        return jsonify({"message": "Pending approval"}), 403

    # Approved: generate license file
    password = generate_password(machine_id)
    license_path = os.path.join(LICENSE_DIR, f"{machine_id}.txt")
    with open(license_path, "w") as f:
        f.write(f"{machine_id}\n{password}")

    # Copy XLSM file
    target_filename = f"QTY_Network_2025_{machine_id}.xlsm"
    target_path = os.path.join(BASE_DIR, target_filename)
    if not os.path.exists(target_path):
        shutil.copyfile("template.xlsm", target_path)

    # Wait for file to be ready
    for _ in range(20):
        if os.path.exists(target_path):
            break
        time.sleep(0.2)

    if not os.path.exists(target_path):
        return jsonify({"error": "Failed to prepare .xlsm"}), 500

    return jsonify({
        "license_file": f"{machine_id}.txt",
        "launcher": "Launcher.xlsm",
        "installer": "installer_lifetime.exe",
        "xlsm_file": target_filename
    })

@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(BASE_DIR, filename, as_attachment=True)

@app.route("/admin")
def admin():
    pending = load_ids(PENDING_FILE)
    allowed = load_ids(ALLOWED_FILE)
    rejected = load_ids(REJECTED_FILE)

    html = """
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending Machine IDs</h2>
    <ul>
    {% for mid in pending %}
        <li>{{ mid }} ✅ <a href="/approve/{{ mid }}">Approve</a> ❌ <a href="/reject/{{ mid }}">Reject</a></li>
    {% endfor %}
    </ul>

    <h2>Approved Machine IDs</h2>
    <ul>
    {% for mid in allowed %}
        <li>{{ mid }}</li>
    {% endfor %}
    </ul>

    <h2>Rejected Machine IDs</h2>
    <ul>
    {% for mid in rejected %}
        <li>{{ mid }}</li>
    {% endfor %}
    </ul>
    """
    return render_template_string(html, pending=pending, allowed=allowed, rejected=rejected)

@app.route("/approve/<machine_id>")
def approve(machine_id):
    pending = load_ids(PENDING_FILE)
    allowed = load_ids(ALLOWED_FILE)
    rejected = load_ids(REJECTED_FILE)

    if machine_id in pending:
        pending.remove(machine_id)
    if machine_id not in allowed:
        allowed.append(machine_id)
    if machine_id in rejected:
        rejected.remove(machine_id)

    save_ids(PENDING_FILE, pending)
    save_ids(ALLOWED_FILE, allowed)
    save_ids(REJECTED_FILE, rejected)
    return "✅ Approved. <a href='/admin'>Back</a>"

@app.route("/reject/<machine_id>")
def reject(machine_id):
    pending = load_ids(PENDING_FILE)
    allowed = load_ids(ALLOWED_FILE)
    rejected = load_ids(REJECTED_FILE)

    if machine_id in pending:
        pending.remove(machine_id)
    if machine_id in allowed:
        allowed.remove(machine_id)
    if machine_id not in rejected:
        rejected.append(machine_id)

    save_ids(PENDING_FILE, pending)
    save_ids(ALLOWED_FILE, allowed)
    save_ids(REJECTED_FILE, rejected)
    return "❌ Rejected. <a href='/admin'>Back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
