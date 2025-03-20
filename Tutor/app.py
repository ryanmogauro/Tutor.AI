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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)