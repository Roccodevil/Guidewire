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

from app.actuary_agent import run_autonomous_actuary, recommend_best_policy
from app.agent_graph import insurance_graph
from app.db_models import ClaimLedger, DeliveryOrder, User, WeeklyPolicy, db, PolicyOption
from app.dispatch_agent import auto_assign_order
from sqlalchemy.exc import OperationalError

from app.services import get_tomtom_route_data
import datetime as dt
from collections import defaultdict

main_bp = Blueprint("main", __name__)


# --- AUTHENTICATION ---
@main_bp.route("/login")
def login():
    return render_template("login.html", login_role=None)


@main_bp.route("/login/<role>", methods=["GET", "POST"])
def login_role(role):
    role = role.lower()
    if role not in {"worker", "company", "admin"}:
        return redirect(url_for("main.login"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        try:
            user = User.query.filter_by(username=username).first()
        except OperationalError:
            db.session.rollback()
            flash("Database connection temporarily unavailable. Please retry in a few seconds.")
            return render_template("login.html", login_role=role), 503

        if user and user.check_password(password):
            if user.role != role:
                flash(f"This account is not a {role} account. Please use the correct login portal.")
                return render_template("login.html", login_role=role), 403
            session["user_id"] = user.id
            session["role"] = user.role
            if user.role == "admin":
                return redirect(url_for("main.admin_dashboard"))
            if user.role == "company":
                return redirect(url_for("main.company_dashboard"))
            return redirect(url_for("main.dashboard"))
        flash("Invalid credentials")
    return render_template("login.html", login_role=role)


@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))


# --- WORKER DASHBOARD ---
@main_bp.route('/')
def dashboard():
    if 'user_id' not in session or session['role'] != 'worker': return redirect(url_for('main.login'))
    worker = User.query.get(session['user_id'])
    policy = WeeklyPolicy.query.filter_by(worker_id=worker.id, is_active=True).first()
    pending_orders = DeliveryOrder.query.filter_by(worker_id=worker.id, status="Pending").all()
    policy_options = PolicyOption.query.all()
    
    time_left_pct = 0; days_left = 0
    if policy:
        import datetime as dt
        end_date = policy.start_date + dt.timedelta(days=7)
        days_left = max(0, (end_date - dt.datetime.utcnow()).days)
        time_left_pct = max(0, min(100, (days_left / 7.0) * 100))
        
    from app.actuary_agent import recommend_best_policy
    recommended = recommend_best_policy(worker.wallet_balance, policy_options) if not policy else None
    
    # NEW: Fetch REAL weather data for the dashboard
    from app.services import get_weather_forecast
    # Use worker's last known location, or default to Delhi
    live_weather = get_weather_forecast(28.6139, 77.2090) 
    
    return render_template('dashboard.html', worker=worker, policy=policy, 
                           pending_orders=pending_orders, options=policy_options, 
                           recommended=recommended, days_left=days_left, 
                           time_left_pct=time_left_pct, live_weather=live_weather)

@main_bp.route("/buy_policy", methods=["POST"])
def buy_policy():
    tier = request.form.get('tier')
    premium = float(request.form.get('premium'))
    worker = User.query.get(session['user_id'])
    
    # Fetch the exact option to copy its terms/limits
    option = PolicyOption.query.filter_by(tier=tier).first()
    
    if worker.wallet_balance >= premium and option:
        worker.wallet_balance -= premium
        new_policy = WeeklyPolicy(
            worker_id=worker.id, tier=tier, total_premium=premium,
            coverage_limit=option.coverage_limit, terms_text=option.terms_text,
            rules_text=option.rules_text
        )
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


@main_bp.route('/api/worker_pending_orders')
def worker_pending_orders():
    if 'user_id' not in session or session.get('role') != 'worker':
        return jsonify({"error": "Unauthorized"}), 401

    orders = DeliveryOrder.query.filter_by(worker_id=session['user_id'], status="Pending").order_by(DeliveryOrder.id.desc()).all()
    return jsonify([
        {
            "id": order.id,
            "origin_name": order.origin_name,
            "origin_lat": order.origin_lat,
            "origin_lon": order.origin_lon,
            "dest_name": order.dest_name,
            "dest_lat": order.dest_lat,
            "dest_lon": order.dest_lon,
        }
        for order in orders
    ])


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
        origin_name=data.get("origin_name", "Pinned Origin"),
        dest_name=data.get("dest_name", "Pinned Destination"),
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
        "fraud_status": "PENDING",       # <--- ADD THIS
        "xai_explanation": "",           # <--- ADD THIS
        "suggested_action": "",
    }

    final_state = insurance_graph.invoke(initial_state)

    if final_state["parametric_triggered"] and final_state["fraud_score"] < 0.5:
        policy = WeeklyPolicy.query.filter_by(worker_id=worker.id, is_active=True).first()
        if policy and policy.coverage_used < policy.coverage_limit:
            payout = min(250.0, policy.coverage_limit - policy.coverage_used) # Don't exceed limit
            policy.coverage_used += payout
            new_claim = ClaimLedger(policy_id=policy.id, payout_amount=payout, reason=final_state["suggested_action"])
            worker.wallet_balance += payout 
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
    all_worker_policies = WeeklyPolicy.query.all()
    active_worker_policies = WeeklyPolicy.query.filter_by(is_active=True).all()
    claims = ClaimLedger.query.order_by(ClaimLedger.timestamp.desc()).all()
    live_orders = DeliveryOrder.query.filter(DeliveryOrder.status.in_(['Pending', 'Active'])).all()

    total_premiums = sum([p.total_premium for p in active_worker_policies])
    total_payouts = sum([c.payout_amount for c in claims])
    net_profit = total_premiums - total_payouts

    worker_by_id = {w.id: w for w in workers}
    policy_by_id = {p.id: p for p in all_worker_policies}

    worker_claim_amount = defaultdict(float)
    worker_claim_count = defaultdict(int)
    tier_claim_amount = defaultdict(float)
    claims_daily = defaultdict(float)

    for claim in claims:
        policy = policy_by_id.get(claim.policy_id)
        if not policy:
            continue
        worker_claim_amount[policy.worker_id] += claim.payout_amount
        worker_claim_count[policy.worker_id] += 1
        tier_claim_amount[policy.tier] += claim.payout_amount
        day_key = claim.timestamp.strftime("%Y-%m-%d")
        claims_daily[day_key] += claim.payout_amount

    worker_coverage_usage = []
    total_coverage_limit = 0.0
    total_coverage_used = 0.0

    utilization_buckets = {
        "0-10%": 0,
        "10-25%": 0,
        "25-50%": 0,
        "50-75%": 0,
        "75-100%": 0,
        ">100%": 0,
    }

    for policy in active_worker_policies:
        w = worker_by_id.get(policy.worker_id)
        if not w:
            continue
        total_coverage_limit += float(policy.coverage_limit or 0)
        total_coverage_used += float(policy.coverage_used or 0)
        utilization_pct = 0.0
        if policy.coverage_limit:
            utilization_pct = (float(policy.coverage_used or 0) / float(policy.coverage_limit)) * 100

        if utilization_pct <= 10:
            utilization_buckets["0-10%"] += 1
        elif utilization_pct <= 25:
            utilization_buckets["10-25%"] += 1
        elif utilization_pct <= 50:
            utilization_buckets["25-50%"] += 1
        elif utilization_pct <= 75:
            utilization_buckets["50-75%"] += 1
        elif utilization_pct <= 100:
            utilization_buckets["75-100%"] += 1
        else:
            utilization_buckets[">100%"] += 1

        worker_coverage_usage.append({
            "worker_id": w.id,
            "username": w.username,
            "tier": policy.tier,
            "coverage_used": float(policy.coverage_used or 0),
            "coverage_limit": float(policy.coverage_limit or 0),
            "utilization_pct": round(utilization_pct, 2),
            "claim_count": worker_claim_count.get(w.id, 0),
            "claim_amount": round(worker_claim_amount.get(w.id, 0.0), 2),
        })

    worker_coverage_usage.sort(key=lambda x: x["coverage_used"], reverse=True)

    tier_performance_map = defaultdict(lambda: {
        "tier": "",
        "active_policies": 0,
        "premium_collected": 0.0,
        "coverage_used": 0.0,
        "coverage_limit": 0.0,
        "claim_paid": 0.0,
    })

    for policy in active_worker_policies:
        t = tier_performance_map[policy.tier]
        t["tier"] = policy.tier
        t["active_policies"] += 1
        t["premium_collected"] += float(policy.total_premium or 0)
        t["coverage_used"] += float(policy.coverage_used or 0)
        t["coverage_limit"] += float(policy.coverage_limit or 0)

    for tier_name, payout in tier_claim_amount.items():
        t = tier_performance_map[tier_name]
        t["tier"] = tier_name
        t["claim_paid"] = float(payout)

    tier_performance = sorted(
        [
            {
                **v,
                "premium_collected": round(v["premium_collected"], 2),
                "coverage_used": round(v["coverage_used"], 2),
                "coverage_limit": round(v["coverage_limit"], 2),
                "claim_paid": round(v["claim_paid"], 2),
            }
            for v in tier_performance_map.values()
            if v["tier"]
        ],
        key=lambda item: item["premium_collected"],
        reverse=True,
    )

    claims_trend = [
        {"date": date_key, "amount": round(amount, 2)}
        for date_key, amount in sorted(claims_daily.items())
    ]

    loss_ratio_pct = 0.0
    if total_premiums > 0:
        loss_ratio_pct = (total_payouts / total_premiums) * 100

    utilization_pct = 0.0
    if total_coverage_limit > 0:
        utilization_pct = (total_coverage_used / total_coverage_limit) * 100

    analytics = {
        "total_coverage_limit": round(total_coverage_limit, 2),
        "total_coverage_used": round(total_coverage_used, 2),
        "coverage_utilization_pct": round(utilization_pct, 2),
        "total_claim_count": len(claims),
        "average_claim_amount": round((total_payouts / len(claims)) if claims else 0.0, 2),
        "loss_ratio_pct": round(loss_ratio_pct, 2),
        "worker_coverage_usage": worker_coverage_usage,
        "worker_utilization_buckets": [
            {"bucket": k, "count": v}
            for k, v in utilization_buckets.items()
        ],
        "tier_performance": tier_performance,
        "claims_trend": claims_trend,
    }
    
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
        admin_analytics=analytics,
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
    # 1. Run the new autonomous ML pipeline
    tiers_data = run_autonomous_actuary()
    
    # 2. Save the LLM-generated policies to the database
    for t in tiers_data:
        # Prepend the profit margin to the description
        business_reasoning = f"[Proj. Margin: {t.get('profit_margin_pct', 0)}%] {t.get('xai_actuarial_reasoning', t.get('xai', ''))}"
        
        option = PolicyOption(
            tier=t.get('tier', 'Custom'), 
            premium=t.get('premium', 0), 
            coverage_limit=t.get('coverage', 0), 
            xai_description=business_reasoning,
            terms_text=t.get('terms', 'Standard platform terms apply.'),
            rules_text=t.get('rules', 'Requires active GPS tracking.')
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

@main_bp.route('/api/admin_live_data')
def admin_live_data():
    """Fetches live order tracking without refreshing the page."""
    live_orders = DeliveryOrder.query.filter(DeliveryOrder.status.in_(['Pending', 'Active'])).all()
    data = []
    for order in live_orders:
        data.append({
            "id": order.id,
            "worker_id": order.worker_id,
            "route": f"{order.origin_name} → {order.dest_name}",
            "status": order.status,
            "lat": order.current_lat,
            "lon": order.current_lon
        })
    return jsonify(data)

@main_bp.route('/api/auto_dispatch', methods=['POST'])
def auto_dispatch():
    data = request.json
    
    # 1. Gather Order Details
    order_details = {
        "origin": data['origin_name'], 
        "destination": data['dest_name'], 
        "estimated_risk": "High Traffic Zone"
    }
    
    # 2. Gather Worker Context (Who has policies?)
    workers = User.query.filter_by(role='worker').all()
    worker_context = []
    for w in workers:
        policy = WeeklyPolicy.query.filter_by(worker_id=w.id, is_active=True).first()
        worker_context.append({
            "id": w.id, 
            "username": w.username, 
            "has_active_policy": True if policy else False,
            "policy_tier": policy.tier if policy else "None"
        })
        
    # 3. Ask the AI Dispatcher who should get the order
    decision = auto_assign_order(order_details, worker_context)
    
    # 4. Create the order in the database
    new_order = DeliveryOrder(
        worker_id=decision['selected_worker_id'],
        origin_lat=data['origin_lat'], origin_lon=data['origin_lon'], origin_name=data['origin_name'],
        dest_lat=data['dest_lat'], dest_lon=data['dest_lon'], dest_name=data['dest_name']
    )
    db.session.add(new_order)
    db.session.commit()
    
    return jsonify({
        "status": "Order Dispatched via AI",
        "assigned_to": decision['selected_worker_id'],
        "xai_audit": decision['xai_reasoning']
    })