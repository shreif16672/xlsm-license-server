import os
import json
import shutil
import time
from flask import Flask, request, jsonify, send_file, render_template_string

app = Flask(__name__)

# Constants
PROGRAM_ID = "xlsm_tool"
ALLOWED_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_FILE = f"pending_ids_{PROGRAM_ID}.json"
REJECTED_FILE = f"rejected_ids_{PROGRAM_ID}.json"
TEMPLATE_FILE = "template.xlsm"
OUTPUT_PREFIX = "QTY_Network_2025_"
LICENSE_DIR = "."

# -------------------------------
# License Data Generator
# -------------------------------
def generate_password(machine_id):
    seed = 12345
    for char in machine_id:
        seed += ord(char)
    return f"PWD{seed}"

def ensure_json(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump([], f)

# -------------------------------
# License API Endpoint
# -------------------------------
@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    if program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Invalid program ID"}), 403

    ensure_json(ALLOWED_FILE)
    ensure_json(PENDING_FILE)
    ensure_json(REJECTED_FILE)

    with open(REJECTED_FILE) as f:
        rejected_ids = json.load(f)
    if machine_id in rejected_ids:
        return jsonify({"valid": False, "reason": "License rejected"}), 403

    with open(ALLOWED_FILE) as f:
        allowed_ids = json.load(f)
    if machine_id in allowed_ids:
        license_path = os.path.join(LICENSE_DIR, "license.txt")
        password = generate_password(machine_id)
        with open(license_path, "w") as f:
            f.write(f"{machine_id}\n{password}")

        # Create XLSM if not exists
        output_filename = f"{OUTPUT_PREFIX}{machine_id}.xlsm"
        if not os.path.exists(output_filename):
            shutil.copyfile(TEMPLATE_FILE, output_filename)

        # Wait until file is created (confirm it's accessible)
        for _ in range(10):
            if os.path.exists(output_filename):
                break
            time.sleep(0.5)

        return jsonify({
            "valid": True,
            "machine_id": machine_id,
            "filename": output_filename
        })

    # Add to pending if not already
    with open(PENDING_FILE) as f:
        pending_ids = json.load(f)
    if machine_id not in pending_ids:
        pending_ids.append(machine_id)
        with open(PENDING_FILE, 'w') as f:
            json.dump(pending_ids, f, indent=2)

    return jsonify({"valid": False, "reason": "Pending approval"}), 403

# -------------------------------
# Admin Panel
# -------------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    ensure_json(ALLOWED_FILE)
    ensure_json(PENDING_FILE)
    ensure_json(REJECTED_FILE)

    if request.method == "POST":
        action = request.form.get("action")
        machine_id = request.form.get("machine_id")

        for file in [ALLOWED_FILE, PENDING_FILE, REJECTED_FILE]:
            with open(file) as f:
                ids = json.load(f)
            if machine_id in ids:
                ids.remove(machine_id)
                with open(file, "w") as f:
                    json.dump(ids, f, indent=2)

        target_file = {
            "approve": ALLOWED_FILE,
            "reject": REJECTED_FILE
        }.get(action)

        if target_file:
            with open(target_file) as f:
                ids = json.load(f)
            if machine_id not in ids:
                ids.append(machine_id)
                with open(target_file, "w") as f:
                    json.dump(ids, f, indent=2)

    with open(PENDING_FILE) as f:
        pending = json.load(f)
    with open(ALLOWED_FILE) as f:
        approved = json.load(f)
    with open(REJECTED_FILE) as f:
        rejected = json.load(f)

    html = """
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending Machine IDs</h2>
    <ul>
    {% for mid in pending %}
        <li>{{ mid }}
            <form method="post" style="display:inline">
                <input type="hidden" name="machine_id" value="{{ mid }}">
                <button type="submit" name="action" value="approve">✅ Approve</button>
                <button type="submit" name="action" value="reject">❌ Reject</button>
            </form>
        </li>
    {% endfor %}
    </ul>

    <h2>Approved Machine IDs</h2>
    <ul>{% for mid in approved %}<li>{{ mid }}</li>{% endfor %}</ul>

    <h2>Rejected Machine IDs</h2>
    <ul>{% for mid in rejected %}<li>{{ mid }}</li>{% endfor %}</ul>
    """

    return render_template_string(html, pending=pending, approved=approved, rejected=rejected)

# -------------------------------
# Start Server
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
