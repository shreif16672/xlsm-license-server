from flask import Flask, request, jsonify, send_file, render_template_string
import os
import json

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LICENSE_FOLDER = os.path.join(BASE_DIR, "licenses")
FILES_FOLDER = BASE_DIR  # All files must be stored here
os.makedirs(LICENSE_FOLDER, exist_ok=True)

pending_file = os.path.join(BASE_DIR, f"pending_ids_{PROGRAM_ID}.json")
approved_file = os.path.join(BASE_DIR, f"allowed_ids_{PROGRAM_ID}.json")
rejected_file = os.path.join(BASE_DIR, f"rejected_ids_{PROGRAM_ID}.json")

def load_ids(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []

def save_ids(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.json
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    if program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Invalid program ID"}), 403

    approved = load_ids(approved_file)
    rejected = load_ids(rejected_file)
    pending = load_ids(pending_file)

    if machine_id in rejected:
        return jsonify({"valid": False, "reason": "Rejected"}), 403

    if machine_id in approved:
        license_data = {
            "machine_id": machine_id,
            "program_id": program_id,
            "status": "approved"
        }
        license_path = os.path.join(LICENSE_FOLDER, f"license_{machine_id}.txt")
        with open(license_path, "w") as f:
            json.dump(license_data, f)
        return jsonify({
            "valid": True,
            "license": license_data,
            "files": [
                f"Launcher.xlsm",
                f"QTY_Network_2025_{machine_id}.xlsm",
                "installer_lifetime.exe"
            ]
        })

    if machine_id not in pending:
        pending.append(machine_id)
        save_ids(pending_file, pending)

    return jsonify({"valid": False, "reason": "Pending approval"}), 403

@app.route("/download/<filename>")
def download_file(filename):
    filepath = os.path.join(FILES_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return f"File {filename} not found", 404

@app.route("/admin")
def admin_panel():
    pending = load_ids(pending_file)
    approved = load_ids(approved_file)
    rejected = load_ids(rejected_file)

    html = """
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending Machine IDs</h2>
    <ul>
    {% for mid in pending %}
        <li>{{ mid }}
            <form action="/approve" method="post" style="display:inline">
                <input type="hidden" name="machine_id" value="{{ mid }}">
                <button type="submit">Approve</button>
            </form>
            <form action="/reject" method="post" style="display:inline">
                <input type="hidden" name="machine_id" value="{{ mid }}">
                <button type="submit">Reject</button>
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

@app.route("/approve", methods=["POST"])
def approve():
    machine_id = request.form["machine_id"]
    pending = load_ids(pending_file)
    approved = load_ids(approved_file)
    if machine_id in pending:
        pending.remove(machine_id)
        save_ids(pending_file, pending)
    if machine_id not in approved:
        approved.append(machine_id)
        save_ids(approved_file, approved)
    return "Approved", 200

@app.route("/reject", methods=["POST"])
def reject():
    machine_id = request.form["machine_id"]
    pending = load_ids(pending_file)
    rejected = load_ids(rejected_file)
    if machine_id in pending:
        pending.remove(machine_id)
        save_ids(pending_file, pending)
    if machine_id not in rejected:
        rejected.append(machine_id)
        save_ids(rejected_file, rejected)
    return "Rejected", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
