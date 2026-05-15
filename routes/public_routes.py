"""
routes/public_routes.py
────────────────────────
All public-facing website pages for Marvel Hospitals.
Landing page data (stats, doctors, departments) is loaded dynamically from DB.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import get_db
from models import Doctor, Department, Patient, Appointment
from sqlalchemy import func

public_bp = Blueprint("public", __name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def get_landing_data():
    """
    Returns a dict with stats + first 6 doctors + all departments.
    All counts come live from the database so the landing page
    always reflects real data.
    """
    try:
        db = next(get_db())

        # ── counts ────────────────────────────────────────────────
        total_doctors     = db.query(func.count(Doctor.doct_Id)).scalar() or 0
        total_patients    = db.query(func.count(Patient.patient_Id)).scalar() or 0
        total_departments = db.query(func.count(Department.dept_Id)).scalar() or 0
        total_appointments = 0
        try:
            total_appointments = db.query(func.count(Appointment.appt_Id)).scalar() or 0
        except Exception:
            pass

        stats = {
            "total_doctors":      total_doctors,
            "total_patients":     total_patients,
            "total_departments":  total_departments,
            "total_appointments": total_appointments,
        }

        # ── departments ───────────────────────────────────────────
        departments = db.query(Department).all()

        # ── doctors preview (first 6 for landing page) ────────────
        doctors = db.query(Doctor).limit(6).all()

        return stats, departments, doctors

    except Exception as exc:
        print(f"[public_routes] DB error: {exc}")
        return None, [], []


# ── Home ──────────────────────────────────────────────────────────────────────

@public_bp.route("/")
def home():
    stats, departments, doctors = get_landing_data()
    return render_template(
        "public/index.html",
        stats=stats,
        departments=departments,
        doctors=doctors,
    )


# ── About ─────────────────────────────────────────────────────────────────────

@public_bp.route("/about")
def about():
    stats, departments, _ = get_landing_data()
    return render_template("public/about.html", stats=stats, departments=departments)


# ── Services / Departments ────────────────────────────────────────────────────

@public_bp.route("/services")
def services():
    _, departments, _ = get_landing_data()
    return render_template("public/services.html", departments=departments)


# ── Doctors ───────────────────────────────────────────────────────────────────

@public_bp.route("/doctors")
def doctors():
    _, departments, doctors = get_landing_data()
    try:
        db = next(get_db())
        all_doctors = db.query(Doctor).limit(6).all()
    except Exception:
        all_doctors = doctors
    return render_template("public/doctors.html", doctors=all_doctors, departments=departments)


# ── JSON API: all doctors (used by landing-page dynamic grid) ──────────────────

@public_bp.route("/api/doctors")
def api_doctors():
    """
    Returns JSON list of doctors with department name.
    The landing page JS fetches this to populate the doctor cards.
    Supports ?name= and ?dept= query params for filtering.
    """
    name_q = request.args.get("name", "").strip().lower()
    dept_q = request.args.get("dept", "").strip().lower()

    try:
        db = next(get_db())
        query = db.query(Doctor, Department).outerjoin(
            Department, Doctor.dept_Id == Department.dept_Id
        )
        results = query.all()

        doctors_list = []
        for doc, dept in results:
            full_name = f"{doc.FName or ''} {doc.LName or ''}".strip().lower()
            dept_name = dept.dept_Name if dept else ""

            # Apply filters
            if name_q and name_q not in full_name:
                continue
            if dept_q and dept_q not in dept_name.lower():
                continue

            doctors_list.append({
                "doct_Id":          doc.doct_Id,
                "FName":            doc.FName or "",
                "LName":            doc.LName or "",
                "Gender":           doc.Gender or "",
                "dept_Name":        dept_name,
                "surgeon_Type":     doc.surgeon_Type or "",
                "experience_years": doc.experience_years or 0,
                "is_dept_head":     bool(doc.is_dept_head),
                "contact_No":       doc.contact_No or "",
                "notes":            doc.notes or "",
            })

        return jsonify({"doctors": doctors_list, "total": len(doctors_list)})

    except Exception as exc:
        print(f"[api/doctors] error: {exc}")
        return jsonify({"doctors": [], "total": 0, "error": str(exc)})


# ── JSON API: stats (used for real-time counter updates) ───────────────────────

@public_bp.route("/api/stats")
def api_stats():
    """Returns live hospital stats as JSON."""
    stats, _, _ = get_landing_data()
    if stats:
        return jsonify(stats)
    return jsonify({"total_doctors": 0, "total_patients": 0,
                    "total_departments": 0, "total_appointments": 0})


# ── Book Appointment ──────────────────────────────────────────────────────────

@public_bp.route("/appointment", methods=["GET", "POST"])
def appointment():
    _, departments, doctors = get_landing_data()
    if request.method == "POST":
        flash("Thank you! Our team will call within 2 hours to confirm your appointment.", "success")
        return redirect(url_for("public.appointment"))
    return render_template("public/appointment.html", departments=departments, doctors=doctors)


# ── Contact ───────────────────────────────────────────────────────────────────

@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name    = request.form.get("name", "").strip()
        email   = request.form.get("email", "").strip()
        phone   = request.form.get("phone", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if name and email and message:
            try:
                from models import ContactMessage
                db = next(get_db())
                msg = ContactMessage(
                    name=name,
                    email=email,
                    phone=phone or None,
                    subject=subject or None,
                    message=message,
                )
                db.add(msg)
                db.commit()
                flash("Message received! We will get back to you within 2 hours.", "success")
            except Exception as exc:
                print(f"[contact] DB save error: {exc}")
                flash("Sorry, something went wrong. Please try again.", "danger")
        else:
            flash("Please fill in all required fields.", "warning")

        return redirect(url_for("public.contact"))

    return render_template("public/contact.html")


# ── Patient Self-Registration ─────────────────────────────────────────────────

@public_bp.route("/patient-register")
def patient_register():
    return render_template("public/register_public.html")
