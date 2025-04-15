from flask import Blueprint, jsonify

user_bp = Blueprint("user", __name__)

@user_bp.route("/")
def home():
    return jsonify(message="User Service Running!"), 200
