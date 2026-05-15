"""
Auditor Routes — Read-Only Oversight Module
Provides dashboard analytics, audit logs, appointment/patient/doctor/billing views.
Accessible only by users with role = 'Auditor'
"""

from flask import Blueprint, render_template, request, session, redirect, jsonify
from flask import Response
from sqlalchemy import func, text, extract, cast, Date
import datetime
import math

from flask import make_response
import csv
import io

from database import get_db_ctx
from models import (
    User, Doctor, Department, Patient, Appointment,
    Bill, Payment, AuditLog, MedicalRecord, BillItem,
    TreatmentCatalogue
)
from config import PAGINATION

auditor_bp = Blueprint("auditor", __name__, url_prefix="/auditor")


# ─────────────────────────────────────────────────────────────
#  Auth guard
# ─────────────────────────────────────────────────────────────
def require_auditor():
    if session.get("role") != "Auditor":
        return redirect("/login")
    return None


# ═════════════════════════════════════════════════════════════
#  PAGE ROUTES
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/dashboard")
def dashboard():
    g = require_auditor()
    if g: return g
    return render_template("auditor/dashboard.html")


@auditor_bp.route("/appointments")
def appointments():
    g = require_auditor()
    if g: return g
    return render_template("auditor/appointments.html")


@auditor_bp.route("/patients")
def patients():
    g = require_auditor()
    if g: return g
    return render_template("auditor/patients.html")


@auditor_bp.route("/doctors")
def doctors():
    g = require_auditor()
    if g: return g
    return render_template("auditor/doctors.html")


@auditor_bp.route("/billing")
def billing():
    g = require_auditor()
    if g: return g
    return render_template("auditor/billing.html")


@auditor_bp.route("/audit-logs")
def audit_logs():
    g = require_auditor()
    if g: return g
    return render_template("auditor/audit_logs.html")


# ═════════════════════════════════════════════════════════════
#  API — KPI Cards
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/kpis")
def api_kpis():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        today = datetime.date.today()
        month_start = today.replace(day=1)

        total_patients = db.query(func.count(Patient.patient_Id)).scalar() or 0

        # Total appointments (ALL TIME)
        total_appointments = db.query(func.count(Appointment.appointment_Id)).scalar() or 0

        # Today's appointments
        appts_today = db.query(func.count(Appointment.appointment_Id))\
            .filter(Appointment.appointment_Date == today).scalar() or 0

        # Monthly appointments
        month_start = today.replace(day=1)

        monthly_appointments = db.query(func.count(Appointment.appointment_Id))\
            .filter(Appointment.appointment_Date >= month_start)\
            .scalar() or 0

        month_revenue = db.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).filter(
            Payment.paid_at != None,
            Payment.paid_at >= month_start,
            func.lower(Payment.payment_status) == "success"
        ).scalar() or 0
        # Total revenue (ALL TIME)
        total_revenue = db.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).filter(
            Payment.paid_at != None,
            func.lower(Payment.payment_status) == "success"
        ).scalar() or 0
        total_doctors = db.query(func.count(Doctor.doct_Id)).scalar() or 0

        pending_bills = db.query(func.count(Bill.bill_id))\
            .filter(Bill.status.in_(["Pending", "Partial"])).scalar() or 0

        return jsonify({
            "total_patients": total_patients,
            "appts_today": appts_today,
            "total_appointments": total_appointments,
            "monthly_appointments": monthly_appointments,
            "month_revenue": float(month_revenue),
            "total_revenue": float(total_revenue),
            "total_doctors": total_doctors,
            "pending_bills": pending_bills,
        })


# ═════════════════════════════════════════════════════════════
#  API — Appointments Over Time (last 30 days)
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/appointments-over-time")
def api_appointments_over_time():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        today = datetime.date.today()
        thirty_ago = today - datetime.timedelta(days=29)

        rows = db.query(
            Appointment.appointment_Date,
            func.count(Appointment.appointment_Id)
        ).filter(
            Appointment.appointment_Date >= thirty_ago
        ).group_by(Appointment.appointment_Date)\
         .order_by(Appointment.appointment_Date).all()

        date_map = {str(r[0]): r[1] for r in rows}
        labels, values = [], []
        for i in range(30):
            d = thirty_ago + datetime.timedelta(days=i)
            labels.append(d.strftime("%d %b"))
            values.append(date_map.get(str(d), 0))

        return jsonify({"labels": labels, "values": values})


# ═════════════════════════════════════════════════════════════
#  API — Peak Booking Days of the Week
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/peak-booking-days")
def api_peak_booking_days():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(
            func.extract("dow", Appointment.appointment_Date).label("dow"),
            func.count(Appointment.appointment_Id).label("cnt")
        ).group_by("dow").order_by("dow").all()

        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        day_map = {int(r[0]): r[1] for r in rows}
        labels = day_names
        values = [day_map.get(i, 0) for i in range(7)]

        return jsonify({"labels": labels, "values": values})


# ═════════════════════════════════════════════════════════════
#  API — Appointment Status Breakdown
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/appointment-status")
def api_appointment_status():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(
            func.lower(Appointment.appointment_status).label("status"),
            func.count(Appointment.appointment_Id)
        ).group_by(
            func.lower(Appointment.appointment_status)
        ).all()

        labels = []
        values = []

        for r in rows:
            # Convert to clean format: checked-in → Checked In
            clean_label = (r.status or "unknown").replace("-", " ").title()
            labels.append(clean_label)
            values.append(r[1])

        return jsonify({
            "labels": labels,
            "values": values
        })


# ═════════════════════════════════════════════════════════════
#  API — Doctor Performance (appointment count per doctor)
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/doctor-performance")
def api_doctor_performance():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(
            (Doctor.FName + " " + Doctor.LName).label("name"),
            func.count(Appointment.appointment_Id).label("cnt")
        ).outerjoin(
            Appointment, Appointment.doct_Id == Doctor.doct_Id
        ).group_by(Doctor.doct_Id, Doctor.FName, Doctor.LName)\
         .order_by(func.count(Appointment.appointment_Id).desc())\
         .limit(10).all()

        return jsonify({
            "labels": [r[0] for r in rows],
            "values": [r[1] for r in rows]
        })


# ═════════════════════════════════════════════════════════════
#  API — Top Diagnoses
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/top-diagnoses")
def api_top_diagnoses():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(
            MedicalRecord.diagnosis,
            func.count(MedicalRecord.record_Id).label("cnt")
        ).filter(
            MedicalRecord.diagnosis != None,
            MedicalRecord.diagnosis != ""
        ).group_by(MedicalRecord.diagnosis)\
         .order_by(func.count(MedicalRecord.record_Id).desc())\
         .limit(10).all()

        return jsonify({
            "labels": [r[0] for r in rows],
            "values": [r[1] for r in rows]
        })


# ═════════════════════════════════════════════════════════════
#  API — Patient Age Distribution
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/age-distribution")
def api_age_distribution():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        today = datetime.date.today()
        patients = db.query(Patient.Date_Of_Birth)\
            .filter(Patient.Date_Of_Birth != None).all()

        buckets = {"0–17": 0, "18–30": 0, "31–45": 0, "46–60": 0, "61–75": 0, "76+": 0}
        for (dob,) in patients:
            try:
                age = (today - dob).days // 365
                if age < 18:
                    buckets["0–17"] += 1
                elif age <= 30:
                    buckets["18–30"] += 1
                elif age <= 45:
                    buckets["31–45"] += 1
                elif age <= 60:
                    buckets["46–60"] += 1
                elif age <= 75:
                    buckets["61–75"] += 1
                else:
                    buckets["76+"] += 1
            except Exception:
                pass

        return jsonify({
            "labels": list(buckets.keys()),
            "values": list(buckets.values())
        })


# ═════════════════════════════════════════════════════════════
#  API — Daily Revenue (last 7 days)
# ═════════════════════════════════════════════════════════════
@auditor_bp.route("/api/daily-revenue")
def api_daily_revenue():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        today = datetime.date.today()
        seven_ago = today - datetime.timedelta(days=6)

        rows = db.query(
            cast(Payment.paid_at, Date).label("day"),
            func.coalesce(func.sum(Payment.amount), 0).label("total")
        ).filter(
            Payment.paid_at != None,
            Payment.paid_at >= seven_ago,
            func.lower(Payment.payment_status) == "success"   # ✅ FIXED
        ).group_by(
            cast(Payment.paid_at, Date)
        ).order_by(
            cast(Payment.paid_at, Date)
        ).all()

        day_map = {str(r[0]): float(r[1]) for r in rows}

        labels, values = [], []
        for i in range(7):
            d = seven_ago + datetime.timedelta(days=i)
            labels.append(d.strftime("%a %d %b"))
            values.append(day_map.get(str(d), 0.0))

        return jsonify({
            "labels": labels,
            "values": values
        })
# ═════════════════════════════════════════════════════════════
#  API — Payment Mode Distribution
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/payment-mode")
def api_payment_mode():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(
            Payment.payment_method,
            func.count(Payment.payment_id)
        ).group_by(Payment.payment_method).all()

        return jsonify({
            "labels": [r[0] or "Unknown" for r in rows],
            "values": [r[1] for r in rows]
        })


# ═════════════════════════════════════════════════════════════
#  API — Revenue by Department
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/revenue-by-department")
def api_revenue_by_department():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(
                Department.dept_Name,
                func.coalesce(func.sum(Payment.amount), 0).label("revenue")
            ).join(
                Doctor, Doctor.dept_Id == Department.dept_Id
            ).join(
                Appointment, Appointment.doct_Id == Doctor.doct_Id
            ).join(
                Bill, Bill.patient_Id == Appointment.patient_Id
            ).join(
                Payment, Payment.bill_id == Bill.bill_id
            ).group_by(Department.dept_Name)\
            .order_by(func.coalesce(func.sum(Payment.amount), 0).desc())\
            .limit(5)\
            .all()

        return jsonify({
            "labels": [r[0] for r in rows],
            "values": [float(r[1]) for r in rows]
        })


# ═════════════════════════════════════════════════════════════
#  API — Blood Group Distribution
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/blood-groups")
def api_blood_groups():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(
            Patient.blood_group,
            func.count(Patient.patient_Id)
        ).filter(
            Patient.blood_group != None,
            Patient.blood_group != ""
        ).group_by(Patient.blood_group)\
         .order_by(Patient.blood_group).all()

        return jsonify({
            "labels": [r[0] for r in rows],
            "values": [r[1] for r in rows]
        })


# ═════════════════════════════════════════════════════════════
#  API — New Patient Registrations per Month (last 12 months)
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/registrations-per-month")
def api_registrations_per_month():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        today = datetime.date.today()
        twelve_ago = today.replace(day=1) - datetime.timedelta(days=365)

        rows = db.query(
            func.extract("year", Patient.registration_date).label("yr"),
            func.extract("month", Patient.registration_date).label("mo"),
            func.count(Patient.patient_Id).label("cnt")
        ).filter(
            Patient.registration_date >= twelve_ago
        ).group_by("yr", "mo")\
         .order_by("yr", "mo").all()

        month_map = {(int(r[0]), int(r[1])): r[2] for r in rows}
        labels, values = [], []
        for i in range(12):
            # Walk backwards 11 months, then forward
            month_offset = (today.month - 11 + i - 1) % 12 + 1
            year_offset = today.year + ((today.month - 11 + i - 1) // 12)
            d = datetime.date(year_offset, month_offset, 1)
            labels.append(d.strftime("%b %Y"))
            values.append(month_map.get((d.year, d.month), 0))

        return jsonify({"labels": labels, "values": values})


# ═════════════════════════════════════════════════════════════
#  API — Read-Only: Appointments list
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/appointments")
def api_appointments():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    page = int(request.args.get("page", 1))
    per_page = PAGINATION["audit_logs"]
    date_from = request.args.get("date_from")
    date_to   = request.args.get("date_to")
    status    = request.args.get("status", "")
    doctor_id = request.args.get("doctor_id", "")

    with get_db_ctx() as db:
        q = db.query(
            Appointment.appointment_Id,
            Appointment.appointment_Date,
            Appointment.appointment_status,
            Appointment.reason,
            Appointment.payment_amount,
            Appointment.mode_of_payment,
            (Patient.FName + " " + Patient.LName).label("patient_name"),
            (Doctor.FName  + " " + Doctor.LName ).label("doctor_name"),
            Department.dept_Name
        ).outerjoin(Patient, Patient.patient_Id == Appointment.patient_Id)\
         .outerjoin(Doctor,  Doctor.doct_Id      == Appointment.doct_Id)\
         .outerjoin(Department, Department.dept_Id == Doctor.dept_Id)

        if date_from:
            q = q.filter(Appointment.appointment_Date >= date_from)
        if date_to:
            q = q.filter(Appointment.appointment_Date <= date_to)
        if status:
            q = q.filter(func.lower(Appointment.appointment_status) == status.lower())
        if doctor_id:
            q = q.filter(Appointment.doct_Id == int(doctor_id))

        total = q.count()
        rows  = q.order_by(Appointment.appointment_Date.desc())\
                  .offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "total": total,
            "pages": math.ceil(total / per_page),
            "page":  page,
            "data": [{
                "id":       r[0],
                "date":     str(r[1]),
                "status":   r[2],
                "reason":   r[3],
                "amount":   float(r[4] or 0),
                "payment_mode": r[5],
                "patient":  r[6],
                "doctor":   r[7],
                "dept":     r[8],
            } for r in rows]
        })


# ═════════════════════════════════════════════════════════════
#  API — Read-Only: Patients list
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/patients")
def api_patients():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    page     = int(request.args.get("page", 1))
    per_page = PAGINATION["audit_logs"]
    search   = request.args.get("search", "").strip()

    with get_db_ctx() as db:
        q = db.query(
            Patient.patient_Id,
            Patient.FName, Patient.LName,
            Patient.Gender, Patient.Date_Of_Birth,
            Patient.blood_group, Patient.contact_No,
            Patient.email, Patient.registration_date
        )
        if search:
            q = q.filter(
                (Patient.FName + " " + Patient.LName).ilike(f"%{search}%") |
                Patient.email.ilike(f"%{search}%") |
                Patient.contact_No.ilike(f"%{search}%")
            )

        total = q.count()
        rows  = q.order_by(Patient.registration_date.desc())\
                  .offset((page - 1) * per_page).limit(per_page).all()

        today = datetime.date.today()
        def calc_age(dob):
            if not dob: return "—"
            return str((today - dob).days // 365)

        return jsonify({
            "total": total,
            "pages": math.ceil(total / per_page),
            "page":  page,
            "data": [{
                "id":           r[0],
                "name":         f"{r[1]} {r[2]}",
                "gender":       r[3],
                "age":          calc_age(r[4]),
                "blood_group":  r[5] or "—",
                "contact":      r[6],
                "email":        r[7],
                "registered":   str(r[8])[:10] if r[8] else "—",
            } for r in rows]
        })


# ═════════════════════════════════════════════════════════════
#  API — Read-Only: Doctors list
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/doctors")
def api_doctors():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    page     = int(request.args.get("page", 1))
    per_page = PAGINATION["audit_logs"]
    search   = request.args.get("search", "").strip()
    dept_id  = request.args.get("dept_id", "")

    with get_db_ctx() as db:
        q = db.query(
            Doctor.doct_Id,
            Doctor.FName, Doctor.LName,
            Doctor.Gender, Doctor.surgeon_Type,
            Doctor.experience_years, Doctor.contact_No,
            Department.dept_Name,
            func.count(Appointment.appointment_Id).label("appt_count")
        ).outerjoin(Department, Department.dept_Id == Doctor.dept_Id)\
         .outerjoin(Appointment, Appointment.doct_Id == Doctor.doct_Id)\
         .group_by(Doctor.doct_Id, Doctor.FName, Doctor.LName, Doctor.Gender,
                   Doctor.surgeon_Type, Doctor.experience_years, Doctor.contact_No,
                   Department.dept_Name)

        if search:
            q = q.filter(
                (Doctor.FName + " " + Doctor.LName).ilike(f"%{search}%")
            )
        if dept_id:
            q = q.filter(Doctor.dept_Id == int(dept_id))

        total = q.count()
        rows  = q.order_by(func.count(Appointment.appointment_Id).desc())\
                  .offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "total": total,
            "pages": math.ceil(total / per_page),
            "page":  page,
            "data": [{
                "id":          r[0],
                "name":        f"Dr. {r[1]} {r[2]}",
                "gender":      r[3],
                "specialty":   r[4] or "General",
                "experience":  r[5] or 0,
                "contact":     r[6],
                "dept":        r[7] or "—",
                "appt_count":  r[8],
            } for r in rows]
        })


# ═════════════════════════════════════════════════════════════
#  API — Read-Only: Billing / Payments list
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/billing")
def api_billing():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    page     = int(request.args.get("page", 1))
    per_page = PAGINATION["audit_logs"]
    status   = request.args.get("status", "")
    date_from = request.args.get("date_from", "")
    date_to   = request.args.get("date_to", "")

    with get_db_ctx() as db:
        q = db.query(
            Bill.bill_id,
            Bill.bill_type,
            Bill.total_amount,
            Bill.amount_paid,
            Bill.status,
            Bill.created_at,
            (Patient.FName + " " + Patient.LName).label("patient_name")
        ).outerjoin(Patient, Patient.patient_Id == Bill.patient_Id)

        if status:
            q = q.filter(Bill.status == status)
        if date_from:
            q = q.filter(Bill.created_at >= date_from)
        if date_to:
            q = q.filter(Bill.created_at <= date_to)

        total = q.count()
        rows  = q.order_by(Bill.created_at.desc())\
                  .offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "total": total,
            "pages": math.ceil(total / per_page),
            "page":  page,
            "data": [{
                "id":           r[0],
                "bill_type":    r[1],
                "total":        float(r[2] or 0),
                "paid":         float(r[3] or 0),
                "status":       r[4],
                "created_at":   str(r[5])[:10] if r[5] else "—",
                "patient":      r[6],
            } for r in rows]
        })


# ═════════════════════════════════════════════════════════════
#  API — Read-Only: Audit Logs list
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/audit-logs")
def api_audit_logs():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    try:
        page     = int(request.args.get("page", 1))
        per_page = PAGINATION["audit_logs"]
        role_f   = request.args.get("role", "")
        search   = request.args.get("search", "").strip()

        with get_db_ctx() as db:
            q = db.query(AuditLog)

            if role_f:
                q = q.filter(AuditLog.role == role_f)

            if search:
                q = q.filter(
                    AuditLog.action.ilike(f"%{search}%") |
                    AuditLog.user_name.ilike(f"%{search}%") |
                    AuditLog.entity.ilike(f"%{search}%")
                )

            total = q.count()

            rows  = q.order_by(AuditLog.timestamp.desc())\
                      .offset((page - 1) * per_page)\
                      .limit(per_page).all()

            return jsonify({
                "total": total,
                "pages": math.ceil(total / per_page),
                "page":  page,
                "data": [{
                    "id":        r.id,
                    "user":      r.user_name,
                    "role":      r.role,
                    "action":    r.action,
                    "entity":    r.entity,
                    "detail":    r.detail,
                    "timestamp": str(r.timestamp)[:19] if r.timestamp else "—",
                } for r in rows]
            })

    except Exception as e:
        print("AUDIT LOG ERROR:", str(e))   # 🔥 THIS WILL SHOW REAL ISSUE
        return jsonify({"error": str(e)}), 500
# ═════════════════════════════════════════════════════════════
#  API — Departments list (for filter dropdowns)
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/departments")
def api_departments():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(Department.dept_Id, Department.dept_Name)\
                  .order_by(Department.dept_Name).all()
        return jsonify([{"id": r[0], "name": r[1]} for r in rows])


# ═════════════════════════════════════════════════════════════
#  API — Gender Distribution
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/gender-distribution")
def api_gender_distribution():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(
            func.count(Patient.patient_Id),
            func.upper(func.substr(Patient.Gender, 1, 1)).label("gender")
        ).filter(
            Patient.Gender != None,
            Patient.Gender != ""
        ).group_by("gender").all()

        labels = [
            "Male" if r[1] == "M"
            else "Female" if r[1] == "F"
            else "Other"
            for r in rows
        ]

        values = [r[0] for r in rows]

        return jsonify({
            "labels": labels,
            "values": values
        })


# ═════════════════════════════════════════════════════════════
#  API — Doctors by Specialization
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/doctors-by-specialization")
def api_doctors_by_specialization():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(
            func.coalesce(
                func.nullif(func.trim(func.lower(Doctor.surgeon_Type)), ''),
                'General'
            ).label("specialization"),
            func.count(Doctor.doct_Id).label("cnt")
        ).group_by("specialization")\
        .order_by(func.count(Doctor.doct_Id).desc())\
        .limit(10)\
        .all()

        labels = []
        values = []

        for r in rows:

            spec = (r[0] or "General").strip().title()

            # convert nan/none/null to General
            if spec.lower() in ["nan", "none", "null"]:
                spec = "General"

            labels.append(spec)
            values.append(r[1])

        return jsonify({
            "labels": labels,
            "values": values
        })


# ═════════════════════════════════════════════════════════════
#  API — Billed vs Paid Amounts by Month (last 6 months)
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/billed-vs-paid")
def api_billed_vs_paid():

    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:

        today = datetime.date.today()
        six_months_ago = today.replace(day=1) - datetime.timedelta(days=180)

        # ─────────────────────────────────────────────
        # BILL TOTALS
        # ─────────────────────────────────────────────
        bill_rows = db.query(
            func.extract("year", Bill.created_at).label("yr"),
            func.extract("month", Bill.created_at).label("mo"),
            func.coalesce(func.sum(Bill.total_amount), 0).label("billed")
        ).filter(
            Bill.created_at != None,
            Bill.created_at >= six_months_ago
        ).group_by("yr", "mo").all()

        # ─────────────────────────────────────────────
        # SUCCESSFUL PAYMENTS ONLY
        # ─────────────────────────────────────────────
        payment_rows = db.query(
            func.extract("year", Payment.paid_at).label("yr"),
            func.extract("month", Payment.paid_at).label("mo"),
            func.coalesce(func.sum(Payment.amount), 0).label("paid")
        ).filter(
            Payment.paid_at != None,
            Payment.paid_at >= six_months_ago,
            func.lower(Payment.payment_status) == "success"
        ).group_by("yr", "mo").all()

        bill_map = {
            (int(r.yr), int(r.mo)): float(r.billed)
            for r in bill_rows
        }

        paid_map = {
            (int(r.yr), int(r.mo)): float(r.paid)
            for r in payment_rows
        }

        labels = []
        billed = []
        paid = []

        for i in range(6):

            d = (
                today.replace(day=1)
                - datetime.timedelta(days=30 * (5 - i))
            )

            key = (d.year, d.month)

            billed_amt = bill_map.get(key, 0)
            paid_amt = paid_map.get(key, 0)

            # SHOW ONLY MONTHS WITH DATA
            if billed_amt > 0 or paid_amt > 0:

                labels.append(
                    d.strftime("%b %Y")
                )

                billed.append(billed_amt)

                paid.append(paid_amt)
        return jsonify({
            "labels": labels,
            "billed": billed,
            "paid": paid
        })

# ═════════════════════════════════════════════════════════════
#  API — Doctor Experience Distribution
# ═════════════════════════════════════════════════════════════

@auditor_bp.route("/api/doctor-experience")
def api_doctor_experience():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(Doctor.experience_years)\
                  .filter(Doctor.experience_years != None).all()

        buckets = {"0–2 yrs": 0, "3–5 yrs": 0, "6–10 yrs": 0,
                   "11–15 yrs": 0, "16–20 yrs": 0, "20+ yrs": 0}
        for (exp,) in rows:
            if exp <= 2:
                buckets["0–2 yrs"] += 1
            elif exp <= 5:
                buckets["3–5 yrs"] += 1
            elif exp <= 10:
                buckets["6–10 yrs"] += 1
            elif exp <= 15:
                buckets["11–15 yrs"] += 1
            elif exp <= 20:
                buckets["16–20 yrs"] += 1
            else:
                buckets["20+ yrs"] += 1

        return jsonify({
            "labels": list(buckets.keys()),
            "values": list(buckets.values())
        })


@auditor_bp.route("/export")
def export_page():
    g = require_auditor()
    if g: return g
    return render_template("auditor/export.html")


@auditor_bp.route("/api/export", methods=["POST"])
def export_data():
    if session.get("role") != "Auditor":
        return jsonify({"detail": "Forbidden"}), 403

    data_type = request.form.get("type")

    with get_db_ctx() as db:

        output = io.StringIO()
        writer = csv.writer(output)

        # ───── Patients ─────
        if data_type == "patients":
            writer.writerow(["ID", "Name", "Gender", "Contact"])

            rows = db.query(Patient).all()
            for p in rows:
                writer.writerow([
                    p.patient_Id,
                    f"{p.FName} {p.LName}",
                    p.Gender,
                    p.contact_No
                ])

        # ───── Appointments ─────
        elif data_type == "appointments":
            writer.writerow(["ID", "Date", "Status"])

            rows = db.query(Appointment).all()
            for a in rows:
                writer.writerow([
                    a.appointment_Id,
                    str(a.appointment_Date),
                    a.appointment_status
                ])

        # ───── Billing ─────
        elif data_type == "billing":
            writer.writerow(["Bill ID", "Total", "Paid", "Status"])

            rows = db.query(Bill).all()
            for b in rows:
                writer.writerow([
                    b.bill_id,
                    float(b.total_amount or 0),
                    float(b.amount_paid or 0),
                    b.status
                ])

        # ───── Audit Logs ─────
        elif data_type == "audit":
            writer.writerow(["User", "Action", "Entity", "Time"])

            rows = db.query(AuditLog).all()
            for l in rows:
                writer.writerow([
                    l.user_name,
                    l.action,
                    l.entity,
                    str(l.timestamp)
                ])

        else:
            return "Invalid export type", 400

        # ───── RESPONSE (FIXED) ─────
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={data_type}.csv"
        response.headers["Content-type"] = "text/csv"

        return response