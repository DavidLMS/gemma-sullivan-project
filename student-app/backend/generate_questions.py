#!/usr/bin/env python3
"""
Question Generator Script
Generates practice questions from processed educational content.

Usage:
    python generate_questions.py <content_file.txt> [--difficulty easy|medium|hard]

Example:
    python generate_questions.py algebra_example.txt --difficulty medium
"""

import sys
import os
import argparse
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from model_service import create_model_service
from parsers import parse_questions
from student_profile import get_student_profile_for_questions

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_previous_questions(questions_dir):
    """Load all previously generated questions from UUID-based system to avoid repetition"""
    previous_questions = []
    
    # Check if registry exists
    registry_file = questions_dir / "questions_registry.json"
    if not registry_file.exists():
        return "None (first time generating questions for this content)"
    
    try:
        with open(registry_file, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        
        # Load questions from individual UUID files
        questions_subdir = questions_dir / "questions"
        if not questions_subdir.exists():
            return "None (no questions found)"
            
        for question_uuid, question_info in registry.get("questions", {}).items():
            question_file = questions_subdir / f"{question_uuid}.json"
            if question_file.exists():
                try:
                    with open(question_file, 'r', encoding='utf-8') as f:
                        question_data = json.load(f)
                    
                    difficulty = question_data.get("difficulty", "unknown")
                    question_text = question_data.get("text", "")
                    if question_text:
                        previous_questions.append(f"[{difficulty.upper()}] {question_text}")
                        
                except Exception as e:
                    logger.warning(f"Could not load question from {question_file}: {e}")
    
    except Exception as e:
        logger.warning(f"Could not load questions registry: {e}")
        return "None (error loading previous questions)"
    
    if not previous_questions:
        return "None (no valid previous questions found)"
    
    return "\n".join([f"- {q}" for q in previous_questions])


def ensure_questions_structure(questions_dir):
    """Ensure the UUID-based questions directory structure exists"""
    questions_dir.mkdir(parents=True, exist_ok=True)
    questions_subdir = questions_dir / "questions"
    questions_subdir.mkdir(parents=True, exist_ok=True)
    
    registry_file = questions_dir / "questions_registry.json"
    if not registry_file.exists():
        # Create initial registry
        initial_registry = {
            "metadata": {
                "topic": questions_dir.name,
                "created_at": datetime.now().isoformat(),
                "version": "2.0_uuid"
            },
            "questions": {}
        }
        with open(registry_file, 'w', encoding='utf-8') as f:
            json.dump(initial_registry, f, indent=2, ensure_ascii=False)
    
    return questions_subdir, registry_file


def save_questions_uuid(questions_result, questions_dir, content_file, difficulty):
    """Save generated questions using UUID-based system"""
    
    questions_subdir, registry_file = ensure_questions_structure(questions_dir)
    
    # Load existing registry
    with open(registry_file, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    
    saved_questions = []
    generation_timestamp = datetime.now().isoformat()
    
    # Process each question type
    for question_type in ['multiple_choice', 'true_false', 'fill_blank', 'short_answer', 'free_recall']:
        if question_type not in questions_result:
            continue
            
        for question in questions_result[question_type]:
            # Generate UUID for this question
            question_uuid = str(uuid.uuid4())
            
            # Create individual question file
            question_data = {
                "uuid": question_uuid,
                "type": question_type,
                "text": question.get("text", ""),
                "difficulty": difficulty,
                "source_content": str(content_file),
                "generated_at": generation_timestamp
            }
            
            # Add type-specific fields
            if question_type == "multiple_choice":
                question_data["options"] = question.get("options", {})
                question_data["correct_answer"] = question.get("correct_answer", "")
            elif question_type == "true_false":
                question_data["correct_answer"] = question.get("correct_answer", "")
            elif question_type == "fill_blank":
                question_data["correct_answer"] = question.get("correct_answer", "")
            elif question_type in ["short_answer", "free_recall"]:
                question_data["sample_answer"] = question.get("sample_answer", "")
            
            # Save individual question file
            question_file = questions_subdir / f"{question_uuid}.json"
            with open(question_file, 'w', encoding='utf-8') as f:
                json.dump(question_data, f, indent=2, ensure_ascii=False)
            
            # Add to registry
            registry["questions"][question_uuid] = {
                "uuid": question_uuid,
                "type": question_type,
                "title": question.get("text", "")[:100] + ("..." if len(question.get("text", "")) > 100 else ""),
                "difficulty": difficulty,
                "file": f"questions/{question_uuid}.json",
                "generated_at": generation_timestamp
            }
            
            saved_questions.append(question_uuid)
            logger.info(f"✓ Saved question {question_uuid}: {question_type}")
    
    # Update registry metadata
    registry["metadata"]["last_updated"] = generation_timestamp
    registry["metadata"]["total_questions"] = len(registry["questions"])
    
    # Save updated registry
    with open(registry_file, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✓ Questions registry updated: {len(saved_questions)} questions added")
    logger.info(f"✓ Registry file: {registry_file}")
    
    return saved_questions


def check_question_requirements(questions_result):
    """Check if we have the required number of questions by type"""
    requirements = {
        'multiple_choice_true_false': 3,  # Combined MC + TF should be 3
        'fill_blank': 2,
        'short_answer': 2,
        'free_recall': 1
    }
    
    current = {
        'multiple_choice_true_false': len(questions_result.get('multiple_choice', [])) + len(questions_result.get('true_false', [])),
        'fill_blank': len(questions_result.get('fill_blank', [])),
        'short_answer': len(questions_result.get('short_answer', [])),
        'free_recall': len(questions_result.get('free_recall', []))
    }
    
    missing = {}
    overgenerated = {}
    
    for question_type, required in requirements.items():
        if current[question_type] < required:
            missing[question_type] = required - current[question_type]
        elif current[question_type] > required:
            overgenerated[question_type] = current[question_type] - required
    
    return missing, current, overgenerated


def merge_questions(existing_result, new_result, missing_requirements):
    """Merge only the needed questions into existing result with strict limits enforcement"""
    requirements_map = {
        'multiple_choice_true_false': ['multiple_choice', 'true_false'],
        'fill_blank': ['fill_blank'],
        'short_answer': ['short_answer'],
        'free_recall': ['free_recall']
    }
    
    # Define absolute maximum limits per type
    absolute_limits = {
        'multiple_choice_true_false': 3,
        'fill_blank': 2,
        'short_answer': 2,
        'free_recall': 1
    }
    
    for requirement_type, needed_count in missing_requirements.items():
        if needed_count <= 0:
            continue
            
        question_types = requirements_map[requirement_type]
        remaining_needed = needed_count
        
        # Check current count for this requirement type
        current_count = 0
        for qtype in question_types:
            current_count += len(existing_result.get(qtype, []))
        
        # Don't exceed absolute limit
        max_allowed_to_add = absolute_limits[requirement_type] - current_count
        remaining_needed = min(remaining_needed, max_allowed_to_add)
        
        if remaining_needed <= 0:
            logger.info(f"✓ Skipping {requirement_type} - already at limit ({current_count}/{absolute_limits[requirement_type]})")
            continue
        
        for question_type in question_types:
            if remaining_needed <= 0:
                break
                
            if question_type not in new_result or not new_result[question_type]:
                continue
                
            # Initialize if doesn't exist
            if question_type not in existing_result:
                existing_result[question_type] = []
            
            # Get next ID for this question type
            next_id = len(existing_result[question_type]) + 1
            
            # Add only the needed number of questions, respecting limits
            questions_to_add = min(remaining_needed, len(new_result[question_type]))
            
            for i in range(questions_to_add):
                question = new_result[question_type][i].copy()
                question['id'] = str(next_id + i)
                existing_result[question_type].append(question)
                remaining_needed -= 1
                
                logger.info(f"✓ Added {question_type} question (ID: {question['id']})")
    
    # Update total count
    total = sum(len(existing_result.get(qtype, [])) for qtype in ['multiple_choice', 'true_false', 'fill_blank', 'short_answer', 'free_recall'])
    existing_result['total_questions'] = total
    
    # Final validation - ensure we don't exceed 8 total questions
    if total > 8:
        logger.warning(f"⚠️  Total questions ({total}) exceeds limit of 8 - this should not happen")
    
    return existing_result


def format_existing_questions_for_prompt(questions_result):
    """Format existing questions for use in prompt to avoid repetition"""
    previous_questions = []
    
    for question_type in ['multiple_choice', 'true_false', 'fill_blank', 'short_answer', 'free_recall']:
        if question_type in questions_result:
            for question in questions_result[question_type]:
                if 'text' in question:
                    previous_questions.append(f"- {question['text']}")
    
    if not previous_questions:
        return "None (first generation attempt)"
    
    return "\n".join(previous_questions)


def main():
    parser = argparse.ArgumentParser(description="Generate practice questions from educational content")
    parser.add_argument("content_file", help="Name of the content file (e.g., algebra_example.txt)")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium",
                       help="Difficulty level for questions (default: medium)")
    
    args = parser.parse_args()
    
    # Set up paths
    processed_dir = Path("content/processed")
    practice_dir = Path("content/generated/practice")
    
    content_file = processed_dir / args.content_file
    content_name = Path(args.content_file).stem
    questions_dir = practice_dir / content_name
    
    logger.info("=" * 60)
    logger.info("QUESTION GENERATOR STARTING")
    logger.info("=" * 60)
    logger.info(f"Content file: {content_file}")
    logger.info(f"Difficulty: {args.difficulty}")
    logger.info(f"Output directory: {questions_dir}")
    
    # Check if content file exists
    if not content_file.exists():
        logger.error(f"Content file not found: {content_file}")
        logger.error(f"Make sure the file exists in the processed directory.")
        return 1
    
    # Load content
    try:
        with open(content_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            logger.error(f"Content file is empty: {content_file}")
            return 1
            
        logger.info(f"Loaded content: {len(content)} characters")
        
    except Exception as e:
        logger.error(f"Error reading content file: {e}")
        return 1
    
    # Get student profile from centralized system
    student_profile = get_student_profile_for_questions(content, args.difficulty)
    
    logger.info(f"Student profile: {student_profile['student_name']}, {student_profile['student_age']} years, {student_profile['student_course']}")
    logger.info(f"Interests: {student_profile['student_interests']}")
    logger.info(f"Language: {student_profile['language']}")
    
    # Load previous questions
    previous_questions = load_previous_questions(questions_dir)
    student_profile["previous_questions"] = previous_questions
    
    if previous_questions != "None (first time generating questions for this content)":
        logger.info(f"Found previous questions - will avoid repetition")
    else:
        logger.info("No previous questions found - generating fresh set")
    
    # Initialize and load model
    logger.info("=" * 60)
    logger.info("LOADING MODEL")
    logger.info("=" * 60)
    
    try:
        service = create_model_service()
        if not service.load_model():
            logger.error("Failed to load model")
            return 1
        logger.info("✓ Model loaded successfully")
    except Exception as e:
        logger.error(f"Error initializing model service: {e}")
        return 1
    
    # Generate questions iteratively to meet requirements
    logger.info("=" * 60)
    logger.info("GENERATING QUESTIONS")
    logger.info("=" * 60)
    
    final_result = None
    generation_attempt = 1
    max_attempts = 3
    
    try:
        while generation_attempt <= max_attempts:
            logger.info(f"Generation attempt #{generation_attempt}")
            
            # Load prompt template
            prompt_template = service.load_prompt("generate_questions")
            
            # Generate questions with parser
            result = service.generate(
                prompt_template=prompt_template,
                variables=student_profile,
                parser_func=parse_questions
            )
            
            if not isinstance(result, dict) or "total_questions" not in result:
                logger.error(f"✗ Generation attempt #{generation_attempt} failed")
                generation_attempt += 1
                continue
            
            logger.info(f"✓ Generated {result['total_questions']} questions in attempt #{generation_attempt}")
            logger.info(f"  - Multiple choice: {len(result.get('multiple_choice', []))}")
            logger.info(f"  - True/False: {len(result.get('true_false', []))}")
            logger.info(f"  - Fill blank: {len(result.get('fill_blank', []))}")
            logger.info(f"  - Short answer: {len(result.get('short_answer', []))}")
            logger.info(f"  - Free recall: {len(result.get('free_recall', []))}")
            
            # Merge with previous results if this isn't the first attempt
            if final_result is not None:
                # Get current missing requirements before merging
                missing_before_merge, _, overgenerated_before = check_question_requirements(final_result)
                
                # If we already have overgeneration, don't merge more
                if overgenerated_before:
                    logger.warning(f"⚠️  Already overgenerated: {overgenerated_before}. Skipping merge.")
                else:
                    final_result = merge_questions(final_result, result, missing_before_merge)
                    logger.info(f"✓ Merged needed questions. Total now: {final_result['total_questions']}")
            else:
                final_result = result
            
            # Check if we have all required questions
            missing, current, overgenerated = check_question_requirements(final_result)
            
            # Log overgeneration if detected
            if overgenerated:
                logger.warning(f"⚠️  Overgeneration detected: {overgenerated}")
                logger.info("Consider stopping generation as requirements may be satisfied")
            
            # Early stop if we have exactly 8 questions (perfect result)
            if final_result['total_questions'] == 8 and not missing:
                logger.info("✓ Perfect result: exactly 8 questions generated!")
                break
            
            # Early stop if we already have overgeneration (prevent further accumulation)
            if overgenerated and final_result['total_questions'] >= 8:
                logger.warning("⚠️  Stopping due to overgeneration. Using current result.")
                break
            
            if not missing:
                logger.info("✓ All required questions generated!")
                break
            else:
                logger.info(f"Still missing: {missing}")
                
                # Prevent infinite loops - if we already have 8+ questions, something is wrong
                if final_result['total_questions'] >= 8:
                    logger.error("❌ Already have 8+ questions but still missing some types. Stopping to prevent overgeneration.")
                    break
                
                # Update student profile with existing questions to avoid repetition
                student_profile["previous_questions"] = format_existing_questions_for_prompt(final_result)
                
                # Create a focused prompt for missing questions
                missing_description = []
                if missing.get('multiple_choice_true_false', 0) > 0:
                    missing_description.append(f"{missing['multiple_choice_true_false']} multiple choice or true/false")
                if missing.get('fill_blank', 0) > 0:
                    missing_description.append(f"{missing['fill_blank']} fill-in-the-blank")
                if missing.get('short_answer', 0) > 0:
                    missing_description.append(f"{missing['short_answer']} short answer")
                if missing.get('free_recall', 0) > 0:
                    missing_description.append(f"{missing['free_recall']} free recall")
                
                logger.info(f"🔄 Generating missing questions: {', '.join(missing_description)}")
                generation_attempt += 1
        
        if final_result is None:
            logger.error("✗ All generation attempts failed")
            return 1
            
        # Save questions using UUID system
        saved_question_uuids = save_questions_uuid(final_result, questions_dir, content_file, args.difficulty)
        
        logger.info("=" * 60)
        logger.info("GENERATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"✓ {len(saved_question_uuids)} questions saved with UUID system")
        logger.info(f"✓ Final totals:")
        logger.info(f"  - Multiple choice: {len(final_result.get('multiple_choice', []))}")
        logger.info(f"  - True/False: {len(final_result.get('true_false', []))}")
        logger.info(f"  - Fill blank: {len(final_result.get('fill_blank', []))}")
        logger.info(f"  - Short answer: {len(final_result.get('short_answer', []))}")
        logger.info(f"  - Free recall: {len(final_result.get('free_recall', []))}")
        logger.info(f"  - Total: {final_result['total_questions']} questions")
        logger.info(f"Directory: {questions_dir}")
        logger.info(f"Registry: {questions_dir}/questions_registry.json")
        
        return 0
            
    except Exception as e:
        logger.error(f"Error during question generation: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())