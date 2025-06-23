from flask import Flask, request, jsonify, render_template_string
import os
import json
import hashlib
import hmac
from datetime import datetime, timedelta

app = Flask(__name__)

# === Configuration for xlsm_tool only ===
PENDING_FILE = "pending_ids_xlsm_tool.json"
ALLOWED_FILE = "allowed_ids_xlsm_tool.json"
SECRET_KEY = "MySecretKeyForHMAC"

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    machine_id = data.get("machine_id")
    duration = data.get("duration")
    program_id = "xlsm_tool"

    if not machine_id:
        return "Missing machine_id", 400

    pending = load_json(PENDING_FILE)
    allowed = load_json(ALLOWED_FILE)

    if machine_id in allowed:
        expiry = None
        if duration:
            expiry = (datetime.utcnow() + timedelta(hours=int(duration))).isoformat()
        payload = {
            "machine_id": machine_id,
            "program_id": program_id,
            "expiry": expiry
        }
        signature = hmac.new(SECRET_KEY.encode(), json.dumps(payload).encode(), hashlib.sha256).hexdigest()
        payload["signature"] = signature
        return jsonify(payload)

    pending[machine_id] = {"program_id": program_id, "duration": duration}
    save_json(PENDING_FILE, pending)
    return "Request submitted and pending approval.", 202

@app.route("/validate", methods=["POST"])
def validate():
    data = request.json
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")

    if not machine_id or program_id != "xlsm_tool":
        return jsonify({"valid": False, "reason": "Invalid or missing fields"}), 400

    allowed = load_json(ALLOWED_FILE)
    record = allowed.get(machine_id)

    if not record:
        return jsonify({"valid": False, "reason": "Not allowed"}), 403

    expiry = record.get("expiry")
    if expiry and datetime.utcnow() > datetime.fromisoformat(expiry):
        return jsonify({"valid": False, "reason": "License expired"}), 403

    return jsonify({"valid": True})

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    pending = load_json(PENDING_FILE)
    allowed = load_json(ALLOWED_FILE)

    if request.method == "POST":
        machine_id = request.form.get("machine_id")
        action = request.form.get("action")

        if machine_id in pending:
            if action == "approve":
                duration = pending[machine_id].get("duration")
                expiry = None
                if duration:
                    expiry = (datetime.utcnow() + timedelta(hours=int(duration))).isoformat()
                allowed[machine_id] = {
                    "program_id": "xlsm_tool",
                    "expiry": expiry
                }
                del pending[machine_id]
                save_json(ALLOWED_FILE, allowed)
                save_json(PENDING_FILE, pending)
            elif action == "reject":
                del pending[machine_id]
                save_json(PENDING_FILE, pending)

    html = "<h1>XLSM Tool License Admin</h1><h2>Pending</h2>"
    if pending:
        html += "<form method='POST'>"
        for mid in pending:
            html += f"<p>{mid} "
            html += f"<button name='action' value='approve'>Approve</button> "
            html += f"<button name='action' value='reject'>Reject</button> "
            html += f"<input type='hidden' name='machine_id' value='{mid}'>"
            html += "</p>"
        html += "</form>"
    else:
        html += "<p>No pending requests.</p>"

    html += "<h2>Approved</h2><ul>"
    for mid in allowed:
        html += f"<li>{mid}</li>"
    html += "</ul>"

    return render_template_string(html)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
