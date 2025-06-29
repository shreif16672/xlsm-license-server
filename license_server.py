from flask import Flask, request, send_file, jsonify, render_template_string
import os
import json
import shutil

app = Flask(__name__)

# Configuration
PROGRAM_ID = "xlsm_tool"
TEMPLATE_FILENAME = "template.xlsm"

# JSON file paths
ALLOWED_IDS_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_IDS_FILE = f"pending_ids_{PROGRAM_ID}.json"
REJECTED_IDS_FILE = f"rejected_ids_{PROGRAM_ID}.json"

# Web admin HTML
ADMIN_TEMPLATE = """
<h1>XLSM Tool License Admin</h1>
<h2>Pending Machine IDs</h2>
<ul>
{% for mid in pending %}
  <li>{{ mid }}
    <form method="post" action="/admin/approve" style="display:inline;">
      <input type="hidden" name="machine_id" value="{{ mid }}">
      <button type="submit">Approve</button>
    </form>
    <form method="post" action="/admin/reject" style="display:inline;">
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

# Utilities
def load_json(file):
    if not os.path.exists(file):
        return []
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def ensure_file(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump([], f)

# API
@app.route("/generate", methods=["POST"])
def generate_license():
    machine_id = request.json.get("machine_id")
    program_id = request.json.get("program_id")
    if program_id != PROGRAM_ID or not machine_id:
        return jsonify({"valid": False, "reason": "Invalid program or ID"}), 403

    allowed = load_json(ALLOWED_IDS_FILE)
    pending = load_json(PENDING_IDS_FILE)
    rejected = load_json(REJECTED_IDS_FILE)

    if machine_id in rejected:
        return jsonify({"valid": False, "reason": "Rejected"}), 403

    if machine_id not in allowed:
        if machine_id not in pending:
            pending.append(machine_id)
            save_json(PENDING_IDS_FILE, pending)
        return jsonify({"valid": False, "reason": "Not approved yet"}), 403

    # License content
    license_content = {
        "machine_id": machine_id,
        "program_id": program_id
    }
    with open("license.txt", "w") as f:
        f.write(json.dumps(license_content))

    return send_file("license.txt", as_attachment=True)

@app.route("/download/<filename>")
def download_file(filename):
    if filename.lower() == "launcher.xlsm" and os.path.exists("Launcher.xlsm"):
        return send_file("Launcher.xlsm", as_attachment=True)

    if filename.lower() == "installer_lifetime.exe" and os.path.exists("installer_lifetime.exe"):
        return send_file("installer_lifetime.exe", as_attachment=True)

    if filename.startswith("QTY_Network_2025_") and filename.endswith(".xlsm"):
        if not os.path.exists(filename):
            if not os.path.exists(TEMPLATE_FILENAME):
                return "Template not found", 404
            shutil.copyfile(TEMPLATE_FILENAME, filename)
        return send_file(filename, as_attachment=True)

    return "File not found", 404

@app.route("/admin", methods=["GET"])
def admin():
    ensure_file(PENDING_IDS_FILE)
    ensure_file(ALLOWED_IDS_FILE)
    ensure_file(REJECTED_IDS_FILE)

    return render_template_string(
        ADMIN_TEMPLATE,
        pending=load_json(PENDING_IDS_FILE),
        approved=load_json(ALLOWED_IDS_FILE),
        rejected=load_json(REJECTED_IDS_FILE)
    )

@app.route("/admin/approve", methods=["POST"])
def approve():
    mid = request.form["machine_id"]
    allowed = load_json(ALLOWED_IDS_FILE)
    pending = load_json(PENDING_IDS_FILE)

    if mid not in allowed:
        allowed.append(mid)
    if mid in pending:
        pending.remove(mid)

    save_json(ALLOWED_IDS_FILE, allowed)
    save_json(PENDING_IDS_FILE, pending)
    return admin()

@app.route("/admin/reject", methods=["POST"])
def reject():
    mid = request.form["machine_id"]
    rejected = load_json(REJECTED_IDS_FILE)
    pending = load_json(PENDING_IDS_FILE)

    if mid not in rejected:
        rejected.append(mid)
    if mid in pending:
        pending.remove(mid)

    save_json(REJECTED_IDS_FILE, rejected)
    save_json(PENDING_IDS_FILE, pending)
    return admin()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
