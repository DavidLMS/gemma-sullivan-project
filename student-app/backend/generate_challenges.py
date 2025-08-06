#!/usr/bin/env python3
"""
Interdisciplinary Challenge Generator Script
Generates experimental challenges that combine multiple educational contents.

Usage:
    python generate_challenges.py <content_file1.txt> [content_file2.txt] [content_file3.txt] [...]

Examples:
    python generate_challenges.py algebra_example.txt
    python generate_challenges.py algebra_example.txt physics_motion.txt
    python generate_challenges.py math_geometry.txt science_plants.txt history_ancient.txt
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
from parsers import parse_challenges, parse_content_summary
from student_profile import get_student_profile_for_challenges

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


def summarize_content(content, content_name, service, student_profile):
    """Summarize individual content for challenge generation"""
    try:
        logger.info(f"📄 Summarizing {content_name}...")
        
        # Prepare variables for summarization
        summary_variables = {
            "content": content,
            "content_name": content_name,
            "student_age": student_profile["student_age"],
            "student_course": student_profile["student_course"],
            "language": student_profile["language"]
        }
        
        # Load summarization prompt
        summary_prompt = service.load_prompt("summarize_for_challenges")
        
        # Generate summary
        summary_result = service.generate(
            prompt_template=summary_prompt,
            variables=summary_variables,
            parser_func=parse_content_summary,
            max_tokens=1000,  # Keep summaries concise
            max_retries=2
        )
        
        if summary_result:
            logger.info(f"✓ Summarized {content_name}: {len(summary_result)} characters")
            return summary_result
        else:
            logger.warning(f"✗ Failed to summarize {content_name}, using original content")
            return f"=== {content_name.upper()} CONTENT ===\n{content}"
            
    except Exception as e:
        logger.error(f"Error summarizing {content_name}: {e}")
        return f"=== {content_name.upper()} CONTENT ===\n{content}"


def load_multiple_contents(content_files, processed_dir, service=None, student_profile=None):
    """Load and optionally summarize multiple content files"""
    combined_contents = []
    content_names = []
    
    # Determine if we should use summarization (multiple files)
    use_summarization = len(content_files) > 1 and service is not None
    
    if use_summarization:
        logger.info("🔄 Multiple contents detected - activating summarization preprocessing")
    
    for content_file_name in content_files:
        content_file = processed_dir / content_file_name
        content_name = Path(content_file_name).stem
        
        if not content_file.exists():
            logger.error(f"Content file not found: {content_file}")
            continue
            
        try:
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            if not content:
                logger.warning(f"Content file is empty: {content_file}")
                continue
            
            logger.info(f"Loaded {content_name}: {len(content)} characters")
            
            if use_summarization:
                # Summarize for efficiency
                processed_content = summarize_content(content, content_name, service, student_profile)
            else:
                # Use full content for single file
                processed_content = f"=== {content_name.upper()} CONTENT ===\n{content}"
            
            combined_contents.append(processed_content)
            content_names.append(content_name)
                
        except Exception as e:
            logger.error(f"Error reading {content_file}: {e}")
    
    if not combined_contents:
        return None, []
    
    return "\n\n".join(combined_contents), content_names


def load_previous_challenges(challenges_dir):
    """Load all previously generated challenges from UUID-based system to avoid repetition"""
    previous_challenges = []
    
    # Check if registry exists
    registry_file = challenges_dir / "challenges_registry.json"
    if not registry_file.exists():
        return "None (first time generating challenges for this content combination)"
    
    try:
        with open(registry_file, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        
        # Load challenges from individual UUID files
        challenges_subdir = challenges_dir / "challenges"
        if not challenges_subdir.exists():
            return "None (no challenges found)"
            
        for challenge_uuid, challenge_info in registry.get("challenges", {}).items():
            challenge_file = challenges_subdir / f"{challenge_uuid}.json"
            if challenge_file.exists():
                try:
                    with open(challenge_file, 'r', encoding='utf-8') as f:
                        challenge_data = json.load(f)
                    
                    title = challenge_data.get("title", "")
                    if title:
                        previous_challenges.append(title)
                        
                except Exception as e:
                    logger.warning(f"Could not load challenge from {challenge_file}: {e}")
    
    except Exception as e:
        logger.warning(f"Could not load challenges registry: {e}")
        return "None (error loading previous challenges)"
    
    if not previous_challenges:
        return "None (no valid previous challenges found)"
    
    return "\n".join([f"- {c}" for c in previous_challenges])




def ensure_challenges_structure(challenges_dir):
    """Ensure the UUID-based challenges directory structure exists"""
    challenges_dir.mkdir(parents=True, exist_ok=True)
    challenges_subdir = challenges_dir / "challenges"
    challenges_subdir.mkdir(parents=True, exist_ok=True)
    
    registry_file = challenges_dir / "challenges_registry.json"
    if not registry_file.exists():
        # Create initial registry
        initial_registry = {
            "metadata": {
                "created_at": datetime.now().isoformat()
            },
            "challenges": {}
        }
        with open(registry_file, 'w', encoding='utf-8') as f:
            json.dump(initial_registry, f, indent=2, ensure_ascii=False)
    
    return challenges_subdir, registry_file


def save_challenges_uuid(challenges_result, challenges_dir, content_names):
    """Save generated challenges using UUID-based system"""
    
    challenges_subdir, registry_file = ensure_challenges_structure(challenges_dir)
    
    # Load existing registry
    with open(registry_file, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    
    saved_challenges = []
    generation_timestamp = datetime.now().isoformat()
    
    # Process each challenge
    for challenge in challenges_result.get('challenges', []):
        # Generate UUID for this challenge
        challenge_uuid = str(uuid.uuid4())
        
        # Create individual challenge file
        challenge_data = {
            "uuid": challenge_uuid,
            "title": challenge.get("title", ""),
            "description": challenge.get("description", ""),
            "learning_goals": challenge.get("learning_goals", ""),
            "deliverables": challenge.get("deliverables", ""),
            "type": challenge.get("type", "experimental_challenge"),
            "source_contents": content_names,
            "interdisciplinary": len(content_names) > 1,
            "generated_at": generation_timestamp
        }
        
        # Save individual challenge file
        challenge_file = challenges_subdir / f"{challenge_uuid}.json"
        with open(challenge_file, 'w', encoding='utf-8') as f:
            json.dump(challenge_data, f, indent=2, ensure_ascii=False)
        
        # Add to registry
        registry["challenges"][challenge_uuid] = {
            "uuid": challenge_uuid,
            "title": challenge.get("title", "")[:100] + ("..." if len(challenge.get("title", "")) > 100 else ""),
            "type": challenge.get("type", "experimental_challenge"),
            "file": f"challenges/{challenge_uuid}.json",
            "generated_at": generation_timestamp,
            "source_contents": content_names,
            "interdisciplinary": len(content_names) > 1
        }
        
        saved_challenges.append(challenge_uuid)
        logger.info(f"✓ Saved challenge {challenge_uuid}: {challenge.get('title', 'Untitled')[:50]}...")
    
    # Update registry metadata
    registry["metadata"]["last_updated"] = generation_timestamp
    registry["metadata"]["total_challenges"] = len(registry["challenges"])
    registry["metadata"]["content_sources"] = content_names
    registry["metadata"]["interdisciplinary"] = len(content_names) > 1
    
    # Save updated registry
    with open(registry_file, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✓ Challenges registry updated: {len(saved_challenges)} challenges added")
    logger.info(f"✓ Registry file: {registry_file}")
    
    return saved_challenges


def check_challenge_requirements(challenges_result):
    """Check if we have the required number of challenges"""
    required_challenges = 5
    
    current_challenges = len(challenges_result.get('challenges', []))
    
    missing = max(0, required_challenges - current_challenges)
    
    return missing, current_challenges


def merge_challenges(existing_result, new_result, missing_count):
    """Merge only the needed challenges into existing result with proper ID numbering"""
    
    if missing_count <= 0:
        return existing_result
    
    # Initialize if doesn't exist
    if 'challenges' not in existing_result:
        existing_result['challenges'] = []
    
    # Get next ID
    next_id = len(existing_result['challenges']) + 1
    
    # Add only the needed number of challenges
    if 'challenges' in new_result and new_result['challenges']:
        challenges_to_add = min(missing_count, len(new_result['challenges']))
        
        for i in range(challenges_to_add):
            challenge = new_result['challenges'][i].copy()
            challenge['id'] = str(next_id + i)
            existing_result['challenges'].append(challenge)
    
    # Update total count
    existing_result['total_challenges'] = len(existing_result['challenges'])
    
    return existing_result


def format_existing_challenges_for_prompt(challenges_result):
    """Format existing challenges for use in prompt to avoid repetition"""
    previous_challenges = []
    
    if 'challenges' in challenges_result:
        for challenge in challenges_result['challenges']:
            if 'title' in challenge:
                previous_challenges.append(f"- {challenge['title']}")
    
    if not previous_challenges:
        return "None (first generation attempt)"
    
    return "\n".join(previous_challenges)


def main():
    parser = argparse.ArgumentParser(description="Generate interdisciplinary experimental challenges from educational content")
    parser.add_argument("content_files", nargs='+', help="Content files to combine (e.g., algebra.txt physics.txt)")
    
    args = parser.parse_args()
    
    # Set up paths
    processed_dir = Path("content/processed")
    experiment_dir = Path("content/generated/experiment")
    
    logger.info("=" * 60)
    logger.info("INTERDISCIPLINARY CHALLENGE GENERATOR STARTING")
    logger.info("=" * 60)
    logger.info(f"Content files: {args.content_files}")
    
    # Initialize and load model early for potential summarization
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
    
    # Get basic student profile for summarization
    from student_profile import get_current_student_profile
    basic_profile = get_current_student_profile()
    basic_student_profile = {
        "student_age": basic_profile["student_age"],
        "student_course": basic_profile["student_course"],
        "language": basic_profile["language"]
    }
    
    # Load and combine content files (with optional summarization)
    combined_content, content_names = load_multiple_contents(
        args.content_files, processed_dir, service, basic_student_profile
    )
    
    if not combined_content:
        logger.error("No valid content files found")
        return 1
    
    # Use single experiment directory for all challenges
    challenges_dir = experiment_dir
    
    logger.info(f"Combined {len(content_names)} content sources")
    logger.info(f"Total content: {len(combined_content)} characters")
    logger.info(f"Output directory: {challenges_dir}")
    
    if len(content_names) > 1:
        logger.info("🌟 Generating INTERDISCIPLINARY challenges!")
    else:
        logger.info("Generating single-subject challenges")
    
    # Get student profile from centralized system
    student_profile = get_student_profile_for_challenges(content_names, combined_content)
    
    logger.info(f"Student profile: {student_profile['student_name']}, {student_profile['student_age']} years, {student_profile['student_course']}")
    logger.info(f"Interests: {student_profile['student_interests']}")
    logger.info(f"Language: {student_profile['language']}")
    
    # Load previous challenges
    previous_challenges = load_previous_challenges(challenges_dir)
    student_profile["previous_challenges"] = previous_challenges
    
    if previous_challenges != "None (first time generating challenges for this content combination)":
        logger.info(f"Found previous challenges - will avoid repetition")
    else:
        logger.info("No previous challenges found - generating fresh set")
    
    # Generate challenges iteratively to meet requirements
    logger.info("=" * 60)
    logger.info("GENERATING CHALLENGES")
    logger.info("=" * 60)
    
    final_result = None
    generation_attempt = 1
    max_attempts = 3
    
    try:
        while generation_attempt <= max_attempts:
            logger.info(f"Generation attempt #{generation_attempt}")
            
            # Load prompt template
            prompt_template = service.load_prompt("generate_challenges")
            
            # Generate challenges with parser
            result = service.generate(
                prompt_template=prompt_template,
                variables=student_profile,
                parser_func=parse_challenges
            )
            
            if not isinstance(result, dict) or "total_challenges" not in result:
                logger.error(f"✗ Generation attempt #{generation_attempt} failed")
                generation_attempt += 1
                continue
            
            logger.info(f"✓ Generated {result['total_challenges']} challenges in attempt #{generation_attempt}")
            
            # Merge with previous results if this isn't the first attempt
            if final_result is not None:
                # Get current missing requirements before merging
                missing_before_merge, _ = check_challenge_requirements(final_result)
                final_result = merge_challenges(final_result, result, missing_before_merge)
                logger.info(f"✓ Merged needed challenges. Total now: {final_result['total_challenges']}")
            else:
                final_result = result
            
            # Check if we have all required challenges
            missing, current = check_challenge_requirements(final_result)
            
            if missing == 0:
                logger.info("✓ All required challenges generated!")
                break
            else:
                logger.info(f"Still missing: {missing} challenges")
                
                # Update student profile with existing challenges to avoid repetition
                student_profile["previous_challenges"] = format_existing_challenges_for_prompt(final_result)
                
                logger.info(f"🔄 Generating {missing} more challenges...")
                generation_attempt += 1
        
        if final_result is None:
            logger.error("✗ All generation attempts failed")
            return 1
            
        # Save challenges using UUID system
        saved_challenge_uuids = save_challenges_uuid(final_result, challenges_dir, content_names)
        
        logger.info("=" * 60)
        logger.info("GENERATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"✓ {len(saved_challenge_uuids)} challenges saved with UUID system")
        logger.info(f"✓ Final total: {final_result['total_challenges']} challenges")
        if len(content_names) > 1:
            logger.info(f"🌟 Interdisciplinary content: {', '.join(content_names)}")
        logger.info(f"Directory: {challenges_dir}")
        logger.info(f"Registry: {challenges_dir}/challenges_registry.json")
        
        return 0
            
    except Exception as e:
        logger.error(f"Error during challenge generation: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())