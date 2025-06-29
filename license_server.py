from flask import Flask, request, send_file, jsonify, render_template_string
import os
import json
import shutil

app = Flask(__name__)

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED_FILE = os.path.join(BASE_DIR, "allowed_ids_xlsm_tool.json")
PENDING_FILE = os.path.join(BASE_DIR, "pending_ids_xlsm_tool.json")
REJECTED_FILE = os.path.join(BASE_DIR, "rejected_ids_xlsm_tool.json")
LICENSE_TEMPLATE = os.path.join(BASE_DIR, "license.txt")
TEMPLATE_XLSM = os.path.join(BASE_DIR, "template.xlsm")

# Ensure files exist
for path in [ALLOWED_FILE, PENDING_FILE, REJECTED_FILE]:
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump([], f)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if program_id != "xlsm_tool":
        return jsonify({"valid": False, "reason": "Invalid program"}), 403

    # Load lists
    with open(ALLOWED_FILE) as f:
        allowed_ids = json.load(f)
    with open(REJECTED_FILE) as f:
        rejected_ids = json.load(f)
    with open(PENDING_FILE) as f:
        pending_ids = json.load(f)

    if machine_id in allowed_ids:
        return send_file(LICENSE_TEMPLATE)
    elif machine_id in rejected_ids:
        return jsonify({"valid": False, "reason": "Rejected"}), 403
    elif machine_id not in pending_ids:
        pending_ids.append(machine_id)
        with open(PENDING_FILE, "w") as f:
            json.dump(pending_ids, f)
    return jsonify({"valid": False, "reason": "Not approved yet"}), 403

@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(BASE_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        return "File not found", 404

@app.route("/admin")
def admin_page():
    with open(PENDING_FILE) as f:
        pending_ids = json.load(f)
    with open(ALLOWED_FILE) as f:
        approved_ids = json.load(f)
    with open(REJECTED_FILE) as f:
        rejected_ids = json.load(f)

    html = """
    <h1>XLSM Tool License Admin</h1>

    <h2>Pending Machine IDs</h2>
    {% for mid in pending %}
        <li>{{ mid }} 
        <a href="/approve/{{ mid }}">✅ Approve</a> 
        <a href="/reject/{{ mid }}">❌ Reject</a></li>
    {% endfor %}

    <h2>Approved Machine IDs</h2>
    {% for mid in approved %}
        <li>{{ mid }}</li>
    {% endfor %}

    <h2>Rejected Machine IDs</h2>
    {% for mid in rejected %}
        <li>{{ mid }}</li>
    {% endfor %}
    """
    return render_template_string(html, pending=pending_ids, approved=approved_ids, rejected=rejected_ids)

@app.route("/approve/<machine_id>")
def approve(machine_id):
    with open(PENDING_FILE) as f:
        pending_ids = json.load(f)
    with open(ALLOWED_FILE) as f:
        allowed_ids = json.load(f)

    if machine_id in pending_ids:
        pending_ids.remove(machine_id)
        if machine_id not in allowed_ids:
            allowed_ids.append(machine_id)

        with open(PENDING_FILE, "w") as f:
            json.dump(pending_ids, f)
        with open(ALLOWED_FILE, "w") as f:
            json.dump(allowed_ids, f)

        # Copy template to custom XLSM
        output_path = os.path.join(BASE_DIR, f"QTY_Network_2025_{machine_id}.xlsm")
        if os.path.exists(TEMPLATE_XLSM):
            shutil.copyfile(TEMPLATE_XLSM, output_path)

    return "✅ Approved."

@app.route("/reject/<machine_id>")
def reject(machine_id):
    with open(PENDING_FILE) as f:
        pending_ids = json.load(f)
    with open(REJECTED_FILE) as f:
        rejected_ids = json.load(f)

    if machine_id in pending_ids:
        pending_ids.remove(machine_id)
        if machine_id not in rejected_ids:
            rejected_ids.append(machine_id)

        with open(PENDING_FILE, "w") as f:
            json.dump(pending_ids, f)
        with open(REJECTED_FILE, "w") as f:
            json.dump(rejected_ids, f)

    return "❌ Rejected."

if __name__ == "__main__":
    app.run(debug=True, port=10000)
