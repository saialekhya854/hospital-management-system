from pydoc import doc

from flask import Blueprint, render_template, request, session, redirect, jsonify
from database import get_db
from models import Doctor, DoctorLeave, User, Department, Appointment, Patient, MedicalRecord, TreatmentCatalogue, Bill, AuditLog
from datetime import date, datetime, timedelta
from sqlalchemy import func
import datetime as dt
from werkzeug.utils import secure_filename
from flask import current_app
import os

doctor_bp = Blueprint("doctor", __name__, url_prefix="")

# ── Auth guard ─────────────────────────────────────────────────────────────────
def _guard():
    if session.get("role", "").lower() != "doctor":
        return jsonify({"detail": "Unauthorized"}), 401
    return None


# ══════════════════════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════════════════════

@doctor_bp.route("/doctor/appointments")
def appointments_page():
    if session.get("role", "").lower() != "doctor":
        return redirect("/login")
    return render_template("doctor/appointments.html")


@doctor_bp.route("/doctor/calendar")
def doctor_calendar():
    if session.get("role", "").lower() != "doctor":
        return redirect("/login")
    return render_template("doctor/calendar.html")


@doctor_bp.route("/doctor/patient-history")
def patient_history():
    if session.get("role", "").lower() != "doctor":
        return redirect("/login")
    return render_template("doctor/patient_history.html")


@doctor_bp.route("/doctor/add-treatment")
def add_treatment():
    if session.get("role", "").lower() != "doctor":
        return redirect("/login")
    return render_template("doctor/add_treatment.html")


@doctor_bp.route("/doctor/profile")
def doctor_profile():
    if session.get("role", "").lower() != "doctor":
        return redirect("/login")
    print("PROFILE SESSION:", dict(session))
    return render_template("doctor/profile.html")

@doctor_bp.route("/api/doctor/profile", methods=["GET", "PUT"])
def api_doctor_profile():
    g = _guard()
    if g:
        return g

    db = next(get_db())
    did = session.get("entity_id")

    # ─────── UPDATE PROFILE ───────
    if request.method == "PUT":
        body = request.form

        doc = db.query(Doctor).filter(Doctor.doct_Id == did).first()

        if not doc:
            return jsonify({"error": "Doctor not found"}), 404

        # UPDATE DOCTOR FIELDS
        doc.FName = body.get("fname", doc.FName)
        doc.LName = body.get("lname", doc.LName)
        doc.contact_No = body.get("contact_no", doc.contact_No)
        doc.office_No = body.get("office_no", doc.office_No)
        image = request.files.get("profile_image")
        print("IMAGE OBJECT:", image)
        if image and image.filename:

            filename = secure_filename(image.filename)

            upload_folder = os.path.join(
                current_app.root_path,
                "static/uploads/doctors"
            )

            os.makedirs(upload_folder, exist_ok=True)

            image_path = os.path.join(upload_folder, filename)

            image.save(image_path)

            doc.profile_image = filename
            print("FILENAME SAVED:", filename)
            print("DB VALUE:", doc.profile_image)
        # ADD THIS BLOCK (THIS IS YOUR FIX)
        user = db.query(User).filter(User.User_ID == doc.User_ID).first()
        if user:
            user.Email = body.get("email", user.Email)

        db.commit()

        return jsonify({"message": "Profile updated successfully"})


    # ─────── GET PROFILE ───────
    result = db.query(Doctor, Department, User)\
        .outerjoin(Department, Doctor.dept_Id == Department.dept_Id)\
        .join(User, Doctor.User_ID == User.User_ID)\
        .filter(Doctor.doct_Id == did)\
        .first()

    if not result:
        return jsonify({"error": "Doctor not found"}), 404

    doc, dept, user = result

    return jsonify({
        "doctor_id": doc.doct_Id,
        "first_name": doc.FName,
        "last_name": doc.LName,
        "gender": doc.Gender,
        "contact": doc.contact_No,
        "email": user.Email,
        "department": dept.dept_Name if dept else None,
        "office_no": doc.office_No,
        "profile_image": doc.profile_image,
        "experience": doc.experience_years
    })

# ══════════════════════════════════════════════════════════════════════════════
# API ── APPOINTMENTS
# ══════════════════════════════════════════════════════════════════════════════

@doctor_bp.route("/api/doctor/appointments")
def api_doctor_appointments():
    g = _guard()
    if g:
        return g

    db  = next(get_db())
    did = session.get("entity_id")

    tab      = request.args.get("tab", "today").strip().lower()
    search   = request.args.get("search", "").strip().lower()
    date_str = request.args.get("date")
    today    = datetime.today().date()

    query = (
        db.query(Appointment, Patient)
        .outerjoin(Patient, Patient.patient_Id == Appointment.patient_Id)
        .filter(Appointment.doct_Id == did)
    )

    # Apply tab filter ONLY if date is NOT selected
    if not date_str:
        if tab == "today":
            query = query.filter(
                Appointment.appointment_Date == today,
                func.lower(Appointment.appointment_status).in_([
                    "scheduled",
                    "checked-in",
                    "in-progress",
                    "completed",
                    "no-show"
                ])
            )
        elif tab == "upcoming":
            query = query.filter(Appointment.appointment_Date > today)
        elif tab == "past":
            query = query.filter(Appointment.appointment_Date < today)
        elif tab == "checked_in":
            query = query.filter(
                func.lower(Appointment.appointment_status) == "checked-in"
            )

    # Apply selected date filter
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            query = query.filter(Appointment.appointment_Date == selected_date)
        except Exception:
            pass

    appointments = query.order_by(Appointment.appointment_Date.desc()).all()

    data = []
    for appt, patient in appointments:
        patient_name = f"{patient.FName} {patient.LName}" if patient else "Unknown"

        if search and search not in patient_name.lower():
            continue

        data.append({
            "appointment_Id": appt.appointment_Id,
            "patient_id": appt.patient_Id,
            "patient_name": patient_name,
            "appointment_date": str(appt.appointment_Date),
            "appointment_time": appt.slot_time.strftime("%H:%M") if appt.slot_time else None,
            "appointment_status": (appt.appointment_status or "").lower(),
            "reason": appt.reason,
        })

    return jsonify({
        "items": data,
        "total": len(data),
        "total_pages": 1
    })
# ── NEW: Doctor chart — appointments per day (last 7 days) ─────────────
@doctor_bp.route("/api/doctor/appt-trend")
def api_doctor_appt_trend():
    g = _guard()
    if g: return g

    import datetime as dt
    db  = next(get_db())
    did = session.get("entity_id")
    today = dt.date.today()

    labels, values = [], []
    for i in range(6, -1, -1):
        d = today - dt.timedelta(days=i)
        cnt = db.query(func.count(Appointment.appointment_Id))\
            .filter(
                Appointment.doct_Id == did,
                Appointment.appointment_Date == d
            ).scalar() or 0
        labels.append(d.strftime("%a %d"))
        values.append(cnt)

    return jsonify({"labels": labels, "values": values})


# ── NEW: Doctor chart — treatment distribution ──────────────────────────
@doctor_bp.route("/api/doctor/treatment-dist")
def api_doctor_treatment_dist():
    g = _guard()
    if g: return g

    db  = next(get_db())
    did = session.get("entity_id")

    from models import TreatmentCatalogue, MedicalRecord
    rows = db.query(
        TreatmentCatalogue.category,
        func.count(TreatmentCatalogue.treatment_id)
    ).join(
        MedicalRecord,
        func.lower(MedicalRecord.treatment).contains(
            func.lower(TreatmentCatalogue.treatment_name)
        )
    ).filter(
        MedicalRecord.doct_Id == did
    ).group_by(TreatmentCatalogue.category).all()

    # Fallback: count from treatment_catalogue for this doctor's dept
    if not rows:
        from models import Doctor as DoctorModel
        doc = db.query(DoctorModel).filter(DoctorModel.doct_Id == did).first()
        if doc:
            rows = db.query(
                TreatmentCatalogue.category,
                func.count(TreatmentCatalogue.treatment_id)
            ).filter(
                TreatmentCatalogue.dept_id == doc.dept_Id
            ).group_by(TreatmentCatalogue.category).all()

    if not rows:
        return jsonify({"labels": [], "values": []})

    return jsonify({
        "labels": [r[0] or "General" for r in rows],
        "values": [r[1] for r in rows]
    })

# ── Single appointment detail ──────────────────────────────────────────────────

@doctor_bp.route("/api/doctor/appointment/<int:appt_id>")
def get_appointment_detail(appt_id):
    g = _guard()
    if g:
        return g

    db = next(get_db())

    result = (
        db.query(Appointment, Patient)
          .outerjoin(Patient, Patient.patient_Id == Appointment.patient_Id)
          .filter(
              Appointment.appointment_Id == appt_id,
              Appointment.doct_Id == session.get("entity_id"),
          )
          .first()
    )

    if not result:
        return jsonify({"error": "Appointment not found"}), 404

    appt, patient = result
    patient_name  = (
        f"{patient.FName} {patient.LName}" if patient else "Unknown"
    )

    return jsonify({
        "appointment_Id": appt.appointment_Id,
        "patient_id": appt.patient_Id,
        "patient_name": patient_name,

        "date": appt.appointment_Date.strftime("%d-%m-%Y")
            if appt.appointment_Date else "",

        "time": appt.slot_time.strftime("%H:%M")
            if appt.slot_time else "",

        "reason": appt.reason or "",
        "status": (appt.appointment_status or "").lower(),
        "token_no": appt.token_no or "",
    })

@doctor_bp.route("/api/doctor/patient-history/<int:patient_id>")
def api_patient_history(patient_id):
    g = _guard()
    if g:
        return g

    db = next(get_db())
    did = session.get("entity_id")

    page = int(request.args.get("page", 1))
    per_page = 5

    query = (
        db.query(MedicalRecord, Doctor)
        .join(Doctor, MedicalRecord.doct_Id == Doctor.doct_Id)
        .filter(
            MedicalRecord.patient_Id == patient_id,
            MedicalRecord.doct_Id == did
        )
    )

    total = query.count()

    records = (
        query.order_by(MedicalRecord.visit_Date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    data = []

    for r, d in records:
        data.append({
        "visit_Date": r.visit_Date.strftime("%Y-%m-%d") if r.visit_Date else None,
        "doctor_name": f"{d.FName} {d.LName}",
        "diagnosis": r.diagnosis,
        "treatment": r.treatment,
        "prescription": r.prescription,
        "bp": r.curr_Blood_Pressure,
        "temp": r.curr_Temp_F,
    })

    return jsonify({
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,
        "items": data
    })
# ══ ADD TREATMENT TO CATALOGUE ══
@doctor_bp.route("/api/doctor/treatments/add", methods=["POST"])
def add_treatment_catalogue():
    g = _guard()
    if g:
        return g

    db   = next(get_db())
    body = request.get_json(silent=True) or {}

    name = (body.get("treatment_name") or "").strip()
    if not name:
        return jsonify({"error": "treatment_name is required"}), 400

    # Check for duplicate
    existing = db.query(TreatmentCatalogue).filter(
        TreatmentCatalogue.treatment_name.ilike(name)
    ).first()
    if existing:
        return jsonify({"error": f'Treatment "{name}" already exists', "treatment_id": existing.treatment_id}), 409

    # Get doctor's dept_id to associate
    from models import Doctor
    did = session.get("entity_id")
    doc = db.query(Doctor).filter(Doctor.doct_Id == did).first()

    new_t = TreatmentCatalogue(
        treatment_name = name,
        category       = (body.get("category") or "").strip() or None,
        default_cost   = _float(body.get("default_cost")),
        dept_id        = doc.dept_Id if doc else None,
    )
    db.add(new_t)
    db.commit()
    db.refresh(new_t)

    return jsonify({
        "message":      "Treatment added to catalogue",
        "treatment_id": new_t.treatment_id,
        "treatment_name": new_t.treatment_name,
    }), 201


# ══ MARK NO-SHOW — called by scheduler or manually ══
@doctor_bp.route("/api/doctor/mark-no-shows", methods=["POST"])
def mark_no_shows():
    """
    Mark appointments as No-Show if:
    - appointment_Date < today  AND  status == 'Scheduled'
    OR
    - appointment is today, appointment_Time <= now - 15 min, status == 'Scheduled'
    """
    

    # Allow scheduler (no session) or doctor
    role = session.get("role", "").lower()
    if role not in ("doctor", "admin", ""):
        return jsonify({"detail": "Unauthorized"}), 401

    db    = next(get_db())
    today = date.today()
    now   = datetime.now()
    cutoff_time = now - timedelta(minutes=15)

    updated = 0

    # 1. Past-date appointments still Scheduled → No-Show
    past_appts = (
        db.query(Appointment)
          .filter(
              Appointment.appointment_Date < today,
              func.lower(Appointment.appointment_status) == "scheduled"
          )
          .all()
    )
    for appt in past_appts:
        appt.appointment_status = "no-show"
        updated += 1

    # 2. Today's appointments past 15-min window still Scheduled → No-Show
    today_appts = (
        db.query(Appointment)
          .filter(
              Appointment.appointment_Date == today,
              func.lower(Appointment.appointment_status) == "scheduled"
          )
          .all()
    )
    for appt in today_appts:
        appt_time = getattr(appt, "appointment_Time", None)
        if appt_time:
            try:
                scheduled_dt = datetime.combine(today, appt_time)
                if scheduled_dt <= cutoff_time:
                    appt.appointment_status = "no-show"
                    updated += 1
            except Exception:
                pass  # No time stored — skip today's

    db.commit()
    return jsonify({"updated": updated, "message": f"{updated} appointment(s) marked as No-Show"})
# ══════════════════════════════════════════════════════════════════════════════
# API ── PATIENT SEARCH  (used by manual picker in add-treatment)
# ══════════════════════════════════════════════════════════════════════════════

@doctor_bp.route("/api/doctor/search-patients")
def search_patients():
    g = _guard()
    if g:
        return g

    q  = request.args.get("q", "").strip()
    db = next(get_db())

    if not q:
        return jsonify([])

    # Search by name or numeric patient ID
    query = db.query(Patient)
    if q.isdigit():
        query = query.filter(Patient.patient_Id == int(q))
    else:
        like = f"%{q}%"
        query = query.filter(
            (Patient.FName + " " + Patient.LName).ilike(like)
        )

    patients = query.limit(10).all()

    return jsonify([
        {
            "patient_Id":  p.patient_Id,
            "FName":       p.FName,
            "LName":       p.LName,
            "Gender":      p.Gender     or "",
            "contact_No":  p.contact_No or "",
        }
        for p in patients
    ])


# ══════════════════════════════════════════════════════════════════════════════
# API ── TREATMENT CATALOGUE  (populates the Treatment <select>)
# ══════════════════════════════════════════════════════════════════════════════

@doctor_bp.route("/api/doctor/treatments")
def get_treatments():
    g = _guard()
    if g:
        return g

    db   = next(get_db())
    cats = db.query(TreatmentCatalogue).order_by(TreatmentCatalogue.treatment_name).all()

    return jsonify([
            {
                "treatment_id":   t.treatment_id,
                "treatment_name": t.treatment_name,
                "category":       t.category,
                "cost":           t.default_cost,
            }
            for t in cats
        ])


# ══════════════════════════════════════════════════════════════════════════════
# API ── ADD TREATMENT  (POST — saves MedicalRecord + marks appointment Done)
# ══════════════════════════════════════════════════════════════════════════════

@doctor_bp.route("/api/doctor/add-treatment", methods=["POST"])
def api_add_treatment():
    g = _guard()
    if g:
        return g

    db   = next(get_db())
    did  = session.get("entity_id")
    body = request.get_json(silent=True) or {}

    patient_id     = body.get("patient_id")
    appointment_id = body.get("appointment_id")
    diagnosis      = (body.get("diagnosis") or "").strip()

    # ── Validation ────────────────────────────────────────────────────────────
    if not patient_id:
        return jsonify({"error": "patient_id is required"}), 400
    if not diagnosis:
        return jsonify({"error": "diagnosis is required"}), 400

    # Verify patient exists
    patient = db.query(Patient).filter(Patient.patient_Id == patient_id).first()
    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    # If appointment_id provided, verify it belongs to this doctor
    if appointment_id:
        appt = (
            db.query(Appointment)
              .filter(
                  Appointment.appointment_Id == appointment_id,
                  Appointment.doct_Id == did,
              )
              .first()
        )
        if not appt:
            return jsonify({"error": "Appointment not found or access denied"}), 404
    else:
        appt = None

    # ── Parse visit date ──────────────────────────────────────────────────────
    visit_date_str = body.get("visit_date")

    try:
        if visit_date_str and visit_date_str != "":
            visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
        else:
            visit_date = datetime.today().date()
    except Exception:
        visit_date = datetime.today().date()

    # ── Parse next-visit date ─────────────────────────────────────────────────
    next_visit_str = body.get("next_visit")
    next_visit = None
    if next_visit_str:
        try:
            next_visit = datetime.strptime(next_visit_str, "%Y-%m-%d").date()
        except ValueError:
            next_visit = None

    # ── Build treatment text (name from catalogue) ────────────────────────────
    treatment_text = body.get("treatment_name") or None

    # ── Save MedicalRecord ────────────────────────────────────────────────────
    record = MedicalRecord(
        doct_Id            = did,
        patient_Id         = patient_id,
        appointment_Id = appointment_id,
        visit_Date         = visit_date,
        curr_Weight        = _float(body.get("curr_weight")),
        curr_height        = _float(body.get("curr_height")),
        curr_Blood_Pressure= body.get("curr_blood_pressure") or None,
        curr_Temp_F        = _float(body.get("curr_temp_f")),
        chief_complaint    = body.get("chief_complaint")  or None,
        diagnosis          = diagnosis,
        treatment          = treatment_text,
        prescription       = body.get("prescription")     or None,
        followup_required  = bool(body.get("followup_required", False)),
        next_Visit         = next_visit,
    )
    db.add(record)

    # ── Update appointment status → Completed ─────────────────────────────────
    if appt and appt.appointment_status not in ("Completed", "Cancelled"):
        appt.appointment_status = "completed"
        appt.completed_at       = datetime.now()

    db.commit()
    db.refresh(record)

    # ── Auto-create Bill linked to this appointment (OPID tracking) ───────────
    treatment_cost = _float(body.get("cost")) or 0

    if treatment_cost > 0:

        treatment_name = body.get("treatment_name") or "General Treatment"

        auto_bill = Bill(
            patient_Id     = patient_id,
            appointment_Id = appointment_id if appointment_id else None,
            bill_type      = "Treatment",
            description    = treatment_name,
            notes          = f"Auto-generated from treatment by Dr. {did}. Diagnosis: {diagnosis[:120]}",
            total_amount   = treatment_cost,
            amount_paid    = 0,
            balance        = treatment_cost,
            status         = "Pending",
            created_by     = session.get("user_id"),
        )

        db.add(auto_bill)
        db.commit()
        # audit log
        db.add(AuditLog(
            user_id   = session.get("user_id"),
            user_name = session.get("user_name", ""),
            role      = session.get("role", ""),
            action    = "AUTO_BILL_CREATED",
            entity    = f"APT-{str(appointment_id).zfill(4)}",
            detail    = f"Bill ₹{treatment_cost} created for patient {patient_id}",
            timestamp = datetime.now(),
        ))
        db.commit()

    return jsonify({
        "message":   "Treatment saved successfully",
        "record_id": record.record_Id,
    }), 201


# ══════════════════════════════════════════════════════════════════════════════
# API ── CALENDAR STATS
# ══════════════════════════════════════════════════════════════════════════════

@doctor_bp.route("/api/doctor/calendar-stats")
def calendar_stats():
    g = _guard()
    if g:
        return g

    db    = next(get_db())
    did   = session.get("entity_id")
    today = datetime.today().date()

    base = db.query(Appointment).filter(Appointment.doct_Id == did)

    return jsonify({
        "total":       base.count(),
        "today":       base.filter(Appointment.appointment_Date == today).count(),
        "scheduled": base.filter(func.lower(Appointment.appointment_status) == "scheduled").count(),
        "completed": base.filter(func.lower(Appointment.appointment_status) == "completed").count(),
        "cancelled": base.filter(func.lower(Appointment.appointment_status) == "cancelled").count(),
        "no_show": base.filter(func.lower(Appointment.appointment_status) == "no-show").count(),
        "in_progress": 0,
        "checked_in":  0,
    })


# ══════════════════════════════════════════════════════════════════════════════
# Utility
# ══════════════════════════════════════════════════════════════════════════════

def _float(val):
    """Safely convert a value to float, returning None on failure."""
    try:
        return float(val) if val not in (None, "", "null") else None
    except (TypeError, ValueError):
        return None

# ─────────────────────────────────────────────────────────────
# API ── GET PATIENT DETAILS (FIXED)
# ─────────────────────────────────────────────────────────────

@doctor_bp.route("/api/doctor/patient/<int:patient_id>")
def get_patient_detail(patient_id):
    g = _guard()
    if g:
        return g

    db = next(get_db())
    p = db.query(Patient).filter(Patient.patient_Id == patient_id).first()

    if not p:
        return jsonify({"error": "Patient not found"}), 404

    return jsonify({
        "patient_Id": p.patient_Id,
        "FName": p.FName,
        "LName": p.LName,
        "Gender": p.Gender,
        "contact_No": p.contact_No,
        "pt_Address": p.pt_Address,   # ✅ FIXED
        "Date_Of_Birth": p.Date_Of_Birth.strftime("%Y-%m-%d") if p.Date_Of_Birth else None  # ✅ FIXED
    })


# ─────────────────────────────────────────────────────────────
# API ── PATIENT HISTORY (FILTERED BY DOCTOR + PATIENT)
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# API ── ALL HISTORY (ONLY CURRENT DOCTOR)
# ─────────────────────────────────────────────────────────────

@doctor_bp.route("/api/doctor/all-history")
def all_history():
    g = _guard()
    if g:
        return g

    db = next(get_db())
    did = session.get("entity_id")  # ✅ current doctor

    records = (
        db.query(MedicalRecord, Doctor, Patient)
        .join(Doctor, MedicalRecord.doct_Id == Doctor.doct_Id)
        .join(Patient, MedicalRecord.patient_Id == Patient.patient_Id)
        .filter(MedicalRecord.doct_Id == did)   # ✅ FIXED
        .order_by(MedicalRecord.visit_Date.desc())
        .all()
    )

    data = []

    for r, d, p in records:
        data.append({
            "visit_Date": r.visit_Date.strftime("%Y-%m-%d") if r.visit_Date else None,
            "doctor_name": f"{d.FName} {d.LName}",
            "patient_name": f"{p.FName} {p.LName}",
            "diagnosis": r.diagnosis,
            "treatment": r.treatment
        })

    return jsonify(data)

# ══════════════════════════════════════════════════════════════════════════════
# DOCTOR DASHBOARD PAGE
# ══════════════════════════════════════════════════════════════════════════════

@doctor_bp.route("/doctor/dashboard")
def doctor_dashboard():
    if session.get("role", "").lower() != "doctor":
        return redirect("/login")
    return render_template("doctor/dashboard.html")


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD API ── 1. Top Diagnoses (bar chart)
# ══════════════════════════════════════════════════════════════════════════════

@doctor_bp.route("/api/doctor/dashboard/top-diagnoses")
def api_doctor_top_diagnoses():
    g = _guard()
    if g:
        return g

    db  = next(get_db())
    did = session.get("entity_id")

    rows = (
        db.query(MedicalRecord.diagnosis, func.count(MedicalRecord.record_Id).label("cnt"))
        .filter(MedicalRecord.doct_Id == did, MedicalRecord.diagnosis != None, MedicalRecord.diagnosis != "")
        .group_by(MedicalRecord.diagnosis)
        .order_by(func.count(MedicalRecord.record_Id).desc())
        .limit(10)
        .all()
    )

    return jsonify({
        "labels": [r[0] for r in rows],
        "values": [r[1] for r in rows]
    })


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD API ── 2. Appointment Trend (line chart, last 30 days weekly)
# ══════════════════════════════════════════════════════════════════════════════

@doctor_bp.route("/api/doctor/dashboard/appt-trend")
def api_doctor_dashboard_appt_trend():
    g = _guard()
    if g:
        return g

    db    = next(get_db())
    did   = session.get("entity_id")
    today = dt.date.today()

    labels, values = [], []
    for i in range(14, -1, -1):
        d = today - dt.timedelta(days=i)
        cnt = (
            db.query(func.count(Appointment.appointment_Id))
            .filter(Appointment.doct_Id == did, Appointment.appointment_Date == d)
            .scalar() or 0
        )
        labels.append(d.strftime("%b %d"))
        values.append(cnt)

    return jsonify({"labels": labels, "values": values})


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD API ── 3. Patients per Doctor (bar chart — hospital-wide)
# ══════════════════════════════════════════════════════════════════════════════

@doctor_bp.route("/api/doctor/dashboard/patients-per-doctor")
def api_doctor_patients_per_doctor():
    g = _guard()
    if g:
        return g

    db = next(get_db())

    rows = (
        db.query(
            Doctor.FName,
            Doctor.LName,
            func.count(func.distinct(Appointment.patient_Id)).label("patient_count")
        )
        .outerjoin(Appointment, Appointment.doct_Id == Doctor.doct_Id)
        .group_by(Doctor.doct_Id, Doctor.FName, Doctor.LName)
        .order_by(func.count(func.distinct(Appointment.patient_Id)).desc())
        .limit(15)
        .all()
    )

    return jsonify({
        "labels": [f"Dr. {r[0]} {r[1]}" for r in rows],
        "values": [r[2] for r in rows]
    })


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD API ── 4. Appointment Status Distribution (pie chart)
# ══════════════════════════════════════════════════════════════════════════════

@doctor_bp.route("/api/doctor/dashboard/appt-status-dist")
def api_doctor_appt_status_dist():
    g = _guard()
    if g:
        return g

    db  = next(get_db())
    did = session.get("entity_id")

    rows = (
        db.query(
            func.lower(Appointment.appointment_status),
            func.count(Appointment.appointment_Id)
        )
        .filter(
            Appointment.doct_Id == did,
            Appointment.appointment_status != None
        )
        .group_by(func.lower(Appointment.appointment_status))
        .all()
    )

    labels = []
    values = []

    for status, count in rows:
        labels.append((status or '').title())
        values.append(count)

    return jsonify({
        "labels": labels,
        "values": values
    })


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD API ── 5. Patient Age Group Distribution (bar chart)
# ══════════════════════════════════════════════════════════════════════════════

@doctor_bp.route("/api/doctor/dashboard/age-groups")
def api_doctor_age_groups():
    g = _guard()
    if g:
        return g

    db  = next(get_db())
    did = session.get("entity_id")

    # Get distinct patients seen by this doctor
    patient_ids = (
        db.query(func.distinct(Appointment.patient_Id))
        .filter(Appointment.doct_Id == did)
        .all()
    )
    patient_ids = [p[0] for p in patient_ids]

    if not patient_ids:
        return jsonify({"labels": ["0–18", "19–35", "36–50", "51–65", "65+"], "values": [0, 0, 0, 0, 0]})

    patients = db.query(Patient.Date_Of_Birth).filter(Patient.patient_Id.in_(patient_ids)).all()

    today = dt.date.today()
    buckets = {"0–18": 0, "19–35": 0, "36–50": 0, "51–65": 0, "65+": 0}

    for (dob,) in patients:
        if not dob:
            continue
        age = (today - dob).days // 365
        if age <= 18:
            buckets["0–18"] += 1
        elif age <= 35:
            buckets["19–35"] += 1
        elif age <= 50:
            buckets["36–50"] += 1
        elif age <= 65:
            buckets["51–65"] += 1
        else:
            buckets["65+"] += 1

    return jsonify({
        "labels": list(buckets.keys()),
        "values": list(buckets.values())
    })

@doctor_bp.route("/doctor/manage-leave", methods=["GET", "POST"])
def manage_leave():

    if session.get("role") != "Doctor":
        return redirect("/login")

    db = next(get_db())

    doctor = db.query(Doctor).filter(
        Doctor.User_ID == session.get("user_id")
    ).first()

    if not doctor:
        return redirect("/doctor/dashboard")

    if request.method == "POST":

        leave_date = request.form.get("leave_date")
        reason = request.form.get("reason")

        leave_date_obj = datetime.strptime(
            leave_date,
            "%Y-%m-%d"
        ).date()

        existing = db.query(DoctorLeave).filter(
            DoctorLeave.doctor_id == doctor.doct_Id,
            DoctorLeave.leave_date == leave_date_obj
        ).first()

        if existing:
            return render_template(
                "doctor/manage_leave.html",
                error="Leave already exists",
                leaves=db.query(DoctorLeave).filter(
                    DoctorLeave.doctor_id == doctor.doct_Id
                ).all()
            )

        leave = DoctorLeave(
            doctor_id=doctor.doct_Id,
            leave_date=leave_date_obj,
            reason=reason
        )

        db.add(leave)
        db.commit()

    leaves = db.query(DoctorLeave).filter(
        DoctorLeave.doctor_id == doctor.doct_Id
    ).order_by(
        DoctorLeave.leave_date.desc()
    ).all()

    return render_template(
        "doctor/manage_leave.html",
        leaves=leaves
    )
