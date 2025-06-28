from flask import Flask, request, jsonify, render_template_string
import json
import os

app = Flask(__name__)

# JSON file paths
PENDING_FILE = "pending_ids_xlsm_tool.json"
ALLOWED_FILE = "allowed_ids_xlsm_tool.json"

# HTML template for admin page
ADMIN_PAGE = """
<!DOCTYPE html>
<html>
<head><title>XLSM Tool License Admin</title></head>
<body>
    <h1>XLSM Tool License Admin</h1>
    <h3>Pending Requests</h3>
    <ul>
    {% for mid in pending_ids %}
        <li>{{ mid }}
            <form action="/approve" method="post" style="display:inline">
                <input type="hidden" name="machine_id" value="{{ mid }}">
                <button type="submit">✅ Approve</button>
            </form>
            <form action="/reject" method="post" style="display:inline">
                <input type="hidden" name="machine_id" value="{{ mid }}">
                <button type="submit">❌ Reject</button>
            </form>
        </li>
    {% endfor %}
    </ul>
    <h3>Approved Machine IDs</h3>
    <ul>
    {% for mid in allowed_ids %}
        <li>{{ mid }}</li>
    {% endfor %}
    </ul>
</body>
</html>
"""

# Load JSON safely
def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return []

# Save JSON safely
def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    try:
        data = request.get_json()
        machine_id = data.get("machine_id")
        program_id = data.get("program_id")

        if not machine_id or not program_id:
            return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400

        if program_id != "xlsm_tool":
            return jsonify({"valid": False, "reason": "Unsupported program ID"}), 400

        allowed_ids = load_json(ALLOWED_FILE)
        if machine_id in allowed_ids:
            license_data = {
                "machine_id": machine_id,
                "program_id": program_id,
                "status": "approved"
            }
            return jsonify({"valid": True, "license": license_data}), 200
        else:
            # Save to pending list
            pending_ids = load_json(PENDING_FILE)
            if machine_id not in pending_ids:
                pending_ids.append(machine_id)
                save_json(PENDING_FILE, pending_ids)
            return jsonify({"valid": False, "reason": "Not allowed"}), 403

    except Exception as e:
        return jsonify({"valid": False, "reason": str(e)}), 500

@app.route("/admin")
def admin():
    pending_ids = load_json(PENDING_FILE)
    allowed_ids = load_json(ALLOWED_FILE)
    return render_template_string(ADMIN_PAGE, pending_ids=pending_ids, allowed_ids=allowed_ids)

@app.route("/approve", methods=["POST"])
def approve():
    try:
        machine_id = request.form.get("machine_id")
        if not machine_id:
            return "Missing machine_id", 400

        allowed_ids = load_json(ALLOWED_FILE)
        pending_ids = load_json(PENDING_FILE)

        if machine_id not in allowed_ids:
            allowed_ids.append(machine_id)
            save_json(ALLOWED_FILE, allowed_ids)

        if machine_id in pending_ids:
            pending_ids.remove(machine_id)
            save_json(PENDING_FILE, pending_ids)

        return render_template_string(ADMIN_PAGE, pending_ids=pending_ids, allowed_ids=allowed_ids)

    except Exception as e:
        return f"Internal Server Error: {e}", 500

@app.route("/reject", methods=["POST"])
def reject():
    try:
        machine_id = request.form.get("machine_id")
        if not machine_id:
            return "Missing machine_id", 400

        pending_ids = load_json(PENDING_FILE)
        if machine_id in pending_ids:
            pending_ids.remove(machine_id)
            save_json(PENDING_FILE, pending_ids)

        allowed_ids = load_json(ALLOWED_FILE)
        return render_template_string(ADMIN_PAGE, pending_ids=pending_ids, allowed_ids=allowed_ids)

    except Exception as e:
        return f"Internal Server Error: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
