"""
Centralized Student Profile Management

This module provides a unified way to access student profile data across all services.
Priority order:
1. profile.json file (if exists)
2. Environment variables  
3. Consistent default values
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

def get_current_student_profile() -> Dict[str, Any]:
    """
    Get the current student profile from profile.json only
    
    Returns:
        dict: Student profile with consistent structure or None if no profile exists
    """
    try:
        # Only try to load from profile.json
        profile_path = Path("profile.json")
        if profile_path.exists():
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
                
            # Debug logging for student creation investigation
            logging.info(f"🔍 Loading profile.json from: {profile_path.absolute()}")
            logging.info(f"📄 Raw profile data: {profile_data}")
                
            # Convert profile.json structure to expected format
            if profile_data:
                converted_profile = {
                    'student_name': profile_data.get('name', 'Student'),
                    'student_age': str(profile_data.get('age', 12)),
                    'student_course': profile_data.get('grade', '7th grade'),
                    'student_interests': profile_data.get('interests', 'learning'),
                    'language': profile_data.get('language', 'English'),
                    'student_id': profile_data.get('id', ''),
                    'completed_onboarding': profile_data.get('completed_onboarding', False)
                }
                logging.info(f"✓ Loaded student profile from profile.json: {profile_data.get('name', 'Unknown')}")
                logging.info(f"🔄 Converted profile structure: {converted_profile}")
                return converted_profile
    
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logging.warning(f"Could not load profile.json: {e}")
    
    # No profile available - return None to trigger onboarding
    logging.info("No profile.json found - onboarding required")
    return None


def get_student_profile_for_content_generation(content: str) -> Dict[str, Any]:
    """
    Get student profile formatted for content generation templates
    
    Args:
        content (str): The educational content to be processed
        
    Returns:
        dict: Profile with content included, ready for template substitution
    """
    profile = get_current_student_profile()
    
    # If no profile exists, return None to indicate onboarding is needed
    if profile is None:
        return None
    
    # Add content and ensure all required fields are present
    return {
        'content': content,
        'student_name': profile['student_name'],
        'student_age': profile['student_age'],
        'student_course': profile['student_course'], 
        'student_interests': profile['student_interests'],
        'language': profile['language']
    }


def get_student_profile_for_questions(content: str, difficulty_level: str = "medium") -> Dict[str, Any]:
    """
    Get student profile formatted for question generation
    
    Args:
        content (str): The educational content
        difficulty_level (str): Question difficulty level
        
    Returns:
        dict: Profile with content and difficulty, ready for question generation
    """
    profile = get_student_profile_for_content_generation(content)
    
    # If no profile exists, return None to indicate onboarding is needed
    if profile is None:
        return None
        
    profile['difficulty_level'] = difficulty_level
    return profile


def get_student_profile_for_challenges(content_sources: list, combined_content: str) -> Dict[str, Any]:
    """
    Get student profile formatted for challenge generation
    
    Args:
        content_sources (list): List of content source names
        combined_content (str): Combined content from all sources
        
    Returns:
        dict: Profile with challenge-specific fields
    """
    profile = get_current_student_profile()
    
    # If no profile exists, return None to indicate onboarding is needed
    if profile is None:
        return None
    
    return {
        'content': combined_content,
        'content_sources': ", ".join(content_sources),
        'is_interdisciplinary': len(content_sources) > 1,
        'student_name': profile['student_name'],
        'student_age': profile['student_age'],
        'student_course': profile['student_course'],
        'student_interests': profile['student_interests'],
        'language': profile['language']
    }


def log_current_profile():
    """Log the current student profile for debugging purposes"""
    profile = get_current_student_profile()
    if profile is None:
        logging.info("No student profile available - onboarding required")
    else:
        logging.info("Current Student Profile:")
        for key, value in profile.items():
            logging.info(f"  {key}: {value}")