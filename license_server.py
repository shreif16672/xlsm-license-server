from flask import Flask, request, jsonify, send_file, render_template_string
import os
import json
import io

app = Flask(__name__)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED_IDS_FILE = os.path.join(DATA_DIR, "allowed_ids_xlsm_tool.json")
PENDING_IDS_FILE = os.path.join(DATA_DIR, "pending_ids_xlsm_tool.json")
TEMPLATE_FILE = os.path.join(DATA_DIR, "template.xlsm")
INSTALLER_FILE = os.path.join(DATA_DIR, "installer_lifetime.exe")
LAUNCHER_FILE = os.path.join(DATA_DIR, "Launcher.xlsm")

def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    machine_id = data.get("machine_id")

    if not machine_id:
        return jsonify({"valid": False, "reason": "No machine_id"}), 400

    allowed_ids = load_json(ALLOWED_IDS_FILE)
    if machine_id not in allowed_ids:
        # Add to pending
        pending_ids = load_json(PENDING_IDS_FILE)
        if machine_id not in pending_ids:
            pending_ids[machine_id] = "pending"
            save_json(PENDING_IDS_FILE, pending_ids)
        return jsonify({"valid": False, "reason": "Not allowed"}), 403

    # Generate dynamic xlsm file
    new_filename = f"QTY_Network_2025_{machine_id}.xlsm"
    with open(TEMPLATE_FILE, "rb") as f:
        template_data = f.read()
    new_xlsm = io.BytesIO(template_data)
    new_xlsm.seek(0)

    return jsonify({
        "valid": True,
        "filename": new_filename,
        "xlsm_data": list(new_xlsm.read()),
    })

@app.route("/download/<filename>")
def download_file(filename):
    if filename.endswith(".exe"):
        return send_file(INSTALLER_FILE, as_attachment=True)
    elif filename.endswith(".xlsm") and filename.startswith("QTY_Network_2025_"):
        return send_file(TEMPLATE_FILE, as_attachment=True)
    elif filename == "Launcher.xlsm":
        return send_file(LAUNCHER_FILE, as_attachment=True)
    return "File not found", 404

@app.route("/admin")
def admin():
    allowed_ids = load_json(ALLOWED_IDS_FILE)
    pending_ids = load_json(PENDING_IDS_FILE)

    html = """
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending</h2>
    {% for mid in pending %}
        <li>
            {{ mid }}
            <form method="post" action="/approve" style="display:inline">
                <input type="hidden" name="machine_id" value="{{ mid }}">
                <button type="submit">✅ Approve</button>
            </form>
            <form method="post" action="/reject" style="display:inline">
                <input type="hidden" name="machine_id" value="{{ mid }}">
                <button type="submit">❌ Reject</button>
            </form>
        </li>
    {% else %}
        <p>No pending requests.</p>
    {% endfor %}
    <h2>Approved</h2>
    {% for mid in allowed %}
        <li>{{ mid }}</li>
    {% else %}
        <p>No approved machines.</p>
    {% endfor %}
    """
    return render_template_string(html, pending=pending_ids.keys(), allowed=allowed_ids.keys())

@app.route("/approve", methods=["POST"])
def approve():
    machine_id = request.form.get("machine_id")
    if machine_id:
        allowed_ids = load_json(ALLOWED_IDS_FILE)
        allowed_ids[machine_id] = "approved"
        save_json(ALLOWED_IDS_FILE, allowed_ids)

        pending_ids = load_json(PENDING_IDS_FILE)
        if machine_id in pending_ids:
            del pending_ids[machine_id]
            save_json(PENDING_IDS_FILE, pending_ids)
    return "<script>window.location.href = '/admin';</script>"

@app.route("/reject", methods=["POST"])
def reject():
    machine_id = request.form.get("machine_id")
    if machine_id:
        pending_ids = load_json(PENDING_IDS_FILE)
        if machine_id in pending_ids:
            del pending_ids[machine_id]
            save_json(PENDING_IDS_FILE, pending_ids)
    return "<script>window.location.href = '/admin';</script>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
