from flask import Blueprint, request, session, jsonify
from database import get_db
from models import Bill, Payment, Patient, AuditLog
from config import PAGINATION
import datetime, math

billing_bp = Blueprint("billing", __name__)

def _allowed():
    return session.get("role") in ("Admin", "Receptionist", "Auditor", "Patient")

def _log(db, action, entity=None, detail=None):
    db.add(AuditLog(
        user_id=session.get("user_id"),
        user_name=session.get("user_name",""),
        role=session.get("role",""),
        action=action,
        entity=entity,
        detail=detail
    ))
    db.commit()


# ─────────────────────────────────────────────
# GET /api/billing
# ─────────────────────────────────────────────

@billing_bp.route("/" \
"api/billing")
def api_bills_list():

    if not _allowed():
        return jsonify({"detail": "Forbidden"}), 403

    page     = int(request.args.get("page", 1))
    per_page = PAGINATION["billing"]

    search = request.args.get("search","").strip()
    status = request.args.get("status","").strip()

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

    rows = q.order_by(
        Bill.created_at.desc(),
        Bill.bill_id.desc()
    ).offset((page-1)*per_page)\
     .limit(per_page)\
     .all()

    items = [{
        "bill_id"     : b.bill_id,
        "patient_name": f"{p.FName} {p.LName}",
        "bill_type"   : b.bill_type,
        "description" : b.description,
        "total_amount": b.total_amount or 0,
        "amount_paid" : b.amount_paid or 0,
        "balance"     : b.balance or 0,
        "status"      : b.status,
        "created_at"  : str(b.created_at),
    } for b,p in rows]

    return jsonify({
        "items": items,
        "total": total,
        "total_pages": math.ceil(total/per_page) or 1
    })


# ─────────────────────────────────────────────
# GET /api/billing/<id>
# ─────────────────────────────────────────────

@billing_bp.route("/api/billing/<int:bid>")
def api_bill_detail(bid):

    db = next(get_db())

    bill = db.query(Bill)\
             .filter(Bill.bill_id == bid)\
             .first()

    if not bill:
        return jsonify({"detail":"Not found"}),404

    pt = db.query(Patient)\
           .filter(Patient.patient_Id == bill.patient_Id)\
           .first()

    return jsonify({
        "bill_id"     : bill.bill_id,
        "patient_name": f"{pt.FName} {pt.LName}" if pt else "—",
        "bill_type"   : bill.bill_type,
        "description" : bill.description,
        "total_amount": bill.total_amount,
        "amount_paid" : bill.amount_paid,
        "balance"     : bill.balance,
        "status"      : bill.status,
        "created_at"  : str(bill.created_at),
    })


# ─────────────────────────────────────────────
# POST /api/billing
# ─────────────────────────────────────────────

@billing_bp.route("/api/billing", methods=["POST"])
def api_bill_create():

    if session.get("role") not in ["Admin","Receptionist"]:
        return jsonify({"detail":"Forbidden"}),403

    body = request.get_json()

    db = next(get_db())

    total = float(body.get("total_amount",0))

    bill = Bill(
        patient_Id = body["patient_id"],
        total_amount = total,
        bill_type = body.get("bill_type"),
        description = body.get("description"),
        amount_paid = 0,
        balance = total,
        status = "Pending"
    )

    db.add(bill)
    db.commit()

    _log(db,"Bill Created","Billing",f"Bill #{bill.bill_id}")

    return jsonify({"ok":True})


# ─────────────────────────────────────────────
# POST /api/billing/payment
# ─────────────────────────────────────────────

@billing_bp.route("/api/billing/payment", methods=["POST"])
def api_record_payment():

    if session.get("role") not in ["Admin","Receptionist"]:
        return jsonify({"detail":"Forbidden"}),403

    body = request.get_json()

    db = next(get_db())

    bill = db.query(Bill)\
             .filter(Bill.bill_id == body.get("bill_id"))\
             .first()

    if not bill:
        return jsonify({"detail":"Bill not found"}),404

    amount = float(body.get("amount") or 0)

    if amount <= 0:
        return jsonify({"detail":"Invalid amount"}),400

    amount = float(body.get("amount") or 0)

    payment_date = body.get("payment_date")

    paid_at = datetime.datetime.strptime(payment_date, "%Y-%m-%d").date() \
          if payment_date else datetime.date.today()

    payment = Payment(
        bill_id = bill.bill_id,
        amount = amount,
        payment_method = body.get("payment_method"),
        transaction_id = body.get("transaction_id"),
        paid_at = paid_at
    )
    
    db.add(payment)

    bill.amount_paid = (bill.amount_paid or 0) + amount
    bill.balance = bill.total_amount - bill.amount_paid

    if bill.balance <= 0:
        bill.status = "Paid"
    else:
        bill.status = "Partial"

    db.commit()

    _log(db,"Payment Recorded","Billing",
         f"Bill #{bill.bill_id} amount {amount}")

    return jsonify({"ok":True})


