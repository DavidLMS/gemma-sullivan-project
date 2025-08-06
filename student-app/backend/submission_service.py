"""
Challenge Submission Storage Service
Handles persistent storage of all challenge submissions with unique IDs
"""

import json
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Base directory for submissions
SUBMISSIONS_DIR = Path("content/experiment_submissions")
SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)

def is_uuid_format(challenge_id: str) -> bool:
    """Check if challenge_id is in UUID format"""
    import re
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, challenge_id, re.IGNORECASE))

class SubmissionService:
    """Service for managing challenge submission storage"""
    
    
    @staticmethod
    def get_next_submission_number(unique_challenge_id: str) -> int:
        """
        Get the next submission number for a challenge
        
        Args:
            unique_challenge_id: Unique challenge ID (e.g., "experiment_1_file0")
            
        Returns:
            Next submission number (1, 2, 3, ...)
        """
        challenge_dir = SUBMISSIONS_DIR / unique_challenge_id
        
        if not challenge_dir.exists():
            logger.info(f"First submission for challenge {unique_challenge_id}")
            return 1
        
        # Find existing submission folders (01, 02, 03, ...)
        existing_submissions = [
            int(d.name) for d in challenge_dir.iterdir() 
            if d.is_dir() and d.name.isdigit()
        ]
        
        if not existing_submissions:
            return 1
        
        next_number = max(existing_submissions) + 1
        logger.info(f"Next submission number for {unique_challenge_id}: {next_number}")
        return next_number
    
    @staticmethod
    def copy_files_to_submission(
        unique_challenge_id: str, 
        submission_number: int, 
        submission_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Copy files from temporary uploads to submission folder
        
        Args:
            unique_challenge_id: Unique challenge ID
            submission_number: Submission number
            submission_data: Submission data with canvasData and file references
            
        Returns:
            Dictionary with file paths relative to submission folder
        """
        # Create submission files directory
        submission_dir = SUBMISSIONS_DIR / unique_challenge_id / f"{submission_number:02d}"
        files_dir = submission_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        
        file_info = {
            "canvas": None,
            "uploads": []
        }
        
        try:
            # Copy canvas drawing if present
            if submission_data.get('canvasData'):
                canvas_path = files_dir / "canvas.png"
                
                # Convert base64 canvas to PNG file
                import base64
                canvas_data = submission_data['canvasData']
                if canvas_data.startswith('data:image/png;base64,'):
                    canvas_data = canvas_data.split(',', 1)[1]
                
                with open(canvas_path, 'wb') as f:
                    f.write(base64.b64decode(canvas_data))
                
                file_info["canvas"] = "files/canvas.png"
                logger.info(f"Saved canvas drawing to {canvas_path}")
            
            # Copy uploaded files if they exist
            # For UUID system, the challenge_id from submission_data is the directory name
            # For legacy system, we need to extract the original challenge_id
            
            challenge_id_for_uploads = submission_data.get('challengeId', unique_challenge_id)
            # Looking for uploads using challenge_id
            
            # Try the challengeId directly first (should work for both UUID and legacy)
            uploads_dir = Path("content/experiment_uploads") / challenge_id_for_uploads
            # Primary upload directory checked
            
            # If not found, the upload directory doesn't exist
            if not uploads_dir.exists():
                # Upload directory not found
            
            # Final upload directory to check
            
            if uploads_dir.exists():
                logger.info(f"✅ Uploads directory found: {uploads_dir}")
                upload_count = 0
                all_files = list(uploads_dir.iterdir())
                # Found files in uploads directory
                
                for file_path in all_files:
                    # Checking file
                    if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                        # Copy with sequential naming
                        upload_count += 1
                        dest_filename = f"upload_{upload_count}{file_path.suffix}"
                        dest_path = files_dir / dest_filename
                        
                        shutil.copy2(file_path, dest_path)
                        file_info["uploads"].append(f"files/{dest_filename}")
                        
                        logger.info(f"✅ Copied upload {file_path.name} to {dest_path}")
                    else:
                        logger.info(f"❌ Skipped file {file_path.name} (not an image or not a file)")
                
                logger.info(f"🎯 RESULT: Copied {upload_count} uploaded files to submission")
            else:
                logger.warning(f"❌ Uploads directory does not exist: {uploads_dir}")
                # Available upload directories:
                base_uploads_dir = Path("content/experiment_uploads")
                if base_uploads_dir.exists():
                    for subdir in base_uploads_dir.iterdir():
                        if subdir.is_dir():
                            logger.info(f"  - {subdir.name}")
                else:
                    logger.warning(f"Base uploads directory does not exist: {base_uploads_dir}")
            
        except Exception as e:
            logger.error(f"Error copying files for submission: {e}")
            # Continue with submission even if file copying fails
        
        return file_info
    
    @staticmethod
    def save_submission(
        submission_data: Dict[str, Any],
        challenge_data: Dict[str, Any],
        feedback_data: Dict[str, Any],
        source_file: str
    ) -> str:
        """
        Save a complete submission with metadata and files
        
        Args:
            submission_data: Data from ChallengeSubmission
            challenge_data: Complete challenge information
            feedback_data: AI feedback result
            source_file: Source file name (e.g., "challenges_0.json")
            
        Returns:
            Submission ID (UUID)
        """
        try:
            # Get challenge ID from submission data
            challenge_id = submission_data['challengeId']
            logger.info(f"💾 SAVE: Processing submission for challenge: {challenge_id}")
            
            # UUID system only - use challenge UUID directly as directory name
            if not is_uuid_format(challenge_id):
                logger.error(f"💾 SAVE: Invalid challenge ID format. Only UUIDs are supported: {challenge_id}")
                raise ValueError(f"Invalid challenge ID format. Only UUIDs are supported: {challenge_id}")
            
            storage_challenge_id = challenge_id
            logger.info(f"💾 SAVE: Using UUID system, storage_id: {storage_challenge_id}")
            
            # Get next submission number
            submission_number = SubmissionService.get_next_submission_number(storage_challenge_id)
            
            # Create submission directory
            submission_dir = SUBMISSIONS_DIR / storage_challenge_id / f"{submission_number:02d}"
            submission_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"💾 SAVE: Created submission directory: {submission_dir}")
            
            # Copy files to submission folder
            file_info = SubmissionService.copy_files_to_submission(
                storage_challenge_id, submission_number, submission_data
            )
            
            # Generate submission ID
            submission_id = str(uuid.uuid4())
            
            # Get student profile from environment
            from api_server import get_student_profile_from_env
            student_profile = get_student_profile_from_env()
            
            # Build submission metadata
            submission_metadata = {
                "submission_id": submission_id,
                "challenge_id": challenge_id,
                "challenge_title": challenge_data.get('title', 'Unknown Challenge'),
                "challenge_description": challenge_data.get('description', 'No description'),
                "submission_number": submission_number,
                "is_final": feedback_data.get('ready_to_submit', False),
                "submitted_at": datetime.now().isoformat(),
                "student_profile": {
                    "name": student_profile['student_name'],
                    "age": student_profile['student_age'],
                    "language": student_profile['language']
                },
                "content": {
                    "text": submission_data.get('textContent', ''),
                    "has_canvas": bool(submission_data.get('canvasData')),
                    "uploaded_files_count": len(file_info["uploads"])
                },
                "files": file_info,
                "ai_feedback": {
                    "delivered": feedback_data.get('delivered', ''),
                    "areas_for_improvement": feedback_data.get('areas_for_improvement', ''),
                    "suggestions": feedback_data.get('suggestions', ''),
                    "overall_assessment": feedback_data.get('overall_assessment', ''),
                    "ready_to_submit": feedback_data.get('ready_to_submit', False),
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            # Save submission JSON
            submission_file = submission_dir / "submission.json"
            with open(submission_file, 'w', encoding='utf-8') as f:
                json.dump(submission_metadata, f, indent=2, ensure_ascii=False)
            
            # Update latest submission pointer
            latest_file = SUBMISSIONS_DIR / storage_challenge_id / "latest_submission.json"
            latest_info = {
                "latest_submission_number": submission_number,
                "submission_id": submission_id,
                "challenge_id": challenge_id,
                "is_final": feedback_data.get('ready_to_submit', False),
                "updated_at": datetime.now().isoformat()
            }
            
            with open(latest_file, 'w', encoding='utf-8') as f:
                json.dump(latest_info, f, indent=2, ensure_ascii=False)
            
            logger.info(
                f"✅ Saved submission {submission_number:02d} for {storage_challenge_id} "
                f"(final: {feedback_data.get('ready_to_submit', False)})"
            )
            
            return submission_id
            
        except Exception as e:
            logger.error(f"Error saving submission: {e}")
            raise


# Global service instance
submission_service = SubmissionService()

def save_challenge_submission(
    submission_data: Dict[str, Any],
    challenge_data: Dict[str, Any], 
    feedback_data: Dict[str, Any],
    source_file: str
) -> str:
    """
    Convenience function to save a challenge submission
    
    Args:
        submission_data: Submission form data
        challenge_data: Challenge definition
        feedback_data: AI feedback result
        source_file: Source file name
        
    Returns:
        Submission ID
    """
    return submission_service.save_submission(
        submission_data, challenge_data, feedback_data, source_file
    )