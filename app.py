
# ============================================================
# FoodLink Rescue - Flask Backend
# ============================================================
# Run this file with: python app.py
# It will start a local server at http://127.0.0.1:5000
# ============================================================

from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import datetime

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = "foodlink_super_secret_key"

# -----------------------------------------------------------
# DATABASE CONFIGURATION
# -----------------------------------------------------------
# SQLite database file will be created in the same directory
DATABASE = "foodlink.db"


def get_db_connection():
    """
    Opens a connection to the SQLite database.
    Returns a connection object with row_factory set so
    that rows behave like dictionaries (accessible by column name).
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Access columns by name, e.g. row["food_name"]
    return conn


def init_db():
    """
    Creates the database and table if they do not exist.
    Also runs migrations to add the 'status' column if needed.
    """
    conn = sqlite3.connect("foodlink.db")
    cursor = conn.cursor()

    # Used food_listings instead of donations to ensure existing routes don't break
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS food_listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_name TEXT,
        quantity TEXT,
        location TEXT,
        submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Check if 'status' and 'created_by' columns exist (Migration)
    cursor.execute("PRAGMA table_info(food_listings)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'status' not in columns:
        cursor.execute("ALTER TABLE food_listings ADD COLUMN status TEXT DEFAULT 'available'")
        print("[MIGRATION] Added 'status' column to food_listings table.")
    if 'created_by' not in columns:
        cursor.execute("ALTER TABLE food_listings ADD COLUMN created_by TEXT")
        print("[MIGRATION] Added 'created_by' column to food_listings table.")

    conn.commit()
    conn.close()
    print("[OK] Database verified.")

# Call this function when the app starts (essential for Gunicorn deployments)
init_db()


# -----------------------------------------------------------
# ROUTES
# -----------------------------------------------------------


@app.route("/", methods=["GET"])
def index():
    """
    Homepage – displays the food donation submission form.
    Redirects NGOs to the view page automatically.
    """
    if not session.get("role"):
        return redirect("/login")
    if session.get("role") == "ngo":
        return redirect(url_for("view"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Simple login route handling both GET (show form) and POST (process form).
    """
    if request.method == "POST":
        role = request.form.get("role")
        user_name = request.form.get("user_name", "").strip() or "Guest"
        if role in ["donor", "ngo"]:
            session["role"] = role
            session["user_name"] = user_name
            return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/switch-role")
def switch_role():
    current_role = session.get("role")
    if current_role == "donor":
        session["role"] = "ngo"
    elif current_role == "ngo":
        session["role"] = "donor"
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/set_role/<role>")
def set_role(role):
    """
    Sets the user's role in the session and redirects accordingly.
    """
    if role in ["donor", "ngo"]:
        session["role"] = role
    elif role == "clear":
        session.pop("role", None)
        return redirect(url_for("index"))
        
    if session.get("role") == "ngo":
        return redirect(url_for("view"))
    return redirect(url_for("index"))


@app.route("/submit", methods=["POST"])
def submit():
    """
    Handles form submission from the homepage.
    Reads form data, validates it, stores it in the database,
    then redirects the user to the listings page.
    """
    # NGOs should not be able to submit donations
    if session.get("role") == "ngo":
        return redirect(url_for("view"))

    # Read form fields (strip whitespace)
    food_name = request.form.get("food_name", "").strip()
    quantity = request.form.get("quantity", "").strip()
    location = request.form.get("location", "").strip()

    # Basic validation – make sure no field is empty
    if not food_name or not quantity or not location:
        error = "⚠️ All fields are required. Please fill in every field."
        return render_template("index.html", error=error)

    # Record the current timestamp
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Insert the new record into the database
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO food_listings (food_name, quantity, location, submitted_at, created_by) VALUES (?, ?, ?, ?, ?)",
        (food_name, quantity, location, submitted_at, session.get('user_name', 'Guest')),
    )
    conn.commit()
    conn.close()

    print(f"[NEW] Listing added: {food_name} | {quantity} | {location}")

    # Redirect to the view page so the user can see all listings
    return redirect(url_for("view"))


@app.route("/view", methods=["GET"])
def view():
    """
    Listings page – fetches all food donations from the database
    and displays them in a table, newest first.
    """
    conn = get_db_connection()
    listings = conn.execute(
        "SELECT * FROM food_listings ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template("view.html", listings=listings)


@app.route("/delete/<int:listing_id>", methods=["POST"])
def delete(listing_id):
    """
    Deletes a single food listing by its ID.
    Useful for NGOs to mark food as 'claimed / collected'.
    """
    conn = get_db_connection()
    conn.execute("DELETE FROM food_listings WHERE id = ?", (listing_id,))
    conn.commit()
    conn.close()

    print(f"[DEL] Listing #{listing_id} deleted (marked as collected).")
    return redirect(url_for("view"))


@app.route("/claim/<int:listing_id>", methods=["POST"])
def claim(listing_id):
    """
    Updates status to 'claimed' by an NGO.
    """
    if session.get("role") != "ngo":
        return redirect(url_for("view"))
    conn = get_db_connection()
    conn.execute("UPDATE food_listings SET status = 'claimed' WHERE id = ?", (listing_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("view"))


@app.route("/pickup/<int:listing_id>", methods=["POST"])
def pickup(listing_id):
    """
    Updates status to 'picked_up' by an NGO.
    """
    if session.get("role") != "ngo":
        return redirect(url_for("view"))
    conn = get_db_connection()
    conn.execute("UPDATE food_listings SET status = 'picked_up' WHERE id = ?", (listing_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("view"))


@app.context_processor
def inject_notifications():
    """
    Provides real-time notifications to all templates based on the current user's role.
    """
    role = session.get('role')
    if not role:
        return dict(notifications=[], has_unread=False, unread_count=0)
        
    conn = get_db_connection()
    try:
        # Fetch the latest 10 items for notifications
        recent = conn.execute("SELECT id, food_name, status, submitted_at, created_by FROM food_listings ORDER BY id DESC LIMIT 10").fetchall()
    except sqlite3.OperationalError:
        recent = []
    finally:
        conn.close()
    
    notifications = []
    current_user = session.get('user_name', 'Guest')
    for item in recent:
        status = item['status']
        created_by = item['created_by']
        if role == 'ngo':
            # NGOs only receive new donation notifications
            if status != 'available':
                continue
            icon = '📢'
            msg = f"New food donation available: {item['food_name']}"
        else:  # donor
            # Skip items not created by this donor, or items with unknown creator
            if not created_by or created_by != current_user:
                continue
            if status == 'claimed':
                icon = '✅'
                msg = f"NGO accepted your donation: {item['food_name']}"
            elif status == 'picked_up':
                icon = '🎉'
                msg = f"Food successfully collected: {item['food_name']}"
            else:
                continue
        
        notifications.append({
            'id': item['id'],
            'status': status,
            'message': msg,
            'icon': icon,
            'timestamp': item['submitted_at']
        })
    
    # Unread calculation differs by role
    if role == 'ngo':
        # NGOs: track by highest ID (new items)
        highest_id = max([n['id'] for n in notifications]) if notifications else 0
        last_seen = session.get('last_seen_notif_id', 0)
        has_unread = last_seen < highest_id
        unread_count = sum(1 for n in notifications if n['id'] > last_seen)
    else:
        # Donors: track by whether there are status changes (notifications exist)
        # This handles the case where existing item status changes (ID doesn't change)
        has_unread = len(notifications) > 0
        unread_count = len(notifications)

    return dict(notifications=notifications, has_unread=has_unread, unread_count=unread_count)

@app.route("/notifications", methods=["GET"])
def notifications_page():
    """
    Displays the notifications and clears the unread state.
    """
    # Calculate highest id to mark as read
    conn = get_db_connection()
    try:
        latest = conn.execute("SELECT id FROM food_listings ORDER BY id DESC LIMIT 1").fetchone()
        if latest:
            session['last_seen_notif_id'] = latest['id']
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()
    return render_template("notifications.html")


# -----------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------

if __name__ == "__main__":

    # Run the development server
    # debug=True  → auto-reloads on code changes & shows detailed errors
    print("[START] FoodLink Rescue running at http://127.0.0.1:5000")
    app.run(debug=True)
