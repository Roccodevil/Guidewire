from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.actuary_agent import calculate_weekly_premium
from app.agent_graph import insurance_graph
from app.db_models import ClaimLedger, DeliveryOrder, User, WeeklyPolicy, db

main_bp = Blueprint("main", __name__)


# --- AUTHENTICATION ---
@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["role"] = user.role
            if user.role == "admin":
                return redirect(url_for("main.admin_dashboard"))
            if user.role == "company":
                return redirect(url_for("main.company_dashboard"))
            return redirect(url_for("main.dashboard"))
        flash("Invalid credentials")
    return render_template("login.html")


@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))


# --- WORKER DASHBOARD ---
@main_bp.route("/")
def dashboard():
    if "user_id" not in session or session["role"] != "worker":
        return redirect(url_for("main.login"))

    worker = User.query.get(session["user_id"])
    policy = WeeklyPolicy.query.filter_by(worker_id=worker.id, is_active=True).first()

    pending_order = DeliveryOrder.query.filter_by(worker_id=worker.id, status="Pending").first()

    return render_template(
        "dashboard.html", worker=worker, policy=policy, pending_order=pending_order
    )


@main_bp.route("/buy_policy", methods=["POST"])
def buy_policy():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    worker = User.query.get(session["user_id"])
    pricing = calculate_weekly_premium(28.6139, 77.2090)

    if worker.wallet_balance >= pricing["total_premium"]:
        worker.wallet_balance -= pricing["total_premium"]
        new_policy = WeeklyPolicy(worker_id=worker.id, total_premium=pricing["total_premium"])
        db.session.add(new_policy)
        db.session.commit()
        return redirect(url_for("main.dashboard"))
    return "Insufficient Funds", 400


# --- COMPANY DASHBOARD (Zomato/Swiggy Simulator) ---
@main_bp.route("/company")
def company_dashboard():
    if "user_id" not in session or session["role"] != "company":
        return redirect(url_for("main.login"))
    workers = User.query.filter_by(role="worker").all()
    active_orders = DeliveryOrder.query.all()
    return render_template("company.html", workers=workers, orders=active_orders)


@main_bp.route("/api/dispatch_order", methods=["POST"])
def dispatch_order():
    data = request.json
    new_order = DeliveryOrder(
        worker_id=data["worker_id"],
        origin_lat=data["origin_lat"],
        origin_lon=data["origin_lon"],
        dest_lat=data["dest_lat"],
        dest_lon=data["dest_lon"],
    )
    db.session.add(new_order)
    db.session.commit()
    return jsonify({"status": "Order Dispatched"})


# --- LANGGRAPH EXECUTION (Triggered by Worker) ---
@main_bp.route("/api/start_delivery", methods=["POST"])
def start_delivery():
    data = request.json
    order = DeliveryOrder.query.get(data["order_id"])
    worker = User.query.get(order.worker_id)

    order.status = "Active"
    db.session.commit()

    initial_state = {
        "worker_id": worker.id,
        "origin_lat": order.origin_lat,
        "origin_lon": order.origin_lon,
        "dest_lat": order.dest_lat,
        "dest_lon": order.dest_lon,
        "route_data": {},
        "parametric_triggered": False,
        "fraud_score": 0.0,
        "suggested_action": "",
    }

    final_state = insurance_graph.invoke(initial_state)

    if final_state["parametric_triggered"] and final_state["fraud_score"] < 0.5:
        policy = WeeklyPolicy.query.filter_by(worker_id=worker.id, is_active=True).first()
        if policy:
            new_claim = ClaimLedger(
                policy_id=policy.id,
                payout_amount=250.0,
                reason=final_state["suggested_action"],
            )
            worker.wallet_balance += 250.0
            db.session.add(new_claim)

    order.status = "Completed"
    db.session.commit()
    return jsonify(final_state)

# --- ADMIN DASHBOARD ---
@main_bp.route("/admin")
def admin_dashboard():
    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("main.login"))
    policies = WeeklyPolicy.query.all()
    claims = ClaimLedger.query.all()
    return render_template("admin.html", policies=policies, claims=claims)

