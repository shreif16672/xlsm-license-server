from flask import Flask, request, jsonify, render_template_string, send_from_directory
import json
import os

app = Flask(__name__)
program_id = "xlsm_tool"

PENDING_FILE = f"pending_ids_{program_id}.json"
APPROVED_FILE = f"allowed_ids_{program_id}.json"
LICENSE_FOLDER = "."

LICENSE_TEXT = "Licensed XLSM Tool — Lifetime Access"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program = data.get("program_id")

    if not machine_id or not program:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 403

    if program != program_id:
        return jsonify({"valid": False, "reason": "Invalid program_id"}), 403

    approved_ids = load_json(APPROVED_FILE)
    pending_ids = load_json(PENDING_FILE)

    if machine_id in approved_ids:
        license_path = os.path.join(LICENSE_FOLDER, "license.txt")
        return send_from_directory(LICENSE_FOLDER, "license.txt", as_attachment=True)
    elif machine_id not in pending_ids:
        pending_ids.append(machine_id)
        save_json(PENDING_FILE, pending_ids)
        return jsonify({"valid": False, "reason": "Not allowed"}), 403
    else:
        return jsonify({"valid": False, "reason": "Not allowed"}), 403

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if request.method == "POST":
        machine_id = request.form.get("machine_id")
        action = request.form.get("action")

        approved = load_json(APPROVED_FILE)
        pending = load_json(PENDING_FILE)

        if action == "approve" and machine_id in pending:
            pending.remove(machine_id)
            if machine_id not in approved:
                approved.append(machine_id)
            save_json(PENDING_FILE, pending)
            save_json(APPROVED_FILE, approved)

        elif action == "reject" and machine_id in pending:
            pending.remove(machine_id)
            save_json(PENDING_FILE, pending)

    pending_ids = load_json(PENDING_FILE)
    approved_ids = load_json(APPROVED_FILE)

    return render_template_string("""
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending Machine IDs</h2>
    <ul>
    {% for mid in pending %}
        <li>{{ mid }}
            <form method="post" style="display:inline">
                <input type="hidden" name="machine_id" value="{{ mid }}">
                <button name="action" value="approve">Approve</button>
                <button name="action" value="reject">Reject</button>
            </form>
        </li>
    {% endfor %}
    </ul>
    <h2>Approved Machine IDs</h2>
    <ul>
    {% for mid in approved %}
        <li>{{ mid }}</li>
    {% endfor %}
    </ul>
    """, pending=pending_ids, approved=approved_ids)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
