"""
HMS — Hospital Management System
Flask application entry point
"""

from flask import Flask, session, redirect
from flask_mail import Message
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

import config
from config import mail

# IMPORTANT
from database import db

# ── Blueprint imports ─────────────────────────────────────────────────────────
from routes.common_routes       import common_bp
from routes.admin_routes        import admin_bp
from routes.receptionist_routes import receptionist_bp
from routes.doctor_routes       import doctor_bp
from routes.patient_routes      import patient_bp
from routes.auditor_routes      import auditor_bp
from routes.billing_routes      import billing_bp
from routes.public_routes       import public_bp


# ── App factory ───────────────────────────────────────────────────────────────
def create_app():

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    # secret key
    app.secret_key = config.SECRET_KEY

    # load config
    app.config.from_object(config)

    # REQUIRED FOR SQLALCHEMY
    app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # init extensions
    db.init_app(app)
    migrate = Migrate(app, db)

    # init flask mail
    mail.init_app(app)

    # ───── GLOBAL MAIL FUNCTION ─────
    def send_email(subject, recipients, body):

        if not recipients:
            return

        recipients = [r for r in recipients if r]

        if not recipients:
            return

        msg = Message(
            subject=subject,
            recipients=recipients,
            body=body
        )

        mail.send(msg)

    app.send_email = send_email

    # At top of app.py, add:

# Inside create_app(), after db.init_app(app):
    def auto_mark_no_shows():
        """Background job: mark overdue Scheduled appointments as No-Show."""
        from datetime import date, datetime, timedelta
        with app.app_context():
            from database import get_db
            from models import Appointment
            db = next(get_db())
            today   = date.today()
            now     = datetime.now()
            cutoff  = now - timedelta(minutes=15)
            updated = 0

            # Past-date → No-Show
            past = db.query(Appointment).filter(
                Appointment.appointment_Date < today,
                Appointment.appointment_status == "Scheduled"
            ).all()
            for a in past:
                a.appointment_status = "No-Show"
                updated += 1

            # Today + 15 min elapsed → No-Show
            today_schd = db.query(Appointment).filter(
                Appointment.appointment_Date == today,
                Appointment.appointment_status == "Scheduled"
            ).all()
            for a in today_schd:
                t = getattr(a, "appointment_Time", None)
                if t:
                    try:
                        if datetime.combine(today, t) <= cutoff:
                            a.appointment_status = "No-Show"
                            updated += 1
                    except Exception:
                        pass

            if updated:
                db.commit()
                print(f"[Scheduler] Marked {updated} appointment(s) as No-Show")

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=auto_mark_no_shows, trigger="interval", minutes=15)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

    # ── Register blueprints ───────────────────────────────────────────────────
    app.register_blueprint(common_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(receptionist_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(auditor_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(public_bp)
    # print(app.url_map)
    # ── Inject session into templates ─────────────────────────────────────────
    @app.context_processor
    def inject_session():
        return {"session": session}

    # ── Error handlers ────────────────────────────────────────────────────────
    @app.errorhandler(401)
    def unauthorized(_):
        return redirect("/login")

    @app.errorhandler(403)
    def forbidden(_):
        return redirect("/login")

    @app.errorhandler(404)
    def not_found(e):
        return (
            "<h2 style='font-family:sans-serif;text-align:center;margin-top:4rem'>"
            "404 — Page not found. <a href='/'>Go home</a></h2>"
        ), 404

    return app


# ── Run ───────────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)