import os

class Config:
    """Base configuration."""
    # Flask config
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'whisper-subtitler-secret-key')
    
    # Database config
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload config
    MAX_CONTENT_LENGTH = 512 * 1024 * 1024  # 512 MB
    ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'avi', 'mov', 'mkv', 'flac', 'ogg', 'm4a'}
    
    # Whisper models
    WHISPER_MODELS = ['tiny', 'base', 'small', 'medium', 'large']
    DEFAULT_WHISPER_MODEL = 'base'
    
    # Gofile API config
    GOFILE_API_URL = 'https://api.gofile.io'
    
    # Session config
    SESSION_TYPE = 'filesystem'
    
    # CORS config
    CORS_HEADERS = 'Content-Type'