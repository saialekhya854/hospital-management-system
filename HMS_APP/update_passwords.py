# from app import app
# from database import db
# from models import User
# from werkzeug.security import generate_password_hash

# print("🚀 Script started...")
# print("HELLO TEST")

# def update_all_passwords():
#     with app.app_context():

#         users = User.query.all()
#         count = 0

#         for user in users:
#             # Skip already hashed passwords (Werkzeug hashes start with 'pbkdf2:')
#             if user.Password and not user.Password.startswith("pbkdf2:"):
#                 user.Password = generate_password_hash(user.Password)
#                 count += 1

#         db.session.commit()

#         print(f"✅ Updated {count} users passwords successfully")


# if __name__ == "__main__":
#     update_all_passwords()



from app import app
from database import db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    users = User.query.all()

    total = len(users)
    print(f"Total users: {total}")

    for i, user in enumerate(users, start=1):
        user.Password = generate_password_hash(user.Password)

        # 👇 show progress
        print(f"Updating {i}/{total}")

    db.session.commit()

print("✅ All passwords updated")