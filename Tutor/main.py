"""Main file"""
from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Handles main function"""
    return render_template('index.html')
