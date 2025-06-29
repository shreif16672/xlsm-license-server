from flask import Flask, request, jsonify, render_template_string
import os
import json
import datetime

app = Flask(__name__)

# Constants
PROGRAM_ID = "xlsm_tool"
LICENSE_FOLDER = "."
PENDING_FILE = f"pending_ids_{PROGRAM_ID}.json"
ALLOWED_FILE = f"allowed_ids_{PROGRAM_ID}.json"
LICENSE_TEMPLATE = "Licensed XLSM Tool — Lifetime Access"
FILES_TO_SEND = {
    "Launcher.xlsm": "Launcher.xlsm",
    "QTY_Network_2025.xlsm": "template.xlsm",
    "installer_lifetime.exe": "installer_lifetime.exe"
}

# Ensure required files exist
for file in [PENDING_FILE, ALLOWED_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

@app.route("/")
def index():
    return "XLSM License Server is running."

@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.json
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 403

    # Check if machine ID is allowed
    with open(ALLOWED_FILE) as f:
        allowed_ids = json.load(f)

    if machine_id in allowed_ids:
        license_data = LICENSE_TEMPLATE
        license_path = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "DynamoLicense", "license.txt")
        os.makedirs(os.path.dirname(license_path), exist_ok=True)
        with open(license_path, "w") as f:
            f.write(license_data)

        # Prepare download links
        downloads = {}
        for display_name, filename in FILES_TO_SEND.items():
            file_url = f"https://raw.githubusercontent.com/shreif16672/xlsm-license-server/main/{filename}"
            downloads[display_name] = file_url

        return jsonify({
            "valid": True,
            "license": license_data,
            "downloads": downloads
        })

    # If not allowed, add to pending
    with open(PENDING_FILE) as f:
        pending_ids = json.load(f)

    if machine_id not in pending_ids:
        pending_ids.append(machine_id)
        with open(PENDING_FILE, "w") as f:
            json.dump(pending_ids, f, indent=2)

    return jsonify({
        "valid": False,
        "reason": "Request not allowed (403)"
    }), 403

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if request.method == "POST":
        action = request.form.get("action")
        machine_id = request.form.get("machine_id")

        if action == "approve":
            with open(ALLOWED_FILE) as f:
                allowed_ids = json.load(f)
            if machine_id not in allowed_ids:
                allowed_ids.append(machine_id)
                with open(ALLOWED_FILE, "w") as f:
                    json.dump(allowed_ids, f, indent=2)

            with open(PENDING_FILE) as f:
                pending_ids = json.load(f)
            if machine_id in pending_ids:
                pending_ids.remove(machine_id)
                with open(PENDING_FILE, "w") as f:
                    json.dump(pending_ids, f, indent=2)

        elif action == "reject":
            with open(PENDING_FILE) as f:
                pending_ids = json.load(f)
            if machine_id in pending_ids:
                pending_ids.remove(machine_id)
                with open(PENDING_FILE, "w") as f:
                    json.dump(pending_ids, f, indent=2)

    with open(PENDING_FILE) as f:
        pending_ids = json.load(f)
    with open(ALLOWED_FILE) as f:
        allowed_ids = json.load(f)

    html = """
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending Machine IDs</h2>
    {% for mid in pending %}
      <form method="post">
        <li>{{ mid }}
            <input type="hidden" name="machine_id" value="{{ mid }}">
            <button name="action" value="approve">Approve</button>
            <button name="action" value="reject">Reject</button>
        </li>
      </form>
    {% else %}
      <p><i>None</i></p>
    {% endfor %}
    <h2>Approved Machine IDs</h2>
    <ul>
    {% for mid in approved %}
        <li>{{ mid }}</li>
    {% else %}
        <p><i>None</i></p>
    {% endfor %}
    </ul>
    """
    return render_template_string(html, pending=pending_ids, approved=allowed_ids)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
