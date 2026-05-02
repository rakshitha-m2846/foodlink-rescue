
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
    
    # Check if 'status' column exists (Migration)
    cursor.execute("PRAGMA table_info(food_listings)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'status' not in columns:
        cursor.execute("ALTER TABLE food_listings ADD COLUMN status TEXT DEFAULT 'available'")
        print("[MIGRATION] Added 'status' column to food_listings table.")

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
    if session.get("role") == "ngo":
        return redirect(url_for("view"))
    return render_template("index.html")


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
        "INSERT INTO food_listings (food_name, quantity, location, submitted_at) VALUES (?, ?, ?, ?)",
        (food_name, quantity, location, submitted_at),
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
        return dict(notifications=[])
        
    conn = get_db_connection()
    try:
        # Fetch the latest 10 items for notifications
        recent = conn.execute("SELECT id, food_name, status FROM food_listings ORDER BY id DESC LIMIT 10").fetchall()
    except sqlite3.OperationalError:
        recent = []
    finally:
        conn.close()
    
    notifications = []
    for item in recent:
        status = item['status']
        if role == 'ngo':
            if status == 'available':
                msg = f"📢 New food donation available: {item['food_name']}"
            elif status == 'claimed':
                msg = f"✅ Donation confirmed: {item['food_name']}"
            elif status == 'picked_up':
                msg = f"🎉 Pickup completed: {item['food_name']}"
        else: # donor
            if status == 'available':
                msg = f"📦 Waiting for NGO to accept: {item['food_name']}"
            elif status == 'claimed':
                msg = f"✅ NGO accepted your donation: {item['food_name']}"
            elif status == 'picked_up':
                msg = f"🎉 Donation completed successfully: {item['food_name']}"
        
        notifications.append({
            'id': item['id'],
            'status': status,
            'message': msg
        })
    
    highest_id = max([n['id'] for n in notifications]) if notifications else 0
    has_unread = session.get('last_seen_notif_id', 0) < highest_id

    return dict(notifications=notifications, has_unread=has_unread)

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
