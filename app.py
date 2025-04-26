import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the Base class
db = SQLAlchemy(model_class=Base)

def create_app():
    """Application factory pattern to create the Flask app instance."""
    # Create the Flask app
    app = Flask(__name__)
    
    # Set up the secret key for sessions
    app.secret_key = os.environ.get("SESSION_SECRET", "whisper-subtitler-secret-key")
    
    # Configure the proxy fix for proper URL generation behind proxies
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Configure the database connection
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Configure file upload settings
    app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024  # 512 MB
    app.config["ALLOWED_EXTENSIONS"] = {
        'mp3', 'mp4', 'wav', 'avi', 'mov', 'mkv', 'flac', 'ogg', 'm4a'
    }
    
    # Configure Whisper models
    app.config["WHISPER_MODELS"] = ['tiny', 'base', 'small', 'medium', 'large']
    app.config["DEFAULT_WHISPER_MODEL"] = 'base'
    
    # Configure Gofile settings
    app.config["GOFILE_API_URL"] = 'https://api.gofile.io'
    
    # Initialize the database with the app
    db.init_app(app)
    
    # Register blueprints
    with app.app_context():
        from routes import main_bp
        from api_routes import api_bp
        
        app.register_blueprint(main_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
        
        # Create all database tables
        from models import SubtitleTask
        db.create_all()
    
    return app