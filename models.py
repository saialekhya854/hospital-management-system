# from database import db
# from sqlalchemy.sql import func


# # ---------------- MANAGEMENT ----------------

# class Role(db.Model):
#     __tablename__ = "roles"
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(50))


# class User(db.Model):
#     __tablename__ = "users"

#     User_ID = db.Column(db.Integer, primary_key=True)
#     Email = db.Column(db.String(100))
#     Password = db.Column(db.String(255))

#     Role_ID = db.Column(db.Integer)
#     Linked_Entity_ID = db.Column(db.BigInteger)

#     Name = db.Column(db.String(100))
#     is_active = db.Column(db.Boolean, default=True)


# # ---------------- STRUCTURE ----------------

# class Department(db.Model):
#     __tablename__ = "department"

#     dept_Id = db.Column(db.Integer, primary_key=True)
#     dept_Name = db.Column(db.String(100))


# class Ward(db.Model):
#     __tablename__ = "ward"

#     ward_No = db.Column(db.Integer, primary_key=True)
#     ward_Name = db.Column(db.String(100))

#     dept_Id = db.Column(db.Integer)


# class Bed(db.Model):
#     __tablename__ = "bed"

#     bed_No = db.Column(db.Integer, primary_key=True)
#     ward_No = db.Column(db.Integer)


# class Room(db.Model):
#     __tablename__ = "room"

#     room_No = db.Column(db.Integer, primary_key=True)
#     dept_Id = db.Column(db.Integer)
#     room_Type = db.Column(db.String(50))


# # ---------------- STAFF ----------------

# class Doctor(db.Model):
#     __tablename__ = "doctor"

#     doct_Id = db.Column(db.Integer, primary_key=True)

#     FName = db.Column(db.String)
#     LName = db.Column(db.String)
#     Gender = db.Column(db.String)

#     dept_Id = db.Column(db.Integer)

#     contact_No = db.Column(db.String)
#     surgeon_Type = db.Column(db.String)
#     office_No = db.Column(db.String)

#     experience_years = db.Column(db.Integer)
#     is_dept_head = db.Column(db.Boolean)
#     notes = db.Column(db.Text)

#     User_ID = db.Column(db.Integer)


# class Nurse(db.Model):
#     __tablename__ = "nurse"

#     nurse_Id = db.Column(db.Integer, primary_key=True)

#     dept_Id = db.Column(db.Integer)

#     FName = db.Column(db.String(50))
#     LName = db.Column(db.String(50))
#     Gender = db.Column(db.String(10))
#     contact_No = db.Column(db.String(25))

#     User_ID = db.Column(db.Integer)


# class Helper(db.Model):
#     __tablename__ = "helpers"

#     helper_Id = db.Column(db.Integer, primary_key=True)

#     dept_Id = db.Column(db.Integer)

#     FName = db.Column(db.String(50))
#     LName = db.Column(db.String(50))
#     Gender = db.Column(db.String(10))
#     contact_No = db.Column(db.String(25))

#     User_ID = db.Column(db.Integer)


# # ---------------- PATIENT ----------------

# class Patient(db.Model):
#     __tablename__ = "patients"

#     patient_Id = db.Column(db.Integer, primary_key=True)

#     FName = db.Column(db.String(50))
#     LName = db.Column(db.String(50))
#     Gender = db.Column(db.String(10))
#     Date_Of_Birth = db.Column(db.Date)

#     contact_No = db.Column(db.String(25))
#     pt_Address = db.Column(db.String(255))

#     blood_group = db.Column(db.String(5))
#     email = db.Column(db.String(100))
#     emergency_contact = db.Column(db.String(25))

#     registration_date = db.Column(db.DateTime, server_default=func.now())

#     User_ID = db.Column(db.Integer)


# # ---------------- APPOINTMENT ----------------

# class Appointment(db.Model):
#     __tablename__ = "appointment"

#     appointment_Id = db.Column(db.Integer, primary_key=True)

#     patient_Id = db.Column(db.Integer)
#     doct_Id = db.Column(db.Integer)

#     reason = db.Column(db.String(255))
#     token_no = db.Column(db.Integer)

#     appointment_Date = db.Column(db.Date)
#     appointment_status = db.Column(db.String(50))

#     payment_amount = db.Column(db.Float)
#     mode_of_payment = db.Column(db.String(50))
#     mode_of_appointment = db.Column(db.String(50))

#     created_at = db.Column(db.DateTime, server_default=func.now())
#     checked_in_at = db.Column(db.DateTime)
#     completed_at = db.Column(db.DateTime)


# # ---------------- MEDICAL RECORD ----------------

# class MedicalRecord(db.Model):
#     __tablename__ = "medical_record"

#     record_Id = db.Column(db.Integer, primary_key=True)

#     doct_Id = db.Column(db.Integer)
#     patient_Id = db.Column(db.Integer)

#     visit_Date = db.Column(db.Date)

#     curr_Weight = db.Column(db.Float)
#     curr_height = db.Column(db.Float)
#     curr_Blood_Pressure = db.Column(db.String(20))
#     curr_Temp_F = db.Column(db.Float)

#     chief_complaint = db.Column(db.Text)
#     diagnosis = db.Column(db.Text)
#     treatment = db.Column(db.Text)
#     prescription = db.Column(db.Text)

#     followup_required = db.Column(db.Boolean)
#     next_Visit = db.Column(db.Date)


# # ---------------- SURGERY ----------------

# class SurgeryRecord(db.Model):
#     __tablename__ = "surgery_records"

#     surgery_Id = db.Column(db.Integer, primary_key=True)

#     patient_Id = db.Column(db.Integer)
#     surgeon_Id = db.Column(db.Integer)

#     surgery_Type = db.Column(db.String(100))
#     surgery_Date = db.Column(db.Date)

#     start_Time = db.Column(db.Time)
#     end_Time = db.Column(db.Time)

#     room_no = db.Column(db.Integer)

#     nurse_Id = db.Column(db.Integer)
#     helper_Id = db.Column(db.Integer)

#     status = db.Column(db.String(50))
#     cost = db.Column(db.Float)
#     notes = db.Column(db.Text)


# # ---------------- BILLING ----------------

# class Bill(db.Model):
#     __tablename__ = "bills"

#     bill_id = db.Column(db.Integer, primary_key=True)

#     patient_Id = db.Column(db.Integer)

#     bill_type = db.Column(db.String(50))
#     description = db.Column(db.Text)

#     total_amount = db.Column(db.Float)
#     amount_paid = db.Column(db.Float)
#     balance = db.Column(db.Float)

#     status = db.Column(db.String(50))
#     created_at = db.Column(db.DateTime, server_default=func.now())


# class Payment(db.Model):
#     __tablename__ = "payments"

#     payment_id = db.Column(db.Integer, primary_key=True)

#     bill_id = db.Column(db.Integer)

#     amount = db.Column(db.Float)
#     payment_method = db.Column(db.String(50))

#     transaction_id = db.Column(db.String(255))
#     payment_status = db.Column(db.String(20))

#     paid_at = db.Column(db.DateTime)


# # ---------------- TREATMENT ----------------

# class TreatmentCatalogue(db.Model):
#     __tablename__ = "treatment_catalogue"

#     treatment_id = db.Column(db.Integer, primary_key=True)
#     treatment_name = db.Column(db.String(100))
#     description = db.Column(db.Text)
#     cost = db.Column(db.Float)


# # ---------------- AUDIT ----------------

# class AuditLog(db.Model):
#     __tablename__ = "audit_logs"

#     id = db.Column(db.Integer, primary_key=True)

#     user_id = db.Column(db.Integer)
#     user_name = db.Column(db.String(100))
#     role = db.Column(db.String(50))

#     action = db.Column(db.String(255))
#     entity = db.Column(db.String(100))
#     detail = db.Column(db.Text)

#     timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())


# # ---------------- STAFF SHIFT ----------------

# class StaffShift(db.Model):
#     __tablename__ = "staff_shifts"

#     shift_Id = db.Column(db.Integer, primary_key=True)

#     doct_Id = db.Column(db.Integer)
#     nurse_Id = db.Column(db.Integer)
#     helper_Id = db.Column(db.Integer)

#     shift_Date = db.Column(db.Date)
#     shift_Start = db.Column(db.Time)
#     shift_End = db.Column(db.Time)


# # ---------------- ROOM RECORD ----------------

# class RoomRecord(db.Model):
#     __tablename__ = "room_records"

#     admisson_ID = db.Column(db.Integer, primary_key=True)

#     room_no = db.Column(db.Integer)
#     patient_Id = db.Column(db.Integer)

#     nurse_Id = db.Column(db.Integer)
#     helper_Id = db.Column(db.Integer)

#     admission_Date = db.Column(db.Date)
#     discharge_Date = db.Column(db.Date)

#     amount = db.Column(db.Float)
#     mode_of_payment = db.Column(db.String(50))


# # ---------------- BED RECORD ----------------

# class BedRecord(db.Model):
#     __tablename__ = "bed_records"

#     admission_Id = db.Column(db.Integer, primary_key=True)

#     bed_No = db.Column(db.Integer)
#     patient_Id = db.Column(db.Integer)

#     nurse_Id = db.Column(db.Integer)
#     helper_Id = db.Column(db.Integer)

#     admission_Date = db.Column(db.Date)
#     discharge_Date = db.Column(db.Date)

#     amount = db.Column(db.Float)
#     mode_of_payment = db.Column(db.String(50))




from datetime import datetime, timezone

from database import db
from sqlalchemy.sql import func


# ---------------- MANAGEMENT ----------------

class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)


class User(db.Model):
    __tablename__ = "users"

    User_ID = db.Column(db.Integer, primary_key=True)
    Email = db.Column(db.String(100))
    Password = db.Column(db.String(255))

    Role_ID = db.Column(db.Integer, db.ForeignKey("roles.id"))
    Linked_Entity_ID = db.Column(db.BigInteger)

    Name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)


# ---------------- STRUCTURE ----------------

class Department(db.Model):
    __tablename__ = "department"

    dept_Id = db.Column(db.Integer, primary_key=True)
    dept_Name = db.Column(db.String(100), unique=True)


class Ward(db.Model):
    __tablename__ = "ward"

    ward_No = db.Column(db.Integer, primary_key=True)
    ward_Name = db.Column(db.String(100))

    dept_Id = db.Column(db.Integer, db.ForeignKey("department.dept_Id"))


class Bed(db.Model):
    __tablename__ = "bed"

    bed_No = db.Column(db.Integer, primary_key=True)
    ward_No = db.Column(db.Integer, db.ForeignKey("ward.ward_No"))


class Room(db.Model):
    __tablename__ = "room"

    room_No = db.Column(db.Integer, primary_key=True)
    dept_Id = db.Column(db.Integer, db.ForeignKey("department.dept_Id"))
    room_Type = db.Column(db.String(50))


# ---------------- STAFF ----------------

class Doctor(db.Model):
    __tablename__ = "doctor"

    doct_Id = db.Column(db.Integer, primary_key=True)

    FName = db.Column(db.String)
    LName = db.Column(db.String)
    Gender = db.Column(db.String)

    dept_Id = db.Column(db.Integer, db.ForeignKey("department.dept_Id"))

    contact_No = db.Column(db.String)
    surgeon_Type = db.Column(db.String)
    office_No = db.Column(db.String)

    experience_years = db.Column(db.Integer)
    is_dept_head = db.Column(db.Boolean)
    notes = db.Column(db.Text)
    profile_image = db.Column(db.String(255), nullable=True)

    User_ID = db.Column(db.Integer, db.ForeignKey("users.User_ID"))


class Nurse(db.Model):
    __tablename__ = "nurse"

    nurse_Id = db.Column(db.Integer, primary_key=True)

    dept_Id = db.Column(db.Integer, db.ForeignKey("department.dept_Id"))

    FName = db.Column(db.String(50))
    LName = db.Column(db.String(50))
    Gender = db.Column(db.String(10))
    contact_No = db.Column(db.String(25))

    User_ID = db.Column(db.Integer, db.ForeignKey("users.User_ID"))


class Helper(db.Model):
    __tablename__ = "helpers"

    helper_Id = db.Column(db.Integer, primary_key=True)

    dept_Id = db.Column(db.Integer, db.ForeignKey("department.dept_Id"))

    FName = db.Column(db.String(50))
    LName = db.Column(db.String(50))
    Gender = db.Column(db.String(10))
    contact_No = db.Column(db.String(25))

    User_ID = db.Column(db.Integer, db.ForeignKey("users.User_ID"))


# ---------------- PATIENT ----------------

class Patient(db.Model):
    __tablename__ = "patients"

    patient_Id = db.Column(db.Integer, primary_key=True)

    FName = db.Column(db.String(50))
    LName = db.Column(db.String(50))
    Gender = db.Column(db.String(10))
    Date_Of_Birth = db.Column(db.Date)

    contact_No = db.Column(db.String(25))
    pt_Address = db.Column(db.String(255))

    blood_group = db.Column(db.String(5))
    email = db.Column(db.String(100))
    emergency_contact = db.Column(db.String(25))

    registration_date = db.Column(db.DateTime, server_default=func.now())

    User_ID = db.Column(db.Integer, db.ForeignKey("users.User_ID"))


# ---------------- APPOINTMENT ----------------

class Appointment(db.Model):
    __tablename__ = "appointment"

    appointment_Id = db.Column(db.Integer, primary_key=True)

    patient_Id = db.Column(db.Integer, db.ForeignKey("patients.patient_Id"))
    doct_Id = db.Column(db.Integer, db.ForeignKey("doctor.doct_Id"))

    reason = db.Column(db.String(255))
    token_no = db.Column(db.Integer)

    appointment_Date = db.Column(db.Date)
    appointment_status = db.Column(db.String(50))

    payment_amount = db.Column(db.Float)
    mode_of_payment = db.Column(db.String(50))
    mode_of_appointment = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, server_default=func.now())
    checked_in_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    slot_time = db.Column(db.Time)
    consultation_fee = db.Column(db.Float)
    payment_status = db.Column(db.String(20), default="Pending")


# ---------------- MEDICAL RECORD ----------------

class MedicalRecord(db.Model):
    __tablename__ = "medical_record"

    record_Id = db.Column(db.Integer, primary_key=True)
    appointment_Id = db.Column(db.Integer, db.ForeignKey("appointment.appointment_Id"))
    doct_Id = db.Column(db.Integer, db.ForeignKey("doctor.doct_Id"))
    patient_Id = db.Column(db.Integer, db.ForeignKey("patients.patient_Id"))

    visit_Date = db.Column(db.Date)

    curr_Weight = db.Column(db.Float)
    curr_height = db.Column(db.Float)
    curr_Blood_Pressure = db.Column(db.String(20))
    curr_Temp_F = db.Column(db.Float)

    chief_complaint = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    prescription = db.Column(db.Text)

    followup_required = db.Column(db.Boolean)
    next_Visit = db.Column(db.Date)


# ---------------- SURGERY ----------------

class SurgeryRecord(db.Model):
    __tablename__ = "surgery_records"

    surgery_Id = db.Column(db.Integer, primary_key=True)

    patient_Id = db.Column(db.Integer, db.ForeignKey("patients.patient_Id"))
    surgeon_Id = db.Column(db.Integer, db.ForeignKey("doctor.doct_Id"))

    surgery_Type = db.Column(db.String(100))
    surgery_Date = db.Column(db.Date)

    start_Time = db.Column(db.Time)
    end_Time = db.Column(db.Time)

    room_no = db.Column(db.Integer, db.ForeignKey("room.room_No"))

    nurse_Id = db.Column(db.Integer, db.ForeignKey("nurse.nurse_Id"))
    helper_Id = db.Column(db.Integer, db.ForeignKey("helpers.helper_Id"))

    status = db.Column(db.String(50))
    cost = db.Column(db.Float)
    notes = db.Column(db.Text)


# ---------------- BILLING ----------------

class Bill(db.Model):
    __tablename__ = "bills"

    bill_id = db.Column(db.Integer, primary_key=True)

    patient_Id     = db.Column(db.Integer, db.ForeignKey("patients.patient_Id"))
    appointment_Id = db.Column(db.Integer, db.ForeignKey("appointment.appointment_Id"), nullable=True)

    bill_type    = db.Column(db.String(50))
    description  = db.Column(db.Text)
    notes        = db.Column(db.Text)

    total_amount = db.Column(db.Float)
    amount_paid  = db.Column(db.Float)
    balance      = db.Column(db.Float)

    status       = db.Column(db.String(50))
    created_by   = db.Column(db.Integer, db.ForeignKey("users.User_ID"), nullable=True)
    created_at   = db.Column(db.DateTime, server_default=func.now())


class Payment(db.Model):
    __tablename__ = "payments"

    payment_id = db.Column(db.Integer, primary_key=True)

    bill_id = db.Column(db.Integer, db.ForeignKey("bills.bill_id"))

    amount = db.Column(db.Float)
    payment_method = db.Column(db.String(50))

    transaction_id = db.Column(db.String(255), unique=True)
    payment_status = db.Column(db.String(20))

    paid_at = db.Column(db.DateTime(timezone=True))


# ---------------- TREATMENT ----------------

class TreatmentCatalogue(db.Model):
    __tablename__ = "treatment_catalogue"

    treatment_id = db.Column(db.Integer, primary_key=True)
    dept_id = db.Column(db.Integer, db.ForeignKey("department.dept_Id"))
    treatment_name = db.Column(db.String(100), unique=True)
    category = db.Column(db.String(100))
    default_cost = db.Column(db.Float)


# ---------------- AUDIT ----------------

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.User_ID"))
    user_name = db.Column(db.String(100))
    role = db.Column(db.String(50))

    action = db.Column(db.String(255))
    entity = db.Column(db.String(100))
    detail = db.Column(db.Text)

    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())


# ---------------- STAFF SHIFT ----------------

class StaffShift(db.Model):
    __tablename__ = "staff_shifts"

    shift_Id = db.Column(db.Integer, primary_key=True)

    doct_Id = db.Column(db.Integer, db.ForeignKey("doctor.doct_Id"))
    nurse_Id = db.Column(db.Integer, db.ForeignKey("nurse.nurse_Id"))
    helper_Id = db.Column(db.Integer, db.ForeignKey("helpers.helper_Id"))

    shift_Date = db.Column(db.Date)
    shift_Start = db.Column(db.Time)
    shift_End = db.Column(db.Time)


# ---------------- ROOM RECORD ----------------

class RoomRecord(db.Model):
    __tablename__ = "room_records"

    admisson_ID = db.Column(db.Integer, primary_key=True)

    room_no = db.Column(db.Integer, db.ForeignKey("room.room_No"))
    patient_Id = db.Column(db.Integer, db.ForeignKey("patients.patient_Id"))

    nurse_Id = db.Column(db.Integer, db.ForeignKey("nurse.nurse_Id"))
    helper_Id = db.Column(db.Integer, db.ForeignKey("helpers.helper_Id"))

    admission_Date = db.Column(db.Date)
    discharge_Date = db.Column(db.Date)

    amount = db.Column(db.Float)
    mode_of_payment = db.Column(db.String(50))


# ---------------- BED RECORD ----------------

class BedRecord(db.Model):
    __tablename__ = "bed_records"

    admission_Id = db.Column(db.Integer, primary_key=True)

    bed_No = db.Column(db.Integer, db.ForeignKey("bed.bed_No"))
    patient_Id = db.Column(db.Integer, db.ForeignKey("patients.patient_Id"))

    nurse_Id = db.Column(db.Integer, db.ForeignKey("nurse.nurse_Id"))
    helper_Id = db.Column(db.Integer, db.ForeignKey("helpers.helper_Id"))

    admission_Date = db.Column(db.Date)
    discharge_Date = db.Column(db.Date)

    amount = db.Column(db.Float)
    mode_of_payment = db.Column(db.String(50))


class FeeMaster(db.Model):
    __tablename__ = "fee_master"

    fee_id = db.Column(db.Integer, primary_key=True)

    dept_Id = db.Column(db.Integer,
        db.ForeignKey("department.dept_Id"))

    doct_Id = db.Column(db.Integer,
        db.ForeignKey("doctor.doct_Id"),
        nullable=True)

    fee_type = db.Column(db.String(50))  
    # consultation / treatment / lab / surgery

    treatment_id = db.Column(db.Integer,
        db.ForeignKey("treatment_catalogue.treatment_id"),
        nullable=True)

    amount = db.Column(db.Float, nullable=False)

    is_active = db.Column(db.Boolean, default=True)

    effective_from = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class BillItem(db.Model):
    __tablename__ = "bill_items"

    item_id = db.Column(db.Integer, primary_key=True)

    bill_id = db.Column(db.Integer,
        db.ForeignKey("bills.bill_id"))

    item_name = db.Column(db.String(150))

    treatment_id = db.Column(db.Integer,
        db.ForeignKey("treatment_catalogue.treatment_id"),
        nullable=True)

    amount = db.Column(db.Float)

    quantity = db.Column(db.Integer, default=1)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    msg_id      = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    email       = db.Column(db.String(120), nullable=False)
    phone       = db.Column(db.String(20))
    subject     = db.Column(db.String(150))
    message     = db.Column(db.Text, nullable=False)
    is_read     = db.Column(db.Boolean, default=False)
    replied_at  = db.Column(db.DateTime, nullable=True)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class DoctorLeave(db.Model):
    __tablename__ = "doctor_leaves"
    leave_Id = db.Column(
        db.Integer,
        primary_key=True
    )
    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctor.doct_Id"),
        nullable=False
    )
    leave_date = db.Column(
        db.Date,
        nullable=False
    )
    reason = db.Column(
        db.String(255)
    )
    status = db.Column(
    db.String(20),
    default="Pending"
)

    approved_by = db.Column(
        db.Integer,
        db.ForeignKey("users.User_ID"),
        nullable=True
    )

    approved_on = db.Column(
        db.DateTime,
        nullable=True
    )

    rejection_reason = db.Column(
        db.String(255),
        nullable=True
    )
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    doctor = db.relationship(
        "Doctor",
        backref=db.backref(
            "leaves",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )