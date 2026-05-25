import uuid

from flask import Blueprint, app, render_template, request, session, redirect, jsonify, current_app
from sqlalchemy import String, func, text, and_
from database import get_db
from models import (
    BillItem,
    FeeMaster,
    Patient,
    Appointment,
    Doctor,
    Department,
    Bill,
    Payment,
    User,
    AuditLog,
    TreatmentCatalogue,
    DoctorLeave
)
from config import PAGINATION
import math
from datetime import date, datetime, timedelta, timezone
from werkzeug.security import generate_password_hash
from flask_mail import Message
from config import mail

receptionist_bp = Blueprint("receptionist", __name__, url_prefix="/receptionist")

def send_email(subject, recipients, body):
    msg = Message(subject, recipients=recipients)
    msg.body = body
    mail.send(msg)

# ── Auth guard ────────────────────────────────────────────────────────────────

def _guard():
    if session.get("role") not in ("Receptionist", "Admin"):
        return redirect("/login")
    return None

def _log(db, action, entity=None, detail=None):
    db.add(AuditLog(
        user_id=session.get("user_id"), user_name=session.get("user_name",""),
        role=session.get("role",""), action=action, entity=entity, detail=detail,
        timestamp=datetime.now(timezone.utc)
    ))
    db.commit()

# ── Page routes ───────────────────────────────────────────────────────────────

@receptionist_bp.route("/dashboard")
def dashboard():
    g = _guard()
    if g: return g
    return render_template("receptionist/dashboard.html")

@receptionist_bp.route("/register-patient")
def register_patient():
    g = _guard()
    if g: return g
    return render_template("receptionist/register_patient.html")

@receptionist_bp.route("/book-appointment")
def book_appointment():
    g = _guard()
    if g: return g
    return render_template("receptionist/book_appointment.html")

@receptionist_bp.route("/check-in")
def check_in():
    g = _guard()
    if g: return g
    return render_template("receptionist/check_in.html")

@receptionist_bp.route("/generate-bill")
def generate_bill_page():
    g = _guard()
    if g: return g
    return render_template("receptionist/generate_bill.html")

@receptionist_bp.route("/record-payment")
def record_payment():
    g = _guard()
    if g: return g
    return render_template("receptionist/record_payment.html")

@receptionist_bp.route("/audit-logs")
def audit_logs():
    g = _guard()
    if g: return g
    return render_template("receptionist/audit_logs.html")

# ══════════════════════════════════════════════════════════════════════════════
#  API — Dashboard stats
# ══════════════════════════════════════════════════════════════════════════════

@receptionist_bp.route("/api/dashboard-stats")
def api_dashboard_stats():
    g = _guard()
    if g: return jsonify({"detail":"Forbidden"}), 403

    db    = next(get_db())
    today = datetime.now(timezone.utc).date()
    appts_today = db.query(func.count(Appointment.appointment_Id))\
        .filter(Appointment.appointment_Date == today).scalar() or 0

    checked_in = db.query(func.count(Appointment.appointment_Id))\
        .filter(
            Appointment.appointment_Date == today,
            func.lower(Appointment.appointment_status) == "checked-in"
        ).scalar() or 0

    pending_checkin = db.query(func.count(Appointment.appointment_Id))\
        .filter(
            Appointment.appointment_Date == today,
            func.lower(Appointment.appointment_status) == "scheduled"
        ).scalar() or 0

    bills_pending = db.query(func.count(Bill.bill_id))\
        .filter(Bill.status.in_(["Pending", "Partial"]),
                Bill.appointment_Id.isnot(None)).scalar() or 0

    return jsonify({
        "appts_today": appts_today,
        "checked_in": checked_in,
        "pending_checkin": pending_checkin,
        "bills_pending": bills_pending,
    })

# ══════════════════════════════════════════════════════════════════════════════
#  API — Today's queue (paginated)
# ══════════════════════════════════════════════════════════════════════════════
# ── NEW: Receptionist chart — appointments per day (last 7 days) ────────
@receptionist_bp.route("/api/appt-trend")
def api_recept_appt_trend():
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    import datetime as dt
    db    = next(get_db())
    today = dt.date.today()

    labels, values = [], []
    for i in range(6, -1, -1):
        d = today - dt.timedelta(days=i)
        cnt = db.query(func.count(Appointment.appointment_Id))\
            .filter(Appointment.appointment_Date == d).scalar() or 0
        labels.append(d.strftime("%a %d"))
        values.append(cnt)

    return jsonify({"labels": labels, "values": values})


# ── NEW: Receptionist chart — appointment status breakdown (last 30 days)
@receptionist_bp.route("/api/appt-status-dist")
def api_recept_appt_status():
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    import datetime as dt
    db    = next(get_db())
    today = dt.date.today()
    thirty_ago = today - dt.timedelta(days=29)

    normalized_status = func.initcap(
    func.lower(Appointment.appointment_status)
    )

    rows = db.query(
        normalized_status.label("status"),
        func.count(Appointment.appointment_Id)
    ).filter(
        Appointment.appointment_Date >= thirty_ago
    ).group_by(
        normalized_status
    ).all()

    if not rows:
        return jsonify({"labels": [], "values": []})

    return jsonify({
        "labels": [
            (r[0] or "Unknown").replace("Checked-In", "Checked-In")
            for r in rows
        ],
        "values": [r[1] for r in rows]
    })


@receptionist_bp.route("/api/today-queue")
def api_today_queue():
    g = _guard()
    if g: return jsonify({"detail":"Forbidden"}), 403

    page     = int(request.args.get("page", 1))
    per_page = PAGINATION["appointments"]
    db       = next(get_db())
    today = datetime.now(timezone.utc).date()

    q = db.query(Appointment, Patient, Doctor, Department)\
          .join(Patient,    Patient.patient_Id == Appointment.patient_Id)\
          .join(Doctor,     Doctor.doct_Id     == Appointment.doct_Id)\
          .outerjoin(Department, Department.dept_Id == Doctor.dept_Id)\
          .filter(Appointment.appointment_Date == today)\
          .order_by(Appointment.appointment_Date)

    total = q.count()
    rows  = q.offset((page-1)*per_page).limit(per_page).all()

    items = [{
        "appointment_Id"    : a.appointment_Id,
        "patient_name"      : f"{p.FName} {p.LName}",
        "doctor_name"       : f"Dr. {d.FName} {d.LName}",
        "dept_name"         : dept.dept_Name if dept else "—",
        "appointment_time"  : f"{a.appointment_Date} {a.slot_time}" if a.slot_time else str(a.appointment_Date),
        "appointment_status": a.appointment_status,
    } for a, p, d, dept in rows]

    return jsonify({"items": items, "total": total,
                    "total_pages": math.ceil(total/per_page) or 1})

# ══════════════════════════════════════════════════════════════════════════════
#  API — Register patient
# ══════════════════════════════════════════════════════════════════════════════

@receptionist_bp.route("/api/register-patient", methods=["POST"])
def api_register_patient():
    g = _guard()
    if g: return jsonify({"detail":"Forbidden"}), 403

    body = request.get_json() or {}
    db   = next(get_db())

    try:
        dob_date = date.fromisoformat(body.get("dob")) if body.get("dob") else None
    except ValueError:
        return jsonify({"detail": "Invalid date of birth"}), 400

    # Create patient
    patient = Patient(
        FName=body.get("fname",""),
        LName=body.get("lname",""),
        Gender=body.get("gender",""),
        Date_Of_Birth=dob_date,
        contact_No=body.get("phone",""),
        pt_Address=body.get("address",""),
        blood_group = body.get("blood_group"),
        email = body.get("email","").strip()
    )
    db.add(patient)
    db.flush()

    email    = body.get("email","").strip()
    password = body.get("password","")
    print("➡ Sending email to:", email)
    # Create user — if email provided but no password, auto-generate one
    if email:
        import secrets, string
        if not password:
            alphabet = string.ascii_letters + string.digits
            password = "".join(secrets.choice(alphabet) for _ in range(10))

        existing_user = db.query(User).filter(User.Email == email).first()

        if existing_user:
            # RESET PASSWORD
            existing_user.Password = generate_password_hash(password)

            patient.User_ID = existing_user.User_ID

        else:
            user = User(
                Email=email,
                Password=generate_password_hash(password),
                Name=f"{body.get('fname','')} {body.get('lname','')}",
                Role_ID=5,
                Linked_Entity_ID=patient.patient_Id,
                is_active=True,
            )

            db.add(user)
            db.flush()
            patient.User_ID = user.User_ID

        user = User(
            Email=email,
            Password=generate_password_hash(password),
            Name=f"{body.get('fname','')} {body.get('lname','')}",
            Role_ID=5,
            Linked_Entity_ID=patient.patient_Id,
            is_active=True,
        )

        db.add(user)
        db.flush()
        patient.User_ID = user.User_ID

        # SEND EMAIL
        try:
            print("➡ Inside email block")
            send_email(
                "Patient Account Created",
                [email],
                f"""
                    Dear {body.get('fname')} {body.get('lname')},

                    Welcome to HMS.

                    Login Email : {email}
                    Password : {password}

                    Regards,
                    HMS Team
                    """
                                )
        except Exception as e:
            print("MAIL ERROR:", e)

    db.commit()

    _log(db, "REGISTER_PATIENT",
         entity=f"PT-{str(patient.patient_Id).zfill(4)}",
         detail=f"New patient: {patient.FName} {patient.LName}")

    return jsonify({"ok": True, "patient_id": patient.patient_Id})

@receptionist_bp.route("/test-mail")
def test_mail():
    try:
        send_email(
            "Test Mail",
            ["your_email@gmail.com"],
            "This is a test email"
        )
        return "Mail Sent"
    except Exception as e:
        return str(e)
# ══════════════════════════════════════════════════════════════════════════════
#  API — Book appointment
# ══════════════════════════════════════════════════════════════════════════════

@receptionist_bp.route("/api/book-appointment", methods=["POST"])
def api_book_appointment():
    g = _guard()
    if g:
        return jsonify({"detail": "Forbidden"}), 403

    body = request.get_json() or {}
    db = next(get_db())

    try:
        appt_date = datetime.fromisoformat(body.get("appointment_date")).date()
        slot_time = datetime.strptime(body.get("appointment_time"), "%H:%M").time()
    except Exception:
        return jsonify({"detail": "Invalid date or time"}), 400

    doctor_id = body.get("doct_id")
    # Prevent booking when doctor is on leave
    doctor_leave = db.query(DoctorLeave).filter(
        DoctorLeave.doctor_id == doctor_id,
        DoctorLeave.leave_date == appt_date,
        DoctorLeave.status == "Approved"
    ).first()

    if doctor_leave:
        return jsonify({
            "detail": "Doctor is unavailable on selected date"
        }), 400
    # CHECK SLOT PROPERLY (IMPORTANT FIX)
    existing = db.query(Appointment).filter(
        Appointment.doct_Id == doctor_id,
        Appointment.appointment_Date == appt_date,
        Appointment.slot_time == slot_time,
        func.lower(Appointment.appointment_status) != "cancelled"
    ).first()

    if existing:
        return jsonify({"detail": "Slot already taken"}), 400

    # ✅ SET CONSULTATION FEE (SIMPLE LOGIC)
    consultation_fee = 500  # you can improve later

    # ✅ CREATE APPOINTMENT (ALL FIELDS FILLED)
    appt = Appointment(
        patient_Id = body.get("patient_id"),
        doct_Id = doctor_id,
        reason = body.get("reason", ""),
        appointment_Date = appt_date,
        slot_time = slot_time,                     
        consultation_fee = consultation_fee,      
        payment_status = "Pending",               
        mode_of_appointment = body.get("mode_of_appointment", "In-Person"),
        appointment_status = "scheduled"
    )

    db.add(appt)
    db.commit()

    #  LOGGING
    _log(
        db,
        "BOOK_APPT",
        entity=f"APT-{str(appt.appointment_Id).zfill(4)}",
        detail=f"Patient {body.get('patient_id')} → Dr. {doctor_id} on {appt_date} at {slot_time}"
    )

    return jsonify({
        "ok": True,
        "appointment_id": appt.appointment_Id
    })

# ══════════════════════════════════════════════════════════════════════════════
#  API — Available slots
# ══════════════════════════════════════════════════════════════════════════════

@receptionist_bp.route("/api/slots")
def api_slots():

    doctor_id = int(request.args.get("doctor_id"))

    appt_date = datetime.strptime(
        request.args.get("date"),
        "%Y-%m-%d"
    ).date()

    db = next(get_db())

    # CHECK DOCTOR LEAVE
    doctor_leave = db.query(DoctorLeave).filter(
        DoctorLeave.doctor_id == doctor_id,
        DoctorLeave.leave_date == appt_date,
        DoctorLeave.status == "Approved"
    ).first()

    if doctor_leave:

        return jsonify({
            "doctor_unavailable": True,
            "slots": []
        })

    # SAME SLOT TIMINGS AS PATIENT
    all_slots = [
        "10:00",
        "11:00",
        "12:00",
        "14:00",
        "15:00",
        "16:00",
        "17:00"
    ]

    # GET BOOKED APPOINTMENTS
    booked = db.query(Appointment).filter(
        Appointment.doct_Id == doctor_id,
        Appointment.appointment_Date == appt_date,
        func.lower(Appointment.appointment_status) != "cancelled"
    ).all()

    booked_times = [
        a.slot_time.strftime("%H:%M")
        for a in booked if a.slot_time
    ]

    now = datetime.now(timezone.utc)

    slots = []

    for s in all_slots:

        slot_time = datetime.strptime(
            s,
            "%H:%M"
        ).time()

        # LOCK PAST TIME SLOTS
        is_past = (
            appt_date == now.date()
            and slot_time <= now.time()
        )

        slots.append({
            "time": s,
            "taken": (s in booked_times) or is_past
        })

    return jsonify({
        "slots": slots
    })
# ══════════════════════════════════════════════════════════════════════════════
#  API — Pending check-in list
# ══════════════════════════════════════════════════════════════════════════════

@receptionist_bp.route("/api/pending-checkin")
def api_pending_checkin():
    g = _guard()
    if g:
        return jsonify({"detail":"Forbidden"}), 403

    page     = int(request.args.get("page", 1))
    per_page = PAGINATION["appointments"]
    search   = request.args.get("search","").strip()

    db    = next(get_db())
    today = datetime.now(timezone.utc).date()
    now = datetime.now(timezone.utc)

    from sqlalchemy import func

    # =========================================================
    # AUTO MARK NO-SHOW
    # =========================================================
    scheduled_appts = db.query(Appointment).filter(
        Appointment.appointment_Date == today,
        func.lower(func.trim(Appointment.appointment_status)) == "scheduled",
        Appointment.slot_time.isnot(None)
    ).all()

    for appt in scheduled_appts:

        # combine date + slot time
        appt_datetime = datetime.combine(
    appt.appointment_Date,
    appt.slot_time
).replace(tzinfo=timezone.utc)

        # if 30 mins passed
        if now > appt_datetime + timedelta(minutes=30):
            appt.appointment_status = "No-Show"

    db.commit()

    # =========================================================
    # FETCH SCHEDULED + NO-SHOW
    # =========================================================
    q = db.query(Appointment, Patient, Doctor, Department)\
        .join(Patient, Patient.patient_Id == Appointment.patient_Id)\
        .join(Doctor, Doctor.doct_Id == Appointment.doct_Id)\
        .outerjoin(Department, Department.dept_Id == Doctor.dept_Id)\
        .filter(
            Appointment.appointment_Date == today,
            func.lower(func.trim(Appointment.appointment_status)).in_([
                "scheduled",
                "no-show"
            ])
        )

    if search:
        q = q.filter(
            (Patient.FName.ilike(f"%{search}%")) |
            (Patient.LName.ilike(f"%{search}%"))
        )

    total = q.count()

    rows = q.order_by(
        Appointment.slot_time
    ).offset((page-1)*per_page).limit(per_page).all()

    items = [{
        "appointment_Id": a.appointment_Id,
        "patient_name": f"{p.FName} {p.LName}",
        "doctor_name": f"Dr. {d.FName} {d.LName}",
        "dept_name": dept.dept_Name if dept else "—",
        "appointment_time": (
            f"{a.appointment_Date} {a.slot_time}"
            if a.slot_time else str(a.appointment_Date)
        ),
        "appointment_status": (a.appointment_status or "").lower(),
    } for a, p, d, dept in rows]

    return jsonify({
        "items": items,
        "total": total,
        "total_pages": math.ceil(total/per_page) or 1
    })
# ══════════════════════════════════════════════════════════════════════════════
#  API — Check-in action
# ══════════════════════════════════════════════════════════════════════════════

@receptionist_bp.route("/api/check-in/<int:aid>", methods=["POST"])
def api_check_in(aid):
    g = _guard()
    if g: return jsonify({"detail":"Forbidden"}), 403

    from datetime import datetime
    from sqlalchemy import func

    db = next(get_db())

    appt = db.query(Appointment).filter(
        Appointment.appointment_Id == aid
    ).first()

    if not appt:
        return jsonify({"detail": "Appointment not found"}), 404

    if (appt.appointment_status or "").lower() != "scheduled":
        return jsonify({"detail": f"Cannot check-in: status is {appt.appointment_status}"}), 400

    # STEP 1: ASSIGN TOKEN (ADD HERE)
    last_token = db.query(func.max(Appointment.token_no)).filter(
            Appointment.doct_Id == appt.doct_Id,
            Appointment.appointment_Date == appt.appointment_Date
        ).scalar() or 0
    appt.token_no = last_token + 1

    # STEP 2: UPDATE STATUS
    appt.appointment_status = "checked-in"
    appt.checked_in_at = datetime.now(timezone.utc)

    # STEP 3: SAVE
    db.commit()

    _log(db, "CHECK_IN",
         entity=f"APT-{str(aid).zfill(4)}",
         detail=f"Scheduled → Checked-In (Token {appt.token_no})")

    return jsonify({
        "ok": True,
        "token_no": appt.token_no   # optional (useful for UI)
    })
# ══════════════════════════════════════════════════════════════════════════════
#  API — Patients list (for dropdowns)
# ══════════════════════════════════════════════════════════════════════════════

@receptionist_bp.route("/api/patients-list")
def api_patients_list():
    g = _guard()
    if g: return jsonify({"detail":"Forbidden"}), 403
    db  = next(get_db())
    pts = db.query(Patient).order_by(Patient.FName).all()
    return jsonify([{"patient_Id": p.patient_Id, "FName": p.FName, "LName": p.LName} for p in pts])

# ══════════════════════════════════════════════════════════════════════════════
#  API — Appointments by patient (for bill dropdown)
# ══════════════════════════════════════════════════════════════════════════════

@receptionist_bp.route("/api/appointments-by-patient/<int:pid>")
def api_appts_by_patient(pid):
    g = _guard()
    if g: return jsonify({"detail":"Forbidden"}), 403

    db = next(get_db())

    appts = db.query(Appointment)\
        .filter(
            Appointment.patient_Id == pid,
            func.lower(Appointment.appointment_status).in_([
                "checked-in",
                "in-progress",
                "completed"
            ])
        )\
        .order_by(Appointment.appointment_Date.desc())\
        .limit(20)\
        .all()

    return jsonify([{
        "appointment_Id": a.appointment_Id,
        "appointment_date": str(a.appointment_Date),
        "appointment_status": (a.appointment_status or "").lower(),
    } for a in appts])


# ══════════════════════════════════════════════════════════════════════════════
#  API — Generate bill (receptionist)
# ══════════════════════════════════════════════════════════════════════════════
@receptionist_bp.route("/api/generate-bill", methods=["POST"])
def generate_bill():
    db = next(get_db())

    data = request.get_json()

    patient_id = data.get("patient_id")
    appointment_id = data.get("appointment_id")
    items = data.get("items", [])

    if not appointment_id:
        return jsonify({"error": "OPID is required"}), 400

    appt = db.query(Appointment).filter(
        Appointment.appointment_Id == appointment_id,
        Appointment.patient_Id == patient_id
    ).first()

    if not appt:
        return jsonify({"error": "Invalid OPID for selected patient"}), 400

    existing_bill = db.query(Bill).filter(
    Bill.appointment_Id == appointment_id
    ).first()


    # ❌ Only block if Paid
    if existing_bill and existing_bill.status == "Paid":
        return jsonify({
            "error": "Payment is already completed."
        }), 400

    #  If Pending / Partial → delete old bill (or update)
    if existing_bill and existing_bill.status in ["Pending", "Partial"]:
        
        # delete old bill items
        db.query(BillItem).filter(
            BillItem.bill_id == existing_bill.bill_id
        ).delete()

        # delete old bill
        db.delete(existing_bill)
        db.commit()
        
    # Get appointment (optional but recommended)
    if appointment_id:
        appt = db.query(Appointment).filter(
            Appointment.appointment_Id == appointment_id
        ).first()

    total_amount = 0
    bill_items_to_add = []

    # ================= PROCESS ITEMS =================
    for item in items:

        name = item.get("name")
        treatment_id = item.get("treatment_id")
        input_cost = float(item.get("cost", 0))
        if input_cost < 0:

            return jsonify({
                "error": "Item amount cannot be negative"
            }), 400
        # 🔥 FIX 1: SKIP INVALID ROWS
        if not treatment_id and (not name or name.lower() == "select treatment"):
            continue

            # 🔥 FIX 2: FORCE INTEGER OR NULL
            try:
                treatment_id = int(treatment_id) if treatment_id else None
            except:
                treatment_id = None

        # 🔥 CASE 2: CONSULTATION
        elif name and "consult" in name.lower():

            if appt:
                # doctor-specific fee
                fee = db.query(FeeMaster).filter(
                    FeeMaster.fee_type == "consultation",
                    FeeMaster.doct_Id == appt.doct_Id,
                    FeeMaster.is_active == True
                ).first()

                # fallback default
                if not fee:
                    fee = db.query(FeeMaster).filter(
                        FeeMaster.fee_type == "consultation",
                        FeeMaster.doct_Id == None,
                        FeeMaster.is_active == True
                    ).first()

                actual_cost = fee.amount if fee else input_cost
            else:
                actual_cost = input_cost

        # 🔥 CASE 3: CUSTOM ITEM (medicine/manual)
        else:
            actual_cost = input_cost

        total_amount += actual_cost

        bill_items_to_add.append({
            "name": name,
            "treatment_id": treatment_id,
            "amount": actual_cost
        })
    # BLOCK INVALID BILL GENERATION
    if total_amount <= 0:

        return jsonify({
            "error": "Bill amount must be greater than 0"
        }), 400
    # ================= CREATE BILL =================
    bill = Bill(
        patient_Id=patient_id,
        appointment_Id=appointment_id,
        total_amount=total_amount,
        amount_paid=0,
        balance=total_amount,
        status="Pending",
        created_at = datetime.now(timezone.utc)
    )

    db.add(bill)
    db.flush()  # get bill_id before commit

    # ================= SAVE BILL ITEMS =================
    for item in bill_items_to_add:
        db.add(BillItem(
            bill_id=bill.bill_id,
            item_name=item["name"],
            treatment_id=item["treatment_id"],
            amount=item["amount"]
        ))

    db.commit()

    return jsonify({
        "message": "Bill generated successfully",
        "bill_id": bill.bill_id,
        "total_amount": float(total_amount)
    })

@receptionist_bp.route("/api/doctors-by-dept/<int:dept_id>")
def api_doctors_by_dept(dept_id):
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())

    doctors = db.query(Doctor)\
        .filter(Doctor.dept_Id == dept_id)\
        .order_by(Doctor.FName).all()

    return jsonify([
        {
            "doct_Id": d.doct_Id,
            "FName": d.FName,
            "LName": d.LName
        }
        for d in doctors
    ])

    

@receptionist_bp.route("/billing")
def billing_page():
    g = _guard()
    if g: return g
    return render_template("receptionist/billing.html")

# ══════════════════════════════════════════════════════════════════════════════
#  API — Treatment-linked bills (OPID tracked, from doctor completions)
# ══════════════════════════════════════════════════════════════════════════════

@receptionist_bp.route("/api/treatment-bills")
def api_treatment_bills():
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    page     = int(request.args.get("page", 1))
    per_page = PAGINATION["billing"]
    search   = request.args.get("search", "").strip()
    status   = request.args.get("status", "").strip()
    db       = next(get_db())

    q = db.query(Bill, Patient, Appointment)\
          .join(Patient, Patient.patient_Id == Bill.patient_Id)\
          .outerjoin(Appointment, Appointment.appointment_Id == Bill.appointment_Id)

    if search:
        q = q.filter(
            (Patient.FName.ilike(f"%{search}%")) |
            (Patient.LName.ilike(f"%{search}%"))
        )
    if status:
        q = q.filter(Bill.status == status)

    total = q.count()
    rows  = q.order_by(Bill.created_at.desc()).offset((page-1)*per_page).limit(per_page).all()

    items = [{
    "bill_id"        : b.bill_id,
    "opid"           : f"APT-{str(a.appointment_Id).zfill(4)}" if a else "—",
    "appointment_id" : a.appointment_Id if a else None,
    "patient_name"   : f"{p.FName} {p.LName}",
    "patient_id"     : p.patient_Id,

    "treatment"      : b.description or "—",

    "total_amount"   : b.total_amount or 0,
    "amount_paid"    : b.amount_paid or 0,
    "balance"        : b.balance or 0,

    "status"         : b.status,
    "is_paid"        : b.status == "Paid",   # ✅ ADD THIS

    "appt_date"      : str(a.appointment_Date) if a and a.appointment_Date else "—",
    "created_at"     : str(b.created_at),
} for b, p, a in rows]

    return jsonify({"items": items, "total": total,
                    "total_pages": math.ceil(total / per_page) or 1})


# ══════════════════════════════════════════════════════════════════════════════
#  API — Record payment against a treatment bill
# ══════════════════════════════════════════════════════════════════════════════

@receptionist_bp.route("/api/treatment-bills/<int:bid>/pay", methods=["POST"])
def api_pay_treatment_bill(bid):
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    body   = request.get_json() or {}
    db     = next(get_db())

    bill = db.query(Bill).filter(Bill.bill_id == bid).first()

    if not bill:
        return jsonify({"detail": "Bill not found"}), 404

    # BLOCK DOUBLE PAYMENT
    if bill.status == "Paid":
        return jsonify({
            "error": "Already paid"
        }), 400

    amount = float(body.get("amount", 0))
    if amount <= 0:
        return jsonify({"detail": "Invalid amount"}), 400

    bill.amount_paid = (bill.amount_paid or 0) + amount
    bill.balance     = max(0, (bill.total_amount or 0) - bill.amount_paid)
    bill.status      = "Paid" if bill.balance <= 0 else "Partial"

    db.commit()

    return jsonify({
        "ok": True,
        "new_status": bill.status,
        "balance": bill.balance
    })


@receptionist_bp.route("/api/billing")
def api_billing():
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    page   = int(request.args.get("page", 1))
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    per_page = PAGINATION["billing"]

    db = next(get_db())

    q = db.query(Bill, Patient)\
          .join(Patient, Patient.patient_Id == Bill.patient_Id)

    if search:
        q = q.filter(
            (Patient.FName.ilike(f"%{search}%")) |
            (Patient.LName.ilike(f"%{search}%"))
        )

    if status:
        q = q.filter(Bill.status == status)

    total = q.count()
    rows  = q.order_by(Bill.created_at.desc())\
             .offset((page-1)*per_page)\
             .limit(per_page).all()

    items = [{
        "bill_id": b.bill_id,
        "patient_name": f"{p.FName} {p.LName}",
        "total_amount": b.total_amount or 0,
        "amount_paid": b.amount_paid or 0,
        "balance": b.balance or 0,
        "status": b.status,
        "created_at": str(b.created_at),
    } for b, p in rows]

    return jsonify({
        "items": items,
        "total": total,
        "total_pages": math.ceil(total / per_page) or 1
    })


@receptionist_bp.route("/api/billing/<int:bid>")
def api_get_bill(bid):
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    db   = next(get_db())
    bill = db.query(Bill, Patient)\
             .join(Patient, Patient.patient_Id == Bill.patient_Id)\
             .filter(Bill.bill_id == bid).first()

    if not bill:
        return jsonify({"detail": "Bill not found"}), 404

    b, p = bill

    return jsonify({
        "bill_id": b.bill_id,
        "patient_name": f"{p.FName} {p.LName}",
        "total_amount": b.total_amount or 0,
        "amount_paid": b.amount_paid or 0,
        "balance": b.balance or 0,
        "status": b.status,
        "created_at": str(b.created_at),
    })

@receptionist_bp.route("/api/treatment-bills/<int:bid>")
def get_treatment_bill(bid):
    g = _guard()
    if g: return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())

    result = db.query(Bill, Patient)\
        .join(Patient, Patient.patient_Id == Bill.patient_Id)\
        .filter(Bill.bill_id == bid).first()

    if not result:
        return jsonify({"detail": "Bill not found"}), 404

    b, p = result

    return jsonify({
        "bill_id": b.bill_id,
        "patient_name": f"{p.FName} {p.LName}",
        "treatment": b.description,
        "total_amount": b.total_amount or 0,
        "amount_paid": b.amount_paid or 0,
        "balance": b.balance or 0,
        "status": b.status,
        "created_at": str(b.created_at),
    })

@receptionist_bp.route('/api/treatments-by-opid/<int:opid>')
def get_treatments_by_opid(opid):
    db = next(get_db())

    rows = db.execute(text("""
        SELECT 
            a."appointment_Id",
            a."appointment_Date",

            p."patient_Id",
            p."FName" || ' ' || p."LName" AS patient_name,

            d."FName" || ' ' || d."LName" AS doctor_name,

            mr.treatment,
            tc.default_cost AS cost,
            mr.diagnosis,
            mr."visit_Date",

            b.bill_id,
            b.total_amount,
            b.amount_paid,
            b.balance,
            b.status

        FROM appointment a
        JOIN patients p ON p."patient_Id" = a."patient_Id"
        JOIN doctor d ON d."doct_Id" = a."doct_Id"

        LEFT JOIN medical_record mr 
            ON mr."appointment_Id" = a."appointment_Id"
        LEFT JOIN treatment_catalogue tc
            ON LOWER(tc.treatment_name) = LOWER(mr.treatment)
                            
        LEFT JOIN bills b 
            ON b."appointment_Id" = a."appointment_Id"

        WHERE a."appointment_Id" = :opid
    """), {"opid": opid}).fetchall()

    if not rows:
        return jsonify({"error": "No data found"}), 404

    return jsonify([
    {
        "treatment": row.treatment,
        "cost": row.cost or 0
    }
    for row in rows
])

@receptionist_bp.route("/api/search-opids")
def api_search_opids():

    g = _guard()
    if g:
        return jsonify({"detail": "Forbidden"}), 403

    q = request.args.get("q", "").strip()

    db = next(get_db())

    if not q:
        return jsonify([])

    appointments = db.query(Appointment, Patient)\
        .join(Patient)\
        .filter(
            Appointment.appointment_Id.cast(String).ilike(f"%{q}%")
        )\
        .limit(10)\
        .all()

    return jsonify([
        {
            "appointment_Id": a.appointment_Id,
            "label": f"{p.FName} {p.LName}"
        }
        for a, p in appointments
    ])

@receptionist_bp.route("/api/opid-list")
def api_opid_list():

    g = _guard()
    if g:
        return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())

    appointments = db.query(Appointment, Patient)\
        .join(Patient)\
        .order_by(Appointment.appointment_Id.desc())\
        .all()

    return jsonify([
        {
            "appointment_Id": a.appointment_Id,
            "patient_name": f"{p.FName} {p.LName}"
        }
        for a, p in appointments
    ])


@receptionist_bp.route("/api/get-appointment/<opid>")
def get_appointment_by_opid(opid):

    db = next(get_db())

    try:
        opid = int(str(opid).replace("APT-", "").strip())
    except:
        return jsonify({"error": "Invalid OPID"}), 400

    result = db.query(Appointment, Patient, Doctor)\
        .join(Patient)\
        .join(Doctor)\
        .filter(Appointment.appointment_Id == opid)\
        .first()

    if not result:
        return jsonify({"error": "Invalid OPID"}), 404

    a, p, d = result

    return jsonify({
        "appointment_Id": a.appointment_Id,
        "opid": f"APT-{str(a.appointment_Id).zfill(4)}",

        "patient_Id": p.patient_Id,
        "patient_name": f"{p.FName} {p.LName}",
        "doctor_name": f"Dr. {d.FName} {d.LName}",

        "date": str(a.appointment_Date),
        "time": str(a.slot_time) if a.slot_time else None,

        "status": a.appointment_status
    })


@receptionist_bp.route("/api/create-order", methods=["POST"])
def create_order():
    import razorpay

    client = razorpay.Client(auth=("rzp_test_SgoWav1ySgiwfc", "HxA4wBDZPlU9AO2FJSfyd31T"))

    amount = int(float(request.json["amount"]) * 100)

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return jsonify(order)

@receptionist_bp.route("/api/verify-payment", methods=["POST"])
def verify_payment():
    data = request.get_json()

    bill_id = data.get("bill_id")
    payment_id = data.get("razorpay_payment_id")

    db = next(get_db())

    bill = db.query(Bill).filter(Bill.bill_id == bill_id).first()

    if not bill:
        return jsonify({"error": "Bill not found"}), 404
    
    if bill.status == "Paid":
        return jsonify({"error": "Already paid"}), 400
    # Update bill
    bill.status = "Paid"
    bill.amount_paid = bill.total_amount
    bill.balance = 0

    # INSERT PAYMENT RECORD
    payment = Payment(
        bill_id=bill_id,
        amount=bill.total_amount,
        payment_method="UPI",
        transaction_id="CASH-" + uuid.uuid4().hex[:10].upper(),
        payment_status="Success",
        paid_at=datetime.now(timezone.utc) 
    )

    db.add(payment)

    db.commit()

    return jsonify({"status": "Payment Verified"})


@receptionist_bp.route("/api/complete-cash-payment", methods=["POST"])
def complete_cash_payment():
    data = request.get_json()

    bill_id = data.get("bill_id")
    amount = data.get("amount")

    db = next(get_db())

    bill = db.query(Bill).filter(Bill.bill_id == bill_id).first()

    if not bill:
        return jsonify({"error": "Bill not found"}), 404
    if bill.status == "Paid":
        return jsonify({"error": "Already paid"}), 400
    # Update bill
    bill.status = "Paid"
    bill.amount_paid = amount
    bill.balance = 0

    # INSERT PAYMENT RECORD
    payment = Payment(
        bill_id=bill_id,
        amount=amount,
        payment_method="Cash",
        transaction_id= uuid.uuid4().hex[:10].upper(),
        payment_status="Success",
        paid_at=datetime.now(timezone.utc)
    )

    db.add(payment)

    db.commit()

    return jsonify({"status": "Cash Payment Successful"})

@receptionist_bp.route("/api/completed-opds")
def completed_opds():
    db = next(get_db())

    rows = db.query(Appointment, Patient)\
        .join(Patient)\
        .filter(Appointment.appointment_status == "Completed")\
        .all()

    return jsonify([{
        "patient_Id": p.patient_Id,
        "patient_name": f"{p.FName} {p.LName}"
    } for a,p in rows])

@receptionist_bp.route("/api/opds-by-patient/<int:pid>")
def opds_by_patient(pid):
    db = next(get_db())

    appts = db.query(Appointment)\
        .filter(Appointment.patient_Id == pid,
                Appointment.appointment_status=="Completed")\
        .all()

    return jsonify([{
        "appointment_Id": a.appointment_Id
    } for a in appts])


@receptionist_bp.route("/api/consultation/<int:opid>")
def consultation(opid):
    db = next(get_db())

    appt = db.query(Appointment)\
        .filter(Appointment.appointment_Id == opid)\
        .first()

    if not appt:
        return jsonify({"error": "Appointment not found"}), 404

    # 🔥 FIRST try doctor-specific fee
    fee = db.query(FeeMaster).filter(
        FeeMaster.fee_type == "consultation",
        FeeMaster.doct_Id == appt.doct_Id,
        FeeMaster.is_active == True
    ).first()

    # 🔥 fallback to default consultation fee
    if not fee:
        fee = db.query(FeeMaster).filter(
            FeeMaster.fee_type == "consultation",
            FeeMaster.doct_Id == None,
            FeeMaster.is_active == True
        ).first()

    return jsonify({
        "name": "Consultation",
        "cost": fee.amount if fee else 0
    })

@receptionist_bp.route("/api/all-treatments")
def get_all_treatments():
    db = next(get_db())

    treatments = db.query(TreatmentCatalogue).all()

    return jsonify([
        {
            "name": t.treatment_name,
            "cost": t.default_cost,
            "treatment_id": t.treatment_id
        }
        for t in treatments
    ])

@receptionist_bp.route("/api/search-patients")
def api_search_patients():
    g = _guard()
    if g:
        return jsonify({"detail": "Forbidden"}), 403

    q = request.args.get("q", "").strip()
    db = next(get_db())

    if not q:
        return jsonify([])

    patients = db.query(Patient).filter(
        (Patient.FName.ilike(f"%{q}%")) |
        (Patient.LName.ilike(f"%{q}%"))
    ).limit(10).all()

    return jsonify([
        {
            "id": p.patient_Id,
            "name": f"{p.FName} {p.LName}"
        }
        for p in patients
    ])

@receptionist_bp.route("/messages")
def messages_page():
    g = _guard()
    if g:
        return g

    db = next(get_db())

    messages = db.execute(text("""
        SELECT *
        FROM contact_messages
        ORDER BY created_at DESC
    """)).mappings().all()

    return render_template(
        "receptionist/messages.html",
        messages=messages
    )


@receptionist_bp.route("/api/messages/<int:mid>/read", methods=["POST"])
def mark_message_read(mid):

    g = _guard()
    if g:
        return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())

    db.execute(
        text("""
            UPDATE contact_messages
            SET is_read = true
            WHERE msg_id = :id
        """),
        {"id": mid}
    )

    db.commit()

    return jsonify({"ok": True})

@receptionist_bp.route("/api/messages/<int:mid>", methods=["DELETE"])
def delete_message(mid):

    g = _guard()
    if g:
        return jsonify({"detail": "Forbidden"}), 403

    db = next(get_db())

    db.execute(
        text("""
            DELETE FROM contact_messages
            WHERE msg_id = :id
        """),
        {"id": mid}
    )

    db.commit()

    return jsonify({"ok": True})
@receptionist_bp.route(
    "/api/messages/reply",
    methods=["POST"]
)
@receptionist_bp.route(
    "/api/messages/reply",
    methods=["POST"]
)
def reply_message():

    g = _guard()

    if g:
        return jsonify({
            "detail": "Forbidden"
        }), 403

    data = request.get_json()

    email = data.get("email")
    subject = data.get("subject")
    message = data.get("message")
    msg_id = data.get("msg_id")

    try:

        send_email(
            subject,
            [email],
            message
        )

        db = next(get_db())

        db.execute(text("""

            UPDATE contact_messages

            SET
                is_read = true,
                replied = true

            WHERE msg_id = :id

        """), {
            "id": msg_id
        })

        db.commit()

        return jsonify({
            "ok": True
        })

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500