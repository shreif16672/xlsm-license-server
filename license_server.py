from flask import Flask, request, jsonify, render_template_string
import json
import os

app = Flask(__name__)

# Files
ALLOWED_FILE = "allowed_ids_xlsm_tool.json"
PENDING_FILE = "pending_ids_xlsm_tool.json"

# Serve the admin panel
@app.route("/admin")
def admin():
    with open(PENDING_FILE, "r") as f:
        pending = json.load(f)
    with open(ALLOWED_FILE, "r") as f:
        allowed = json.load(f)

    html = """
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending Requests</h2>
    {% for item in pending %}
        <li>{{ item }} 
            <form action="/approve" method="post" style="display:inline;">
                <input type="hidden" name="machine_id" value="{{ item }}">
                <button type="submit">✅ Approve</button>
            </form>
            <form action="/reject" method="post" style="display:inline;">
                <input type="hidden" name="machine_id" value="{{ item }}">
                <button type="submit">❌ Reject</button>
            </form>
        </li>
    {% else %}
        <p>No pending requests.</p>
    {% endfor %}
    <h2>Approved Machine IDs</h2>
    {% for item in allowed %}
        <li>{{ item }}</li>
    {% endfor %}
    """
    return render_template_string(html, pending=pending, allowed=allowed)

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.json
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    if program_id != "xlsm_tool":
        return jsonify({"valid": False, "reason": "Invalid program_id"}), 403

    with open(ALLOWED_FILE, "r") as f:
        allowed_ids = json.load(f)

    if machine_id in allowed_ids:
        license_data = {
            "machine_id": machine_id,
            "program_id": program_id,
            "license": "VALID"
        }
        return jsonify({"valid": True, "license": license_data})
    else:
        with open(PENDING_FILE, "r") as f:
            pending_ids = json.load(f)
        if machine_id not in pending_ids:
            pending_ids.append(machine_id)
            with open(PENDING_FILE, "w") as f:
                json.dump(pending_ids, f, indent=4)
        return jsonify({"valid": False, "reason": "Not approved"}), 403

@app.route("/approve", methods=["POST"])
def approve():
    machine_id = request.form.get("machine_id")

    with open(ALLOWED_FILE, "r") as f:
        allowed_ids = json.load(f)
    with open(PENDING_FILE, "r") as f:
        pending_ids = json.load(f)

    if machine_id and machine_id not in allowed_ids:
        allowed_ids.append(machine_id)
        with open(ALLOWED_FILE, "w") as f:
            json.dump(allowed_ids, f, indent=4)
    if machine_id in pending_ids:
        pending_ids.remove(machine_id)
        with open(PENDING_FILE, "w") as f:
            json.dump(pending_ids, f, indent=4)

    return "Approved."

@app.route("/reject", methods=["POST"])
def reject():
    machine_id = request.form.get("machine_id")
    with open(PENDING_FILE, "r") as f:
        pending_ids = json.load(f)
    if machine_id in pending_ids:
        pending_ids.remove(machine_id)
        with open(PENDING_FILE, "w") as f:
            json.dump(pending_ids, f, indent=4)
    return "Rejected."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
