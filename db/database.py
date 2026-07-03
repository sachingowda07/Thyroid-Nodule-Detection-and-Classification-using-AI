import sqlite3
import os

DB_NAME = "thyroiddetect.db"


# -------------------------------------------------------
# Initialize database
# -------------------------------------------------------
def init_db():
    os.makedirs("db", exist_ok=True)

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # ---------------- USERS TABLE ----------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            dob TEXT,
            age TEXT,
            email TEXT UNIQUE,
            phone TEXT UNIQUE,
            password TEXT
        )
    """)

    # ---------------- PATIENT REPORT TABLE ----------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS patient_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT,
            age INTEGER,
            gender TEXT,
            phone TEXT,
            email TEXT,
            image_path TEXT,
            prediction TEXT,
            confidence REAL,
            date_time TEXT
        )
    """)

    conn.commit()
    conn.close()


# -------------------------------------------------------
# Create a new user
# -------------------------------------------------------
def create_user(name, dob, age, email, phone, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO users(name, dob, age, email, phone, password)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, dob, age, email, phone, password))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()

# -------------------------------------------------------
# Login: verify user
# -------------------------------------------------------
def verify_login(identifier, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT id, name FROM users
        WHERE (email=? OR phone=?) AND password=?
    """, (identifier, identifier, password))

    row = c.fetchone()
    conn.close()

    if row:
        return row[0], row[1]
    return None, None


# -------------------------------------------------------
# Get user by ID
# -------------------------------------------------------
def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()

    conn.close()
    return user


# -------------------------------------------------------
# SAVE PATIENT REPORT
# -------------------------------------------------------
def save_patient_report(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        INSERT INTO patient_reports
        (patient_name, age, gender, phone, email, image_path,
         prediction, confidence, date_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["patient_name"],
        data["age"],
        data["gender"],
        data["phone"],
        data["email"],
        data["image_path"],
        data["prediction"],
        data["confidence"],
        data["date_time"]
    ))

    conn.commit()
    conn.close()


# -------------------------------------------------------
# SEARCH REPORTS (History page)
# -------------------------------------------------------
def search_reports(keyword):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT * FROM patient_reports
        WHERE phone LIKE ? OR email LIKE ? OR patient_name LIKE ?
        ORDER BY id DESC
    """, (
        f"%{keyword}%",
        f"%{keyword}%",
        f"%{keyword}%"
    ))

    rows = c.fetchall()
    conn.close()
    return rows


# -------------------------------------------------------
# GET ALL REPORTS FOR LOGGED-IN USER
# -------------------------------------------------------
def get_user_reports(phone):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT patient_name, age, gender, phone, email, image_path,
               prediction, confidence, date_time
        FROM patient_reports
        WHERE phone = ?
        ORDER BY id DESC
    """, (phone,))

    rows = c.fetchall()
    conn.close()
    return rows


# -------------------------------------------------------
# USER DASHBOARD STATISTICS
# -------------------------------------------------------
def get_user_stats(phone):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Total uploads
    c.execute("""
        SELECT COUNT(*) FROM patient_reports WHERE phone = ?
    """, (phone,))
    total_reports = c.fetchone()[0]

    # Most common prediction
    c.execute("""
        SELECT prediction, COUNT(prediction) AS count
        FROM patient_reports
        WHERE phone = ?
        GROUP BY prediction
        ORDER BY count DESC
        LIMIT 1
    """, (phone,))
    
    row = c.fetchone()
    most_common = row[0] if row else "None"

    conn.close()

    return {
        "total_reports": total_reports,
        "most_common_prediction": most_common
    }
