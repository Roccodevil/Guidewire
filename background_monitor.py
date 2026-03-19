import time

from apscheduler.schedulers.background import BackgroundScheduler

from app import create_app
from app.agent_graph import insurance_graph
from app.db_models import ClaimLedger, User, WeeklyPolicy, db

app = create_app()


def monitor_active_policies():
    """
    This function runs every X minutes. It finds all active workers,
    checks their current assumed coordinates, and runs the LangGraph AI.
    """
    with app.app_context():
        print("\n--- Running Autonomous Policy Monitor ---")
        active_policies = WeeklyPolicy.query.filter_by(is_active=True).all()

        if not active_policies:
            print("No active policies to monitor.")
            return

        for policy in active_policies:
            worker = User.query.get(policy.worker_id)
            print(f"Checking risk for Worker: {worker.username} (Policy #{policy.id})")

            state = {
                "worker_id": worker.id,
                "origin_lat": 28.6139,
                "origin_lon": 77.2090,
                "dest_lat": 28.5355,
                "dest_lon": 77.2410,
                "route_data": {},
                "parametric_triggered": False,
                "fraud_score": 0.0,
                "suggested_action": "",
            }

            result = insurance_graph.invoke(state)

            if result["parametric_triggered"] and result["fraud_score"] < 0.5:
                print(f"*** TRIGGER EVENT DETECTED FOR {worker.username} ***")

                new_claim = ClaimLedger(
                    policy_id=policy.id,
                    payout_amount=250.0,
                    reason=result["suggested_action"],
                )
                worker.wallet_balance += 250.0
                db.session.add(new_claim)
                db.session.commit()
                print(f"Automated Payout Complete: ₹250 to {worker.username}")
            else:
                print("Status: Clear. No payout triggered.")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(monitor_active_policies, "interval", minutes=1)
    scheduler.start()
    print("Autonomous Background Monitor Started.")


if __name__ == "__main__":
    start_scheduler()

    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down monitor.")