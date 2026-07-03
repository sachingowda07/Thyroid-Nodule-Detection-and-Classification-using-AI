import os
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime

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

UPLOAD_FOLDER = "static/uploads"
PROFILE_FOLDER = "static/profile"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_FOLDER, exist_ok=True)

init_db()


# =====================================================
# GMAIL SMTP - Auto Email Sending
# =====================================================

SMTP_EMAIL = "sachingowda6325@gmail.com"
SMTP_PASSWORD = "ocpgcspletbhmnvz"   # Gmail App Password, no spaces


def send_report_email(to_email, patient_name, prediction, confidence, date_time):
    try:
        subject = "Your Thyroid AI Report - ThyroidDetect"

        body = f"""
Dear {patient_name},

Your thyroid scan has been successfully analyzed.

----------------------------
AI DIAGNOSIS REPORT
----------------------------
Patient Name : {patient_name}
Result       : {prediction}
Confidence   : {confidence:.2f}%
Date         : {date_time}

NOTE:
This report is AI-generated.
Please consult a medical professional for confirmation.

Regards,
ThyroidDetect Team
"""

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        server.quit()

        print("✅ Email Sent Successfully")
        return True

    except Exception as e:
        print("❌ Email Error:", e)
        return False


@app.route("/")
def home_page():
    username = session.get("name")
    return render_template("home.html", active_page="home", username=username)


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

        return render_template("login.html", error="Invalid login credentials!", active_page="login")

    return render_template("login.html", active_page="login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        dob = request.form["dob"]
        age = request.form["age"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]

        success = create_user(name, dob, age, email, phone, password)

        if success:
            user_id, user_name = verify_login(email, password)

            session["user_id"] = user_id
            session["name"] = user_name

            return redirect(url_for("home_page"))

        return render_template(
            "register.html",
            error="Email or Phone Number already exists!",
            active_page="register"
        )

    return render_template("register.html", active_page="register")


@app.route("/upload", methods=["GET", "POST"])
def upload_page():
    if request.method == "POST":

        patient_name = request.form["patient_name"]
        age = request.form["age"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        email = request.form["email"]

        image = request.files["image"]

        if not image:
            return render_template("upload.html", error="Please upload an image!", active_page="upload")

        filename = image.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        image.save(filepath)

        result = predict(filepath)

        if result == "Not a thyroid ultrasound image":
            return render_template(
                "result.html",
                image_path=filepath,
                label="Invalid Image",
                confidence=0,
                explanation="This is not a thyroid ultrasound image.",
                active_page="upload"
            )

        prediction, confidence = result
        date_time = datetime.now().strftime("%d %b %Y, %I:%M %p")

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

        send_report_email(
            email,
            patient_name,
            prediction,
            confidence,
            date_time
        )

        return render_template(
            "result.html",
            image_path=filepath,
            label=prediction,
            confidence=confidence,
            explanation="AI-based thyroid classification",
            patient_name=patient_name,
            age=age,
            gender=gender,
            date_time=date_time,
            phone=phone,
            email=email,
            active_page="upload"
        )

    return render_template("upload.html", active_page="upload")


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


@app.route("/history", methods=["GET", "POST"])
def history():
    results = []

    if request.method == "POST":
        keyword = request.form["keyword"]
        results = search_reports(keyword)

    return render_template("history.html", results=results, active_page="history")


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

    return render_template(
        "profile.html",
        user=user_data,
        reports=reports,
        stats=stats,
        active_page="profile"
    )


@app.route("/diseases")
def diseases():
    return render_template("diseases.html", active_page="diseases")


@app.route("/about")
def about():
    return render_template("about.html", active_page="about")


@app.route("/contact")
def contact():
    return render_template("contact.html", active_page="contact")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
