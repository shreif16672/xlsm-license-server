import os
import json
import shutil
from flask import Flask, request, jsonify, send_from_directory, render_template_string

app = Flask(__name__)

DATA_FOLDER = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = os.path.join(DATA_FOLDER, "template.xlsm")

@app.route('/generate', methods=['POST'])
def generate_license():
    data = request.json
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

    allowed_path = os.path.join(DATA_FOLDER, f"allowed_ids_{program_id}.json")
    pending_path = os.path.join(DATA_FOLDER, f"pending_ids_{program_id}.json")

    # Load allowed list
    if os.path.exists(allowed_path):
        with open(allowed_path, 'r') as f:
            allowed_ids = json.load(f)
    else:
        allowed_ids = []

    # Check approval
    if machine_id in allowed_ids:
        # Generate customized .xlsm
        filename = f"QTY_Network_2025_{machine_id}.xlsm"
        target_path = os.path.join(DATA_FOLDER, filename)
        if not os.path.exists(target_path):
            shutil.copy(TEMPLATE_FILE, target_path)

        # Generate license.txt
        license_data = f"{machine_id}\nPWD17610"
        license_file_path = os.path.join(DATA_FOLDER, "license.txt")
        with open(license_file_path, "w") as f:
            f.write(license_data)

        return jsonify({
            "valid": True,
            "license": "Licensed XLSM Tool — Lifetime Access",
            "files": [
                {"filename": "license.txt", "path": "license.txt"},
                {"filename": "Launcher.xlsm", "path": "Launcher.xlsm"},
                {"filename": filename, "path": filename},
                {"filename": "installer_lifetime.exe", "path": "installer_lifetime.exe"}
            ]
        })

    # Not approved → Add to pending list
    if os.path.exists(pending_path):
        with open(pending_path, 'r') as f:
            pending_ids = json.load(f)
    else:
        pending_ids = []

    if machine_id not in pending_ids:
        pending_ids.append(machine_id)
        with open(pending_path, 'w') as f:
            json.dump(pending_ids, f)

    return jsonify({"valid": False, "reason": "Not approved"}), 403


@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(DATA_FOLDER, filename, as_attachment=True)


@app.route('/admin/<program_id>')
def admin(program_id):
    allowed_path = os.path.join(DATA_FOLDER, f"allowed_ids_{program_id}.json")
    pending_path = os.path.join(DATA_FOLDER, f"pending_ids_{program_id}.json")

    with open(allowed_path, 'r') if os.path.exists(allowed_path) else open(os.devnull, 'r') as f:
        allowed = json.load(f) if os.path.getsize(allowed_path) > 0 else []

    with open(pending_path, 'r') if os.path.exists(pending_path) else open(os.devnull, 'r') as f:
        pending = json.load(f) if os.path.getsize(pending_path) > 0 else []

    html = """
    <h1>Admin Panel - {{ program_id }}</h1>
    <h2>✅ Approved IDs</h2>
    <ul>
    {% for mid in allowed %}
        <li>{{ mid }}</li>
    {% endfor %}
    </ul>
    <h2>⏳ Pending Requests</h2>
    <ul>
    {% for mid in pending %}
        <li>
            {{ mid }}
            <form method="post" action="/approve/{{ program_id }}/{{ mid }}" style="display:inline;">
                <button type="submit">Approve</button>
            </form>
        </li>
    {% endfor %}
    </ul>
    """
    return render_template_string(html, allowed=allowed, pending=pending, program_id=program_id)


@app.route('/approve/<program_id>/<machine_id>', methods=['POST'])
def approve(program_id, machine_id):
    allowed_path = os.path.join(DATA_FOLDER, f"allowed_ids_{program_id}.json")
    pending_path = os.path.join(DATA_FOLDER, f"pending_ids_{program_id}.json")

    # Load allowed and pending
    allowed = []
    pending = []
    if os.path.exists(allowed_path):
        with open(allowed_path, 'r') as f:
            allowed = json.load(f)

    if os.path.exists(pending_path):
        with open(pending_path, 'r') as f:
            pending = json.load(f)

    # Approve ID
    if machine_id not in allowed:
        allowed.append(machine_id)
        with open(allowed_path, 'w') as f:
            json.dump(allowed, f)

    if machine_id in pending:
        pending.remove(machine_id)
        with open(pending_path, 'w') as f:
            json.dump(pending, f)

    return f"✅ Machine ID {machine_id} approved for {program_id}. <a href='/admin/{program_id}'>Back</a>"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
