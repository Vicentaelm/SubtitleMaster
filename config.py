import os

class Config:
    """Base configuration."""
    # Flask config
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'whisper-subtitler-secret-key')
    
    # Database config
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload config for legacy compatibility
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1 GB (maximum possible for paid users)
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
    
    # User Plans Configuration
    # Free plan limits
    FREE_MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB
    FREE_MAX_CONCURRENT_TASKS = 1
    FREE_MAX_TASKS_PER_DAY = 5
    
    # Paid plan limits
    PAID_MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1 GB
    PAID_MAX_CONCURRENT_TASKS = 1
    PAID_MAX_TASKS_PER_DAY = float('inf')  # Unlimited
    
    # Path to paid users CSV file
    PAID_USERS_CSV = os.path.join(os.path.dirname(__file__), 'paid_users.csv')
    
    # PayPal settings
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', 'your-paypal-client-id')
    PAYPAL_SUBSCRIPTION_PRICE = '9.99'  # Monthly subscription price in USD
    PAYPAL_SUBSCRIPTION_DESCRIPTION = 'Whisper Subtitler Pro - Monthly Subscription'
    PAYPAL_CURRENCY = 'USD'
    PAYPAL_RETURN_URL = '/subscription/success'  # Redirect URL after successful payment