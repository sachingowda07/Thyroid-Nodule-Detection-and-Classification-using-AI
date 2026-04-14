import os
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from predict import predict
from db.database import (
    init_db,
    verify_login,
    create_user,
    save_patient_report,
    search_reports,
    get_user_by_id,
    get_user_reports,
    get_user_stats
)

app = Flask(__name__)
app.secret_key = "thyroiddetect_secret_key_123"

# FOLDERS
UPLOAD_FOLDER = "static/uploads"
PROFILE_FOLDER = "static/profile"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_FOLDER, exist_ok=True)

# Initialize DB
init_db()

# =====================================================
# GMAIL SMTP — auto email sending for report
# =====================================================
SMTP_EMAIL = "psshreyas007@gmail.com"
SMTP_PASSWORD = "mkfndgwwqxivyuye"   # App password (no spaces)

def send_report_email(to_email, patient_name, prediction, confidence, date_time):
    try:
        subject = "Your Thyroid AI Report - ThyroidDetect"
        body = f"""
        Dear {patient_name},

        Your thyroid scan has been successfully analyzed.

        -----------------------------
        AI DIAGNOSIS REPORT
        -----------------------------
        Result: {prediction}
        Confidence: {confidence}%
        Date: {date_time}

        NOTE: This report is AI-generated.
        Please consult a medical professional for confirmation.

        Regards,
        ThyroidDetect Team
        """

        msg = MIMEMultipart()
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        server.quit()

        print("✔ Email sent successfully!")
    except Exception as e:
        print("❌ Email sending failed:", str(e))


# =====================================================
# HOME PAGE
# =====================================================
@app.route("/")
def home_page():
    username = session.get("name")
    return render_template("home.html", active_page="home", username=username)


# =====================================================
# LOGIN
# =====================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form["identifier"]
        password = request.form["password"]

        user_id, name = verify_login(identifier, password)

        if user_id:
            session["user_id"] = user_id
            session["name"] = name
            return redirect("/")

        return render_template("login.html", error="Invalid login!", active_page="login")

    return render_template("login.html", active_page="login")


# =====================================================
# REGISTER
# =====================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        dob = request.form["dob"]
        age = request.form["age"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]

        create_user(name, dob, age, email, phone, password)
        return redirect("/login")

    return render_template("register.html", active_page="register")


# =====================================================
# UPLOAD + PREDICTION + SAVE + EMAIL
# =====================================================
@app.route("/upload", methods=["GET", "POST"])
def upload_page():

    if request.method == "POST":

        # Patient Info
        patient_name = request.form["patient_name"]
        age = request.form["age"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        email = request.form["email"]

        # Image Upload
        image = request.files["image"]
        if not image:
            return render_template("upload.html", error="Please upload an image", active_page="upload")

        filename = image.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        image.save(filepath)

        # Prediction
        result = predict(filepath)

        if result == "Not a thyroid ultrasound image":
            date_time = datetime.now().strftime("%d %b %Y, %I:%M %p")
            # also save last_report so View Last Report doesn't crash
            session["last_report"] = {
                "image_path": filepath,
                "label": "Invalid Image",
                "confidence": 0,
                "explanation": "This is not a thyroid ultrasound image.",
                "patient_name": patient_name,
                "age": age,
                "gender": gender,
                "phone": phone,
                "email": email,
                "date_time": date_time
            }
            return render_template("result.html",
                                   image_path=filepath,
                                   label="Invalid Image",
                                   confidence=0,
                                   explanation="This is not a thyroid ultrasound image.",
                                   patient_name=patient_name,
                                   age=age,
                                   gender=gender,
                                   phone=phone,
                                   email=email,
                                   date_time=date_time,
                                   active_page="upload")

        prediction, confidence = result
        date_time = datetime.now().strftime("%d %b %Y, %I:%M %p")

        # Save to DB
        save_patient_report({
            "patient_name": patient_name,
            "age": age,
            "gender": gender,
            "phone": phone,
            "email": email,
            "image_path": filepath,
            "prediction": prediction,
            "confidence": confidence,
            "date_time": date_time
        })

        # SEND EMAIL
        send_report_email(email, patient_name, prediction, confidence, date_time)

        # Save LAST REPORT in session (for View Last Report from profile)
        session["last_report"] = {
            "image_path": filepath,
            "label": prediction,
            "confidence": confidence,
            "explanation": "AI-based thyroid classification",
            "patient_name": patient_name,
            "age": age,
            "gender": gender,
            "phone": phone,
            "email": email,
            "date_time": date_time
        }

        # Show Result Page
        return render_template(
            "result.html",
            image_path=filepath,
            label=prediction,
            confidence=confidence,
            explanation="AI-based thyroid classification",
            patient_name=patient_name,
            age=age,
            gender=gender,
            phone=phone,
            email=email,
            date_time=date_time,
            active_page="upload"
        )

    return render_template("upload.html", active_page="upload")


# =====================================================
# FULL REPORT PAGE (used by View Full Report button)
# =====================================================
@app.route("/report")
def report():
    return render_template(
        "report.html",
        image_path=request.args.get("image_path"),
        label=request.args.get("label"),
        confidence=request.args.get("confidence"),
        explanation=request.args.get("explanation"),
        patient_name=request.args.get("patient_name"),
        age=request.args.get("age"),
        gender=request.args.get("gender"),
        phone=request.args.get("phone"),
        email=request.args.get("email"),
        date_time=request.args.get("date_time"),
        active_page="report"
    )


# =====================================================
# VIEW LAST REPORT (from Profile page)
# =====================================================
@app.route("/last_report")
def last_report():
    data = session.get("last_report")
    if not data:
        return redirect(url_for("upload_page"))
    # reuse same report page
    return redirect(url_for("report", **data))


# =====================================================
# HISTORY PAGE
# =====================================================
@app.route("/history", methods=["GET", "POST"])
def history():
    results = []

    if request.method == "POST":
        keyword = request.form["keyword"]
        results = search_reports(keyword)

    return render_template("history.html", results=results, active_page="history")


# =====================================================
# PROFILE IMAGE UPLOAD
# =====================================================
@app.route("/upload_profile_image", methods=["POST"])
def upload_profile_image():
    if "user_id" not in session:
        return redirect("/login")

    image = request.files.get("profile_image")
    if not image or image.filename == "":
        return redirect("/profile")

    filename = f"user_{session['user_id']}.jpg"
    filepath = os.path.join(PROFILE_FOLDER, filename)
    image.save(filepath)

    # store only in session (enough for demo)
    session["profile_image"] = filepath

    return redirect("/profile")


# =====================================================
# PROFILE PAGE
# =====================================================
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")

    user = get_user_by_id(session["user_id"])

    user_data = {
        "name": user[1],
        "dob": user[2],
        "age": user[3],
        "email": user[4],
        "phone": user[5]
    }

    reports = get_user_reports(user_data["phone"])
    stats = get_user_stats(user_data["phone"])

    return render_template("profile.html",
                           user=user_data,
                           reports=reports,
                           stats=stats,
                           active_page="profile")


# =====================================================
# STATIC PAGES
# =====================================================
@app.route("/diseases")
def diseases():
    return render_template("diseases.html", active_page="diseases")


@app.route("/about")
def about():
    return render_template("about.html", active_page="about")


@app.route("/contact")
def contact():
    return render_template("contact.html", active_page="contact")


# =====================================================
# LOGOUT
# =====================================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =====================================================
# RUN SERVER
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)
