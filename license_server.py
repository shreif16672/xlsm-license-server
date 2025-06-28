from flask import Flask, request, jsonify, render_template_string, redirect
import os
import json

app = Flask(__name__)

LICENSES_FOLDER = "."

def load_json(filename):
    path = os.path.join(LICENSES_FOLDER, filename)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []

def save_json(filename, data):
    path = os.path.join(LICENSES_FOLDER, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/")
def home():
    return "✅ XLSM License Server is running."

@app.route("/generate", methods=["POST"])
def generate():
    try:
        machine_id = request.json.get("machine_id")
        program_id = request.json.get("program_id")

        if not machine_id or not program_id:
            return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

        allowed_ids = load_json(f"allowed_ids_{program_id}.json")
        if machine_id in allowed_ids:
            license_data = {
                "machine_id": machine_id,
                "program_id": program_id,
                "license": "valid"
            }
            return jsonify({"valid": True, "license": license_data})
        else:
            pending_ids = load_json(f"pending_ids_{program_id}.json")
            if machine_id not in pending_ids:
                pending_ids.append(machine_id)
                save_json(f"pending_ids_{program_id}.json", pending_ids)
            return jsonify({"valid": False, "reason": "Not allowed"}), 403

    except Exception as e:
        return jsonify({"valid": False, "reason": str(e)}), 500

@app.route("/admin")
def admin():
    program = "xlsm_tool"
    allowed_ids = load_json(f"allowed_ids_{program}.json")
    pending_ids = load_json(f"pending_ids_{program}.json")
    html = f"""
    <h1>XLSM Tool License Admin</h1>
    <h3>Pending Requests</h3>
    <ul>
        {''.join(f"<li>{mid} <form action='/approve/{program}/{mid}' method='post' style='display:inline;'><button type='submit'>✅ Approve</button></form> <form action='/reject/{program}/{mid}' method='post' style='display:inline;'><button type='submit'>❌ Reject</button></form></li>" for mid in pending_ids)}
    </ul>
    <h3>Approved Machine IDs</h3>
    <ul>
        {''.join(f"<li>{mid}</li>" for mid in allowed_ids)}
    </ul>
    """
    return render_template_string(html)

@app.route("/approve/<program>/<machine_id>", methods=["POST"])
def approve_id(program, machine_id):
    allowed_ids = load_json(f"allowed_ids_{program}.json")
    pending_ids = load_json(f"pending_ids_{program}.json")

    if machine_id not in allowed_ids:
        allowed_ids.append(machine_id)
    if machine_id in pending_ids:
        pending_ids.remove(machine_id)

    save_json(f"allowed_ids_{program}.json", allowed_ids)
    save_json(f"pending_ids_{program}.json", pending_ids)

    return redirect("/admin")

@app.route("/reject/<program>/<machine_id>", methods=["POST"])
def reject_id(program, machine_id):
    pending_ids = load_json(f"pending_ids_{program}.json")
    if machine_id in pending_ids:
        pending_ids.remove(machine_id)
        save_json(f"pending_ids_{program}.json", pending_ids)
    return redirect("/admin")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
