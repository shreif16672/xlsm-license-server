from flask import Flask, request, jsonify, render_template_string, send_from_directory
import json
import os

app = Flask(__name__)

DATA_FOLDER = os.path.dirname(os.path.abspath(__file__))
ALLOWED_FILE = os.path.join(DATA_FOLDER, "allowed_ids_xlsm_tool.json")
PENDING_FILE = os.path.join(DATA_FOLDER, "pending_ids_xlsm_tool.json")
REJECTED_FILE = os.path.join(DATA_FOLDER, "rejected_ids_xlsm_tool.json")

FILES_TO_SEND = ["Launcher.xlsm", "installer_lifetime.exe"]

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    machine_id = data.get("machine_id", "")
    program_id = data.get("program_id", "")
    
    if program_id != "xlsm_tool":
        return jsonify({"valid": False, "reason": "Invalid program ID"}), 403

    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)
    rejected = load_json(REJECTED_FILE)

    if machine_id in rejected:
        return jsonify({"valid": False, "reason": "Machine ID was rejected"}), 403

    if machine_id in allowed:
        license_data = {
            "machine_id": machine_id,
            "program_id": program_id
        }
        return jsonify({
            "valid": True,
            "license": license_data,
            "files": FILES_TO_SEND + [f"QTY_Network_2025_{machine_id}.xlsm"]
        })

    if machine_id not in pending:
        pending.append(machine_id)
        save_json(PENDING_FILE, pending)

    return jsonify({
        "valid": False,
        "reason": "Pending approval"
    }), 403

@app.route("/download/<filename>")
def download(filename):
    try:
        return send_from_directory(DATA_FOLDER, filename, as_attachment=True)
    except FileNotFoundError:
        return "File not found", 404

@app.route("/admin")
def admin():
    pending = load_json(PENDING_FILE)
    allowed = load_json(ALLOWED_FILE)
    rejected = load_json(REJECTED_FILE)

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
    """
    return render_template_string(html, pending=pending, allowed=allowed, rejected=rejected)

@app.route("/approve", methods=["POST"])
def approve():
    machine_id = request.form.get("machine_id")
    pending = load_json(PENDING_FILE)
    allowed = load_json(ALLOWED_FILE)
    rejected = load_json(REJECTED_FILE)

    if machine_id in pending:
        pending.remove(machine_id)
        if machine_id not in allowed:
            allowed.append(machine_id)

    if machine_id in rejected:
        rejected.remove(machine_id)

    save_json(PENDING_FILE, pending)
    save_json(ALLOWED_FILE, allowed)
    save_json(REJECTED_FILE, rejected)
    return "Approved. <a href='/admin'>Back</a>"

@app.route("/reject", methods=["POST"])
def reject():
    machine_id = request.form.get("machine_id")
    pending = load_json(PENDING_FILE)
    rejected = load_json(REJECTED_FILE)

    if machine_id in pending:
        pending.remove(machine_id)
        if machine_id not in rejected:
            rejected.append(machine_id)

    save_json(PENDING_FILE, pending)
    save_json(REJECTED_FILE, rejected)
    return "Rejected. <a href='/admin'>Back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
