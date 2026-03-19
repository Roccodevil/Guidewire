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

from app.actuary_agent import calculate_weekly_premium, generate_policy_tiers, recommend_best_policy
from app.agent_graph import insurance_graph
from app.db_models import ClaimLedger, DeliveryOrder, User, WeeklyPolicy, db, PolicyOption

from app.services import get_tomtom_route_data

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
    if 'user_id' not in session or session['role'] != 'worker': return redirect(url_for('main.login'))
    worker = User.query.get(session['user_id'])
    policy = WeeklyPolicy.query.filter_by(worker_id=worker.id, is_active=True).first()
    pending_orders = DeliveryOrder.query.filter_by(worker_id=worker.id, status="Pending").all()
    
    policy_options = PolicyOption.query.all()
    recommended = recommend_best_policy(worker.wallet_balance, policy_options) if not policy else None
    
    return render_template('dashboard.html', worker=worker, policy=policy, pending_orders=pending_orders, options=policy_options, recommended=recommended)


@main_bp.route("/buy_policy", methods=["POST"])
def buy_policy():
    tier = request.form.get('tier')
    premium = float(request.form.get('premium'))
    worker = User.query.get(session['user_id'])
    
    if worker.wallet_balance >= premium:
        worker.wallet_balance -= premium
        new_policy = WeeklyPolicy(worker_id=worker.id, tier=tier, total_premium=premium)
        db.session.add(new_policy)
        db.session.commit()
        return redirect(url_for('main.dashboard'))
    return "Insufficient Funds", 400

# --- ADD THIS TO WORKER DASHBOARD ROUTES ---
@main_bp.route('/api/reject_order', methods=['POST'])
def reject_order():
    """Allows the worker to reject a pending delivery."""
    data = request.json
    order = DeliveryOrder.query.get(data['order_id'])
    if order:
        order.status = "Rejected"
        db.session.commit()
        return jsonify({"status": "Order Rejected"})
    return jsonify({"error": "Order not found"}), 404


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
    return jsonify({
        "parametric_triggered": final_state["parametric_triggered"],
        "suggested_action": final_state["suggested_action"],
        "route_data": final_state.get("route_data", {}) # Contains the TomTom polyline
    })


# --- ADMIN: WORKER MANAGEMENT ---
@main_bp.route('/admin/add_worker', methods=['POST'])
def add_worker():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('main.login'))

    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return "Username and password are required", 400

    if User.query.filter_by(username=username).first():
        return "Username already exists", 400

    new_worker = User(username=username, role='worker')
    new_worker.set_password(password)
    db.session.add(new_worker)
    db.session.commit()
    return redirect(url_for('main.admin_dashboard'))


@main_bp.route('/admin/delete_worker/<int:id>', methods=['POST'])
def delete_worker(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('main.login'))

    DeliveryOrder.query.filter_by(worker_id=id).delete()
    WeeklyPolicy.query.filter_by(worker_id=id).delete()
    User.query.filter_by(id=id, role='worker').delete()
    db.session.commit()
    return redirect(url_for('main.admin_dashboard'))


# --- ADMIN: MANUAL POLICY CREATION ---
@main_bp.route('/admin/add_policy', methods=['POST'])
def add_policy():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('main.login'))

    tier = request.form.get('tier')
    premium_raw = request.form.get('premium')
    coverage_raw = request.form.get('coverage')
    desc = request.form.get('description')

    if not tier or premium_raw is None or coverage_raw is None or not desc:
        return "Missing required fields", 400

    try:
        premium = float(premium_raw)
        coverage = float(coverage_raw)
    except (TypeError, ValueError):
        return "Premium and coverage must be numeric", 400

    new_policy = PolicyOption(tier=tier, premium=premium, coverage_limit=coverage, xai_description=desc)
    db.session.add(new_policy)
    db.session.commit()
    return redirect(url_for('main.admin_dashboard'))


@main_bp.route('/admin/delete_policy_option/<int:id>', methods=['POST'])
def delete_policy_option(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('main.login'))

    PolicyOption.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for('main.admin_dashboard'))


# --- ADMIN DASHBOARD ---
@main_bp.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin': 
        return redirect(url_for('main.login'))
    
    workers = User.query.filter_by(role='worker').all()
    policy_options = PolicyOption.query.all()
    active_worker_policies = WeeklyPolicy.query.filter_by(is_active=True).all()
    claims = ClaimLedger.query.order_by(ClaimLedger.timestamp.desc()).all()
    live_orders = DeliveryOrder.query.filter(DeliveryOrder.status.in_(['Pending', 'Active'])).all()

    total_premiums = sum([p.total_premium for p in active_worker_policies])
    total_payouts = sum([c.payout_amount for c in claims])
    net_profit = total_premiums - total_payouts
    
    return render_template(
        'admin.html',
        workers=workers,
        policy_options=policy_options,
        active_worker_policies=active_worker_policies,
        claims=claims,
        live_orders=live_orders,
        total_premiums=total_premiums,
        total_payouts=total_payouts,
        net_profit=net_profit,
    )

# --- ADD THIS TO ADMIN ROUTES FOR MANUAL POLICY OVERRIDE ---
@main_bp.route('/api/update_policy', methods=['POST'])
def update_policy():
    """Allows admin to manually override a worker's policy premium."""
    policy_id = request.form.get('policy_id')
    new_premium = request.form.get('new_premium')
    
    policy = WeeklyPolicy.query.get(policy_id)
    if policy:
        policy.total_premium = float(new_premium)
        db.session.commit()
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/api/generate_tiers', methods=['POST'])
def generate_tiers():
    PolicyOption.query.delete() # Clear old ones
    
    # Simulate AR and Weather data
    tiers_data = generate_policy_tiers(ar_baseline_risk=42.5, weather_forecast="Heavy Monsoon Rains")
    
    for t in tiers_data:
        option = PolicyOption(
            tier=t['tier'], premium=t['premium'], 
            coverage_limit=t['coverage'], xai_description=t['xai']
        )
        db.session.add(option)
    db.session.commit()
    return redirect(url_for('main.admin_dashboard'))

# --- LIVE TRACKING API (Called by Worker's JS while driving) ---
@main_bp.route('/api/update_gps', methods=['POST'])
def update_gps():
    data = request.json
    order = DeliveryOrder.query.get(data['order_id'])
    if order:
        order.current_lat = data['lat']
        order.current_lon = data['lon']
        db.session.commit()
    return jsonify({"status": "GPS Updated"})
