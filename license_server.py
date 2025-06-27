import os
import json
from flask import Flask, request, jsonify, send_file, render_template_string

app = Flask(__name__)
PROGRAM_ID = "xlsm_tool"

ALLOWED_FILE = f"allowed_ids_{PROGRAM_ID}.json"
PENDING_FILE = f"pending_ids_{PROGRAM_ID}.json"
TEMPLATE_FILE = "template.xlsm"
INSTALLER_FILE = "installer_lifetime.exe"
LAUNCHER_FILE = "Launcher.xlsm"


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.get_json()
    machine_id = data.get("machine_id")

    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)

    if machine_id in allowed:
        # Generate .xlsm filename
        new_filename = f"QTY_Network_2025_{machine_id}.xlsm"
        with open(TEMPLATE_FILE, "rb") as f:
            content = f.read()

        # Save generated file to disk
        with open(new_filename, "wb") as f:
            f.write(content)

        return jsonify({
            "status": "approved",
            "files": {
                "xlsm": new_filename,
                "installer": INSTALLER_FILE,
                "launcher": LAUNCHER_FILE
            }
        })

    else:
        # Save to pending if not already listed
        if machine_id not in pending:
            pending[machine_id] = {}
            save_json(PENDING_FILE, pending)

        return jsonify({
            "status": "pending",
            "message": "Your request is pending approval."
        })


@app.route("/admin", methods=["GET"])
def admin_page():
    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)

    pending_html = ""
    for mid in pending:
        pending_html += f"<li>{mid} " \
                        f"<form method='post' action='/approve' style='display:inline'>" \
                        f"<input type='hidden' name='machine_id' value='{mid}'>" \
                        f"<button type='submit'>✅ Approve</button></form> " \
                        f"<form method='post' action='/reject' style='display:inline'>" \
                        f"<input type='hidden' name='machine_id' value='{mid}'>" \
                        f"<button type='submit'>❌ Reject</button></form></li>"

    approved_html = "".join(f"<li>{mid}</li>" for mid in allowed)

    return render_template_string(f"""
        <h2>XLSM Tool License Admin</h2>
        <h3>Pending</h3>
        <ul>{pending_html if pending_html else "<li>No pending requests.</li>"}</ul>
        <h3>Approved</h3>
        <ul>{approved_html if approved_html else "<li>No approved IDs.</li>"}</ul>
    """)


@app.route("/approve", methods=["POST"])
def approve():
    machine_id = request.form.get("machine_id")
    allowed = load_json(ALLOWED_FILE)
    pending = load_json(PENDING_FILE)

    if machine_id:
        allowed[machine_id] = {}
        pending.pop(machine_id, None)
        save_json(ALLOWED_FILE, allowed)
        save_json(PENDING_FILE, pending)
    return "", 302, {'Location': '/admin'}


@app.route("/reject", methods=["POST"])
def reject():
    machine_id = request.form.get("machine_id")
    pending = load_json(PENDING_FILE)

    if machine_id in pending:
        pending.pop(machine_id)
        save_json(PENDING_FILE, pending)
    return "", 302, {'Location': '/admin'}


@app.route("/download/<filename>", methods=["GET"])
def download(filename):
    return send_file(filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
