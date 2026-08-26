import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash, g

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("DATABASE_PATH", os.path.join(BASE, "vivahsetu.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "CHANGE_ME_IN_PRODUCTION")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db:
        db.close()


def init():
    d = get_db()
    d.executescript("""
    CREATE TABLE IF NOT EXISTS enquiries(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      phone TEXT NOT NULL,
      event_type TEXT,
      event_date TEXT,
      guests INTEGER,
      budget TEXT,
      location TEXT,
      message TEXT,
      status TEXT DEFAULT 'New',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS vendors(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      business TEXT NOT NULL,
      category TEXT NOT NULL,
      phone TEXT NOT NULL,
      area TEXT,
      price TEXT,
      capacity INTEGER,
      description TEXT,
      status TEXT DEFAULT 'Pending',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS venues(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      area TEXT NOT NULL,
      price INTEGER NOT NULL,
      capacity INTEGER NOT NULL,
      rating REAL DEFAULT 4.5,
      tag TEXT DEFAULT 'Popular',
      description TEXT DEFAULT '',
      active INTEGER DEFAULT 1
    );
    """)

    if d.execute("SELECT COUNT(*) FROM venues").fetchone()[0] == 0:
        d.executemany(
            """INSERT INTO venues
            (name, area, price, capacity, rating, tag, description)
            VALUES(?,?,?,?,?,?,?)""",
            [
                ("Royal Palace Banquet", "Padribazar, Gorakhpur", 90000, 700, 4.8, "Premium",
                 "Spacious banquet for weddings and receptions."),
                ("Green Leaf Lawn", "Mohaddipur, Gorakhpur", 75000, 600, 4.7, "Popular",
                 "Open lawn with flexible decoration options."),
                ("The Grand Orchid", "Medical Road, Gorakhpur", 145000, 800, 4.9, "Luxury",
                 "Premium venue for grand celebrations."),
                ("Shagun Marriage Garden", "Taramandal, Gorakhpur", 65000, 350, 4.6, "Value",
                 "Comfortable venue for mid-size celebrations."),
                ("Royal Orchid Banquet", "Golghar, Gorakhpur", 110000, 500, 4.8, "Popular",
                 "Modern banquet with premium ambience."),
                ("Sunrise Celebration Hall", "Rapti Nagar, Gorakhpur", 55000, 250, 4.5, "Budget",
                 "Affordable hall for intimate celebrations.")
            ]
        )
    d.commit()


def admin_only(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*a, **k)
    return w


@app.route("/")
def home():
    venues = get_db().execute(
        "SELECT * FROM venues WHERE active=1 ORDER BY rating DESC"
    ).fetchall()
    return render_template("index.html", venues=venues)


@app.post("/api/enquiry")
def enquiry():
    x = request.form
    if not x.get("name") or not x.get("phone"):
        return jsonify(ok=False, error="Name and mobile are required."), 400

    get_db().execute(
        """INSERT INTO enquiries
        (name,phone,event_type,event_date,guests,budget,location,message)
        VALUES(?,?,?,?,?,?,?,?)""",
        (
            x.get("name"), x.get("phone"), x.get("event_type"),
            x.get("event_date"), x.get("guests") or None, x.get("budget"),
            x.get("location"), x.get("message")
        )
    )
    get_db().commit()
    return jsonify(ok=True, message="Enquiry received. Our team will contact you shortly.")


@app.post("/api/vendor")
def vendor():
    x = request.form
    if not x.get("business") or not x.get("category") or not x.get("phone"):
        return jsonify(ok=False, error="Business, category and mobile are required."), 400

    get_db().execute(
        """INSERT INTO vendors(business,category,phone,area,price,capacity,description)
        VALUES(?,?,?,?,?,?,?)""",
        (
            x.get("business"), x.get("category"), x.get("phone"), x.get("area"),
            x.get("price"), x.get("capacity") or None, x.get("description")
        )
    )
    get_db().commit()
    return jsonify(ok=True, message="Application submitted for verification.")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        flash("Invalid password.")
    return render_template("login.html")


@app.get("/admin/logout")
def logout():
    session.clear()
    return redirect("/admin/login")


@app.get("/admin")
@admin_only
def admin():
    d = get_db()
    stats = {
        "enquiries": d.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0],
        "new": d.execute("SELECT COUNT(*) FROM enquiries WHERE status='New'").fetchone()[0],
        "vendors": d.execute("SELECT COUNT(*) FROM vendors").fetchone()[0],
        "pending": d.execute("SELECT COUNT(*) FROM vendors WHERE status='Pending'").fetchone()[0],
        "venues": d.execute("SELECT COUNT(*) FROM venues WHERE active=1").fetchone()[0],
    }
    return render_template(
        "admin.html",
        stats=stats,
        enquiries=d.execute("SELECT * FROM enquiries ORDER BY id DESC LIMIT 100").fetchall(),
        vendors=d.execute("SELECT * FROM vendors ORDER BY id DESC LIMIT 100").fetchall(),
        venues=d.execute("SELECT * FROM venues ORDER BY id DESC").fetchall(),
    )


@app.post("/admin/enquiry/<int:i>/status")
@admin_only
def enquiry_status(i):
    get_db().execute(
        "UPDATE enquiries SET status=? WHERE id=?",
        (request.form["status"], i)
    )
    get_db().commit()
    return redirect("/admin#enquiries")


@app.post("/admin/vendor/<int:i>/status")
@admin_only
def vendor_status(i):
    get_db().execute(
        "UPDATE vendors SET status=? WHERE id=?",
        (request.form["status"], i)
    )
    get_db().commit()
    return redirect("/admin#vendors")


@app.post("/admin/venue/add")
@admin_only
def venue_add():
    x = request.form
    get_db().execute(
        """INSERT INTO venues(name,area,price,capacity,rating,tag,description)
        VALUES(?,?,?,?,?,?,?)""",
        (
            x["name"], x["area"], x["price"], x["capacity"],
            x.get("rating") or 4.5, x.get("tag") or "Popular",
            x.get("description") or ""
        )
    )
    get_db().commit()
    return redirect("/admin#venues")


@app.post("/admin/venue/<int:i>/toggle")
@admin_only
def venue_toggle(i):
    get_db().execute("UPDATE venues SET active=1-active WHERE id=?", (i,))
    get_db().commit()
    return redirect("/admin#venues")


with app.app_context():
    init()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
