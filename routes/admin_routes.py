from flask import Blueprint, flash, render_template, request, session, redirect, jsonify
from sqlalchemy import case, func, text
import datetime, math
from flask import current_app
from werkzeug.security import generate_password_hash
import random
import string

# Local imports
from database import get_db_ctx, get_db
from models import (User, Doctor, Department, Patient, Appointment,
                    Bill, Payment, AuditLog, Role, TreatmentCatalogue, DoctorLeave )
from config import PAGINATION



def generate_temp_password(length=8):
    return ''.join(random.choices(
        string.ascii_letters + string.digits, k=length
    ))

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# ── Auth guard ────────────────────────────────────────────────────────────────

def require_admin():
    if session.get("role") != "Admin":
        return redirect("/login")
    return None

# ── Page routes ───────────────────────────────────────────────────────────────

@admin_bp.route("/dashboard")
def dashboard():
    g = require_admin()
    if g: return g
    return render_template("admin/dashboard.html")

@admin_bp.route("/users")
def users():
    g = require_admin()
    if g: return g
    return render_template("admin/users.html")

@admin_bp.route("/doctors")
def doctors():
    g = require_admin()
    if g: return g
    return render_template("admin/doctors.html")

@admin_bp.route("/departments")
def departments():
    g = require_admin()
    if g: return g
    return render_template("admin/departments.html")

@admin_bp.route("/patients")
def admin_patients():
    g = require_admin()
    if g: return g
    return render_template("admin/patients.html")

@admin_bp.route("/appointments")
def appointments():
    g = require_admin()
    if g: return g
    return render_template("admin/appointments.html")

@admin_bp.route("/billing")
def billing():
    g = require_admin()
    if g: return g
    return render_template("admin/billing.html")

@admin_bp.route("/audit-logs")
def audit_logs():
    g = require_admin()
    if g: return g
    return render_template("admin/audit_logs.html")

# ══════════════════════════════════════════════════════════════════════════════
#  API — Dashboard KPIs
# ══════════════════════════════════════════════════════════════════════════════
@admin_bp.route("/api/kpis")
def api_kpis():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        today = datetime.date.today()

        total_patients = db.query(func.count(Patient.patient_Id)).scalar() or 0

        appts_today = db.query(func.count(Appointment.appointment_Id))\
            .filter(Appointment.appointment_Date == today).scalar() or 0

        pending_bills = db.query(func.count(Bill.bill_id))\
            .filter(Bill.status.in_(["Pending", "Partial"])).scalar() or 0

        revenue = db.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).filter(
            Payment.paid_at != None,
            func.lower(Payment.payment_status) == "success"
        ).scalar() or 0

        week_labels, week_data = [], []
        for i in range(7):
            d = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=i)
            cnt = db.query(func.count(Appointment.appointment_Id))\
                .filter(Appointment.appointment_Date == d).scalar() or 0
            week_labels.append(d.strftime("%a"))
            week_data.append(cnt)

        dept_rows = db.query(Department.dept_Name, func.count(Appointment.appointment_Id))\
            .outerjoin(Doctor, Doctor.dept_Id == Department.dept_Id)\
            .outerjoin(Appointment, Appointment.doct_Id == Doctor.doct_Id)\
            .group_by(Department.dept_Name).all()

        return jsonify({
            "total_patients": total_patients,
            "appts_today": appts_today,
            "pending_bills": pending_bills,
            "revenue_month": revenue,
            "weekly_labels": week_labels,
            "weekly_counts": week_data,
            "dept_labels": [r[0] for r in dept_rows],
            "dept_counts": [r[1] for r in dept_rows]
        })
# ── NEW: Treatment distribution ────────────────────────────────────────
@admin_bp.route("/api/admin/treatment-stats")
def api_treatment_stats():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(
            TreatmentCatalogue.category,
            func.count(TreatmentCatalogue.treatment_id)
        ).group_by(TreatmentCatalogue.category).all()

        if not rows:
            return jsonify({"labels": [], "values": []})

        return jsonify({
            "labels": [r[0] or "Uncategorised" for r in rows],
            "values": [r[1] for r in rows]
        })


# ── NEW: Patient registration trend (last 30 days) ──────────────────────
@admin_bp.route("/api/admin/patient-trend")
def api_patient_trend():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403

    import datetime as dt
    with get_db_ctx() as db:
        today = dt.date.today()
        thirty_ago = today - dt.timedelta(days=29)

        rows = db.query(
            func.date(Patient.registration_date),
            func.count(Patient.patient_Id)
        ).filter(
            Patient.registration_date >= thirty_ago
        ).group_by(
            func.date(Patient.registration_date)
        ).all()

        date_map = {str(r[0]): r[1] for r in rows}
        labels, values = [], []
        for i in range(30):
            d = thirty_ago + dt.timedelta(days=i)
            labels.append(d.strftime("%d %b"))
            values.append(date_map.get(str(d), 0))

        return jsonify({"labels": labels, "values": values})
    
    
# ══════════════════════════════════════════════════════════════════════════════
#  API — Dashboard Charts
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/api/admin/appt-status")
def api_appt_status():

    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:

        rows = db.query(
            func.lower(Appointment.appointment_status),
            func.count(Appointment.appointment_Id)
        ).filter(
            Appointment.appointment_status != None
        ).group_by(
            func.lower(Appointment.appointment_status)
        ).all()

        labels = []
        values = []

        for status, count in rows:
            labels.append((status or "unknown").title())
            values.append(count)

        return jsonify({
            "labels": labels,
            "values": values
        })

@admin_bp.route("/api/admin/age-distribution")
def api_age_distribution():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    import datetime as dt
    with get_db_ctx() as db:
        patients = db.query(Patient.Date_Of_Birth).filter(Patient.Date_Of_Birth != None).all()
        today = dt.date.today()
        buckets = {"0-10": 0, "11-20": 0, "21-30": 0, "31-40": 0, "41-50": 0, "51-60": 0, "61-70": 0, "71+": 0}
        for (dob,) in patients:
            age = (today - dob).days // 365
            if age <= 10:    buckets["0-10"] += 1
            elif age <= 20:  buckets["11-20"] += 1
            elif age <= 30:  buckets["21-30"] += 1
            elif age <= 40:  buckets["31-40"] += 1
            elif age <= 50:  buckets["41-50"] += 1
            elif age <= 60:  buckets["51-60"] += 1
            elif age <= 70:  buckets["61-70"] += 1
            else:            buckets["71+"] += 1
        return jsonify({"labels": list(buckets.keys()), "values": list(buckets.values())})


@admin_bp.route("/api/admin/payment-modes")
def api_payment_modes():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    with get_db_ctx() as db:
        rows = db.query(
            Appointment.mode_of_payment,
            func.count(Appointment.appointment_Id)
        ).filter(Appointment.mode_of_payment != None).group_by(Appointment.mode_of_payment).all()
        rows = [(r[0] or "Unknown", r[1]) for r in rows]
        return jsonify({"labels": [r[0] for r in rows], "values": [r[1] for r in rows]})


@admin_bp.route("/api/admin/monthly-registrations")
def api_monthly_registrations():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    import datetime as dt
    with get_db_ctx() as db:
        today = dt.date.today()
        labels, values = [], []
        for i in range(11, -1, -1):
            month_date = (today.replace(day=1) - dt.timedelta(days=i * 28)).replace(day=1)
            next_month = (month_date.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
            cnt = db.query(func.count(Patient.patient_Id)).filter(
                Patient.registration_date >= month_date,
                Patient.registration_date < next_month
            ).scalar() or 0
            labels.append(month_date.strftime("%b %Y"))
            values.append(cnt)
        return jsonify({"labels": labels, "values": values})


@admin_bp.route("/api/admin/patient-gender")
def api_patient_gender():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    with get_db_ctx() as db:
        rows = db.query(
            case(
                (Patient.Gender.in_(["M", "Male", "male"]), "Male"),
                (Patient.Gender.in_(["F", "Female", "female"]), "Female"),
                else_="Other"
            ).label("gender"),
            func.count(Patient.patient_Id)
        ).group_by("gender").all()
        return jsonify({"labels": [r[0] for r in rows], "values": [r[1] for r in rows]})


@admin_bp.route("/api/admin/doctors-by-dept")
def api_doctors_by_dept_chart():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    with get_db_ctx() as db:
        rows = db.query(
            Department.dept_Name,
            func.count(Doctor.doct_Id)
        ).outerjoin(Doctor, Doctor.dept_Id == Department.dept_Id).group_by(Department.dept_Name).all()
        return jsonify({"labels": [r[0] for r in rows], "values": [r[1] for r in rows]})


@admin_bp.route("/api/admin/patients-per-doctor")
def api_patients_per_doctor():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    with get_db_ctx() as db:
        rows = db.query(
            Doctor.FName, Doctor.LName,
            func.count(Appointment.patient_Id.distinct())
        ).outerjoin(Appointment, Appointment.doct_Id == Doctor.doct_Id)\
         .group_by(Doctor.doct_Id, Doctor.FName, Doctor.LName)\
         .order_by(func.count(Appointment.patient_Id.distinct()).desc())\
         .limit(10).all()
        labels = [f"Dr. {r[0]} {r[1]}" for r in rows]
        return jsonify({"labels": labels, "values": [r[2] for r in rows]})


@admin_bp.route("/api/admin/appts-by-slot")
def api_appts_by_slot():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    with get_db_ctx() as db:
        rows = db.query(
            Appointment.slot_time,
            func.count(Appointment.appointment_Id)
        ).filter(Appointment.slot_time != None)\
         .group_by(Appointment.slot_time)\
         .order_by(Appointment.slot_time).all()
        labels = [str(r[0])[:5] if r[0] else "Unknown" for r in rows]
        return jsonify({"labels": labels, "values": [r[1] for r in rows]})


@admin_bp.route("/api/admin/billed-vs-paid")
def api_billed_vs_paid():

    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403

    import datetime as dt

    with get_db_ctx() as db:

        today = dt.date.today()

        labels = []
        billed_vals = []
        paid_vals = []

        for i in range(5, -1, -1):

            month_date = (
                today.replace(day=1) - dt.timedelta(days=i * 30)
            ).replace(day=1)

            next_month = (
                month_date.replace(day=28) + dt.timedelta(days=4)
            ).replace(day=1)

            billed = db.query(
                func.coalesce(func.sum(Bill.total_amount), 0)
            ).filter(
                Bill.created_at != None,
                Bill.created_at >= month_date,
                Bill.created_at < next_month
            ).scalar() or 0

            paid = db.query(
                func.coalesce(func.sum(Payment.amount), 0)
            ).filter(
                Payment.paid_at != None,
                Payment.paid_at >= month_date,
                Payment.paid_at < next_month,
                func.lower(Payment.payment_status) == "success"
            ).scalar() or 0

            # SHOW ONLY MONTHS HAVING DATA
            if billed > 0 or paid > 0:

                labels.append(
                    month_date.strftime("%b %Y")
                )

                billed_vals.append(
                    round(float(billed), 2)
                )

                paid_vals.append(
                    round(float(paid), 2)
                )
        
        return jsonify({
            "labels": labels,
            "billed": billed_vals,
            "paid": paid_vals
        })

@admin_bp.route("/api/admin/monthly-revenue")
def api_monthly_revenue():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    import datetime as dt
    with get_db_ctx() as db:
        today = dt.date.today()
        labels, values = [], []
        for i in range(11, -1, -1):
            month_date = (today.replace(day=1) - dt.timedelta(days=i * 28)).replace(day=1)
            next_month = (month_date.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
            revenue = db.query(
                func.coalesce(func.sum(Payment.amount), 0)
            ).filter(
                Payment.paid_at != None,
                Payment.paid_at >= month_date,
                Payment.paid_at < next_month,
                func.lower(Payment.payment_status) == "success"
            ).scalar() or 0
            labels.append(month_date.strftime("%b %Y"))
            values.append(round(float(revenue), 2))
        return jsonify({"labels": labels, "values": values})


# ══════════════════════════════════════════════════════════════════════════════
#  API — Recent Appointments
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/api/admin/appointments/recent")
def api_recent_appts():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        page = int(request.args.get("page", 1))
        per_page = PAGINATION["appointments"]

        q = db.query(Appointment, Patient, Doctor, Department)\
            .join(Patient, Patient.patient_Id == Appointment.patient_Id)\
            .join(Doctor, Doctor.doct_Id == Appointment.doct_Id)\
            .outerjoin(Department, Department.dept_Id == Doctor.dept_Id)\
            .order_by(Appointment.appointment_Date.desc())

        total = q.count()
        rows = q.offset((page-1)*per_page).limit(per_page).all()

        items = [{
            "appointment_Id": a.appointment_Id,
            "patient_name": f"{p.FName} {p.LName}",
            "doctor_name": f"{d.FName} {d.LName}",
            "dept_name": dept.dept_Name if dept else "—",
            "appointment_date": str(a.appointment_Date),
            "appointment_status": a.appointment_status
        } for a,p,d,dept in rows]

        return jsonify({"items": items, "total": total, "total_pages": math.ceil(total/per_page) or 1})

# ══════════════════════════════════════════════════════════════════════════════
#  API — Users CRUD
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/api/admin/users")
def api_users_list():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403

    page, per_page = int(request.args.get("page", 1)), PAGINATION["users"]
    search, role_f, status_f = request.args.get("search","").strip(), request.args.get("role","").strip(), request.args.get("status","").strip()

    with get_db_ctx() as db:
        q = db.query(User, Role).outerjoin(Role, Role.id == User.Role_ID)
        if search:
            q = q.filter((User.Name.ilike(f"%{search}%")) | (User.Email.ilike(f"%{search}%")))
        if role_f:
            q = q.filter(Role.name == role_f)
        if status_f:
            q = q.filter(User.is_active == (status_f == "Active"))

        total = q.count()
        rows = q.order_by(User.User_ID.desc()).offset((page-1)*per_page).limit(per_page).all()

        items = [{
            "User_ID": u.User_ID, "Name": u.Name, "Email": u.Email,
            "Role_ID": u.Role_ID, "role_name": r.name if r else "—", "is_active": u.is_active,
        } for u, r in rows]

        return jsonify({"items": items, "total": total, "total_pages": math.ceil(total/per_page) or 1})

@admin_bp.route("/api/admin/users/<int:uid>")
def api_user_get(uid):
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    with get_db_ctx() as db:
        user = db.query(User).filter(User.User_ID == uid).first()
        if not user: return jsonify({"detail": "Not found"}), 404
        return jsonify({"User_ID": user.User_ID, "Name": user.Name, "Email": user.Email, "Role_ID": user.Role_ID, "is_active": user.is_active})


@admin_bp.route("/api/admin/department-stats")
def department_stats():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403

    with get_db_ctx() as db:
        rows = db.query(
            Department.dept_Name,
            func.count(Appointment.appointment_Id)
        ).outerjoin(
            Doctor, Doctor.dept_Id == Department.dept_Id
        ).outerjoin(
            Appointment, Appointment.doct_Id == Doctor.doct_Id
        ).group_by(Department.dept_Name).all()

        return jsonify({
            "labels": [r[0] for r in rows],
            "values": [r[1] for r in rows]
        })

@admin_bp.route("/api/admin/users", methods=["POST"])
def api_user_create():

    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403

    body = request.get_json() or {}

    with get_db_ctx() as db:

        # Generate random password
        temp_password = generate_temp_password()
        print("Generated Password:", temp_password)
        user = User(
            Name=body.get("name",""),
            Email=body.get("email",""),
            Password=generate_password_hash(temp_password),
            Role_ID=body.get("role_id"),
            is_active=True
        )

        db.add(user)
        db.commit()

        db.refresh(user)

        # 🔥 HANDLE DOCTOR ROLE HERE
        if user.Role_ID == 2:  # Doctor

            name_parts = (user.Name or "").split()

            doc = Doctor(
                User_ID=user.User_ID,
                FName=name_parts[0] if name_parts else "",
                LName=" ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            )

            db.add(doc)
            db.commit()
            db.refresh(doc)

            # 🔗 LINK USER ↔ DOCTOR
            user.Linked_Entity_ID = doc.doct_Id
            db.commit()
        # Get role name
        role = db.query(Role).filter(Role.id == user.Role_ID).first()
        role_name = role.name if role else "User"

        # Send email for ALL roles
        if user.Email:
            try:
                current_app.send_email(
                    "Welcome to LifeCare Hospitals",
                    [user.Email],
                    f"""
Dear {user.Name},

Your account has been created.

Role: {role_name}
Login Email: {user.Email}
Password: {temp_password}

Please change your password after login.

Regards,
LifeCare Hospitals
"""
                )
                print("User email sent")
            except Exception as e:
                print("Email error:", e)

        _log(db, "ADD_USER", f"User {user.Email} created")

        return jsonify({
            "ok": True,
            "user_id": user.User_ID,
            "password": temp_password
        })


@admin_bp.route("/api/admin/users/<int:uid>", methods=["PUT"])
def api_user_update(uid):
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    body = request.get_json() or {}
    with get_db_ctx() as db:
        user = db.query(User).filter(User.User_ID == uid).first()
        if not user: return jsonify({"detail": "Not found"}), 404
        user.Name, user.Email, user.Role_ID = body.get("name", user.Name), body.get("email", user.Email), body.get("role_id", user.Role_ID)
        if body.get("password"):
            user.Password = generate_password_hash(body["password"])
        db.commit()
        _log(db, "UPDATE_USER", f"User {uid} updated")
        return jsonify({"ok": True})

@admin_bp.route("/api/admin/users/<int:uid>/toggle", methods=["POST"])
def api_user_toggle(uid):
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    with get_db_ctx() as db:
        user = db.query(User).filter(User.User_ID == uid).first()
        if not user: return jsonify({"detail": "Not found"}), 404
        user.is_active = not user.is_active
        db.commit()
        _log(db, "ACTIVATE_USER" if user.is_active else "DEACTIVATE_USER", f"User {uid} status changed")
        return jsonify({"ok": True})


@admin_bp.route("/api/admin/doctors")
def api_doctors():

    page = int(request.args.get("page", 1))
    per_page = PAGINATION.get("doctors", 10)
    search = request.args.get("search", "")
    dept_id = request.args.get("dept", "")

    with get_db_ctx() as db:

        # 🔹 BASE QUERY (Doctor only for count)
        base_q = db.query(Doctor)

        if search:
            base_q = base_q.filter(
                (Doctor.FName.ilike(f"%{search}%")) |
                (Doctor.LName.ilike(f"%{search}%"))
            )

        if dept_id:
            base_q = base_q.filter(Doctor.dept_Id == int(dept_id))

        # TOTAL COUNT
        total = base_q.count()

        # 🔹 PAGINATED QUERY (with join)
        q = db.query(Doctor, Department)\
              .outerjoin(Department, Doctor.dept_Id == Department.dept_Id)

        if search:
            q = q.filter(
                (Doctor.FName.ilike(f"%{search}%")) |
                (Doctor.LName.ilike(f"%{search}%"))
            )

        if dept_id:
            q = q.filter(Doctor.dept_Id == int(dept_id))

        # ✅ APPLY pagination HERE ONLY
        rows = q.order_by(Doctor.doct_Id.desc())\
                .offset((page - 1) * per_page)\
                .limit(per_page)\
                .all()

        items = [{
            "doct_Id": d.doct_Id,
            "User_ID": d.User_ID,
            "FName": d.FName,
            "LName": d.LName,
            "dept_Name": dept.dept_Name if dept else None,
            "surgeon_Type": d.surgeon_Type,
            "contact_No": d.contact_No
        } for d, dept in rows]

        return jsonify({
            "items": items,
            "total": total,
            "total_pages": math.ceil(total / per_page)
        })
    
    
@admin_bp.route("/api/admin/doctors/<int:did>")
def api_doctor_get(did):
    with get_db_ctx() as db:
        doc = db.query(Doctor).filter(Doctor.doct_Id == did).first()
        if not doc: return jsonify({"detail": "Not found"}), 404
        user = db.query(User).filter(User.User_ID == doc.User_ID).first()

        return jsonify({
            "doct_Id": doc.doct_Id,
            "FName": doc.FName,
            "LName": doc.LName,
            "Gender": doc.Gender,
            "contact_No": doc.contact_No,
            "surgeon_Type": doc.surgeon_Type,
            "office_No": doc.office_No,
            "dept_Id": doc.dept_Id,
            "email": user.Email if user else ""
        })
            
@admin_bp.route("/api/admin/doctors", methods=["POST"])
def api_doctor_create():

    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403

    body = request.get_json() or {}

    with get_db_ctx() as db:

        # ✅ Generate random password
        temp_password = generate_temp_password()

        user = User(
            Name=f"{body.get('fname')} {body.get('lname')}",
            Email=body.get("email"),
            Password=generate_password_hash(temp_password),
            Role_ID=2,
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # 🔥 HANDLE DOCTOR ROLE
        if user.Role_ID == 2:  # Doctor
            name_parts = (user.Name or "").split()

            doc = Doctor(
                User_ID=user.User_ID,
                FName=name_parts[0] if name_parts else "",
                LName=" ".join(name_parts[1:]) if len(name_parts) > 1 else "",

                Gender=body.get("gender"),
                dept_Id=body.get("dept_id"),
                contact_No=body.get("contact_no"),
                surgeon_Type=body.get("surgeon_type"),
                office_No=body.get("office_no"),
                experience_years=body.get("experience_years"),
                is_dept_head=body.get("is_dept_head"),
                notes=body.get("notes")
                )

            db.add(doc)
            db.commit()
            db.refresh(doc)

            # 🔗 Link user to doctor
            user.Linked_Entity_ID = doc.doct_Id
            db.commit()
            # send email
        if user.Email:
            try:
                current_app.send_email(
                    "Doctor Account Created",
                    [user.Email],
                    f"""
Dear {doc.FName} {doc.LName},

Your account has been created.

Login Email: {user.Email}
Password: {temp_password}

Please change your password after login.

Regards,
LifeCare Hospitals
"""
                )
                print("Doctor email sent")
            except Exception as e:
                print("Email error:", e)

        _log(db, "ADD_DOCTOR", f"{doc.FName} {doc.LName} added")

        return jsonify({"ok": True})

# =================================================================═════════════════════════════════════════════════════════════
#  API — Doctors CRUD (continued)   
# =================================================================═════════════════════════════════════════════════════════════
@admin_bp.route("/api/admin/doctors/<int:did>", methods=["PUT"])
def api_doctor_update(did):
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    body = request.get_json() or {}
    with get_db_ctx() as db:
        doc = db.query(Doctor).filter(Doctor.doct_Id == did).first()
        if not doc: return jsonify({"detail": "Not found"}), 404
        for k, v in {"FName":"fname","LName":"lname","Gender":"gender","dept_Id":"dept_id","contact_No":"contact_no","surgeon_Type":"surgeon_type","office_No":"office_no"}.items():
            setattr(doc, k, body.get(v, getattr(doc, k)))
        db.commit()
        _log(db, "UPDATE_DOCTOR", f"Doctor {did} updated")
        return jsonify({"ok": True})

@admin_bp.route("/api/admin/doctors-by-dept/<int:dept_id>")
def api_doctors_by_dept(dept_id):
    with get_db_ctx() as db:
        docs = db.query(Doctor).filter(Doctor.dept_Id == dept_id).all()
        return jsonify([{"doct_Id": d.doct_Id, "FName": d.FName, "LName": d.LName} for d in docs])

# ══════════════════════════════════════════════════════════════════════════════
#  API — Departments CRUD
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/api/admin/departments")
def api_departments_list():
    page, per_page = int(request.args.get("page", 1)), PAGINATION["departments"]
    search = request.args.get("search","").strip()
    with get_db_ctx() as db:
        q = db.query(Department)
        if search: q = q.filter(Department.dept_Name.ilike(f"%{search}%"))
        if "page" not in request.args:
            rows = q.order_by(Department.dept_Name).all()
            return jsonify([{"dept_Id": d.dept_Id, "dept_Name": d.dept_Name} for d in rows])
        total = q.count()
        rows = q.order_by(Department.dept_Name).offset((page-1)*per_page).limit(per_page).all()
        items = [{"dept_Id": d.dept_Id, "dept_Name": d.dept_Name, "doctor_count": db.query(func.count(Doctor.doct_Id)).filter(Doctor.dept_Id == d.dept_Id).scalar() or 0} for d in rows]
        return jsonify({"items": items, "total": total, "total_pages": math.ceil(total/per_page) or 1})

@admin_bp.route("/api/admin/departments", methods=["POST"])
def api_dept_create():
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    body = request.get_json() or {}
    with get_db_ctx() as db:
        dept = Department(dept_Name=body.get("dept_Name",""))
        db.add(dept); db.commit()
        _log(db, "ADD_DEPT", f"Department '{dept.dept_Name}' created")
        return jsonify({"ok": True})

@admin_bp.route("/api/admin/departments/<int:did>", methods=["PUT"])
def api_dept_update(did):
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    body = request.get_json() or {}
    with get_db_ctx() as db:
        dept = db.query(Department).filter(Department.dept_Id == did).first()
        if not dept: return jsonify({"detail": "Not found"}), 404
        dept.dept_Name = body.get("dept_Name", dept.dept_Name)
        db.commit()
        _log(db, "UPDATE_DEPT", f"Department {did} updated")
        return jsonify({"ok": True})

@admin_bp.route("/api/admin/departments/<int:did>", methods=["DELETE"])
def api_dept_delete(did):
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    with get_db_ctx() as db:
        docs = db.query(func.count(Doctor.doct_Id)).filter(Doctor.dept_Id == did).scalar()
        if docs: return jsonify({"detail": f"Cannot delete: {docs} doctors assigned"}), 400
        dept = db.query(Department).filter(Department.dept_Id == did).first()
        if dept: db.delete(dept); db.commit(); _log(db, "DELETE_DEPT", f"Department {did} deleted")
        return jsonify({"ok": True})

# ══════════════════════════════════════════════════════════════════════════════
#  API — Patients
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/api/admin/patients")
def api_patients_list():
    page, per_page = int(request.args.get("page", 1)), int(request.args.get("per_page", PAGINATION["patients"]))
    search, gender = request.args.get("search","").strip(), request.args.get("gender","").strip()
    with get_db_ctx() as db:
        q = db.query(Patient)
        if search: q = q.filter((Patient.FName.ilike(f"%{search}%")) | (Patient.LName.ilike(f"%{search}%")))
        if gender: q = q.filter(Patient.Gender == gender)
        total = q.count()
        rows = q.order_by(Patient.patient_Id.desc()).offset((page-1)*per_page).limit(per_page).all()
        items = [{"patient_Id": p.patient_Id, "FName": p.FName, "LName": p.LName, "Gender": p.Gender, "Date_Of_Birth": str(p.Date_Of_Birth) if p.Date_Of_Birth else None, "contact_No": p.contact_No, "pt_Address": p.pt_Address} for p in rows]
        return jsonify({"items": items, "total": total, "total_pages": math.ceil(total/per_page) or 1})

@admin_bp.route("/api/admin/patients/<int:pid>")
def api_patient_get(pid):
    with get_db_ctx() as db:
        p = db.query(Patient).filter(Patient.patient_Id == pid).first()
        if not p: return jsonify({"detail": "Not found"}), 404
        return jsonify({"patient_Id": p.patient_Id, "FName": p.FName, "LName": p.LName, "Gender": p.Gender, "Date_Of_Birth": str(p.Date_Of_Birth) if p.Date_Of_Birth else None, "contact_No": p.contact_No, "pt_Address": p.pt_Address})

# ══════════════════════════════════════════════════════════════════════════════
#  API — Appointments (admin)
# ══════════════════════════════════════════════════════════════════════════════
@admin_bp.route("/api/admin/appointments")
def api_appts_list():

    page = int(request.args.get("page", 1))
    per_page = PAGINATION["appointments"]

    d_from = request.args.get("date_from","")
    d_to   = request.args.get("date_to","")
    dept_f = request.args.get("dept","")
    status = request.args.get("status","")

    with get_db_ctx() as db:

        q = db.query(Appointment)\
            .join(Patient, Patient.patient_Id == Appointment.patient_Id)\
            .join(Doctor, Doctor.doct_Id == Appointment.doct_Id)\
            .outerjoin(Department, Department.dept_Id == Doctor.dept_Id)\
            .add_entity(Patient)\
            .add_entity(Doctor)\
            .add_entity(Department)

        if d_from:
            q = q.filter(Appointment.appointment_Date >= d_from)

        if d_to:
            q = q.filter(Appointment.appointment_Date <= d_to)

        if dept_f:
            q = q.filter(Doctor.dept_Id == int(dept_f))

        if status:
           q = q.filter(
            func.lower(Appointment.appointment_status) == status.lower()
        )

        total = q.count()

        rows = q.order_by(Appointment.appointment_Date.desc())\
            .offset((page-1)*per_page)\
            .limit(per_page).all()
        items = [{
            "appointment_Id": a.appointment_Id,
            "patient_name": f"{p.FName} {p.LName}",
            "doctor_name": f"{d.FName} {d.LName}",
            "dept_name": dept.dept_Name if dept else "—",
            "appointment_date": str(a.appointment_Date),
            "appointment_status": a.appointment_status
        } for a,p,d,dept in rows]

        return jsonify({
            "items": items,
            "total": total,
            "total_pages": math.ceil(total/per_page) or 1
        })

@admin_bp.route("/api/admin/appointments/<int:aid>/cancel", methods=["POST"])
def api_cancel_appt(aid):
    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403
    with get_db_ctx() as db:
        appt = db.query(Appointment).filter(Appointment.appointment_Id == aid).first()
        if not appt: return jsonify({"detail": "Not found"}), 404
        appt.appointment_status = "Cancelled"
        db.commit()
        _log(db, "CANCEL_APPT", f"Appointment {aid} cancelled")
        return jsonify({"ok": True})

# ── Internal helper ───────────────────────────────────────────────────────────

def _log(db, action, detail=None):
    db.add(AuditLog(
        user_id=session.get("user_id"),
        user_name=session.get("user_name",""),
        role=session.get("role",""),
        action=action, detail=detail,
        timestamp=datetime.datetime.now()
    ))
    db.commit()

@admin_bp.route("/api/admin/doctors/<int:did>", methods=["DELETE"])
def api_doctor_delete(did):

    if session.get("role") != "Admin":
        return jsonify({"detail": "Forbidden"}), 403

    from models import MedicalRecord  # ✅ IMPORTANT

    with get_db_ctx() as db:

        doc = db.query(Doctor)\
                .filter(Doctor.doct_Id == did)\
                .first()

        if not doc:
            return jsonify({"detail": "Doctor not found"}), 404

        # 🔴 CHECK: Is doctor used in medical records?
        record_count = db.query(MedicalRecord)\
            .filter(MedicalRecord.doct_Id == did)\
            .count()

        if record_count > 0:
            return jsonify({
                "ok": False,
                "detail": f"Cannot delete doctor. {record_count} medical records are linked."
            }), 400

        # ✅ Safe to delete
        # Delete doctor first
        db.delete(doc)

        # Flush immediately so FK is cleared
        db.flush()

        # Then delete linked user
        if doc.User_ID:
            user = db.query(User)\
                    .filter(User.User_ID == doc.User_ID)\
                    .first()

            if user:
                db.delete(user)

        db.commit()

        return jsonify({
            "ok": True,
            "message": "Doctor deleted successfully"
        })

# ── Contact Messages ──────────────────────────────────────────────────────────

@admin_bp.route("/messages")
def contact_messages():
    """Admin page to view all contact messages from the public form."""
    if session.get("role") != "Admin":
        return redirect("/login")
    try:
        from models import ContactMessage
        db = next(get_db())
        messages = db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).all()
    except Exception as exc:
        print(f"[admin/messages] error: {exc}")
        messages = []
    return render_template("admin/contact_messages.html", messages=messages)


@admin_bp.route("/api/admin/messages/<int:mid>/read", methods=["POST"])
def api_mark_message_read(mid):
    """Mark a contact message as read."""
    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 401
    try:
        from models import ContactMessage
        db = next(get_db())
        msg = db.query(ContactMessage).filter(ContactMessage.msg_id == mid).first()
        if not msg:
            return jsonify({"error": "Not found"}), 404
        msg.is_read = True
        db.commit()
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@admin_bp.route("/api/admin/messages/<int:mid>", methods=["DELETE"])
def api_delete_message(mid):
    """Delete a contact message."""
    if session.get("role") != "Admin":
        return jsonify({"error": "Unauthorized"}), 401
    try:
        from models import ContactMessage
        db = next(get_db())
        msg = db.query(ContactMessage).filter(ContactMessage.msg_id == mid).first()
        if not msg:
            return jsonify({"error": "Not found"}), 404
        db.delete(msg)
        db.commit()
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── Global Audit Logs API (used by admin & receptionist templates) ─────────────

@admin_bp.route("/api/audit-logs")
def api_audit_logs():
    """
    Shared audit log API used by admin/audit_logs.html and
    receptionist/audit_logs.html templates.
    Accessible by Admin and Receptionist; Auditor uses /auditor/api/audit-logs.
    """
    role = session.get("role")
    if role not in ("Admin", "Receptionist", "Auditor"):
        return jsonify({"detail": "Forbidden"}), 403

    page     = int(request.args.get("page", 1))
    per_page = PAGINATION.get("audit_logs", 15)

    user_filter   = request.args.get("user", "").strip()
    role_filter   = request.args.get("role", "").strip()
    action_filter = request.args.get("action", "").strip()
    date_from     = request.args.get("date_from", "").strip()
    date_to       = request.args.get("date_to", "").strip()

    db = next(get_db())
    q  = db.query(AuditLog)

    # Receptionists only see their own role
    if role == "Receptionist":
        q = q.filter(AuditLog.role == "Receptionist")
    elif role_filter:
        q = q.filter(AuditLog.role == role_filter)

    if user_filter:
        q = q.filter(AuditLog.user_name.ilike(f"%{user_filter}%"))
    if action_filter:
        q = q.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    if date_from:
        try:
            import datetime as _dt
            q = q.filter(AuditLog.timestamp >= _dt.datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            import datetime as _dt
            end = _dt.datetime.fromisoformat(date_to) + _dt.timedelta(days=1)
            q = q.filter(AuditLog.timestamp < end)
        except ValueError:
            pass

    import math as _math
    total = q.count()
    rows  = q.order_by(AuditLog.timestamp.desc())\
             .offset((page - 1) * per_page)\
             .limit(per_page)\
             .all()

    items = [{
        "id"        : r.id,
        "timestamp" : r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if r.timestamp else "—",
        "user_name" : r.user_name or "—",
        "role"      : r.role or "—",
        "action"    : r.action or "—",
        "entity"    : r.entity or "—",
        "detail"    : r.detail or "—",
    } for r in rows]

    return jsonify({
        "items"      : items,
        "total"      : total,
        "total_pages": _math.ceil(total / per_page) or 1,
        "page"       : page,
    })


@admin_bp.route("/api/audit-logs/export")
def api_audit_logs_export():
    """CSV export of audit logs."""
    role = session.get("role")
    if role not in ("Admin", "Auditor"):
        return jsonify({"detail": "Forbidden"}), 403

    import csv, io as _io
    import datetime as _dt

    role_filter   = request.args.get("role", "").strip()
    action_filter = request.args.get("action", "").strip()
    date_from     = request.args.get("date_from", "").strip()
    date_to       = request.args.get("date_to", "").strip()

    db = next(get_db())
    q  = db.query(AuditLog)

    if role_filter:
        q = q.filter(AuditLog.role == role_filter)
    if action_filter:
        q = q.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    if date_from:
        try:
            q = q.filter(AuditLog.timestamp >= _dt.datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            end = _dt.datetime.fromisoformat(date_to) + _dt.timedelta(days=1)
            q = q.filter(AuditLog.timestamp < end)
        except ValueError:
            pass

    rows = q.order_by(AuditLog.timestamp.desc()).limit(10000).all()

    output = _io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "User", "Role", "Action", "Entity", "Detail"])
    for r in rows:
        writer.writerow([
            r.id,
            r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if r.timestamp else "",
            r.user_name or "", r.role or "", r.action or "",
            r.entity or "", r.detail or "",
        ])

    from flask import make_response
    resp = make_response(output.getvalue())
    resp.headers["Content-Type"] = "text/csv"
    resp.headers["Content-Disposition"] = (
        f"attachment; filename=audit_logs_{_dt.date.today()}.csv"
    )
    return resp
@admin_bp.route("/doctor-leaves")
def doctor_leaves():

    db = next(get_db())

    leaves = (
        db.query(
            DoctorLeave,
            Doctor,
            Department
        )
        .join(
            Doctor,
            DoctorLeave.doctor_id == Doctor.doct_Id
        )
        .join(
            Department,
            Doctor.dept_Id == Department.dept_Id
        )
        .order_by(DoctorLeave.created_at.desc())
        .all()
    )

    return render_template(
        "admin/doctor_leaves.html",
        leaves=leaves
    )
@admin_bp.route("/doctor-leave/<int:leave_id>/approve")
def approve_doctor_leave(leave_id):

    db = next(get_db())

    leave = db.query(DoctorLeave).filter(
        DoctorLeave.leave_Id == leave_id
    ).first()

    if not leave:
        flash("Leave request not found", "danger")
        return redirect("/admin/doctor-leaves")

    leave.status = "Approved"

    leave.approved_by = session.get("user_id")

    leave.approved_on = datetime.datetime.utcnow()

    db.commit()

    flash("Leave approved successfully", "success")

    return redirect("/admin/doctor-leaves")

@admin_bp.route("/doctor-leave/<int:leave_id>/reject")
def reject_doctor_leave(leave_id):

    db = next(get_db())

    leave = db.query(DoctorLeave).filter(
        DoctorLeave.leave_Id == leave_id
    ).first()

    if not leave:
        flash("Leave request not found", "danger")
        return redirect("/admin/doctor-leaves")

    leave.status = "Rejected"

    leave.approved_by = session.get("user_id")

    leave.approved_on = datetime.datetime.utcnow()

    db.commit()

    flash("Leave rejected", "warning")

    return redirect("/admin/doctor-leaves")