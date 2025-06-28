from flask import Flask, request, jsonify, send_from_directory
import json
import os

app = Flask(__name__)

PROGRAM_ID = "xlsm_tool"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ALLOWED_IDS_FILE = os.path.join(BASE_DIR, f"allowed_ids_{PROGRAM_ID}.json")
PENDING_IDS_FILE = os.path.join(BASE_DIR, f"pending_ids_{PROGRAM_ID}.json")

FILES_FOLDER = BASE_DIR  # All files (xlsm, exe) are in the repo root
LICENSE_KEY = "ENJAZ2025"  # The key expected by the xlsm logic

# Load JSON
def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

# Save JSON
def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/generate", methods=["POST"])
def generate_license():
    try:
        data = request.get_json()
        machine_id = data["machine_id"]
        program_id = data.get("program_id", "xlsm_tool")  # default to xlsm_tool

        allowed_file = f"allowed_ids_{program_id}.json"
        pending_file = f"pending_ids_{program_id}.json"

        # Load allowed list
        allowed_ids = load_json(allowed_file)
        if not isinstance(allowed_ids, list):
            allowed_ids = []

        if machine_id in allowed_ids:
            # ✅ Approved
            license_data = {"machine_id": machine_id, "program_id": program_id}
            encoded = base64.b64encode(json.dumps(license_data).encode()).decode()
            return jsonify({"valid": True, "license": encoded})
        else:
            # Add to pending list only if not already there
            pending_ids = load_json(pending_file)
            if not isinstance(pending_ids, list):
                pending_ids = []
            if machine_id not in pending_ids:
                pending_ids.append(machine_id)
                save_json(pending_file, pending_ids)

            return jsonify({"valid": False, "reason": "Not allowed"})
    except Exception as e:
        return jsonify({"valid": False, "reason": str(e)})

        # Approved license
        license_data = {
            "machine_id": machine_id,
            "program_id": PROGRAM_ID,
            "license": LICENSE_KEY
        }

        # File paths (generic fallback filename is template.xlsm)
        files = {
            "installer": "installer_lifetime.exe",
            "launcher": "Launcher.xlsm",
            "xlsm": f"QTY_Network_2025_{machine_id}.xlsm" if os.path.exists(os.path.join(FILES_FOLDER, f"QTY_Network_2025_{machine_id}.xlsm")) else "template.xlsm"
        }

        return jsonify({
            "valid": True,
            "license": license_data,
            "files": files
        })

    except Exception as e:
        return jsonify({"valid": False, "reason": str(e)}), 500

@app.route("/files/<filename>", methods=["GET"])
def download_file(filename):
    return send_from_directory(FILES_FOLDER, filename, as_attachment=True)

@app.route("/admin")
def admin_panel():
    allowed_ids = load_json(ALLOWED_IDS_FILE)
    pending_ids = load_json(PENDING_IDS_FILE)

    html = "<h2>XLSM Tool License Admin</h2><h3>Pending Requests</h3><ul>"
    for mid in pending_ids:
        html += f"<li>{mid} <form action='/approve' method='post' style='display:inline;'><input type='hidden' name='id' value='{mid}'><button type='submit'>✅ Approve</button></form> <form action='/reject' method='post' style='display:inline;'><input type='hidden' name='id' value='{mid}'><button type='submit'>❌ Reject</button></form></li>"
    html += "</ul><h3>Approved Machine IDs</h3><ul>"
    for mid in allowed_ids:
        html += f"<li>{mid}</li>"
    html += "</ul>"
    return html

@app.route("/approve/<program>/<machine_id>", methods=["POST"])
def approve_id(program, machine_id):
    try:
        allowed_file = f"allowed_ids_{program}.json"
        pending_file = f"pending_ids_{program}.json"

        allowed_ids = load_json(allowed_file)
        if not isinstance(allowed_ids, list):
            allowed_ids = []

        pending_ids = load_json(pending_file)
        if not isinstance(pending_ids, list):
            pending_ids = []

        if machine_id not in allowed_ids:
            allowed_ids.append(machine_id)
        if machine_id in pending_ids:
            pending_ids.remove(machine_id)

        save_json(allowed_file, allowed_ids)
        save_json(pending_file, pending_ids)

        return redirect("/admin")
    except Exception as e:
        return f"Internal Server Error: {e}", 500

@app.route("/reject", methods=["POST"])
def reject_id():
    mid = request.form.get("id")
    pending = load_json(PENDING_IDS_FILE)
    if mid in pending:
        pending.remove(mid)
        save_json(PENDING_IDS_FILE, pending)
    return '<script>window.location.href="/admin";</script>'

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
