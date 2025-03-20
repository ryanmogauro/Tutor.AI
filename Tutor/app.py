"""App entry point"""
import os
from flask import Flask, render_template
from study_guide import study_guide_bp
from main import main_bp

app = Flask(__name__)

app.register_blueprint(main_bp)
app.register_blueprint(study_guide_bp)

@app.route('/')
def index():
    """App entry point"""
    return render_template('index.html')



if __name__ == '__main__':
    # Create the guides directory if it doesn't exist
    os.makedirs("static/guides", exist_ok=True)
    app.run(debug=True)
