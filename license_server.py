from flask import Flask, request, jsonify, render_template_string, send_file
import os
import json
import shutil
import zipfile

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
PENDING_FILE = "pending_ids_xlsm_tool.json"
ALLOWED_FILE = "allowed_ids_xlsm_tool.json"
TEMPLATE_FILE = "template.xlsm"
LAUNCHER_FILE = "Launcher.xlsm"
INSTALLER_FILE = "installer_lifetime.exe"

def read_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def write_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")
    duration = data.get("duration", "lifetime")

    if program_id != PROGRAM_ID:
        return jsonify({"error": "Invalid program ID"}), 400

    allowed = read_json(ALLOWED_FILE)
    pending = read_json(PENDING_FILE)

    # ✅ Approved — generate ZIP
    if machine_id in allowed:
        xlsm_name = f"QTY_Network_2025_{machine_id}.xlsm"
        if not os.path.exists(xlsm_name):
            shutil.copy(TEMPLATE_FILE, xlsm_name)

        zip_name = f"license_package_{machine_id}.zip"
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            zipf.write(xlsm_name)
            zipf.write(LAUNCHER_FILE)
            zipf.write(INSTALLER_FILE)

        return send_file(zip_name, as_attachment=True)

    # ❌ Not approved — add to pending
    if machine_id not in pending:
        pending[machine_id] = {
            "program_id": program_id,
            "duration": duration
        }
        write_json(PENDING_FILE, pending)

    return jsonify({"status": "pending", "message": "Request submitted and waiting for approval."}), 202

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        action = request.form.get("action")
        machine_id = request.form.get("machine_id")

        pending = read_json(PENDING_FILE)
        allowed = read_json(ALLOWED_FILE)

        if action == "approve" and machine_id in pending:
            allowed[machine_id] = pending.pop(machine_id)
            write_json(ALLOWED_FILE, allowed)
            write_json(PENDING_FILE, pending)
        elif action == "reject" and machine_id in pending:
            pending.pop(machine_id)
            write_json(PENDING_FILE, pending)

    pending = read_json(PENDING_FILE)
    allowed = read_json(ALLOWED_FILE)

    html = """
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending</h2>
    {% if pending %}
        <ul>
        {% for machine_id in pending %}
            <li>
                <strong>{{ machine_id }}</strong>
                <form method="post" style="display:inline;">
                    <input type="hidden" name="machine_id" value="{{ machine_id }}">
                    <button type="submit" name="action" value="approve">✅ Approve</button>
                    <button type="submit" name="action" value="reject">❌ Reject</button>
                </form>
            </li>
        {% endfor %}
        </ul>
    {% else %}
        <p>No pending requests.</p>
    {% endif %}

    <h2>Approved</h2>
    {% if approved %}
        <ul>
        {% for machine_id in approved %}
            <li>{{ machine_id }}</li>
        {% endfor %}
        </ul>
    {% else %}
        <p>No approved machines.</p>
    {% endif %}
    """
    return render_template_string(html, pending=pending, approved=allowed)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
