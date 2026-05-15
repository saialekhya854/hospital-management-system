import random
from app import app
from database import get_db_ctx
from models import Appointment, Doctor

with app.app_context():
    with get_db_ctx() as db:
        doctor_ids = [d[0] for d in db.query(Doctor.doct_Id).all()]

        # Assign weights (some doctors get more patients)
        weights = [random.randint(1, 10) for _ in doctor_ids]

        appointments = db.query(Appointment).all()

        for appt in appointments:
            appt.doct_Id = random.choices(doctor_ids, weights=weights)[0]

        db.commit()

print("Weighted random doctor assignment completed!")