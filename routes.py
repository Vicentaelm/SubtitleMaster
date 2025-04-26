import os
import logging
import uuid
import tempfile
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    session, flash, abort, send_file, jsonify
)
from werkzeug.utils import secure_filename

from app import db
from models import SubtitleTask
from services.file_sharing import get_file_sharing_service
from whisper_subtitler import process_file, is_ffmpeg_available
from config import Config
from plan_manager import PlanManager

# Initialize file sharing service
file_sharing = get_file_sharing_service('gofile')

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create blueprint
main_bp = Blueprint('main', __name__)

# Helper functions
def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def generate_task_id():
    """Generate a unique task ID."""
    return str(uuid.uuid4())

def ensure_session_id():
    """Ensure the session has a unique ID."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

# Routes
@main_bp.route('/')
def index():
    """Render the index page with file upload form."""
    # Ensure session ID
    session_id = ensure_session_id()
    
    # Get available models and formats
    models = Config.WHISPER_MODELS
    formats = ['srt', 'vtt', 'txt']
    
    # Check if ffmpeg is available
    ffmpeg_available = is_ffmpeg_available()
    
    # Get available languages
    languages = [
        {'code': 'auto', 'name': 'Auto-detect'},
        {'code': 'en', 'name': 'English'},
        {'code': 'es', 'name': 'Spanish'},
        {'code': 'fr', 'name': 'French'},
        {'code': 'de', 'name': 'German'},
        {'code': 'it', 'name': 'Italian'},
        {'code': 'pt', 'name': 'Portuguese'},
        {'code': 'nl', 'name': 'Dutch'},
        {'code': 'ru', 'name': 'Russian'},
        {'code': 'zh', 'name': 'Chinese'},
        {'code': 'ja', 'name': 'Japanese'},
        {'code': 'ko', 'name': 'Korean'},
        {'code': 'ar', 'name': 'Arabic'},
        {'code': 'hi', 'name': 'Hindi'},
        {'code': 'same', 'name': 'Same as input'}
    ]
    
    # Get user email from form (if provided)
    user_email = request.args.get('email', None)
    
    # Get user's plan information
    limits = PlanManager.get_user_plan_limits(email=user_email, session_id=session_id)
    
    return render_template(
        'index.html', 
        models=models, 
        default_model=Config.DEFAULT_WHISPER_MODEL,
        formats=formats,
        languages=languages,
        ffmpeg_available=ffmpeg_available,
        plan_name=limits['plan_name'],
        max_file_size=limits['max_file_size'] / (1024 * 1024),  # Convert to MB
        max_tasks_per_day=limits['max_tasks_per_day'] if limits['max_tasks_per_day'] != float('inf') else 'Unlimited'
    )
    
@main_bp.route('/subscription')
def subscription():
    """Show the subscription page."""
    # Ensure session ID
    session_id = ensure_session_id()
    
    # Get user email from form (if provided)
    user_email = request.args.get('email', None)
    
    # Get user's plan information
    limits = PlanManager.get_user_plan_limits(email=user_email, session_id=session_id)
    is_paid = limits['plan_name'] == 'Pro'
    
    return render_template(
        'subscription.html',
        plan_name=limits['plan_name'],
        is_paid=is_paid,
        paypal_client_id=Config.PAYPAL_CLIENT_ID,
        subscription_price=Config.PAYPAL_SUBSCRIPTION_PRICE,
        currency=Config.PAYPAL_CURRENCY,
        free_max_file_size=Config.FREE_MAX_FILE_SIZE / (1024 * 1024),  # Convert to MB
        paid_max_file_size=Config.PAID_MAX_FILE_SIZE / (1024 * 1024),  # Convert to MB
        free_max_tasks_per_day=Config.FREE_MAX_TASKS_PER_DAY,
        paid_max_tasks_per_day='Unlimited'
    )

@main_bp.route('/subscription/success')
def subscription_success():
    """Handle successful subscription."""
    # Get query parameters
    subscription_id = request.args.get('subscription_id', None)
    payer_id = request.args.get('payer_id', None)
    payer_email = request.args.get('payer_email', None)
    
    # You would normally validate the payment with PayPal here
    # For now, we'll just show a success message
    
    # Store the email in session for future use
    if payer_email:
        session['user_email'] = payer_email
    
    # Flash a success message
    flash('Thank you for subscribing to the Pro plan! You now have access to all premium features.', 'success')
    
    # Redirect to the home page
    return redirect(url_for('main.index'))

@main_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and redirect to processing."""
    # Ensure session ID
    session_id = ensure_session_id()
    
    # Get user email from form (if provided)
    user_email = request.form.get('user_email', None)
    
    # Check concurrent tasks limit before processing any further
    can_create_task, active_tasks, max_concurrent = PlanManager.check_concurrent_tasks(session_id)
    if not can_create_task:
        flash(f'You already have {active_tasks} active task(s). Your plan allows a maximum of {max_concurrent} concurrent task(s). Please wait for your current task to complete.', 'error')
        return redirect(url_for('main.index'))
    
    # Check daily task limit
    can_create_daily, daily_tasks, max_daily = PlanManager.check_daily_task_limit(session_id)
    if not can_create_daily:
        flash(f'You have reached your daily limit of {max_daily} tasks. Please try again tomorrow or upgrade to a paid plan for unlimited tasks.', 'error')
        return redirect(url_for('main.index'))
    
    # Check if the post request has the file part
    if 'file' not in request.files:
        flash('No file part in the request', 'error')
        return redirect(url_for('main.index'))
    
    file = request.files['file']
    
    # If user does not select file, browser also submits an empty part without filename
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('main.index'))
    
    # Get file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset file pointer to beginning
    
    # Check file size against plan limits
    is_size_allowed, max_size, plan_name = PlanManager.check_file_size_limit(
        file_size, 
        email=user_email, 
        session_id=session_id
    )
    
    if not is_size_allowed:
        # Convert max_size to MB for display
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = file_size / (1024 * 1024)
        
        flash(f'File size ({file_size_mb:.1f} MB) exceeds your {plan_name} plan limit of {max_size_mb:.1f} MB. Please upgrade to a paid plan for larger files.', 'error')
        return redirect(url_for('main.index'))
    
    # Get processing options from form
    language = request.form.get('language', 'auto')
    output_language = request.form.get('output_language', 'same')
    model = request.form.get('model', Config.DEFAULT_WHISPER_MODEL)
    format_type = request.form.get('format', 'srt')
    
    # Check if the file extension is allowed
    if not allowed_file(file.filename):
        flash(f'File type not allowed. Supported types: {", ".join(Config.ALLOWED_EXTENSIONS)}', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Save the file to a temporary location
        filename = secure_filename(file.filename)
        temp_file = tempfile.mktemp(suffix=os.path.splitext(filename)[1])
        file.save(temp_file)
        
        # Upload the file to file sharing service
        logger.info(f"Uploading {filename} to file sharing service")
        file_info = file_sharing.upload_file(temp_file, filename)
        
        # Generate task ID
        task_id = generate_task_id()
        
        # Create task record in the database
        task = SubtitleTask(
            task_id=task_id,
            session_id=session_id,
            status='pending',
            original_filename=filename,
            input_gofile_id=file_info['fileId'],
            input_gofile_link=file_info['downloadPage'],
            language=language,
            output_language=output_language,
            model=model,
            format_type=format_type
        )
        
        db.session.add(task)
        db.session.commit()
        
        # Store the task ID in the session
        session['current_task_id'] = task_id
        
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        # Redirect to processing page
        return redirect(url_for('main.processing_redirect'))
    
    except Exception as e:
        logger.error(f"Error in file upload: {str(e)}")
        flash(f'Error processing file: {str(e)}', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/processing-redirect')
def processing_redirect():
    """Renders a page that will use JavaScript to properly process the file upload."""
    task_id = session.get('current_task_id')
    if not task_id:
        flash('No active task found', 'error')
        return redirect(url_for('main.index'))
    
    # Get task information
    task = SubtitleTask.query.filter_by(task_id=task_id).first_or_404()
    
    # Here we could trigger the Celery task, but for simplicity,
    # we'll process directly (this is not ideal for production use)
    try:
        # Process the file
        process_subtitles(task)
        
        # Redirect to the task status page
        return redirect(url_for('main.task_status', task_id=task_id))
    
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        task.status = 'failed'
        task.message = str(e)
        db.session.commit()
        flash(f'Error processing file: {str(e)}', 'error')
        return redirect(url_for('main.index'))

def process_subtitles(task):
    """Process the subtitles for a task."""
    # Update task status
    task.status = 'processing'
    task.progress = 'Downloading input file...'
    db.session.commit()
    
    try:
        # Create a temporary directory for processing
        temp_dir = tempfile.mkdtemp()
        input_file = os.path.join(temp_dir, task.original_filename)
        
        # Download the file from file sharing service
        import requests
        
        # Get direct download URL from file sharing service
        direct_url = file_sharing.get_direct_download_url(task.input_gofile_id)
        
        # Update progress
        task.progress = 'Downloading media file...'
        db.session.commit()
        
        # Download the file
        with requests.get(direct_url, stream=True) as r:
            r.raise_for_status()
            with open(input_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        # Update progress
        task.progress = 'Transcribing audio...'
        db.session.commit()
        
        # Process the file with Whisper
        subtitle_path = process_file(
            input_file,
            language=task.language,
            model=task.model,
            format_type=task.format_type,
            output_language=task.output_language
        )
        
        # Update progress
        task.progress = 'Uploading subtitles...'
        db.session.commit()
        
        # Generate a proper subtitle filename
        filename_base = os.path.splitext(task.original_filename)[0]
        subtitle_filename = f"{filename_base}.{task.format_type}"
        
        # Upload subtitle file to file sharing service
        subtitle_info = file_sharing.upload_file(subtitle_path, subtitle_filename)
        
        # Update task with the results
        task.status = 'completed'
        task.subtitle_gofile_id = subtitle_info['fileId']
        task.subtitle_gofile_link = subtitle_info['downloadPage']
        task.subtitle_filename = subtitle_filename
        task.completed_at = datetime.utcnow()
        task.progress = 'Done'
        db.session.commit()
        
        # Clean up
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
        
    except Exception as e:
        logger.error(f"Error processing subtitles: {str(e)}")
        task.status = 'failed'
        task.message = str(e)
        db.session.commit()
        raise

@main_bp.route('/task/<task_id>')
def task_status(task_id):
    """Show the status of a specific task."""
    # Get the task
    task = SubtitleTask.query.filter_by(task_id=task_id).first_or_404()
    
    # Return the task status page
    return render_template('task_status.html', task=task)

@main_bp.route('/tasks')
def tasks_list():
    """Show a list of tasks for the current session."""
    # Ensure session ID
    session_id = ensure_session_id()
    
    # Get tasks for this session
    tasks = SubtitleTask.query.filter_by(session_id=session_id).order_by(SubtitleTask.created_at.desc()).all()
    
    # Render the tasks list template
    return render_template('tasks_list.html', tasks=tasks)

@main_bp.route('/result')
def result():
    """Show the result of the most recent completed task."""
    task_id = request.args.get('task_id') or session.get('current_task_id')
    
    if not task_id:
        flash('No task specified', 'error')
        return redirect(url_for('main.index'))
    
    # Get the task
    task = SubtitleTask.query.filter_by(task_id=task_id).first_or_404()
    
    # Redirect to task status if not completed
    if task.status != 'completed':
        return redirect(url_for('main.task_status', task_id=task_id))
    
    # Store the current task ID in the session
    session['current_task_id'] = task_id
    
    # Render the result template
    return render_template('result.html', task=task)