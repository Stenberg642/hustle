from datetime import datetime
from app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    role = db.Column(db.String(20), default="user")
    is_admin = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    current_streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    weekly_streak = db.Column(db.Integer, default=0)
    debt = db.Column(db.Integer, default=0)           

    last_checkin_date = db.Column(db.Date)

    checkins = db.relationship("CheckIn", backref="user", lazy=True)


class CheckIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    checkin_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="pending")
    proof_file = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "checkin_date", name="unique_daily_checkin"),
    )


class Leaderboard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    total_points = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    rank_position = db.Column(db.Integer)

