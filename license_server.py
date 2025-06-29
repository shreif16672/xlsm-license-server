from flask import Flask, request, jsonify, render_template_string, send_from_directory
import os
import json

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(DATA_DIR, "static")

# File paths
PENDING_FILE = os.path.join(DATA_DIR, f"pending_ids_{PROGRAM_ID}.json")
ALLOWED_FILE = os.path.join(DATA_DIR, f"allowed_ids_{PROGRAM_ID}.json")
REJECTED_FILE = os.path.join(DATA_DIR, f"rejected_ids_{PROGRAM_ID}.json")

# Ensure data files exist
for file_path in [PENDING_FILE, ALLOWED_FILE, REJECTED_FILE]:
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump([], f)

def load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    if program_id != PROGRAM_ID:
        return jsonify({"valid": False, "reason": "Invalid program_id"}), 403

    allowed_ids = load_json(ALLOWED_FILE)
    if machine_id in allowed_ids:
        license_data = {
            "program": program_id,
            "machine_id": machine_id,
            "license": "Licensed XLSM Tool — Lifetime Access"
        }
        return jsonify({
            "valid": True,
            "license": license_data,
            "files": [
                "Launcher.xlsm",
                "installer_lifetime.exe",
                f"QTY_Network_2025_{machine_id}.xlsm"
            ]
        })

    # Add to pending if not already there
    pending_ids = load_json(PENDING_FILE)
    if machine_id not in pending_ids:
        pending_ids.append(machine_id)
        save_json(PENDING_FILE, pending_ids)

    return jsonify({
        "valid": False,
        "reason": "Request not allowed",
        "status": "pending"
    }), 403

@app.route("/static/<filename>")
def download_file(filename):
    return send_from_directory(STATIC_DIR, filename, as_attachment=True)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    pending_ids = load_json(PENDING_FILE)
    approved_ids = load_json(ALLOWED_FILE)
    rejected_ids = load_json(REJECTED_FILE)

    if request.method == "POST":
        action = request.form.get("action")
        machine_id = request.form.get("machine_id")

        if action == "approve":
            if machine_id not in approved_ids:
                approved_ids.append(machine_id)
            if machine_id in pending_ids:
                pending_ids.remove(machine_id)
        elif action == "reject":
            if machine_id not in rejected_ids:
                rejected_ids.append(machine_id)
            if machine_id in pending_ids:
                pending_ids.remove(machine_id)

        save_json(PENDING_FILE, pending_ids)
        save_json(ALLOWED_FILE, approved_ids)
        save_json(REJECTED_FILE, rejected_ids)

    # Render HTML admin page
    html = """
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending Machine IDs</h2>
    <ul>
      {% for mid in pending %}
        <li>{{ mid }}
          <form method="post" style="display:inline;">
            <input type="hidden" name="machine_id" value="{{ mid }}">
            <button type="submit" name="action" value="approve">Approve</button>
            <button type="submit" name="action" value="reject">Reject</button>
          </form>
        </li>
      {% endfor %}
    </ul>

    <h2>Approved Machine IDs</h2>
    <ul>{% for mid in approved %}<li>{{ mid }}</li>{% endfor %}</ul>

    <h2>Rejected Machine IDs</h2>
    <ul>{% for mid in rejected %}<li>{{ mid }}</li>{% endfor %}</ul>
    """

    return render_template_string(html, pending=pending_ids, approved=approved_ids, rejected=rejected_ids)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
