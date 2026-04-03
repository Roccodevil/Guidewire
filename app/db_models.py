from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False) 
    wallet_balance = db.Column(db.Float, default=1000.0)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# NEW: Admin generates these using Autoregressor/XAI
class PolicyOption(db.Model):
    __tablename__ = 'policy_options'
    id = db.Column(db.Integer, primary_key=True)
    tier = db.Column(db.String(50), nullable=False)
    premium = db.Column(db.Float, nullable=False)
    coverage_limit = db.Column(db.Float, nullable=False)
    xai_description = db.Column(db.Text, nullable=False)
    terms_text = db.Column(db.Text, default="1. Payouts capped at weekly limit. 2. Must be online during event.")
    rules_text = db.Column(db.Text, default="Requires active GPS telemetry and platform connection.")
    is_active = db.Column(db.Boolean, default=True)

class WeeklyPolicy(db.Model):
    __tablename__ = 'weekly_policies'
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tier = db.Column(db.String(50), nullable=False)
    total_premium = db.Column(db.Float, nullable=False)
    coverage_limit = db.Column(db.Float, nullable=False)
    coverage_used = db.Column(db.Float, default=0.0) # NEW: Track payouts
    terms_text = db.Column(db.Text)
    rules_text = db.Column(db.Text)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class DeliveryOrder(db.Model):
    __tablename__ = 'delivery_orders'
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    origin_name = db.Column(db.String(100))
    dest_name = db.Column(db.String(100))
    origin_lat = db.Column(db.Float, nullable=False)
    origin_lon = db.Column(db.Float, nullable=False)
    dest_lat = db.Column(db.Float, nullable=False)
    dest_lon = db.Column(db.Float, nullable=False)
    # NEW: Live tracking fields
    current_lat = db.Column(db.Float)
    current_lon = db.Column(db.Float)
    status = db.Column(db.String(20), default="Pending") 

class ClaimLedger(db.Model):
    __tablename__ = 'claim_ledger'
    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('weekly_policies.id'), nullable=False)
    payout_amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)