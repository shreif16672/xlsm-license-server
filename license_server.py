from flask import Flask, request, jsonify, render_template_string
import os
import json
from datetime import datetime

app = Flask(__name__)

# ----------------------------
# Utility for safe file access
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def get_json_path(filename):
    return os.path.join(BASE_DIR, filename)

def load_json(filename):
    path = get_json_path(filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_json(filename, data):
    path = get_json_path(filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# -----------------------
# Program ID for this app
# -----------------------
PROGRAM_ID = "xlsm_tool"
allowed_file = f"allowed_ids_{PROGRAM_ID}.json"
pending_file = f"pending_ids_{PROGRAM_ID}.json"

# ----------------------------
# License request endpoint
# ----------------------------
@app.route("/generate", methods=["POST"])
def generate_license():
    data = request.json
    machine_id = data.get("machine_id")

    allowed_ids = load_json(allowed_file)
    if machine_id in allowed_ids:
        return jsonify({"status": "approved", "license": f"LICENSED_{machine_id}"})
    
    pending_ids = load_json(pending_file)
    if machine_id not in pending_ids:
        pending_ids[machine_id] = datetime.utcnow().isoformat()
        save_json(pending_file, pending_ids)

    return jsonify({"status": "pending", "reason": "Not allowed"})

# ----------------------------
# Admin approval page
# ----------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    allowed_ids = load_json(allowed_file)
    pending_ids = load_json(pending_file)

    if request.method == "POST":
        action = request.form.get("action")
        machine_id = request.form.get("machine_id")

        if action == "approve":
            if machine_id not in allowed_ids:
                allowed_ids[machine_id] = datetime.utcnow().isoformat()
                save_json(allowed_file, allowed_ids)
            if machine_id in pending_ids:
                del pending_ids[machine_id]
                save_json(pending_file, pending_ids)
        elif action == "reject":
            if machine_id in pending_ids:
                del pending_ids[machine_id]
                save_json(pending_file, pending_ids)

    html = """
    <h2>XLSM Tool License Admin</h2>
    <h3>Pending</h3>
    {% if not pending %}
        <p>No pending requests.</p>
    {% else %}
        <ul>
        {% for mid in pending %}
            <li>
                <form method="POST" style="display:inline;">
                    <input type="hidden" name="machine_id" value="{{ mid }}">
                    <button name="action" value="approve">✅ Approve</button>
                    <button name="action" value="reject">❌ Reject</button>
                </form>
                {{ mid }}
            </li>
        {% endfor %}
        </ul>
    {% endif %}

    <h3>Approved</h3>
    <ul>
    {% for mid in approved %}
        <li>{{ mid }}</li>
    {% endfor %}
    </ul>
    """

    return render_template_string(html, pending=pending_ids, approved=allowed_ids)

# ----------------------------
# Run app
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
