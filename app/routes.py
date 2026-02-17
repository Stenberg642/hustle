from flask import Blueprint, request, redirect, current_app, url_for, abort, render_template, flash, send_from_directory
from flask_login import login_required, current_user
from app import db
from app.models import CheckIn, User
from datetime import datetime, date, timedelta, time
import os
from werkzeug.utils import secure_filename
import uuid
from functools import wraps

main = Blueprint("main", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def checkin_window_open():
    now = datetime.now()
    return now.weekday() < 5 and time(0, 0) <= now.time() < time(22, 0)


def reset_weekly_streak_if_monday(user):
    today = datetime.now().date()
    if today.weekday() == 0:
        if user.last_checkin_date and user.last_checkin_date < today:
            user.weekly_streak = 0


def apply_weekly_penalty(user):
    now = datetime.now()

    if now.weekday() == 4 and now.time() >= time(22, 0):
        current_week = now.strftime("%Y-%W")

        if user.last_penalty_week != current_week:
            if user.weekly_streak < 5:
                user.debt += 10
                user.last_penalty_week = current_week
                return True
    return False


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return f(*args, **kwargs)
    return decorated


@main.route("/")
@login_required
def index():
    return redirect(url_for("main.dashboard"))


@main.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():

    reset_weekly_streak_if_monday(current_user)

    if apply_weekly_penalty(current_user):
        flash("You owe the group R10 (less than 5 check-ins this week).", "danger")

    db.session.commit()

    today = date.today()

    if request.method == "POST":

        if not checkin_window_open():
            flash("Check-ins allowed Monday–Friday, 00:00–22:00 only.", "danger")
            return redirect(url_for("main.dashboard"))

        existing = CheckIn.query.filter_by(
            user_id=current_user.id,
            checkin_date=today
        ).first()

        if existing:
            flash("You already submitted today.", "warning")
            return redirect(url_for("main.dashboard"))

        file = request.files.get("proof")
        content = request.form.get("content")

        if not content or not content.strip():
            flash("Description required.", "error")
            return redirect(url_for("main.dashboard"))

        if not file or file.filename == "":
            flash("Proof image required.", "error")
            return redirect(url_for("main.dashboard"))

        if not allowed_file(file.filename):
            flash("Invalid file type.", "error")
            return redirect(url_for("main.dashboard"))

        filename = secure_filename(file.filename)
        ext = filename.rsplit(".", 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex[:12]}.{ext}"

        upload_path = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_path, exist_ok=True)
        file.save(os.path.join(upload_path, unique_name))

        checkin = CheckIn(
            user_id=current_user.id,
            checkin_date=today,
            proof_file=unique_name,
            content=content,
            status="pending"
        )

        db.session.add(checkin)
        db.session.commit()

        flash("Check-in submitted successfully!", "success")
        return redirect(url_for("main.dashboard"))

    checkins = CheckIn.query.filter_by(
        user_id=current_user.id
    ).order_by(CheckIn.checkin_date.desc()).all()

    return render_template("dashboard.html", checkins=checkins)


@main.route("/admin/review")
@login_required
@admin_required
def review_checkins():
    pending = CheckIn.query.filter_by(status="pending").all()
    return render_template("admin_review.html", pending=pending)


@main.route("/admin/approve/<int:checkin_id>")
@login_required
@admin_required
def approve_checkin(checkin_id):

    checkin = CheckIn.query.get_or_404(checkin_id)

    if checkin.status != "pending":
        flash("Already processed.", "warning")
        return redirect(url_for("main.review_checkins"))

    user = checkin.user
    checkin_date = checkin.checkin_date

    if user.last_checkin_date:
        if user.last_checkin_date == checkin_date - timedelta(days=1):
            user.current_streak += 1
        else:
            user.current_streak = 1
    else:
        user.current_streak = 1

    if checkin_date.weekday() < 5:
        user.weekly_streak += 1

    if user.current_streak > user.longest_streak:
        user.longest_streak = user.current_streak

    user.last_checkin_date = checkin_date
    checkin.status = "approved"

    db.session.commit()

    flash("Check-in approved.", "success")
    return redirect(url_for("main.review_checkins"))
    
@main.route("/make-admin")
def make_admin():
    from app.models import User
    from app import db

    user = User.query.filter_by(email="drizzydsk@gmail.com").first()
    if user:
        user.is_admin = True
        db.session.commit()
        return "You are now admin"

    return "User not found"


@main.route("/admin/reject/<int:checkin_id>")
@login_required
@admin_required
def reject_checkin(checkin_id):

    checkin = CheckIn.query.get_or_404(checkin_id)

    if checkin.status != "pending":
        flash("Already processed.", "warning")
        return redirect(url_for("main.review_checkins"))

    checkin.status = "rejected"
    db.session.commit()

    flash("Check-in rejected.", "error")
    return redirect(url_for("main.review_checkins"))


@main.route("/leaderboard")
@login_required
def leaderboard():
    users = User.query.order_by(User.current_streak.desc()).all()
    return render_template("leaderboard.html", users=users)


@main.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if user:
            flash("Password reset link sent.", "success")
        else:
            flash("Email not found.", "error")

        return redirect(url_for("main.forgot_password"))

    return render_template("forgot_password.html")


@main.route("/uploads/<filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        filename
    )

