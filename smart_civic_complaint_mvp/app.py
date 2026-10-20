import os
import re
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher
from functools import wraps
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "civic_complaints.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-secret")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "demo123")

CATEGORIES = {
    "Road damage": ["pothole", "road", "street", "crack", "asphalt", "footpath"],
    "Streetlight": ["streetlight", "street light", "lamp", "light", "dark", "pole"],
    "Garbage / sanitation": ["garbage", "trash", "waste", "bin", "rubbish", "smell", "dump"],
    "Water leakage": ["water", "leak", "pipe", "burst", "drain", "sewage", "overflow"],
    "Other": []
}

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            latitude TEXT,
            longitude TEXT,
            reporter_name TEXT,
            photo_filename TEXT,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Submitted',
            duplicate_of INTEGER,
            admin_note TEXT,
            resolution_filename TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (duplicate_of) REFERENCES complaints(id)
        )
        """)
        count = db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
        if count == 0:
            samples = [
                ("Large pothole near school", "A deep pothole is dangerous for motorcycles and cars.", "Road damage", "Main Road, near City School", "24.8607", "67.0011", "Demo Resident", None, "High", "In progress", None, "Road team assigned.", None, now(), now()),
                ("Streetlight not working", "The streetlight has been off for three nights.", "Streetlight", "Block B, Park Street", "24.8612", "67.0024", "Ayesha", None, "Medium", "Submitted", None, None, None, now(), now()),
                ("Water pipe leaking", "Clean water is leaking continuously from a roadside pipe.", "Water leakage", "Market Road, near bus stop", "24.8598", "67.0040", "Ali", None, "High", "Resolved", None, "Pipe repaired in demo.", None, now(), now()),
                ("Garbage bin overflowing", "Waste is overflowing from the public bin.", "Garbage / sanitation", "Community Park entrance", "24.8620", "67.0031", "Demo Resident", None, "Medium", "Submitted", None, None, None, now(), now())
            ]
            db.executemany("""
                INSERT INTO complaints
                (title, description, category, location, latitude, longitude, reporter_name, photo_filename,
                 priority, status, duplicate_of, admin_note, resolution_filename, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, samples)

def classify_category(text):
    normalized = re.sub(r"\s+", " ", text.lower())
    best_category, best_score = "Other", 0
    for category, keywords in CATEGORIES.items():
        score = sum(1 for keyword in keywords if keyword in normalized)
        if score > best_score:
            best_category, best_score = category, score
    return best_category

def priority_for(category, text):
    text = text.lower()
    urgent_terms = ["dangerous", "accident", "injury", "school", "hospital", "exposed wire", "burst", "flood", "fire"]
    if any(term in text for term in urgent_terms):
        return "High"
    if category in ("Water leakage", "Road damage"):
        return "High"
    if category in ("Streetlight", "Garbage / sanitation"):
        return "Medium"
    return "Low"

def similarity_text(a, b):
    clean = lambda s: re.sub(r"[^a-z0-9 ]", " ", s.lower()).strip()
    return SequenceMatcher(None, clean(a), clean(b)).ratio()

def find_duplicate(db, title, description, location, category):
    recent = db.execute("""
        SELECT id, title, description, location, category
        FROM complaints
        WHERE created_at >= datetime('now', '-30 days')
        ORDER BY id DESC LIMIT 100
    """).fetchall()
    combined = f"{title} {description}"
    for row in recent:
        if row["category"] == category and similarity_text(combined, f'{row["title"]} {row["description"]}') >= 0.76:
            if similarity_text(location, row["location"]) >= 0.40 or location.lower() in row["location"].lower() or row["location"].lower() in location.lower():
                return row["id"]
    return None

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file, prefix):
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        raise ValueError("Please upload a JPG, PNG, or WEBP image.")
    safe = secure_filename(file.filename)
    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{safe}"
    file.save(UPLOAD_DIR / filename)
    return filename

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin login required."}), 401
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect demo password. Try demo123 unless you configured ADMIN_PASSWORD.", "error")
    return render_template("login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin.html")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.get("/api/meta")
def meta():
    return jsonify({"categories": list(CATEGORIES.keys()), "statuses": ["Submitted", "Under review", "In progress", "Resolved", "Rejected"]})

@app.post("/api/complaints")
def create_complaint():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    reporter = request.form.get("reporter_name", "").strip()[:100]
    latitude = request.form.get("latitude", "").strip()[:30]
    longitude = request.form.get("longitude", "").strip()[:30]
    if not title or not description or not location:
        return jsonify({"error": "Title, description, and location are required."}), 400
    if len(title) > 120 or len(description) > 2000 or len(location) > 200:
        return jsonify({"error": "Please shorten one or more fields."}), 400
    text = f"{title} {description}"
    category = classify_category(text)
    priority = priority_for(category, text)
    try:
        photo = save_upload(request.files.get("photo"), "complaint")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    with get_db() as db:
        duplicate = find_duplicate(db, title, description, location, category)
        cur = db.execute("""
            INSERT INTO complaints
            (title, description, category, location, latitude, longitude, reporter_name, photo_filename,
             priority, status, duplicate_of, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Submitted', ?, ?, ?)
        """, (title, description, category, location, latitude, longitude, reporter or "Anonymous",
              photo, priority, duplicate, now(), now()))
        complaint_id = cur.lastrowid
    return jsonify({
        "message": "Complaint submitted successfully.",
        "id": complaint_id,
        "category": category,
        "priority": priority,
        "possible_duplicate_of": duplicate
    }), 201

@app.get("/api/complaints/<int:complaint_id>")
def track_complaint(complaint_id):
    with get_db() as db:
        row = db.execute("""
            SELECT id, title, category, location, priority, status, duplicate_of, admin_note, created_at, updated_at
            FROM complaints WHERE id = ?
        """, (complaint_id,)).fetchone()
    if not row:
        return jsonify({"error": "No complaint found with that ID."}), 404
    return jsonify(dict(row))

@app.get("/api/admin/complaints")
@admin_required
def list_complaints():
    status = request.args.get("status", "").strip()
    category = request.args.get("category", "").strip()
    query = "SELECT * FROM complaints WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, id DESC"
    with get_db() as db:
        rows = db.execute(query, params).fetchall()
    return jsonify([dict(row) for row in rows])

@app.patch("/api/admin/complaints/<int:complaint_id>")
@admin_required
def update_complaint(complaint_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    priority = data.get("priority")
    note = data.get("admin_note", "")
    valid_statuses = {"Submitted", "Under review", "In progress", "Resolved", "Rejected"}
    valid_priorities = {"Low", "Medium", "High"}
    if status not in valid_statuses or priority not in valid_priorities:
        return jsonify({"error": "Choose a valid status and priority."}), 400
    with get_db() as db:
        exists = db.execute("SELECT id FROM complaints WHERE id=?", (complaint_id,)).fetchone()
        if not exists:
            return jsonify({"error": "Complaint not found."}), 404
        db.execute("""
            UPDATE complaints SET status=?, priority=?, admin_note=?, updated_at=? WHERE id=?
        """, (status, priority, str(note)[:1000], now(), complaint_id))
    return jsonify({"message": "Complaint updated."})

@app.post("/api/admin/complaints/<int:complaint_id>/resolution")
@admin_required
def upload_resolution(complaint_id):
    try:
        filename = save_upload(request.files.get("evidence"), "resolution")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not filename:
        return jsonify({"error": "Choose an image as resolution evidence."}), 400
    with get_db() as db:
        exists = db.execute("SELECT id FROM complaints WHERE id=?", (complaint_id,)).fetchone()
        if not exists:
            (UPLOAD_DIR / filename).unlink(missing_ok=True)
            return jsonify({"error": "Complaint not found."}), 404
        db.execute("UPDATE complaints SET resolution_filename=?, updated_at=? WHERE id=?", (filename, now(), complaint_id))
    return jsonify({"message": "Resolution evidence uploaded.", "filename": filename})

@app.get("/api/admin/stats")
@admin_required
def admin_stats():
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
        open_count = db.execute("SELECT COUNT(*) FROM complaints WHERE status NOT IN ('Resolved','Rejected')").fetchone()[0]
        resolved = db.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0]
        high = db.execute("SELECT COUNT(*) FROM complaints WHERE priority='High' AND status NOT IN ('Resolved','Rejected')").fetchone()[0]
    return jsonify({"total": total, "open": open_count, "resolved": resolved, "high_priority": high})

@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "Image too large. Maximum request size is 5 MB."}), 413

init_db()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
