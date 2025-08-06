"""
Asynchronous feedback processing queue system for challenge evaluations.
Allows students to continue working while feedback is generated in the background.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from model_service import create_model_service
from parsers import get_parser

# Configure logging
logger = logging.getLogger(__name__)

# Global queue and task storage
feedback_queue: asyncio.Queue = None
task_results: Dict[str, Dict[str, Any]] = {}
feedback_worker_task: asyncio.Task = None
model_service = None

# Task statuses
TASK_STATUS_PENDING = "pending"
TASK_STATUS_PROCESSING = "processing" 
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_ERROR = "error"

class FeedbackTask:
    """Represents a feedback task with all necessary data"""
    
    def __init__(self, task_id: str, challenge_data: Dict[str, Any], submission_data: Dict[str, Any], variables: Dict[str, Any], images: list = None, source_file: str = None):
        """Initialize a feedback task.
        
        Args:
            task_id: Unique identifier for the task.
            challenge_data: Challenge information and requirements.
            submission_data: Student's submission data.
            variables: Template variables for AI processing.
            images: Optional list of images in the submission.
            source_file: Source file name for tracking.
        """
        self.task_id = task_id
        self.challenge_data = challenge_data
        self.submission_data = submission_data
        self.variables = variables
        self.images = images or []
        self.source_file = source_file or "unknown.json"  # Track source file for unique ID generation
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None

async def initialize_feedback_queue():
    """Initialize the global feedback queue and start worker.
    
    Sets up the async queue, model service, and background worker task.
    """
    global feedback_queue, feedback_worker_task, model_service
    
    if feedback_queue is None:
        feedback_queue = asyncio.Queue(maxsize=100)  # Allow up to 100 pending tasks
        logger.info("Feedback queue initialized with max size 100")
    
    if model_service is None:
        logger.info("🚀 Creating model service for feedback processing...")
        logger.info("🔍 Calling create_model_service()...")
        
        model_service = create_model_service()
        
        logger.info(f"✅ Model service created: {type(model_service).__name__}")
        logger.info(f"📝 Service details: {model_service}")
        
        # Load model in background to avoid first-task delay
        logger.info("🔥 Loading model service for feedback processing...")
        logger.info("🎯 About to call load_model()...")
        
        try:
            logger.info("⚡ Calling model_service.load_model()...")
            model_loaded = model_service.load_model()
            logger.info(f"📊 load_model() returned: {model_loaded}")
            
            if model_loaded:
                logger.info("✅ Model service loaded successfully for feedback queue")
                logger.info(f"🎉 Client state after load_model(): {getattr(model_service, 'client', 'No client attribute')}")
            else:
                logger.warning("⚠️ Model service failed to load - feedback tasks will fail")
                logger.warning(f"❌ Client state after failed load: {getattr(model_service, 'client', 'No client attribute')}")
                
        except Exception as e:
            logger.error(f"💥 Error loading model service: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"🔍 Full traceback:\n{traceback.format_exc()}")
            logger.error(f"❌ Client state after exception: {getattr(model_service, 'client', 'No client attribute')}")
    
    if feedback_worker_task is None or feedback_worker_task.done():
        feedback_worker_task = asyncio.create_task(feedback_worker())
        logger.info("Feedback worker started")

async def stop_feedback_queue():
    """Stop the feedback worker gracefully"""
    global feedback_worker_task
    
    if feedback_worker_task and not feedback_worker_task.done():
        logger.info("Stopping feedback worker...")
        feedback_worker_task.cancel()
        try:
            await feedback_worker_task
        except asyncio.CancelledError:
            logger.info("Feedback worker stopped")
        finally:
            feedback_worker_task = None

async def feedback_worker():
    """Background worker that processes feedback tasks from the queue"""
    logger.info("Feedback worker started - waiting for tasks...")
    
    while True:
        try:
            # Get next task from queue (blocks until available)
            task: FeedbackTask = await feedback_queue.get()
            
            logger.info(f"Processing feedback task: {task.task_id}")
            
            # Update task status to processing
            task_results[task.task_id]['status'] = TASK_STATUS_PROCESSING
            task_results[task.task_id]['started_at'] = datetime.now().isoformat()
            task.started_at = datetime.now()
            
            try:
                # Process the feedback
                result = await process_feedback_task(task)
                
                # Save the submission to persistent storage
                try:
                    from submission_service import save_challenge_submission
                    
                    submission_id = save_challenge_submission(
                        submission_data=task.submission_data,
                        challenge_data=task.challenge_data['challenge'],
                        feedback_data=result,
                        source_file=task.source_file
                    )
                    
                    logger.info(f"✓ Submission saved with ID: {submission_id}")
                    
                    # Add submission ID to result
                    result['submission_id'] = submission_id
                    
                    
                except Exception as save_error:
                    logger.error(f"Error saving submission: {save_error}")
                    # Continue with feedback even if submission save fails
                
                # Mark as completed
                task_results[task.task_id].update({
                    'status': TASK_STATUS_COMPLETED,
                    'result': result,
                    'completed_at': datetime.now().isoformat(),
                    'processing_time_seconds': (datetime.now() - task.started_at).total_seconds()
                })
                
                logger.info(f"✓ Feedback task {task.task_id} completed successfully in {task_results[task.task_id]['processing_time_seconds']:.1f}s")
                
            except Exception as e:
                # Mark as error
                task_results[task.task_id].update({
                    'status': TASK_STATUS_ERROR,
                    'error': str(e),
                    'completed_at': datetime.now().isoformat()
                })
                
                logger.error(f"✗ Feedback task {task.task_id} failed: {e}")
            
            # Mark task as done in queue
            feedback_queue.task_done()
            
        except asyncio.CancelledError:
            logger.info("Feedback worker cancelled")
            break
        except Exception as e:
            logger.error(f"Unexpected error in feedback worker: {e}")
            # Continue processing other tasks

async def process_feedback_task(task: FeedbackTask) -> Dict[str, Any]:
    """Process a single feedback task using the model service (NON-BLOCKING)"""
    
    try:
        # Load the evaluation prompt template
        prompt_template = model_service.load_prompt('evaluate_challenge')
        
        # Get parser function
        parser_func = get_parser('challenge_feedback')
        
        # Generate evaluation with AI (using visual capabilities if images present)
        logger.info(f"Generating challenge evaluation for task {task.task_id} with {len(task.images)} images...")
        
        # CRITICAL FIX: Execute model generation in separate thread to avoid blocking event loop
        logger.info(f"Running model generation in separate thread for task {task.task_id}")
        evaluation_result = await asyncio.to_thread(
            model_service.generate,
            prompt_template=prompt_template,
            variables=task.variables,
            parser_func=parser_func,
            max_tokens=1024,
            max_retries=3,
            images=task.images if task.images else None
        )
        logger.info(f"Thread-based generation completed for task {task.task_id}")
        
        if not evaluation_result:
            raise ValueError("Model failed to generate valid feedback")
        
        logger.info(f"✓ Challenge evaluation completed for task {task.task_id}: ready_to_submit={evaluation_result.get('ready_to_submit', False)}")
        
        return evaluation_result
        
    except Exception as e:
        logger.error(f"Error processing feedback task {task.task_id}: {e}")
        raise

def create_feedback_task(challenge_data: Dict[str, Any], submission_data: Dict[str, Any], variables: Dict[str, Any], images: list = None, source_file: str = None) -> str:
    """Create a new feedback task and add it to the queue"""
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Create task object
    task = FeedbackTask(
        task_id=task_id,
        challenge_data=challenge_data,
        submission_data=submission_data,
        variables=variables,
        images=images,
        source_file=source_file
    )
    
    # Initialize task result tracking
    task_results[task_id] = {
        'status': TASK_STATUS_PENDING,
        'created_at': task.created_at.isoformat(),
        'challenge_id': submission_data.get('challengeId', 'unknown'),
        'challenge_title': challenge_data.get('challenge', {}).get('title', 'Unknown Challenge')[:100],
        'has_images': len(images) > 0 if images else False,
        'started_at': None,
        'completed_at': None,
        'result': None,
        'error': None
    }
    
    # Add to queue (non-blocking)
    try:
        feedback_queue.put_nowait(task)
        logger.info(f"✓ Feedback task {task_id} created and queued")
        logger.info(f"Queue status: {feedback_queue.qsize()} pending tasks")
    except asyncio.QueueFull:
        # Clean up if queue is full
        del task_results[task_id]
        raise ValueError("Feedback queue is full. Please try again later.")
    
    return task_id

def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get the current status and result of a feedback task"""
    
    if task_id not in task_results:
        return None
    
    task_info = task_results[task_id].copy()
    
    # Add queue position if still pending
    if task_info['status'] == TASK_STATUS_PENDING:
        task_info['queue_position'] = get_queue_position(task_id)
        task_info['estimated_wait_minutes'] = estimate_wait_time(task_id)
    
    return task_info

def get_queue_position(task_id: str) -> int:
    """Get the position of a task in the queue (1 = next to process)"""
    # This is a simplified implementation - in production you might want more accurate tracking
    if task_results[task_id]['status'] != TASK_STATUS_PENDING:
        return 0
    
    # Count pending tasks created before this one
    this_task_created = task_results[task_id]['created_at']
    position = 1  # Start at 1 (next to process)
    
    for other_task_id, other_info in task_results.items():
        if (other_info['status'] == TASK_STATUS_PENDING and 
            other_info['created_at'] < this_task_created):
            position += 1
    
    return position

def estimate_wait_time(task_id: str) -> float:
    """Estimate wait time in minutes based on queue position and average processing time"""
    position = get_queue_position(task_id)
    
    # Calculate average processing time from completed tasks
    completed_tasks = [info for info in task_results.values() 
                      if info['status'] == TASK_STATUS_COMPLETED and 
                         info.get('processing_time_seconds')]
    
    if completed_tasks:
        avg_processing_time = sum(task['processing_time_seconds'] for task in completed_tasks) / len(completed_tasks)
    else:
        # Default estimate: 2 minutes per task (conservative)
        avg_processing_time = 120
    
    # Estimate: (position - 1) * average_time (since position 1 is currently processing)
    estimated_seconds = max(0, (position - 1) * avg_processing_time)
    return estimated_seconds / 60  # Convert to minutes

def cleanup_old_tasks(hours: int = 24):
    """Remove task results older than specified hours to prevent memory leaks"""
    cutoff_time = datetime.now().timestamp() - (hours * 3600)
    
    old_task_ids = []
    for task_id, info in task_results.items():
        try:
            created_timestamp = datetime.fromisoformat(info['created_at']).timestamp()
            if created_timestamp < cutoff_time:
                old_task_ids.append(task_id)
        except:
            # If we can't parse the timestamp, it's probably old
            old_task_ids.append(task_id)
    
    for task_id in old_task_ids:
        del task_results[task_id]
    
    if old_task_ids:
        logger.info(f"Cleaned up {len(old_task_ids)} old task results")

def get_queue_stats() -> Dict[str, Any]:
    """Get statistics about the feedback queue"""
    pending_count = sum(1 for info in task_results.values() if info['status'] == TASK_STATUS_PENDING)
    processing_count = sum(1 for info in task_results.values() if info['status'] == TASK_STATUS_PROCESSING)
    completed_count = sum(1 for info in task_results.values() if info['status'] == TASK_STATUS_COMPLETED)
    error_count = sum(1 for info in task_results.values() if info['status'] == TASK_STATUS_ERROR)
    
    return {
        'queue_size': feedback_queue.qsize() if feedback_queue else 0,
        'pending_tasks': pending_count,
        'processing_tasks': processing_count,
        'completed_tasks': completed_count,
        'error_tasks': error_count,
        'total_tasks': len(task_results)
    }

# Initialize queue when module is imported
async def init():
    """Initialize the feedback queue system"""
    await initialize_feedback_queue()

if __name__ == "__main__":
    # Initialize the feedback queue when run directly
    asyncio.run(initialize_feedback_queue())