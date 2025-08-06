"""
Discovery Mode Service for Socratic Learning with Multimodal AI
Handles camera capture + audio questions + guided discovery using Gemma 3n
"""

import asyncio
import base64
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from model_service import create_model_service
from parsers import get_parser
from xapi_logger import xapi_logger

# Configure logging
logger = logging.getLogger(__name__)

# Discovery data storage for tutor synchronization
DISCOVERY_DATA_DIR = Path("content/discovery_data")
DISCOVERY_IMAGES_DIR = DISCOVERY_DATA_DIR / "images"
DISCOVERY_DATA_DIR.mkdir(parents=True, exist_ok=True)
DISCOVERY_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Get question limit from environment
DISCOVERY_QUESTION_LIMIT = int(os.getenv('DISCOVERY_QUESTION_LIMIT', '5'))

class DiscoveryInvestigation:
    """Represents a discovery investigation for button-based learning"""
    
    def __init__(self, investigation_id: str = None):
        """Initialize a new discovery investigation.
        
        Args:
            investigation_id: Unique identifier for the investigation. Generated if None.
        """
        self.investigation_id = investigation_id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.initial_image = None
        self.initial_question = None
        self.subject_identified = None
        self.learning_intent = None
        self.internal_answers: List[str] = []
        self.selected_questions: List[str] = []  # Track question selection path
        self.question_count = 0
        self.final_answer_choice = None
        self.status = "active"  # active, completed
        
    def add_selected_question(self, question: str):
        """Add a selected question to the investigation path.
        
        Args:
            question: The question text selected by the student.
        """
        self.selected_questions.append(question)
        self.question_count += 1
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert investigation to dictionary for JSON serialization.
        
        Returns:
            Dictionary containing all investigation data.
        """
        return {
            "investigation_id": self.investigation_id,
            "created_at": self.created_at.isoformat(),
            "initial_image": self.initial_image,
            "initial_question": self.initial_question,
            "subject_identified": self.subject_identified,
            "learning_intent": self.learning_intent,
            "internal_answers": self.internal_answers,
            "selected_questions": self.selected_questions,
            "question_count": self.question_count,
            "final_answer_choice": self.final_answer_choice,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiscoveryInvestigation':
        """Create investigation from dictionary data.
        
        Args:
            data: Dictionary containing investigation data.
            
        Returns:
            DiscoveryInvestigation instance.
        """
        investigation = cls(data["investigation_id"])
        investigation.created_at = datetime.fromisoformat(data["created_at"])
        investigation.initial_image = data.get("initial_image")
        investigation.initial_question = data.get("initial_question")
        investigation.subject_identified = data.get("subject_identified")
        investigation.learning_intent = data.get("learning_intent")
        investigation.internal_answers = data.get("internal_answers", [])
        investigation.selected_questions = data.get("selected_questions", [])
        investigation.question_count = data.get("question_count", 0)
        investigation.final_answer_choice = data.get("final_answer_choice")
        investigation.status = data.get("status", "active")
        return investigation

class DiscoveryService:
    """Service for handling discovery mode interactions with button-based methodology"""
    
    def __init__(self):
        """Initialize the discovery service."""
        self.model_service = None
        self.active_investigations: Dict[str, DiscoveryInvestigation] = {}
        
    async def get_model_service(self):
        """Get model service instance with lazy loading.
        
        Returns:
            Model service instance ready for use.
        """
        if self.model_service is None:
            self.model_service = create_model_service()
            # Load model in background if not already loaded
            if not hasattr(self.model_service, '_model_loaded') or not self.model_service._model_loaded:
                def load_model():
                    return self.model_service.load_model()
                
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(None, load_model)
                if success:
                    logger.info("✓ Discovery service model loaded successfully")
                else:
                    logger.error("✗ Discovery service failed to load model")
                    raise RuntimeError("Failed to load model for discovery service")
        
        return self.model_service
    
    def preprocess_image(self, image_data: str) -> str:
        """Preprocess base64 image for optimal model performance.
        
        Args:
            image_data: Base64 encoded image data, optionally with data URL prefix.
            
        Returns:
            Clean base64 image data ready for AI processing.
        """
        try:
            # Handle data URL format (data:image/png;base64,...)
            if image_data.startswith('data:image'):
                header, base64_data = image_data.split(',', 1)
            else:
                base64_data = image_data
            
            # For now, just return the base64 data without PIL processing
            logger.info(f"Image preprocessing: {len(base64_data)} characters")
            return base64_data
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            # Return original if preprocessing fails
            return base64_data if 'base64_data' in locals() else image_data
    
    async def transcribe_audio(self, audio_data: bytes, audio_format: str = "wav") -> str:
        """Transcribe audio to text using speech recognition.
        
        Args:
            audio_data: Raw audio data in bytes.
            audio_format: Audio format (wav, mp3, etc.).
            
        Returns:
            Transcribed text or placeholder message.
        """
        try:
            # For now, return a placeholder message
            logger.info(f"Audio transcription requested (length: {len(audio_data)} bytes)")
            return "Audio transcription is not yet implemented. Please type your question."
            
        except Exception as e:
            logger.error(f"Error in audio transcription placeholder: {e}")
            return "Error processing audio. Please try again or type your question."
    
    async def start_discovery_investigation(self, image_data: str, question_text: str, 
                                          student_profile: Dict[str, str]) -> Dict[str, Any]:
        """
        Start a new discovery investigation with button-based questions
        
        Args:
            image_data: Base64 encoded image
            question_text: Student's question about the image
            student_profile: Student information for personalization
            
        Returns:
            Dict with investigation_id, internal answers (hidden), and guiding questions
        """
        try:
            logger.info(f"Starting discovery investigation for question: '{question_text[:100]}...'")
            
            # Preprocess image
            processed_image = self.preprocess_image(image_data)
            
            # Get model service
            model_service = await self.get_model_service()
            
            # Load discovery initial prompt template
            prompt_template = model_service.load_prompt('discover_initial')
            
            # Prepare variables for the prompt
            variables = {
                'student_question': question_text,
                'student_name': student_profile.get('student_name', 'Student'),
                'student_age': student_profile.get('student_age', '13'),
                'language': student_profile.get('language', 'English')
            }
            
            # Get parser for discovery initial
            parser_func = get_parser('discovery_initial')
            
            # Generate initial analysis with multimodal AI
            logger.info("Sending image + question to Gemma 3n for discovery investigation...")
            
            # Execute in thread to avoid blocking
            def generate_initial():
                return model_service.generate(
                    prompt_template=prompt_template,
                    variables=variables,
                    parser_func=parser_func,
                    max_tokens=1024,
                    max_retries=3,
                    images=[image_data]  # Send original image data like Experiment mode
                )
            
            initial_result = await asyncio.to_thread(generate_initial)
            
            if not initial_result:
                raise ValueError("Model failed to generate discovery investigation")
            
            # Create new investigation
            investigation = self.create_investigation(image_data, question_text, initial_result)
            
            logger.info(f"✓ Discovery investigation started: {investigation.investigation_id}")
            
            # Return only the data the frontend needs (no internal answers)
            return {
                'investigation_id': investigation.investigation_id,
                'subject_identified': initial_result['subject_identified'],
                'learning_intent': initial_result['learning_intent'],
                'contextual_intro': initial_result['contextual_intro'],
                'guiding_questions': initial_result['guiding_questions'],
                'question_count': investigation.question_count,
                'question_limit': DISCOVERY_QUESTION_LIMIT
            }
            
        except Exception as e:
            logger.error(f"Error in discovery analysis: {e}")
            raise
    
    async def process_question_selection(self, investigation_id: str, selected_question: str,
                                       student_profile: Dict[str, str]) -> Dict[str, Any]:
        """
        Process student's question selection to generate follow-up questions
        
        Args:
            investigation_id: Active discovery investigation ID
            selected_question: Question the student chose to explore
            student_profile: Student information
            
        Returns:
            Dict with encouragement, follow-up questions, or reveal trigger
        """
        try:
            # Get active investigation
            if investigation_id not in self.active_investigations:
                # Try to load from disk
                investigation = self.load_investigation(investigation_id)
                if not investigation:
                    raise ValueError(f"Discovery investigation {investigation_id} not found")
                self.active_investigations[investigation_id] = investigation
            else:
                investigation = self.active_investigations[investigation_id]
            
            logger.info(f"Processing question selection for investigation {investigation_id}: '{selected_question[:100]}...'")
            
            # Add selected question to investigation path
            investigation.add_selected_question(selected_question)
            
            # Check if we've reached the question limit
            if investigation.question_count >= DISCOVERY_QUESTION_LIMIT:
                logger.info(f"Question limit reached for investigation {investigation_id}, triggering reveal")
                return {'should_reveal': True, 'investigation_id': investigation_id}
            
            # Get model service
            model_service = await self.get_model_service()
            
            # Load discovery question prompt template
            prompt_template = model_service.load_prompt('discover_question')
            
            # Prepare variables for question prompt
            variables = {
                'selected_question': selected_question,
                'subject_identified': investigation.subject_identified,
                'learning_intent': investigation.learning_intent,
                'question_count': investigation.question_count,
                'question_limit': DISCOVERY_QUESTION_LIMIT,
                'internal_answers': '\n'.join(f"{i+1}. {answer}" for i, answer in enumerate(investigation.internal_answers)),
                'student_name': student_profile.get('student_name', 'Student'),
                'student_age': student_profile.get('student_age', '13'),
                'language': student_profile.get('language', 'English')
            }
            
            # Get parser for question flow
            parser_func = get_parser('discovery_question')
            
            # Generate follow-up questions with AI
            logger.info("Generating follow-up questions based on selection...")
            
            def generate_questions():
                return model_service.generate(
                    prompt_template=prompt_template,
                    variables=variables,
                    parser_func=parser_func,
                    max_tokens=512,
                    max_retries=3
                    # No images needed for follow-up questions
                )
            
            question_result = await asyncio.to_thread(generate_questions)
            
            if not question_result:
                raise ValueError("Model failed to generate follow-up questions")
            
            # Save investigation
            self.save_investigation(investigation)
            
            logger.info(f"✓ Follow-up questions generated for investigation {investigation_id}")
            
            return {
                'investigation_id': investigation_id,
                'encouragement': question_result['encouragement'],
                'guiding_questions': question_result['guiding_questions'],
                'question_count': investigation.question_count,
                'question_limit': DISCOVERY_QUESTION_LIMIT,
                'should_reveal': False
            }
            
        except Exception as e:
            logger.error(f"Error processing question selection: {e}")
            raise
    
    async def reveal_answer_options(self, investigation_id: str, 
                                  student_profile: Dict[str, str]) -> Dict[str, Any]:
        """
        Generate final answer options for accordion display
        
        Args:
            investigation_id: Active discovery investigation ID
            student_profile: Student information
            
        Returns:
            Dict with conclusion intro, answer options, and completion message
        """
        try:
            # Get active investigation
            if investigation_id not in self.active_investigations:
                investigation = self.load_investigation(investigation_id)
                if not investigation:
                    raise ValueError(f"Discovery investigation {investigation_id} not found")
                self.active_investigations[investigation_id] = investigation
            else:
                investigation = self.active_investigations[investigation_id]
            
            logger.info(f"Revealing answer options for investigation {investigation_id}")
            
            # Get model service
            model_service = await self.get_model_service()
            
            # Load discovery reveal prompt template
            prompt_template = model_service.load_prompt('discover_reveal')
            
            # Prepare variables for reveal prompt
            variables = {
                'subject_identified': investigation.subject_identified,
                'learning_intent': investigation.learning_intent,
                'selected_questions': ' | '.join(investigation.selected_questions),
                'internal_answers': '\n'.join(f"{i+1}. {answer}" for i, answer in enumerate(investigation.internal_answers)),
                'student_name': student_profile.get('student_name', 'Student'),
                'student_age': student_profile.get('student_age', '13'),
                'language': student_profile.get('language', 'English')
            }
            
            # Get parser for reveal
            parser_func = get_parser('discovery_reveal')
            
            # Generate answer options with AI
            logger.info("Generating final answer options for reveal...")
            
            def generate_reveal():
                return model_service.generate(
                    prompt_template=prompt_template,
                    variables=variables,
                    parser_func=parser_func,
                    max_tokens=1024,
                    max_retries=3
                )
            
            reveal_result = await asyncio.to_thread(generate_reveal)
            
            if not reveal_result:
                raise ValueError("Model failed to generate answer options")
            
            logger.info(f"✓ Answer options generated for investigation {investigation_id}")
            
            return {
                'investigation_id': investigation_id,
                'conclusion_intro': reveal_result['conclusion_intro'],
                'answer_options': reveal_result['answer_options'],
                'completion_message': reveal_result['completion_message']
            }
            
        except Exception as e:
            logger.error(f"Error revealing answer options: {e}")
            raise
    
    async def complete_investigation(self, investigation_id: str, selected_answer: str) -> Dict[str, Any]:
        """
        Complete the investigation with the student's final answer choice
        
        Args:
            investigation_id: Active discovery investigation ID
            selected_answer: Student's final answer choice
            
        Returns:
            Dict with completion confirmation
        """
        try:
            # Get active investigation
            if investigation_id not in self.active_investigations:
                investigation = self.load_investigation(investigation_id)
                if not investigation:
                    raise ValueError(f"Discovery investigation {investigation_id} not found")
                self.active_investigations[investigation_id] = investigation
            else:
                investigation = self.active_investigations[investigation_id]
            
            # Set final answer and mark as completed
            investigation.final_answer_choice = selected_answer
            investigation.status = "completed"
            
            # Save investigation for tutor review
            self.save_investigation(investigation)
            
            # Remove from active investigations
            del self.active_investigations[investigation_id]
            
            logger.info(f"✓ Investigation {investigation_id} completed with answer: {selected_answer}")
            
            # Log xAPI statement for discovery exploration
            try:
                xapi_logger.log_discovery_exploration(
                    investigation_id=investigation_id,
                    subject_identified=investigation.subject_identified or "Unknown subject",
                    initial_question=investigation.initial_question or "No initial question",
                    selected_questions=investigation.selected_questions,
                    final_choice=selected_answer,
                    questions_explored=investigation.question_count
                )
            except Exception as xapi_error:
                logger.error(f"Error logging xAPI statement for discovery exploration: {xapi_error}")
            
            return {
                'investigation_id': investigation_id,
                'status': 'completed',
                'message': 'Your discovery has been recorded! Great investigation work.'
            }
            
        except Exception as e:
            logger.error(f"Error completing investigation: {e}")
            raise
    
    def save_image_file(self, investigation_id: str, image_data: str) -> str:
        """Save base64 image data as separate file and return relative path"""
        try:
            # Extract base64 data (remove data:image/jpeg;base64, prefix)
            if image_data.startswith('data:image/'):
                # Split on comma to get just the base64 part
                base64_data = image_data.split(',')[1]
                # Get image format from the prefix
                image_format = image_data.split(';')[0].split('/')[1]  # jpeg, png, etc.
            else:
                # Assume it's already just base64 data
                base64_data = image_data
                image_format = 'jpg'  # default
            
            # Decode base64 to bytes
            image_bytes = base64.b64decode(base64_data)
            
            # Create filename with investigation ID
            filename = f"{investigation_id}.{image_format}"
            image_path = DISCOVERY_IMAGES_DIR / filename
            
            # Save image file
            with open(image_path, 'wb') as f:
                f.write(image_bytes)
            
            # Return relative path for storage in JSON
            relative_path = f"images/{filename}"
            logger.info(f"Saved discovery image: {relative_path}")
            return relative_path
            
        except Exception as e:
            logger.error(f"Error saving image file: {e}")
            # Fallback to storing truncated base64 if file save fails
            return image_data[:100] + "..." if len(image_data) > 100 else image_data
    
    def create_investigation(self, image_data: str, question_text: str, 
                           initial_result: Dict[str, Any]) -> DiscoveryInvestigation:
        """Create a new discovery investigation with initial data"""
        investigation = DiscoveryInvestigation()
        
        # Save image as separate file and store path
        image_path = self.save_image_file(investigation.investigation_id, image_data)
        investigation.initial_image = image_path
        investigation.initial_question = question_text
        investigation.subject_identified = initial_result.get('subject_identified')
        investigation.learning_intent = initial_result.get('learning_intent')
        investigation.internal_answers = initial_result.get('internal_answers', [])
        
        # Store in active investigations
        self.active_investigations[investigation.investigation_id] = investigation
        
        # Save to disk
        self.save_investigation(investigation)
        
        logger.info(f"Created discovery investigation: {investigation.investigation_id}")
        return investigation
    
    def save_investigation(self, investigation: DiscoveryInvestigation):
        """Save investigation to disk for tutor synchronization"""
        try:
            investigation_file = DISCOVERY_DATA_DIR / f"{investigation.investigation_id}.json"
            with open(investigation_file, 'w', encoding='utf-8') as f:
                json.dump(investigation.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Discovery investigation saved: {investigation.investigation_id}")
        except Exception as e:
            logger.error(f"Error saving discovery investigation {investigation.investigation_id}: {e}")
    
    def load_investigation(self, investigation_id: str) -> Optional[DiscoveryInvestigation]:
        """Load investigation from disk"""
        try:
            investigation_file = DISCOVERY_DATA_DIR / f"{investigation_id}.json"
            if investigation_file.exists():
                with open(investigation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                investigation = DiscoveryInvestigation.from_dict(data)
                logger.info(f"Discovery investigation loaded: {investigation_id}")
                return investigation
        except Exception as e:
            logger.error(f"Error loading discovery investigation {investigation_id}: {e}")
        return None
    
    def get_investigation_data_for_tutor(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent completed investigations for tutor synchronization"""
        try:
            investigations = []
            investigation_files = sorted(DISCOVERY_DATA_DIR.glob("*.json"), 
                                       key=lambda f: f.stat().st_mtime, reverse=True)
            
            for investigation_file in investigation_files[:limit]:
                try:
                    with open(investigation_file, 'r', encoding='utf-8') as f:
                        investigation_data = json.load(f)
                    
                    # Only return completed investigations
                    if investigation_data.get("status") == "completed":
                        investigations.append(investigation_data)
                except Exception as e:
                    logger.error(f"Error reading investigation file {investigation_file}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(investigations)} completed discovery investigations for tutor")
            return investigations
            
        except Exception as e:
            logger.error(f"Error getting investigation data: {e}")
            return []

# Global discovery service instance
discovery_service = DiscoveryService()

async def get_discovery_service() -> DiscoveryService:
    """Get the global discovery service instance"""
    return discovery_service