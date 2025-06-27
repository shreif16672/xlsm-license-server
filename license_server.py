from flask import Flask, request, jsonify, render_template_string, send_file
import os
import j
import shutil
from io import BytesIO
import zipfile

app = Flask(__name__)

# === Configuration ===
PROGRAM_ID = "xlsm_tool"
PENDING_FILE = "pending_ids_xlsm_tool.json"
ALLOWED_FILE = "allowed_ids_xlsm_tool.json"
TEMPLATE_FILE = "template.xlsm"
LAUNCHER_FILE = "Launcher.xlsm"
INSTALLER_FILE = "installer_lifetime.exe"

# === JSON File Handling ===
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

# === License Generator ===
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

    # === Approved: Send ZIP in memory ===
    if machine_id in allowed:
        xlsm_name = f"QTY_Network_2025_{machine_id}.xlsm"
        shutil.copy(TEMPLATE_FILE, xlsm_name)

        mem_zip = BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(xlsm_name, arcname=os.path.basename(xlsm_name))
            zf.write(LAUNCHER_FILE, arcname=os.path.basename(LAUNCHER_FILE))
            zf.write(INSTALLER_FILE, arcname=os.path.basename(INSTALLER_FILE))

        os.remove(xlsm_name)

        mem_zip.seek(0)
        return send_file(mem_zip, mimetype="application/zip",
                         download_name=f"license_package_{machine_id}.zip",
                         as_attachment=True)

    # === New Request: Add to pending list ===
    if machine_id not in pending:
        pending[machine_id] = {
            "program_id": program_id,
            "duration": duration
        }
        write_json(PENDING_FILE, pending)

    return jsonify({"status": "pending", "message": "Request submitted and waiting for approval."}), 202

# === Admin Panel ===
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

# === Entry Point ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
