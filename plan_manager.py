import os
import csv
import logging
from datetime import datetime
from config import Config
from models import SubtitleTask
from app import db

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PlanManager:
    """Handles user plan detection and enforcement of limitations."""
    
    @staticmethod
    def is_paid_user(email=None, session_id=None):
        """
        Check if a user is on the paid plan.
        
        Args:
            email: User's email (if user account-based)
            session_id: User's session ID (if session-based)
            
        Returns:
            bool: True if the user is a paid user, False otherwise
        """
        if email:
            # If email is provided, check against paid users CSV
            try:
                with open(Config.PAID_USERS_CSV, 'r') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        if row['email'].lower() == email.lower():
                            # Check if subscription is still valid
                            if 'subscription_end_date' in row:
                                end_date = datetime.strptime(row['subscription_end_date'], '%Y-%m-%d')
                                if end_date > datetime.now():
                                    return True
                            else:
                                # No end date means permanent subscription
                                return True
            except Exception as e:
                logger.error(f"Error checking paid user status: {e}")
                # Default to free user if there's an error
                return False
                
        # If session-based, check additional sources here
        # This is a placeholder for future implementation
        
        return False
    
    @staticmethod
    def get_user_plan_limits(email=None, session_id=None):
        """
        Get the limits for the user's plan.
        
        Args:
            email: User's email (if user account-based)
            session_id: User's session ID (if session-based)
            
        Returns:
            dict: Dictionary containing the limits for the user's plan
        """
        is_paid = PlanManager.is_paid_user(email, session_id)
        
        if is_paid:
            return {
                'max_file_size': Config.PAID_MAX_FILE_SIZE,
                'max_concurrent_tasks': Config.PAID_MAX_CONCURRENT_TASKS,
                'max_tasks_per_day': Config.PAID_MAX_TASKS_PER_DAY,
                'plan_name': 'Pro'
            }
        else:
            return {
                'max_file_size': Config.FREE_MAX_FILE_SIZE,
                'max_concurrent_tasks': Config.FREE_MAX_CONCURRENT_TASKS,
                'max_tasks_per_day': Config.FREE_MAX_TASKS_PER_DAY,
                'plan_name': 'Free'
            }
    
    @staticmethod
    def check_file_size_limit(file_size, email=None, session_id=None):
        """
        Check if the file size is within the user's plan limits.
        
        Args:
            file_size: Size of the file in bytes
            email: User's email (if user account-based)
            session_id: User's session ID (if session-based)
            
        Returns:
            tuple: (is_allowed, max_size, plan_name)
        """
        limits = PlanManager.get_user_plan_limits(email, session_id)
        max_size = limits['max_file_size']
        plan_name = limits['plan_name']
        
        return file_size <= max_size, max_size, plan_name
    
    @staticmethod
    def check_concurrent_tasks(session_id):
        """
        Check if the user has reached their concurrent task limit.
        
        Args:
            session_id: User's session ID
            
        Returns:
            tuple: (is_allowed, active_tasks, max_tasks)
        """
        # Get user's plan limits
        limits = PlanManager.get_user_plan_limits(session_id=session_id)
        max_tasks = limits['max_concurrent_tasks']
        
        # Count active tasks for this session
        active_tasks = SubtitleTask.query.filter_by(
            session_id=session_id,
            status='pending'
        ).count()
        
        return active_tasks < max_tasks, active_tasks, max_tasks
    
    @staticmethod
    def check_daily_task_limit(session_id):
        """
        Check if the user has reached their daily task limit.
        
        Args:
            session_id: User's session ID
            
        Returns:
            tuple: (is_allowed, daily_tasks, max_tasks)
        """
        # Get user's plan limits
        limits = PlanManager.get_user_plan_limits(session_id=session_id)
        max_tasks = limits['max_tasks_per_day']
        
        # Get today's date range
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Count tasks created today for this session
        daily_tasks = SubtitleTask.query.filter(
            SubtitleTask.session_id == session_id,
            SubtitleTask.created_at >= today_start,
            SubtitleTask.created_at <= today_end
        ).count()
        
        return daily_tasks < max_tasks, daily_tasks, max_tasks