from flask import Flask, request, jsonify, send_file, render_template_string
import json
import os
import shutil

app = Flask(__name__)

ALLOWED_FILE = "allowed_ids_xlsm_tool.json"
PENDING_FILE = "pending_ids_xlsm_tool.json"
TEMPLATE_FILE = "template.xlsm"


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    machine_id = data.get("machine_id")
    program_id = data.get("program_id")
    duration = data.get("duration")

    if not machine_id or not program_id:
        return jsonify({"error": "Missing machine_id or program_id"}), 400

    allowed = load_json(ALLOWED_FILE)
    if machine_id in allowed:
        return jsonify({"valid": True, "message": "Already approved"}), 200

    pending = load_json(PENDING_FILE)
    pending[machine_id] = {"program_id": program_id, "duration": duration}
    save_json(PENDING_FILE, pending)
    return jsonify({"valid": False, "reason": "Pending approval"}), 202


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        data = request.get_json()
        machine_id = data.get("machine_id")
        action = data.get("action")

        if not machine_id or action not in ["approve", "reject"]:
            return "Invalid input", 400

        pending = load_json(PENDING_FILE)
        allowed = load_json(ALLOWED_FILE)

        if action == "approve" and machine_id in pending:
            allowed[machine_id] = pending.pop(machine_id)
            save_json(ALLOWED_FILE, allowed)
            save_json(PENDING_FILE, pending)
            return "Approved", 200

        elif action == "reject" and machine_id in pending:
            pending.pop(machine_id)
            save_json(PENDING_FILE, pending)
            return "Rejected", 200

        return "Machine ID not found", 404

    # HTML admin panel
    pending = load_json(PENDING_FILE)
    allowed = load_json(ALLOWED_FILE)

    html = f"""
    <h1>XLSM Tool License Admin</h1>
    <h2>Pending</h2>
    {"<br>".join([f'<li>{mid}</li>' for mid in pending]) or "No pending requests."}
    <h2>Approved</h2>
    {"<br>".join([f'<li>{mid}</li>' for mid in allowed]) or "No approved machines."}
    """
    return render_template_string(html)


@app.route("/download", methods=["GET"])
def download():
    machine_id = request.args.get("mid")
    if not machine_id:
        return "Missing machine ID", 400

    allowed = load_json(ALLOWED_FILE)
    if machine_id not in allowed:
        return "Machine not approved", 403

    src_path = os.path.abspath(TEMPLATE_FILE)
    dst_path = os.path.abspath(f"QTY_Network_2025_{machine_id}.xlsm")

    try:
        shutil.copyfile(src_path, dst_path)
        return send_file(dst_path, as_attachment=True)
    except Exception as e:
        return f"Error: {str(e)}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
