
# ============================================================
# FoodLink Rescue - Flask Backend
# ============================================================
# Run this file with: python app.py
# It will start a local server at http://127.0.0.1:5000
# ============================================================

from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import datetime

# Initialize the Flask application
app = Flask(__name__)

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
    Creates the 'food_listings' table if it doesn't already exist.
    Called once when the app starts up.
    """
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS food_listings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name   TEXT    NOT NULL,
            quantity    TEXT    NOT NULL,
            location    TEXT    NOT NULL,
            submitted_at TEXT   NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully.")


# -----------------------------------------------------------
# ROUTES
# -----------------------------------------------------------


@app.route("/", methods=["GET"])
def index():
    """
    Homepage – displays the food donation submission form.
    """
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    """
    Handles form submission from the homepage.
    Reads form data, validates it, stores it in the database,
    then redirects the user to the listings page.
    """
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


# -----------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------

if __name__ == "__main__":
    # Initialize the database (creates table if missing)
    init_db()

    # Run the development server
    # debug=True  → auto-reloads on code changes & shows detailed errors
    print("[START] FoodLink Rescue running at http://127.0.0.1:5000")
    app.run(debug=True)
