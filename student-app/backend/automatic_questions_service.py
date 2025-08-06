"""
Automatic Questions Service
Handles automatic generation of practice questions based on difficulty progression
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Constants
CONTENT_DIR = Path("content")
PROGRESS_FILE = CONTENT_DIR / "progress.json"
PRACTICE_PROGRESS_FILE = CONTENT_DIR / "practice_progress.json"
EXPERIMENT_PROGRESS_FILE = CONTENT_DIR / "experiment_progress.json"
GENERATED_PRACTICE_DIR = CONTENT_DIR / "generated" / "practice"
GENERATED_EXPERIMENT_DIR = CONTENT_DIR / "generated" / "experiment"
PROCESSED_DIR = CONTENT_DIR / "processed"

DIFFICULTY_LEVELS = ["easy", "medium", "hard"]

class AutomaticQuestionsService:
    """Service for managing automatic question generation based on student progress"""
    
    def __init__(self):
        self.progress_file = PROGRESS_FILE
        self.practice_progress_file = PRACTICE_PROGRESS_FILE
        self.experiment_progress_file = EXPERIMENT_PROGRESS_FILE
        self.generated_dir = GENERATED_PRACTICE_DIR
        self.experiment_dir = GENERATED_EXPERIMENT_DIR
        self.processed_dir = PROCESSED_DIR
        
        # Locks to prevent race conditions
        self._challenge_generation_locks = {}  # content_key -> Lock
        self._question_generation_locks = {}   # content_id -> Lock
    
    def _get_challenge_lock(self, content_key: str) -> asyncio.Lock:
        """Get or create a lock for challenge generation for specific content combination"""
        if content_key not in self._challenge_generation_locks:
            self._challenge_generation_locks[content_key] = asyncio.Lock()
        return self._challenge_generation_locks[content_key]
    
    def _get_question_lock(self, content_id: str) -> asyncio.Lock:
        """Get or create a lock for question generation for specific content"""
        if content_id not in self._question_generation_locks:
            self._question_generation_locks[content_id] = asyncio.Lock()
        return self._question_generation_locks[content_id]
        
    def load_progress_data(self) -> Dict[str, Any]:
        """Load current progress data"""
        try:
            if self.progress_file.exists():
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading progress data: {e}")
        return {}
    
    def save_progress_data(self, progress_data: Dict[str, Any]) -> bool:
        """Save progress data"""
        try:
            # Ensure directory exists
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Error saving progress data: {e}")
            return False
    
    def load_practice_progress_data(self) -> Dict[str, Any]:
        """Load practice progress data"""
        try:
            if self.practice_progress_file.exists():
                with open(self.practice_progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading practice progress data: {e}")
        return {}
    
    def load_experiment_progress_data(self) -> Dict[str, Any]:
        """Load experiment progress data"""
        try:
            if self.experiment_progress_file.exists():
                with open(self.experiment_progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading experiment progress data: {e}")
        return {}
    
    def initialize_questions_tracking(self, content_id: str) -> Dict[str, Any]:
        """Initialize questions tracking for a content"""
        return {
            "easy_generated": False,
            "medium_generated": False,
            "hard_generations": 0,
            "current_available_difficulty": None
        }
    
    def initialize_challenges_tracking(self, content_id: str) -> Dict[str, Any]:
        """Initialize challenges tracking for a content"""
        return {
            "generated": False,
            "last_generated": None,
            "source_contents": [],
            "generation_count": 0
        }
    
    async def trigger_initial_questions(self, content_id: str) -> bool:
        """
        Trigger initial easy questions generation when content is first accessed
        
        Args:
            content_id: Content identifier
            
        Returns:
            True if questions were triggered for generation, False otherwise
        """
        # Use lock to prevent race conditions
        async with self._get_question_lock(content_id):
            try:
                logger.info(f"Checking if initial questions needed for content: {content_id}")
                
                # Load current progress
                progress_data = self.load_progress_data()
                
                # Initialize content progress if not exists
                if content_id not in progress_data:
                    progress_data[content_id] = {}
                
                # Initialize questions tracking if not exists
                if "questions" not in progress_data[content_id]:
                    progress_data[content_id]["questions"] = self.initialize_questions_tracking(content_id)
                
                questions_data = progress_data[content_id]["questions"]
                
                # Check if easy questions already generated (double-check after acquiring lock)
                if questions_data.get("easy_generated", False):
                    logger.info(f"Easy questions already generated for {content_id}")
                    return False
                
                # Trigger easy questions generation
                logger.info(f"Triggering easy questions generation for {content_id}")
                success = await self._generate_questions_async(content_id, "easy")
                
                if success:
                    # Update progress to mark easy as generated
                    questions_data["easy_generated"] = True
                    questions_data["current_available_difficulty"] = "easy"
                    progress_data[content_id]["questions"] = questions_data
                    
                    # Save updated progress
                    if self.save_progress_data(progress_data):
                        logger.info(f"Successfully generated and tracked easy questions for {content_id}")
                        
                        # Trigger challenge generation after easy questions are successfully generated
                        logger.info(f"Easy questions completed for {content_id}, triggering challenge generation")
                        try:
                            # Run challenge generation in background (don't wait for completion)
                            asyncio.create_task(self.trigger_challenge_generation(content_id))
                            logger.info(f"Challenge generation task created for {content_id}")
                        except Exception as e:
                            logger.error(f"Error creating challenge generation task for {content_id}: {e}")
                        
                        return True
                    else:
                        logger.error(f"Failed to save progress after generating easy questions for {content_id}")
                
                return False
                
            except Exception as e:
                logger.error(f"Error triggering initial questions for {content_id}: {e}")
                return False
    
    async def check_completion_and_progress(self, content_id: str) -> Optional[str]:
        """
        Check if current difficulty level is completed and trigger next level if needed
        
        Args:
            content_id: Content identifier
            
        Returns:
            Next difficulty level that was triggered, or None if no progression
        """
        try:
            logger.info(f"Checking completion and progression for content: {content_id}")
            
            # Load progress data
            progress_data = self.load_progress_data()
            practice_progress = self.load_practice_progress_data()
            
            if content_id not in progress_data:
                logger.warning(f"Content {content_id} not found in progress data")
                return None
            
            if "questions" not in progress_data[content_id]:
                logger.warning(f"Questions data not found for {content_id}")
                return None
            
            questions_data = progress_data[content_id]["questions"]
            current_difficulty = questions_data.get("current_available_difficulty")
            
            if not current_difficulty:
                logger.info(f"No current difficulty set for {content_id}")
                return None
            
            # Check if current difficulty is completed
            if self._is_difficulty_completed(content_id, current_difficulty, practice_progress):
                logger.info(f"{current_difficulty.title()} questions completed for {content_id}")
                
                # Determine next difficulty
                next_difficulty = self._get_next_difficulty(current_difficulty, questions_data)
                
                if next_difficulty:
                    logger.info(f"Triggering {next_difficulty} questions for {content_id}")
                    
                    # Generate next difficulty questions
                    success = await self._generate_questions_async(content_id, next_difficulty)
                    
                    if success:
                        # Update progress tracking
                        if next_difficulty == "medium":
                            questions_data["medium_generated"] = True
                        elif next_difficulty == "hard":
                            questions_data["hard_generations"] += 1
                        
                        questions_data["current_available_difficulty"] = next_difficulty
                        progress_data[content_id]["questions"] = questions_data
                        
                        # Save updated progress
                        if self.save_progress_data(progress_data):
                            logger.info(f"Successfully generated and tracked {next_difficulty} questions for {content_id}")
                            return next_difficulty
                        else:
                            logger.error(f"Failed to save progress after generating {next_difficulty} questions")
                
            return None
            
        except Exception as e:
            logger.error(f"Error checking completion and progression for {content_id}: {e}")
            return None
    
    def _is_difficulty_completed(self, content_id: str, difficulty: str, practice_progress: Dict[str, Any]) -> bool:
        """
        Check if all questions of a specific difficulty are completed correctly
        
        Args:
            content_id: Content identifier
            difficulty: Difficulty level to check
            practice_progress: Practice progress data
            
        Returns:
            True if all questions of the difficulty are answered correctly
        """
        try:
            if content_id not in practice_progress:
                return False
            
            content_progress = practice_progress[content_id]
            
            # Get all question files for this content and difficulty
            content_practice_dir = self.generated_dir / content_id
            if not content_practice_dir.exists():
                return False
            
            # Find all question files for this difficulty
            question_files = list(content_practice_dir.glob(f"questions_*_{difficulty}.json"))
            
            if not question_files:
                logger.warning(f"No {difficulty} question files found for {content_id}")
                return False
            
            # Check if all questions in all files are answered correctly
            for question_file in question_files:
                try:
                    with open(question_file, 'r', encoding='utf-8') as f:
                        questions_data = json.load(f)
                    
                    # Extract question IDs from the file
                    question_ids = []
                    for section in questions_data.get('questions', {}).values():
                        if isinstance(section, list):
                            for question in section:
                                if 'id' in question:
                                    question_ids.append(question['id'])
                    
                    # Check if all questions are answered correctly
                    for question_id in question_ids:
                        if question_id not in content_progress:
                            logger.debug(f"Question {question_id} not answered yet")
                            return False
                        
                        if not content_progress[question_id].get('correct', False):
                            logger.debug(f"Question {question_id} not answered correctly")
                            return False
                
                except Exception as e:
                    logger.error(f"Error reading question file {question_file}: {e}")
                    return False
            
            logger.info(f"All {difficulty} questions completed correctly for {content_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking difficulty completion: {e}")
            return False
    
    def _get_next_difficulty(self, current_difficulty: str, questions_data: Dict[str, Any]) -> Optional[str]:
        """
        Get the next difficulty level to generate
        
        Args:
            current_difficulty: Current difficulty level
            questions_data: Questions tracking data
            
        Returns:
            Next difficulty level or None if no progression needed
        """
        if current_difficulty == "easy":
            if not questions_data.get("medium_generated", False):
                return "medium"
        elif current_difficulty == "medium":
            if questions_data.get("hard_generations", 0) == 0:
                return "hard"
        elif current_difficulty == "hard":
            # Always generate new hard questions when completed
            return "hard"
        
        return None
    
    async def _generate_questions_async(self, content_id: str, difficulty: str) -> bool:
        """
        Generate questions asynchronously using the existing generate_questions.py script
        
        Args:
            content_id: Content identifier
            difficulty: Difficulty level
            
        Returns:
            True if generation was successful
        """
        try:
            logger.info(f"Starting async generation of {difficulty} questions for {content_id}")
            
            # Verify the processed content file exists
            content_file = self.processed_dir / f"{content_id}.txt"
            
            if not content_file.exists():
                logger.error(f"Content file not found: {content_file}")
                return False
            
            # Run generate_questions.py script asynchronously
            # Note: generate_questions.py expects just the filename, not the full path
            cmd = [
                "python", 
                "generate_questions.py", 
                f"{content_id}.txt", 
                "--difficulty", difficulty
            ]
            
            logger.info(f"Executing command: {' '.join(cmd)}")
            
            # Run the command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(__file__).parent
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Successfully generated {difficulty} questions for {content_id}")
                if stdout:
                    logger.debug(f"Generation output: {stdout.decode()}")
                return True
            else:
                logger.error(f"Error generating {difficulty} questions for {content_id}")
                if stderr:
                    logger.error(f"Generation error: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error in async question generation for {content_id} ({difficulty}): {e}")
            return False
    
    def get_questions_status(self, content_id: str) -> Dict[str, Any]:
        """
        Get current questions generation status for a content
        
        Args:
            content_id: Content identifier
            
        Returns:
            Dictionary with questions status information
        """
        try:
            progress_data = self.load_progress_data()
            
            if content_id not in progress_data or "questions" not in progress_data[content_id]:
                return self.initialize_questions_tracking(content_id)
            
            return progress_data[content_id]["questions"]
            
        except Exception as e:
            logger.error(f"Error getting questions status for {content_id}: {e}")
            return self.initialize_questions_tracking(content_id)
    
    def discover_accessed_content(self) -> list[str]:
        """
        Discover all content files that have been actually accessed by the user (based on progress.json)
        
        Returns:
            List of content filenames that the user has actually visited in Learn section
        """
        try:
            progress_data = self.load_progress_data()
            
            if not progress_data:
                logger.info("No progress data found, no content has been accessed")
                return []
            
            content_files = []
            for content_id, content_progress in progress_data.items():
                # Check if user has actually viewed any sections
                textbook_viewed = content_progress.get('textbook', {}).get('viewedSections', 0)
                story_viewed = content_progress.get('story', {}).get('viewedSections', 0)
                
                if textbook_viewed > 0 or story_viewed > 0:
                    content_files.append(content_id)
                    logger.debug(f"Found accessed content: {content_id} (textbook: {textbook_viewed}, story: {story_viewed})")
                else:
                    logger.debug(f"Content exists but not accessed: {content_id}")
            
            logger.info(f"Discovered {len(content_files)} actually accessed content files: {content_files}")
            return content_files
            
        except Exception as e:
            logger.error(f"Error discovering accessed content: {e}")
            return []
    
    async def trigger_challenge_generation(self, trigger_content_id: str) -> bool:
        """
        Trigger challenge generation after easy questions are generated for content
        
        Args:
            trigger_content_id: The content ID that triggered this generation
            
        Returns:
            True if challenges were triggered for generation, False otherwise
        """
        try:
            logger.info(f"Checking if challenges should be generated (triggered by {trigger_content_id})")
            
            # Get all accessed content for interdisciplinary challenges
            accessed_content = self.discover_accessed_content()
            
            if not accessed_content:
                logger.warning("No processed content found, cannot generate challenges")
                return False
            
            # Create a combined key for tracking challenge generation
            content_key = "_".join(sorted(accessed_content))
            
            # Use lock to prevent race conditions for this content combination
            async with self._get_challenge_lock(content_key):
                if len(accessed_content) == 1 and accessed_content[0] == trigger_content_id:
                    logger.info(f"Only one content accessed ({trigger_content_id}), generating single-content challenges")
                    content_files = [f"{trigger_content_id}.txt"]
                else:
                    logger.info(f"Multiple content accessed, generating interdisciplinary challenges from: {accessed_content}")
                    content_files = [f"{content}.txt" for content in accessed_content]
                
                # Load current progress to track challenge generation
                progress_data = self.load_progress_data()
                
                if content_key not in progress_data:
                    progress_data[content_key] = {}
                
                # Initialize challenge tracking if not exists
                if "challenges" not in progress_data[content_key]:
                    progress_data[content_key]["challenges"] = self.initialize_challenges_tracking(content_key)
                
                challenges_data = progress_data[content_key]["challenges"]
                
                # Check if challenges already generated for this content combination (double-check after lock)
                if challenges_data.get("generated", False) and challenges_data.get("source_contents") == accessed_content:
                    logger.info(f"Challenges already generated for content combination: {accessed_content}")
                    return False
                
                # Trigger challenge generation
                logger.info(f"Triggering challenge generation for content files: {content_files}")
                success = await self._generate_challenges_async(content_files, accessed_content)
                
                if success:
                    # Update progress to mark challenges as generated
                    from datetime import datetime
                    challenges_data["generated"] = True
                    challenges_data["last_generated"] = datetime.now().isoformat()
                    challenges_data["source_contents"] = accessed_content
                    challenges_data["generation_count"] += 1
                    progress_data[content_key]["challenges"] = challenges_data
                    
                    # Save updated progress
                    if self.save_progress_data(progress_data):
                        logger.info(f"Successfully generated and tracked challenges for content combination: {accessed_content}")
                        return True
                    else:
                        logger.error("Failed to save progress after generating challenges")
                
                return False
            
        except Exception as e:
            logger.error(f"Error triggering challenge generation: {e}")
            return False
    
    def count_available_challenges(self) -> int:
        """
        Count available (non-rejected) challenges
        
        Returns:
            Number of available challenges
        """
        try:
            experiment_dir = Path("content/generated/experiment")
            if not experiment_dir.exists():
                return 0
            
            registry_file = experiment_dir / "challenges_registry.json"
            if not registry_file.exists():
                return 0
            
            with open(registry_file, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            # Load experiment progress to get rejected IDs
            experiment_progress = self.load_experiment_progress_data()
            rejected_ids = set(experiment_progress.get('rejected', []))
            
            # Count non-rejected challenges
            available_count = 0
            for challenge_uuid in registry.get("challenges", {}):
                if challenge_uuid not in rejected_ids:
                    available_count += 1
            
            return available_count
            
        except Exception as e:
            logger.error(f"Error counting available challenges: {e}")
            return 0

    async def check_challenge_exhaustion_and_regenerate(self) -> bool:
        """
        Check if challenges are exhausted and regenerate if needed
        
        Returns:
            True if challenges were regenerated, False otherwise
        """
        try:
            logger.info("Checking for challenge exhaustion")
            
            # Get current content combination
            accessed_content = self.discover_accessed_content()
            
            if not accessed_content:
                logger.warning("No processed content found for challenge regeneration")
                return False
            
            # Check if we have any available (non-rejected) challenges
            available_challenges = self.count_available_challenges()
            
            # Load experiment progress to check if user has made enough decisions
            experiment_progress = self.load_experiment_progress_data()
            rejected_count = len(experiment_progress.get("rejected", []))
            accepted_count = len(experiment_progress.get("accepted", []))
            total_decisions = rejected_count + accepted_count
            
            # Only regenerate if:
            # 1. No challenges are available AND
            # 2. User has made at least 3 decisions (to prevent immediate regeneration)
            if available_challenges > 0:
                logger.info(f"Challenges not exhausted ({available_challenges} available, {total_decisions} decisions made)")
                return False
            
            if total_decisions < 3:
                logger.info(f"Not enough decisions made yet (only {total_decisions}, need at least 3)")
                return False
            
            logger.info(f"Challenges exhausted (0 available, {total_decisions} decisions made), triggering regeneration")
            
            # Trigger regeneration
            content_files = [f"{content}.txt" for content in accessed_content]
            success = await self._generate_challenges_async(content_files, accessed_content, is_regeneration=True)
            
            if success:
                # Update progress tracking
                progress_data = self.load_progress_data()
                content_key = "_".join(sorted(accessed_content))
                
                if content_key in progress_data and "challenges" in progress_data[content_key]:
                    from datetime import datetime
                    challenges_data = progress_data[content_key]["challenges"]
                    challenges_data["last_generated"] = datetime.now().isoformat()
                    challenges_data["generation_count"] += 1
                    
                    self.save_progress_data(progress_data)
                    logger.info(f"Successfully regenerated challenges for content combination: {accessed_content}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking challenge exhaustion and regenerating: {e}")
            return False
    
    async def _generate_challenges_async(self, content_files: list[str], content_names: list[str], is_regeneration: bool = False) -> bool:
        """
        Generate challenges asynchronously using the existing generate_challenges.py script
        
        Args:
            content_files: List of content filenames (with .txt extension)
            content_names: List of content names (without extension) for tracking
            is_regeneration: Whether this is a regeneration (for different prompting)
            
        Returns:
            True if generation was successful
        """
        try:
            action = "regenerating" if is_regeneration else "generating"
            logger.info(f"Starting async {action} of challenges for contents: {content_names}")
            
            # Verify all content files exist
            for content_file in content_files:
                content_path = self.processed_dir / content_file
                if not content_path.exists():
                    logger.error(f"Content file not found: {content_path}")
                    return False
            
            # Build command for generate_challenges.py
            cmd = ["python", "generate_challenges.py"] + content_files
            
            logger.info(f"Executing challenge generation command: {' '.join(cmd)}")
            
            # Run the command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(__file__).parent
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Successfully {action} challenges for contents: {content_names}")
                if stdout:
                    logger.debug(f"Generation output: {stdout.decode()}")
                return True
            else:
                logger.error(f"Error {action} challenges for contents: {content_names}")
                if stderr:
                    logger.error(f"Generation error: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error in async challenge generation for contents {content_names}: {e}")
            return False

# Global service instance
automatic_questions_service = AutomaticQuestionsService()