"""
xAPI (Experience API) Logger for Student Activity Tracking
Logs all student interactions in xAPI format to logs/student.log
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)
STUDENT_LOG_FILE = LOGS_DIR / "student.log"

class XAPILogger:
    """xAPI compliant logger for student learning activities"""
    
    def __init__(self):
        pass
    
    def _get_current_actor(self) -> Dict[str, Any]:
        """Get current actor based on current student profile"""
        from student_profile import get_current_student_profile
        
        profile = get_current_student_profile()
        
        if profile is None:
            # No profile available - use default values
            return {
                "name": "anonymous_student",
                "account": {
                    "name": "Anonymous Student"
                }
            }
        
        # Use actual profile data
        student_id = profile.get('student_id', 'unknown_id')
        student_name = profile.get('student_name', 'Unknown Student')
        
        return {
            "name": student_id,
            "account": {
                "name": student_name
            }
        }
    
    def _create_statement(self, verb_id: str, verb_display: str, object_id: str, 
                         object_name: str, object_description: str, 
                         result: Optional[Dict[str, Any]] = None,
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a basic xAPI statement structure"""
        statement = {
            "actor": self._get_current_actor(),
            "verb": {
                "id": verb_id,
                "display": {"en": verb_display}
            },
            "object": {
                "id": object_id,
                "definition": {
                    "name": {"en": object_name},
                    "description": {"en": object_description}
                }
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if result:
            statement["result"] = result
        if context:
            statement["context"] = context
            
        return statement
    
    def _log_statement(self, statement: Dict[str, Any]):
        """Write statement to student.log file"""
        try:
            with open(STUDENT_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(statement, ensure_ascii=False) + '\n')
            logger.info(f"xAPI statement logged: {statement['verb']['display']['en']} - {statement['object']['definition']['name']['en']}")
        except Exception as e:
            logger.error(f"Error logging xAPI statement: {e}")
    
    def log_content_navigation(self, content_name: str, content_type: str, section: str):
        """Log when student navigates to specific content section"""
        statement = self._create_statement(
            verb_id="http://adlnet.gov/expapi/verbs/experienced",
            verb_display="experienced",
            object_id=f"http://gemma-app.local/content/{content_name}",
            object_name=f"{content_name.replace('_', ' ').title()} Content",
            object_description=f"Educational content: {content_name}",
            context={
                "category": "learn",
                "type": content_type,  # "textbook" or "story"
                "section": section     # "3"
            }
        )
        self._log_statement(statement)
    
    def log_question_answered(self, question_id: str, question_text: str, 
                             student_answer: str, is_correct: bool, 
                             feedback: str, score_raw: int = None, score_max: int = None):
        """Log when student answers a practice question"""
        result = {
            "response": student_answer,
            "success": is_correct
        }
        
        if score_raw is not None and score_max is not None:
            result["score"] = {
                "raw": score_raw,
                "max": score_max
            }
        
        statement = self._create_statement(
            verb_id="http://adlnet.gov/expapi/verbs/answered",
            verb_display="answered",
            object_id=f"http://gemma-app.local/questions/{question_id}",
            object_name="Practice Question",
            object_description="Educational practice question",
            result=result,
            context={
                "extensions": {
                    "http://gemma-app.local/xapi/question_text": question_text,
                    "http://gemma-app.local/xapi/student_answer": student_answer,
                    "http://gemma-app.local/xapi/feedback": feedback
                }
            }
        )
        self._log_statement(statement)
    
    def log_challenge_submitted(self, challenge_id: str, challenge_title: str,
                               submission_id: str, submission_content: str,
                               ai_feedback: str, is_final_submission: bool,
                               submission_type: str = "text"):
        """Log when student submits a challenge"""
        statement = self._create_statement(
            verb_id="http://adlnet.gov/expapi/verbs/submitted",
            verb_display="submitted",
            object_id=f"http://gemma-app.local/challenges/{challenge_id}",
            object_name=challenge_title,
            object_description="Experimental challenge submission",
            result={
                "completion": True,
                "response": submission_content[:500] + "..." if len(submission_content) > 500 else submission_content,
                "extensions": {
                    "http://gemma-app.local/xapi/final_submission": is_final_submission
                }
            },
            context={
                "extensions": {
                    "http://gemma-app.local/xapi/submission_id": submission_id,
                    "http://gemma-app.local/xapi/ai_feedback": ai_feedback,
                    "http://gemma-app.local/xapi/submission_type": submission_type
                }
            }
        )
        self._log_statement(statement)
    
    def log_discovery_exploration(self, investigation_id: str, subject_identified: str,
                                 initial_question: str, selected_questions: list,
                                 final_choice: str, questions_explored: int):
        """Log when student completes a discovery investigation"""
        statement = self._create_statement(
            verb_id="http://adlnet.gov/expapi/verbs/explored",
            verb_display="explored",
            object_id=f"http://gemma-app.local/discovery/{investigation_id}",
            object_name=f"Discovery Investigation: {subject_identified}",
            object_description=f"Student investigation about {subject_identified}",
            result={
                "completion": True,
                "response": final_choice,
                "extensions": {
                    "http://gemma-app.local/xapi/questions_explored": questions_explored
                }
            },
            context={
                "extensions": {
                    "http://gemma-app.local/xapi/initial_question": initial_question,
                    "http://gemma-app.local/xapi/selected_questions": selected_questions,
                    "http://gemma-app.local/xapi/image_uploaded": True,
                    "http://gemma-app.local/xapi/final_choice": final_choice
                }
            }
        )
        self._log_statement(statement)

# Global instance
xapi_logger = XAPILogger()