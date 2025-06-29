from flask import Flask, request, jsonify, send_file, render_template_string, redirect
import os
import json
import shutil

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
TEMPLATE_FILE = "template.xlsm"
LICENSE_FOLDER = "."

def get_machine_lists():
    def read_json(file):
        if os.path.exists(file):
            with open(file, "r") as f:
                return json.load(f)
        return []

    allowed = read_json(f"allowed_ids_{PROGRAM_ID}.json")
    pending = read_json(f"pending_ids_{PROGRAM_ID}.json")
    rejected = read_json(f"rejected_ids_{PROGRAM_ID}.json")
    return allowed, pending, rejected

def write_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/")
def home():
    return "XLSM Tool License Server"

@app.route("/request_license")
def request_license():
    machine_id = request.args.get("machine_id")
    program_id = request.args.get("program_id")

    if not machine_id or not program_id:
        return jsonify({"status": "error", "reason": "Missing machine_id or program_id"}), 400

    if program_id != PROGRAM_ID:
        return jsonify({"status": "error", "reason": "Invalid program_id"}), 403

    allowed, pending, rejected = get_machine_lists()

    if machine_id in rejected:
        return jsonify({"status": "rejected"}), 403

    if machine_id in allowed:
        # Create license content matching .xlsm validation
        password = generate_password(machine_id)
        license_content = f"{machine_id}\n{password}"
        return jsonify({"status": "approved", "license": license_content})

    if machine_id not in pending:
        pending.append(machine_id)
        write_json(f"pending_ids_{PROGRAM_ID}.json", pending)

    return jsonify({"status": "pending"})

def generate_password(machine_id):
    seed = 12345
    for c in machine_id:
        seed += ord(c)
    return f"PWD{seed}"

@app.route("/generate")
def generate():
    machine_id = request.args.get("machine_id")
    program_id = request.args.get("program_id")

    if not machine_id or not program_id:
        return "Missing machine_id or program_id", 400

    if program_id != PROGRAM_ID:
        return "Invalid program_id", 403

    allowed, _, _ = get_machine_lists()

    if machine_id not in allowed:
        return "Not allowed", 403

    # Create machine-specific copy
    new_filename = f"QTY_Network_2025_{machine_id}.xlsm"
    new_path = os.path.join(LICENSE_FOLDER, new_filename)

    if not os.path.exists(new_path):
        shutil.copyfile(TEMPLATE_FILE, new_path)

    # License file content
    password = generate_password(machine_id)
    license_content = f"{machine_id}\n{password}"
    return jsonify({"license": license_content})

@app.route("/admin")
def admin():
    allowed, pending, rejected = get_machine_lists()

    def build_list(title, items, action=None):
        out = f"<h3>{title}</h3><ul>"
        for item in items:
            out += f"<li>{item}"
            if action == "pending":
                out += f' ✅ <a href="/approve?machine_id={item}">Approve</a> ❌ <a href="/reject?machine_id={item}">Reject</a>'
            out += "</li>"
        return out + "</ul>"

    page = f"""
    <h1>XLSM Tool License Admin</h1>
    {build_list("Pending Machine IDs", pending, action="pending")}
    {build_list("Approved Machine IDs", allowed)}
    {build_list("Rejected Machine IDs", rejected)}
    """
    return render_template_string(page)

@app.route("/approve")
def approve():
    machine_id = request.args.get("machine_id")
    allowed, pending, rejected = get_machine_lists()

    if machine_id in pending:
        pending.remove(machine_id)
        allowed.append(machine_id)
        write_json(f"pending_ids_{PROGRAM_ID}.json", pending)
        write_json(f"allowed_ids_{PROGRAM_ID}.json", allowed)

    return redirect("/admin")

@app.route("/reject")
def reject():
    machine_id = request.args.get("machine_id")
    allowed, pending, rejected = get_machine_lists()

    if machine_id in pending:
        pending.remove(machine_id)
        rejected.append(machine_id)
        write_json(f"pending_ids_{PROGRAM_ID}.json", pending)
        write_json(f"rejected_ids_{PROGRAM_ID}.json", rejected)

    return redirect("/admin")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
