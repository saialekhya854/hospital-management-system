from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify, current_app
from sqlalchemy.orm import Session
from database import get_db
from models import User, Patient, AuditLog, Role
from config import SECRET_KEY
import datetime
from datetime import timezone
from werkzeug.security import check_password_hash, generate_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

common_bp = Blueprint("common", __name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(pwd: str) -> str:
    return generate_password_hash(pwd)

def log_action(db: Session, user_id, user_name, role, action, entity=None, detail=None):
    db.add(AuditLog(
        user_id=user_id, user_name=user_name, role=role,
        action=action, entity=entity, detail=detail,
        timestamp=datetime.datetime.now(timezone.utc)
    ))
    db.commit()

ROLE_MAP = {1: "Admin", 2: "Doctor", 3: "Receptionist", 4: "Nurse",
            5: "Patient", 6: "Helper", 7: "Auditor"}

ROLE_HOME = {
    "Admin"        : "/admin/dashboard",
    "Doctor"       : "/doctor/dashboard",
    "Receptionist" : "/receptionist/dashboard",
    "Patient"      : "/patient/profile",
    "Auditor"      : "/auditor/dashboard",
    "Nurse"        : "/doctor/calendar",
    "Helper"       : "/doctor/calendar",
}


# ── Login ─────────────────────────────────────────────────────────────────────

@common_bp.route("/dashboard")
def index():
    if "user_id" in session:
        role = session.get("role", "")
        return redirect(ROLE_HOME.get(role, "/login"))
    return redirect("/login")

@common_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        success = request.args.get("success")
        return render_template("common/login.html", success=success)

    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    db = next(get_db())
    user = db.query(User).filter(
    User.Email.ilike(email),
    User.is_active == True
    ).first()

    print("EMAIL:", email)
    print("PASSWORD SENT:", password)

    if not user:
        print("USER NOT FOUND")
        return render_template(
            "common/login.html",
            error="Invalid email or password."
        )

    print("HASH STORED:", user.Password)
    print("PASSWORD MATCH:",
        check_password_hash(user.Password, password))

    if not check_password_hash(user.Password, password):
        return render_template(
            "common/login.html",
            error="Invalid email or password."
        )

    role_name = ROLE_MAP.get(user.Role_ID, "Unknown")
    initials  = "".join(w[0].upper() for w in (user.Name or "U").split()[:2])

    session["user_id"]       = user.User_ID
    session["user_name"]     = user.Name
    session["user_initials"] = initials
    session["role"]          = role_name
    session["role_id"]       = user.Role_ID
    session["entity_id"]     = user.Linked_Entity_ID

    log_action(db, user.User_ID, user.Name, role_name, "LOGIN",
               entity="Session", detail=f"Login from {request.remote_addr}")

    return redirect(ROLE_HOME.get(role_name, "/login"))

# ── Logout ────────────────────────────────────────────────────────────────────

@common_bp.route("/logout")
def logout():
    db = next(get_db())
    if "user_id" in session:
        log_action(db, session["user_id"], session.get("user_name",""),
                   session.get("role",""), "LOGOUT", entity="Session")
    session.clear()
    return redirect("/login")

# ── Self-register (Patient) ───────────────────────────────────────────────────

@common_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("public/register.html")

    data = request.form

    fname    = data.get("fname", "").strip()
    lname    = data.get("lname", "").strip()
    dob      = data.get("dob")
    gender   = data.get("gender", "")
    phone    = data.get("phone", "").strip()
    address  = data.get("address", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "")

    # Required validation
    if not all([fname, lname, dob, gender, phone, email, password]):
        return render_template(
            "public/register.html",
            error="Please fill all required fields."
        )

    db = next(get_db())

    # Check existing email
    existing_user = db.query(User).filter(
        User.Email.ilike(email)
    ).first()

    if existing_user:
        return render_template(
            "public/register.html",
            error="Email already registered."
        )

    # Password validation
    if len(password) < 6:
        return render_template(
            "public/register.html",
            error="Password must be at least 6 characters."
        )

    # DOB validation
    try:
        dob_date = datetime.date.fromisoformat(dob)

    except ValueError:
        return render_template(
            "public/register.html",
            error="Invalid date of birth."
        )

    try:

        # Create patient
        patient = Patient(
            FName=fname,
            LName=lname,
            Gender=gender,
            Date_Of_Birth=dob_date,
            contact_No=phone,
            pt_Address=address,
            blood_group=data.get("blood_group"),
            email=email
        )

        db.add(patient)
        db.flush()

        # Create user
        user = User(
            Email=email,
            Password=hash_password(password),
            Name=f"{fname} {lname}",
            Role_ID=5,
            Linked_Entity_ID=patient.patient_Id,
            is_active=True
        )

        db.add(user)
        db.flush()

        # Link patient to user
        patient.User_ID = user.User_ID

        db.commit()

        return redirect(url_for(
            "common.login",
            success="Registration successful. Please login."
        ))

    except Exception as e:
        db.rollback()
        print("REGISTER ERROR:", e)

        return render_template(
            "public/register.html",
            error="Registration failed."
        )

# ── Change password (API) ─────────────────────────────────────────────────────

@common_bp.route("/api/auth/change-password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return jsonify({"detail": "Not authenticated"}), 401

    body    = request.get_json() or {}
    curr    = body.get("current_password","")
    new_pwd = body.get("new_password","")

    if not curr or not new_pwd:
        return jsonify({"detail": "Both fields required"}), 400
    if len(new_pwd) < 8:
        return jsonify({"detail": "Password must be at least 8 characters"}), 400

    db   = next(get_db())
    user = db.query(User).filter(User.User_ID == session["user_id"]).first()
    if not user or not check_password_hash(user.Password, curr):
        return jsonify({"detail": "Current password is incorrect"}), 400

    user.Password = hash_password(new_pwd)
    db.commit()
    log_action(db, user.User_ID, user.Name, session.get("role",""), "CHANGE_PASSWORD")
    return jsonify({"ok": True})

# ── Forgot Password ───────────────────────────────────────────────────────────

def _get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

@common_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("common/forgot_password.html")

    email = request.form.get("email", "").strip()
    db    = next(get_db())
    user  = db.query(User).filter(User.Email.ilike(email), User.is_active == True).first()

    # Always show success to prevent user enumeration
    if user:
        s     = _get_serializer()
        token = s.dumps(email, salt="password-reset-salt")
        link  = url_for("common.reset_password", token=token, _external=True)
        try:
            from config import mail
            from flask_mail import Message
            msg = Message(
                subject="Password Reset — Marvel Hospitals",
                recipients=[email],
                body=(
                    f"Hello {user.Name},\n\n"
                    f"Click the link below to reset your password (valid for 30 minutes):\n\n"
                    f"{link}\n\n"
                    f"If you did not request this, please ignore this email.\n\n"
                    f"Regards,\nMarvel Hospitals Team"
                )
            )
            mail.send(msg)
        except Exception as e:
            print(f"[ForgotPassword] Email send failed: {e}")

    return render_template("common/forgot_password.html",
                           success="If that email is registered, a reset link has been sent.")


# ── Reset Password ────────────────────────────────────────────────────────────

@common_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    if request.method == "GET":
        return render_template("common/reset_password.html")

    # Get form data
    email   = request.form.get("email")
    new_pwd = request.form.get("password")
    confirm = request.form.get("confirm_password")

    # Validations
    if not email:
        return render_template("common/reset_password.html",
                               error="Email is required.")

    if len(new_pwd) < 8:
        return render_template("common/reset_password.html",
                               error="Password must be at least 8 characters.")

    if new_pwd != confirm:
        return render_template("common/reset_password.html",
                               error="Passwords do not match.")

    # Update password
    db = next(get_db())
    user = db.query(User).filter(User.Email.ilike(email)).first()

    if not user:
        return render_template("common/reset_password.html",
                               error="User not found.")

    user.Password = hash_password(new_pwd)
    db.commit()

    log_action(
        db,
        user.User_ID,
        user.Name,
        ROLE_MAP.get(user.Role_ID, ""),
        "PASSWORD_RESET",
        entity="Session",
        detail="Password reset via form"
    )

    return redirect(url_for("common.login",
                            success="Password updated successfully"))