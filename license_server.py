from flask import Flask, request, jsonify, render_template_string
import json
import os

app = Flask(__name__)

DATA_FILE = "allowed_ids_xlsm_tool.json"
PENDING_FILE = "pending_ids_xlsm_tool.json"
REJECTED_FILE = "rejected_ids_xlsm_tool.json"

FILES_TO_SEND = [
    "Launcher.xlsm",
    "installer_lifetime.exe"
]

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    # Load allowed and rejected lists
    allowed = load_json(DATA_FILE)
    rejected = load_json(REJECTED_FILE)

    if machine_id in rejected:
        return jsonify({"valid": False, "reason": "Rejected"}), 403

    if machine_id in allowed:
        license_data = {"machine_id": machine_id, "program_id": program_id}
        files = FILES_TO_SEND + [f"QTY_Network_2025_{machine_id}.xlsm"]
        return jsonify({"valid": True, "license": license_data, "files": files})
    else:
        # Add to pending if not already there
        pending = load_json(PENDING_FILE)
        if machine_id not in pending:
            pending.append(machine_id)
            save_json(PENDING_FILE, pending)
        return jsonify({"valid": False, "reason": "Pending approval"}), 403

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    pending = load_json(PENDING_FILE)
    allowed = load_json(DATA_FILE)
    rejected = load_json(REJECTED_FILE)

    if request.method == "POST":
        action = request.form.get("action")
        machine_id = request.form.get("machine_id")

        if action == "approve":
            if machine_id not in allowed:
                allowed.append(machine_id)
                save_json(DATA_FILE, allowed)
            pending = [id for id in pending if id != machine_id]
            save_json(PENDING_FILE, pending)
        elif action == "reject":
            if machine_id not in rejected:
                rejected.append(machine_id)
                save_json(REJECTED_FILE, rejected)
            pending = [id for id in pending if id != machine_id]
            save_json(PENDING_FILE, pending)

    return render_template_string("""
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending Machine IDs</h2>
    <ul>
    {% for mid in pending %}
        <li>{{ mid }}
            <form method="post" style="display:inline">
                <input type="hidden" name="machine_id" value="{{ mid }}">
                <button type="submit" name="action" value="approve">Approve</button>
                <button type="submit" name="action" value="reject">Reject</button>
            </form>
        </li>
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
    """, pending=pending, allowed=allowed, rejected=rejected)

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
