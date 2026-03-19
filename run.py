from app import create_app
from app.db_models import User, db

app = create_app()


def seed_database():
    if not User.query.first():
        worker = User(username="worker1", role="worker")
        worker.set_password("1234")

        admin = User(username="admin", role="admin")
        admin.set_password("1234")

        company = User(username="company", role="company")
        company.set_password("1234")

        db.session.add_all([worker, admin, company])
        db.session.commit()
        print("Demo accounts created: worker1, admin, company (Password: 1234)")


if __name__ == "__main__":
    with app.app_context():
        seed_database()
    app.run(debug=True, port=5000)
