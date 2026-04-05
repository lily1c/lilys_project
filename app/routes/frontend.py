from flask import Blueprint, send_from_directory
import os

frontend_bp = Blueprint('frontend', __name__)

@frontend_bp.route('/dashboard')
def dashboard():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), '..', 'static'),
        'dashboard.html'
    )
