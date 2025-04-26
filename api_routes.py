import logging
from flask import Blueprint, jsonify, request, session
from models import SubtitleTask
from services.file_sharing import get_file_sharing_service
from app import db

# Initialize file sharing service
file_sharing = get_file_sharing_service('gofile')

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__)

# Helper functions
def ensure_session_id():
    """Ensure the session has a unique ID."""
    if 'session_id' not in session:
        import uuid
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

# API Routes
@api_bp.route('/server', methods=['GET'])
def get_server():
    """Get the best file sharing server for uploads."""
    try:
        # For Gofile, this gets the best server dynamically
        server = file_sharing._get_server() if hasattr(file_sharing, '_get_server') else "current"
        return jsonify({'status': 'success', 'server': server})
    except Exception as e:
        logger.error(f"Error getting file sharing server: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/direct-link', methods=['GET'])
def get_direct_link():
    """Get a direct download link for a file ID."""
    try:
        file_id = request.args.get('id')
        if not file_id:
            return jsonify({'status': 'error', 'message': 'No file ID provided'}), 400
        
        direct_url = file_sharing.get_direct_download_url(file_id)
        if not direct_url:
            return jsonify({'status': 'error', 'message': 'Could not get direct download URL'}), 404
        
        return jsonify({
            'status': 'success',
            'url': direct_url
        })
    
    except Exception as e:
        logger.error(f"Error getting direct link: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/tasks', methods=['POST'])
def create_task():
    """Create a new subtitle generation task."""
    # This route is a placeholder for future Celery task creation
    return jsonify({'status': 'error', 'message': 'Not implemented yet'}), 501

@api_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get the status of a specific task."""
    try:
        task = SubtitleTask.query.filter_by(task_id=task_id).first()
        
        if not task:
            return jsonify({'status': 'error', 'message': 'Task not found'}), 404
        
        return jsonify({
            'status': 'success',
            'task': task.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error getting task: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/tasks', methods=['GET'])
def get_my_tasks():
    """Get all tasks for the current session."""
    try:
        session_id = ensure_session_id()
        
        tasks = SubtitleTask.query.filter_by(session_id=session_id).order_by(
            SubtitleTask.created_at.desc()
        ).all()
        
        return jsonify({
            'status': 'success',
            'tasks': [task.to_dict() for task in tasks]
        })
    
    except Exception as e:
        logger.error(f"Error getting tasks: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500