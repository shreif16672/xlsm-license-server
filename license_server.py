from flask import Flask, request, jsonify, send_file, render_template_string
import os
import json

app = Flask(__name__)

# File paths
allowed_file = "allowed_ids_xlsm_tool.json"
pending_file = "pending_ids_xlsm_tool.json"
license_file = "license.txt"

# Ensure files exist
for f in [allowed_file, pending_file]:
    if not os.path.exists(f):
        with open(f, "w") as file:
            json.dump([], file)

# Admin HTML template
admin_template = """
<!DOCTYPE html>
<html>
<head><title>XLSM Tool License Admin</title></head>
<body>
<h2>XLSM Tool License Admin</h2>

<h3>Pending Requests</h3>
<ul>
  {% for id in pending %}
    <li>{{ id }}
      <form action="/approve" method="post" style="display:inline;">
        <input type="hidden" name="machine_id" value="{{ id }}">
        <button type="submit">✅ Approve</button>
      </form>
      <form action="/reject" method="post" style="display:inline;">
        <input type="hidden" name="machine_id" value="{{ id }}">
        <button type="submit">❌ Reject</button>
      </form>
    </li>
  {% endfor %}
</ul>

<h3>Approved Machine IDs</h3>
<ul>
  {% for id in allowed %}
    <li>{{ id }}</li>
  {% endfor %}
</ul>
</body>
</html>
"""

@app.route('/admin')
def admin():
    with open(pending_file) as f:
        pending = json.load(f)
    with open(allowed_file) as f:
        allowed = json.load(f)
    return render_template_string(admin_template, pending=pending, allowed=allowed)

@app.route('/approve', methods=['POST'])
def approve():
    machine_id = request.form.get("machine_id")
    if not machine_id:
        return "Missing machine_id", 400

    # Load current lists
    with open(pending_file) as f:
        pending = json.load(f)
    with open(allowed_file) as f:
        allowed = json.load(f)

    # Move to allowed if not already there
    if machine_id in pending:
        pending.remove(machine_id)
        if machine_id not in allowed:
            allowed.append(machine_id)
        with open(pending_file, "w") as f:
            json.dump(pending, f)
        with open(allowed_file, "w") as f:
            json.dump(allowed, f)
    return "Approved", 200

@app.route('/reject', methods=['POST'])
def reject():
    machine_id = request.form.get("machine_id")
    if not machine_id:
        return "Missing machine_id", 400

    with open(pending_file) as f:
        pending = json.load(f)
    if machine_id in pending:
        pending.remove(machine_id)
        with open(pending_file, "w") as f:
            json.dump(pending, f)
    return "Rejected", 200

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json(force=True)
        machine_id = data.get("machine_id", "").strip()
        program_id = data.get("program_id", "").strip()

        if not machine_id or not program_id:
            return jsonify({"valid": False, "reason": "Missing machine_id or program_id"}), 400
        if program_id != "xlsm_tool":
            return jsonify({"valid": False, "reason": "Invalid program_id"}), 403

        with open(allowed_file) as f:
            allowed = json.load(f)
        if machine_id in allowed:
            with open(license_file, "r") as lf:
                license_content = lf.read()
            return jsonify({"valid": True, "license": license_content})
        else:
            with open(pending_file) as f:
                pending = json.load(f)
            if machine_id not in pending:
                pending.append(machine_id)
                with open(pending_file, "w") as f:
                    json.dump(pending, f)
            return jsonify({"valid": False, "reason": "Not allowed"}), 403
    except Exception as e:
        return jsonify({"valid": False, "reason": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
