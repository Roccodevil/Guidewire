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
from datetime import datetime, timedelta

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

    route_info = get_tomtom_route_data(
        float(data["origin_lat"]),
        float(data["origin_lon"]),
        float(data["dest_lat"]),
        float(data["dest_lon"]),
    )
    by_road_distance_km = route_info.get("route_length_km")

    if by_road_distance_km is None:
        fallback_distance = data.get("distance_km")
        by_road_distance_km = float(fallback_distance) if fallback_distance is not None else None

    new_order = DeliveryOrder(
        worker_id=data["worker_id"],
        origin_lat=data["origin_lat"],
        origin_lon=data["origin_lon"],
        origin_name=data.get("origin_name", "Unknown Origin"),
        dest_lat=data["dest_lat"],
        dest_lon=data["dest_lon"],
        dest_name=data.get("dest_name", "Unknown Destination"),
        distance_km=by_road_distance_km
    )
    db.session.add(new_order)
    db.session.commit()
    return jsonify({"status": "Order Dispatched", "order_id": new_order.id, "distance_km": new_order.distance_km})


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


@main_bp.route('/api/admin/analysis', methods=['GET'])
def admin_analysis_data():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401

    granularity = request.args.get('granularity', 'daily').lower()
    if granularity not in ('daily', 'weekly'):
        granularity = 'daily'

    start_raw = request.args.get('start')
    end_raw = request.args.get('end')
    worker_id_raw = request.args.get('worker_id')

    today = datetime.utcnow().date()
    default_start = today - timedelta(days=30)

    try:
        start_date = datetime.strptime(start_raw, '%Y-%m-%d').date() if start_raw else default_start
        end_date = datetime.strptime(end_raw, '%Y-%m-%d').date() if end_raw else today
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    if end_date < start_date:
        return jsonify({"error": "End date cannot be before start date."}), 400

    # Policy analytics
    policies = WeeklyPolicy.query.all()
    policy_money = {}
    policy_uses = {}

    for policy in policies:
        tier = policy.tier or 'Unknown'
        policy_money[tier] = policy_money.get(tier, 0.0) + float(policy.total_premium or 0.0)
        policy_uses[tier] = policy_uses.get(tier, 0) + 1

    policy_labels = sorted(policy_money.keys())
    policy_total_amounts = [round(policy_money[label], 2) for label in policy_labels]
    policy_use_counts = [policy_uses[label] for label in policy_labels]

    # Compensation trend analytics
    all_claims = ClaimLedger.query.order_by(ClaimLedger.timestamp.asc()).all()
    filtered_claims = []
    for claim in all_claims:
        claim_date = claim.timestamp.date()
        if start_date <= claim_date <= end_date:
            filtered_claims.append(claim)

    grouped = {}
    for claim in filtered_claims:
        claim_date = claim.timestamp.date()
        if granularity == 'weekly':
            bucket_date = claim_date - timedelta(days=claim_date.weekday())
        else:
            bucket_date = claim_date
        key = bucket_date.isoformat()
        grouped[key] = grouped.get(key, 0.0) + float(claim.payout_amount or 0.0)

    labels = []
    values = []
    cursor = start_date
    if granularity == 'weekly':
        cursor = start_date - timedelta(days=start_date.weekday())
        end_cursor = end_date - timedelta(days=end_date.weekday())
        while cursor <= end_cursor:
            key = cursor.isoformat()
            labels.append(key)
            values.append(round(grouped.get(key, 0.0), 2))
            cursor += timedelta(days=7)
    else:
        while cursor <= end_date:
            key = cursor.isoformat()
            labels.append(key)
            values.append(round(grouped.get(key, 0.0), 2))
            cursor += timedelta(days=1)

    worker_policy_payload = None
    if worker_id_raw:
        try:
            worker_id = int(worker_id_raw)
        except ValueError:
            return jsonify({"error": "worker_id must be an integer."}), 400

        worker = User.query.filter_by(id=worker_id, role='worker').first()
        if not worker:
            return jsonify({"error": "Worker not found."}), 404

        worker_policies = WeeklyPolicy.query.filter_by(worker_id=worker_id).all()
        worker_policy_money = {}
        worker_policy_uses = {}

        for policy in worker_policies:
            tier = policy.tier or 'Unknown'
            worker_policy_money[tier] = worker_policy_money.get(tier, 0.0) + float(policy.total_premium or 0.0)
            worker_policy_uses[tier] = worker_policy_uses.get(tier, 0) + 1

        worker_labels = sorted(worker_policy_uses.keys())
        worker_policy_payload = {
            "worker_id": worker_id,
            "worker_name": worker.username,
            "labels": worker_labels,
            "use_counts": [worker_policy_uses[label] for label in worker_labels],
            "total_amounts": [round(worker_policy_money.get(label, 0.0), 2) for label in worker_labels],
        }

    return jsonify({
        "policy": {
            "labels": policy_labels,
            "total_amounts": policy_total_amounts,
            "use_counts": policy_use_counts,
        },
        "compensation": {
            "labels": labels,
            "totals": values,
            "granularity": granularity,
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "worker_policy": worker_policy_payload,
    })
