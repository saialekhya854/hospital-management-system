from flask import Blueprint, render_template, request, session, redirect, jsonify
from database import get_db
from models import (
    Patient,
    Appointment,
    Bill,
    MedicalRecord,
    Doctor,
    Department,
    AuditLog,
    DoctorLeave
)
import datetime
from datetime import timezone

patient_bp = Blueprint("patient", __name__, url_prefix="/patient")

# ── Auth guard ─────────────────────────
def _guard():
    if session.get("role") != "Patient":
        return redirect("/login")
    return None

def _patient_id():
    pid = session.get("entity_id")
    print("PATIENT ID:", pid)   
    return pid

# ── Pages ─────────────────────────

@patient_bp.route("/profile")
def profile():
    g = _guard()
    if g: return g
    return render_template("patient/profile.html")


@patient_bp.route("/appointments")
def appointments():
    g = _guard()
    if g: return g
    return render_template("patient/my_appointments.html")


@patient_bp.route("/bills")
def bills():
    g = _guard()
    if g: return g
    return render_template("patient/my_bills.html")


@patient_bp.route("/treatments")
def treatments():
    g = _guard()
    if g: return g
    return render_template("patient/view_treatments.html")


# ── API PROFILE ─────────────────────────

@patient_bp.route("/api/profile")
def api_profile():
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())
    p = db.query(Patient).filter(Patient.patient_Id == _patient_id()).first()

    if not p:
        return jsonify({"detail": "Not found"}), 404

    return jsonify({
        "FName": p.FName,
        "LName": p.LName,
        "contact_No": p.contact_No,
        "Date_Of_Birth": p.Date_Of_Birth.strftime("%Y-%m-%d") if p.Date_Of_Birth else None,
        "Address": p.pt_Address,
        "Gender": p.Gender
    })

@patient_bp.route("/api/profile", methods=["PUT"])
def update_profile():
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    data = request.get_json()
    db = next(get_db())

    p = db.query(Patient).filter(
        Patient.patient_Id == _patient_id()
    ).first()

    if not p:
        return jsonify({"detail": "Not found"}), 404

    # ✅ Update fields
    p.FName = data.get("fname", p.FName)
    p.LName = data.get("lname", p.LName)
    p.contact_No = data.get("phone", p.contact_No)
    p.pt_Address = data.get("address", p.pt_Address)
    p.Gender = data.get("gender", p.Gender)

    if data.get("dob"):
        p.Date_Of_Birth = datetime.datetime.strptime(
            data.get("dob"), "%Y-%m-%d"
        ).date()

    db.commit()

    return jsonify({"ok": True})

# ── API APPOINTMENTS ─────────────────────────

@patient_bp.route("/api/appointments")
def api_appointments():
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())
    tab = request.args.get("tab", "All")

    today = datetime.datetime.now(timezone.utc).date()

    appts = db.query(Appointment).filter(
        Appointment.patient_Id == _patient_id()
    ).all()

    data = []

    for a in appts:
        date = a.appointment_Date
        status = (a.appointment_status or "").strip().lower()

        print("Checking:", date, status, "TAB:", tab)

        if tab == "Upcoming":
            if not (date and date >= today and status == "scheduled"):
                continue

        elif tab == "Past":
            if not (date and date < today):
                continue

        elif tab == "Cancelled":
            if status != "cancelled":
                continue

        print("REQUEST DATA:", data)

        doc = db.query(Doctor).filter(Doctor.doct_Id == a.doct_Id).first()

        doctor_name = f"{doc.FName} {doc.LName}" if doc else "-"

        data.append({
            "appointment_id": a.appointment_Id,
            "date": date.strftime("%Y-%m-%d") if date else None,
            "status": status,
            "reason": a.reason,
            "doctor": doctor_name
        })

    return jsonify(data)

@patient_bp.route("/api/appointments", methods=["POST"])
def create_appointment():
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    data = request.get_json()
    db = next(get_db())

    now = datetime.datetime.now(timezone.utc)

    appt_date = datetime.datetime.strptime(
        data.get("appointment_date"), "%Y-%m-%d"
    ).date()

    appt_time = datetime.datetime.strptime(
        data.get("appointment_time"), "%H:%M"
    ).time()

    # Block past date
    if appt_date < now.date():
        return jsonify({"error": "Cannot book past date"}), 400

    # Block past time (same day)
    if appt_date == now.date() and appt_time <= now.time():
        return jsonify({"error": "Cannot book past time"}), 400
    
    # Prevent booking when doctor is on leave
    doctor_leave = db.query(DoctorLeave).filter(
    DoctorLeave.doctor_id == int(data.get("doct_id")),
    DoctorLeave.leave_date == appt_date,
    DoctorLeave.status == "Approved"
    ).first()

    if doctor_leave:
        return jsonify({
            "error": "Doctor is unavailable on selected date"
        }), 400
    # Prevent double booking
    existing = db.query(Appointment).filter(
        Appointment.doct_Id == int(data.get("doct_id")),
        Appointment.appointment_Date == appt_date,
        Appointment.slot_time == appt_time,
        Appointment.appointment_status != "Cancelled"
    ).first()

    if existing:
        return jsonify({"error": "Slot already booked"}), 400
    print("REQUEST DATA:", data)
    new_appt = Appointment(
        patient_Id=_patient_id(),
        doct_Id=int(data.get("doct_id")),   

        reason=data.get("reason"),
        appointment_Date=datetime.datetime.strptime(
            data.get("appointment_date"), "%Y-%m-%d"
        ).date(),

        slot_time = datetime.datetime.strptime(
            data.get("appointment_time"), "%H:%M"
        ).time(),

        appointment_status="scheduled",
        mode_of_appointment=data.get("mode_of_appointment")
    )

    db.add(new_appt)
    db.commit()

    return jsonify({"message": "Appointment booked successfully"})

@patient_bp.route("/api/appointments/<int:appt_id>/cancel", methods=["PATCH"])
def cancel_appointment(appt_id):
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())

    appt = db.query(Appointment).filter(
        Appointment.appointment_Id == appt_id,
        Appointment.patient_Id == _patient_id()
    ).first()

    if not appt:
        return jsonify({"error": "Appointment not found"}), 404

    if (appt.appointment_status or "").lower() != "scheduled":
        return jsonify({"error": "Only scheduled appointments can be cancelled"}), 400

    # ⏱️ Optional: prevent cancel within 1 hour
    now = datetime.datetime.now(timezone.utc)
    appt_datetime = datetime.datetime.combine(
    appt.appointment_Date,
    appt.slot_time
).replace(tzinfo=timezone.utc)

    if (appt_datetime - now).total_seconds() <= 3600:
        return jsonify({"error": "Cannot cancel within 1 hour of appointment"}), 400

    appt.appointment_status = "Cancelled"
    db.commit()

    return jsonify({"message": "Appointment cancelled successfully"})

@patient_bp.route("/api/departments")
def api_departments():
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())

    depts = db.query(Department).all()

    return jsonify([
        {"dept_Id": d.dept_Id, "dept_Name": d.dept_Name}
        for d in depts
    ])

@patient_bp.route("/api/doctors/<int:dept_id>")
def api_doctors(dept_id):

    g = _guard()
    if g:
        return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())

    doctors = db.query(Doctor).filter(
        Doctor.dept_Id == dept_id
    ).all()

    today = datetime.datetime.now(timezone.utc).date()

    data = []

    for d in doctors:

        leave_exists = db.query(DoctorLeave).filter(
            DoctorLeave.doctor_id == d.doct_Id,
            DoctorLeave.leave_date == today,
            DoctorLeave.status == "Approved"
        ).first()

        data.append({
            "doct_Id": d.doct_Id,
            "FName": d.FName,
            "LName": d.LName,
            "is_on_leave": bool(leave_exists)
        })

    return jsonify(data)

@patient_bp.route("/api/slots")
def api_slots():
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    doctor_id = int(request.args.get("doctor_id"))
    date = datetime.datetime.strptime(
        request.args.get("date"), "%Y-%m-%d"
    ).date()

    db = next(get_db())

    doctor_leave = db.query(DoctorLeave).filter(
    DoctorLeave.doctor_id == doctor_id,
    DoctorLeave.leave_date == date,
    DoctorLeave.status == "Approved"
    ).first()

    if doctor_leave:

        return jsonify({
            "doctor_unavailable": True,
            "slots": []
        })

    all_slots = [
        "10:00", "11:00", "12:00", 
        "14:00", "15:00", "16:00", 
        "17:00"
    ]

    booked = db.query(Appointment).filter(
        Appointment.doct_Id == doctor_id,
        Appointment.appointment_Date == date
    ).all()

    booked_times = [
        a.slot_time.strftime("%H:%M")
        for a in booked if a.slot_time
    ]

    now = datetime.datetime.now(timezone.utc)

    slots = []
    for s in all_slots:
        slot_time = datetime.datetime.strptime(s, "%H:%M").time()

        is_past = (
            date == now.date() and slot_time <= now.time()
        )

        slots.append({
            "time": s,
            "taken": (s in booked_times) or is_past
        })

    return jsonify({"slots": slots})

# ── API BILLS ─────────────────────────

@patient_bp.route("/api/bills")
def api_bills():
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())

    bills = db.query(Bill).filter(
        Bill.patient_Id == _patient_id()
    ).all()

    data = []
    for b in bills:
        data.append({
            "bill_id": b.bill_id,
            "type": b.bill_type,
            "total": b.total_amount,
            "paid": b.amount_paid,
            "balance": b.balance,
            "status": b.status,
            "date": b.created_at.strftime("%Y-%m-%d") if b.created_at else None
        })

    return jsonify(data)


# ── API TREATMENTS ─────────────────────────

@patient_bp.route("/api/treatments")
def api_treatments():
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())

    rows = db.query(
        MedicalRecord,
        Doctor
    ).outerjoin(
        Doctor, MedicalRecord.doct_Id == Doctor.doct_Id
    ).filter(
        MedicalRecord.patient_Id == _patient_id()
    ).order_by(
        MedicalRecord.visit_Date.desc()
    ).all()

    data = []

    for r, d in rows:
        doctor_name = f"Dr. {d.FName} {d.LName}" if d else "—"

        data.append({
            "date": r.visit_Date.strftime("%Y-%m-%d") if r.visit_Date else None,
            "diagnosis": r.diagnosis,
            "treatment": r.treatment,
            "prescription": r.prescription,

            "doctor": doctor_name,

            "followup_required": r.followup_required,
            "followup_date": r.next_Visit.strftime("%Y-%m-%d") if r.next_Visit else None
        })

    return jsonify(data)

from flask import make_response

@patient_bp.route("/api/billing/<int:bill_id>/invoice")
def download_invoice(bill_id):

    g = _guard()
    if g:
        return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())

    bill = db.query(Bill).filter(
        Bill.bill_id == bill_id,
        Bill.patient_Id == _patient_id()
    ).first()

    if not bill:
        return jsonify({"error": "Bill not found"}), 404

    invoice_text = f"""
<html>
<head>
    <title>Invoice</title>
</head>
<body style="font-family: Arial; padding: 30px;">
    <h1>LIFECARE HOSPITAL</h1>
    <hr>

    <h2>Invoice</h2>

    <p><strong>Invoice ID:</strong> BL-{str(bill.bill_id).zfill(4)}</p>
    <p><strong>Date:</strong> {bill.created_at.strftime("%Y-%m-%d") if bill.created_at else ''}</p>

    <p><strong>Type:</strong> {bill.bill_type}</p>
    <p><strong>Total:</strong> ₹{bill.total_amount}</p>
    <p><strong>Paid:</strong> ₹{bill.amount_paid}</p>
    <p><strong>Balance:</strong> ₹{bill.balance}</p>
    <p><strong>Status:</strong> {bill.status}</p>

    <br><br>

    <p>Thank you for visiting LIFECARE HOSPITAL.</p>
</body>
</html>
"""

    response = make_response(invoice_text)

    response.headers["Content-Type"] = "text/plain"
    response.headers["Content-Disposition"] = (
        f"attachment; filename=invoice_{bill.bill_id}.txt"
    )

    return response