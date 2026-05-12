import os
import shutil
import logging
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)

def save_user_resume(user_id, file):
    """
    Saves the uploaded resume persistently in /uploads/resumes/<user_id>/.
    Returns the final absolute path of the saved file.
    """
    try:
        # 1. Create base directory if not exists
        base_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
        resume_dir = os.path.join(base_dir, "resumes", str(user_id))
        os.makedirs(resume_dir, exist_ok=True)

        # 2. Secure filename and define path
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        # Add timestamp to avoid collisions if they upload same file twice
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        final_filename = f"{timestamp}_{filename}"
        dest_path = os.path.join(resume_dir, final_filename)

        # 3. Save the file
        file.save(dest_path)
        logger.info(f"Persistent storage: Saved resume for user {user_id} at {dest_path}")
        
        return dest_path
    except Exception as e:
        logger.error(f"Failed to save resume persistently: {e}")
        return None

def get_user_resume(user_id):
    """
    Returns the path to the most recent resume for the user.
    """
    try:
        base_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
        resume_dir = os.path.join(base_dir, "resumes", str(user_id))
        
        if not os.path.exists(resume_dir):
            return None
            
        # List files and sort by name (which starts with timestamp)
        files = [f for f in os.listdir(resume_dir) if os.path.isfile(os.path.join(resume_dir, f))]
        if not files:
            return None
            
        # Get the latest one
        files.sort(reverse=True)
        latest_file = files[0]
        return os.path.abspath(os.path.join(resume_dir, latest_file))
    except Exception as e:
        logger.error(f"Error retrieving resume for user {user_id}: {e}")
        return None

def delete_user_files(user_id):
    """
    Deletes all files belonging to a user (resumes and general uploads).
    """
    try:
        base_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
        resume_dir = os.path.join(base_dir, "resumes", str(user_id))
        
        if os.path.exists(resume_dir):
            shutil.rmtree(resume_dir)
            logger.info(f"Deleted resume directory for user {user_id}")

        # Also cleanup any legacy files in the main uploads folder starting with user_id
        for f in os.listdir(base_dir):
            if f.startswith(f"{user_id}_"):
                try:
                    os.remove(os.path.join(base_dir, f))
                except OSError:
                    pass
    except Exception as e:
        logger.error(f"Error deleting files for user {user_id}: {e}")
