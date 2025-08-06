"""
Module for parsing model outputs with XML-based structured formats for tutor-app.
Specifically designed for parsing student performance reports with simplified XML structure.

Structure:
<report>
  <executive_summary>...</executive_summary>
  <findings>...</findings>  
  <progression>...</progression>  
  <recommendations>...</recommendations>  
  <priority_focus>...</priority_focus>  
  <notes>...</notes>
</report>

All sections contain narrative text, no nested sub-tags.
"""

import logging
import re
from typing import Dict, Optional, Any, List, Tuple

logger = logging.getLogger(__name__)

# Common typos mapping for XML tags that Gemma frequently makes
COMMON_TAG_TYPOS = {
    # Recommendations variants
    'recommendaions': 'recommendations',
    'recommendaion': 'recommendations', 
    'recomendations': 'recommendations',
    'recomendaions': 'recommendations',
    'recommendtions': 'recommendations',
    'recomendtions': 'recommendations',
    'reccommendations': 'recommendations',
    'reccomendations': 'recommendations',
    
    # Progression variants
    'progrression': 'progression',
    'progresion': 'progression',
    'progresssion': 'progression',
    'progreesion': 'progression',
    'progresion': 'progression',
    'progresstion': 'progression',
    
    # Executive Summary variants
    'executiv_summary': 'executive_summary',
    'executive_sumary': 'executive_summary',
    'executiv_sumary': 'executive_summary',
    'executive_summry': 'executive_summary',
    'executve_summary': 'executive_summary',
    'executiv_summery': 'executive_summary',
    
    # Priority Focus variants
    'priorit_focus': 'priority_focus',
    'priority_focuss': 'priority_focus',
    'priortiy_focus': 'priority_focus',
    'priority_foccus': 'priority_focus',
    'priorty_focus': 'priority_focus',
    'prioritie_focus': 'priority_focus',
    
    # Findings variants
    'findinggs': 'findings',
    'findigns': 'findings',
    'finidngs': 'findings',
    'findngs': 'findings',
    'findingss': 'findings',
    
    # Notes variants
    'notess': 'notes',
    'nots': 'notes',
    'noets': 'notes',
    'note': 'notes'
}

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def find_similar_tags(response_str: str, target_tag: str, max_distance: int = 2) -> List[Tuple[str, int]]:
    """Find XML tags similar to target_tag using fuzzy matching"""
    # Find all XML tags in the response
    tag_pattern = r'</?(\w+)>'
    found_tags = re.findall(tag_pattern, response_str.lower())
    
    similar_tags = []
    for tag in set(found_tags):  # Remove duplicates
        distance = levenshtein_distance(tag.lower(), target_tag.lower())
        if distance <= max_distance and distance > 0:  # Similar but not exact
            similar_tags.append((tag, distance))
    
    # Sort by distance (closest first)
    similar_tags.sort(key=lambda x: x[1])
    return similar_tags

def find_best_tag_match(response_str: str, target_tag: str) -> Tuple[Optional[str], Optional[str]]:
    """Find the best matching tag for target_tag, handling typos and mismatches
    
    Returns:
        Tuple of (actual_tag_found, correction_type) where correction_type can be:
        None (exact match), 'typo', 'fuzzy', 'variant'
    """
    
    # Step 1: Check exact match first
    if f'<{target_tag}>' in response_str.lower():
        return target_tag, None
    
    # Step 2: Check common typos mapping
    target_lower = target_tag.lower()
    for typo, correct in COMMON_TAG_TYPOS.items():
        if correct == target_lower and f'<{typo}>' in response_str.lower():
            logger.info(f"Found common typo: '{typo}' -> '{correct}'")
            return typo, 'typo'
    
    # Step 3: Use fuzzy matching for similar tags
    similar_tags = find_similar_tags(response_str, target_tag, max_distance=2)
    if similar_tags:
        best_match, distance = similar_tags[0]
        logger.info(f"Found fuzzy match for '{target_tag}': '{best_match}' (distance: {distance})")
        return best_match, 'fuzzy'
    
    # Step 4: Try to find mismatched opening/closing tags
    opening_pattern = rf'<({target_tag}[\w]*?)>'
    closing_pattern = rf'</(\w*?{target_tag}[\w]*?)>'
    
    opening_matches = re.findall(opening_pattern, response_str, re.IGNORECASE)
    closing_matches = re.findall(closing_pattern, response_str, re.IGNORECASE)
    
    if opening_matches or closing_matches:
        # Find the most common variant
        all_variants = opening_matches + closing_matches
        if all_variants:
            best_variant = max(set(all_variants), key=all_variants.count)
            logger.info(f"Found tag variant for '{target_tag}': '{best_variant}'")
            return best_variant, 'variant'
    
    return None, None

def parse_simple_xml_tag(response_str: str, tag_name: str) -> Optional[str]:
    """
    Parse a simple XML tag from model response with resilience to typos
    
    Args:
        response_str: Model response string
        tag_name: Name of the XML tag to extract
        
    Returns:
        Extracted content or None if parsing failed
    """
    try:
        # First try exact match
        start_tag = f"<{tag_name}>"
        end_tag = f"</{tag_name}>"
        
        start_index = response_str.find(start_tag)
        end_index = response_str.find(end_tag)
        
        if start_index != -1 and end_index != -1:
            start_index += len(start_tag)
            content = response_str[start_index:end_index].strip()
            return content if content else None
        
        # If exact match failed, try resilient matching
        logger.info(f'Exact match failed for <{tag_name}>, trying resilient matching...')
        
        # Find the best matching tag variant
        actual_tag, correction_type = find_best_tag_match(response_str, tag_name)
        if not actual_tag:
            logger.warning(f'No matching tag found for <{tag_name}> even with fuzzy matching')
            return None
        
        # Log the correction if one was made
        if correction_type:
            logger.info(f"Applied {correction_type} correction: <{tag_name}> found as <{actual_tag}>")
        
        # Try to extract with the found variant
        return extract_content_with_mismatched_tags(response_str, actual_tag, tag_name)
        
    except Exception as e:
        logger.error(f'Error parsing tag <{tag_name}>: {e}')
        return None

def extract_content_with_mismatched_tags(response_str: str, actual_tag: str, target_tag: str) -> Optional[str]:
    """Extract content even when opening and closing tags might be different"""
    try:
        # Try with the actual tag found
        start_tag = f"<{actual_tag}>"
        end_tag = f"</{actual_tag}>"
        
        start_index = response_str.find(start_tag)
        end_index = response_str.find(end_tag)
        
        if start_index != -1 and end_index != -1:
            start_index += len(start_tag)
            content = response_str[start_index:end_index].strip()
            logger.info(f'Successfully extracted <{target_tag}> content using tag variant <{actual_tag}>')
            return content if content else None
        
        # If that didn't work, try to find any reasonable boundaries
        # Look for opening tag variants
        opening_pattern = rf'<{re.escape(actual_tag)}[^>]*?>'
        opening_match = re.search(opening_pattern, response_str, re.IGNORECASE)
        
        if not opening_match:
            return None
        
        start_index = opening_match.end()
        
        # Look for any closing tag that might match
        possible_closing_tags = [
            f"</{actual_tag}>",
            f"</{target_tag}>",  # Try the target tag as closing
        ]
        
        # Add variations from the typo mapping
        for typo, correct in COMMON_TAG_TYPOS.items():
            if correct.lower() == target_tag.lower():
                possible_closing_tags.append(f"</{typo}>")
        
        best_end_index = -1
        best_closing_tag = None
        
        for closing_tag in possible_closing_tags:
            end_index = response_str.find(closing_tag, start_index)
            if end_index != -1:
                if best_end_index == -1 or end_index < best_end_index:
                    best_end_index = end_index
                    best_closing_tag = closing_tag
        
        if best_end_index != -1:
            content = response_str[start_index:best_end_index].strip()
            logger.info(f'Extracted <{target_tag}> content with mismatched tags: {opening_match.group()} ... {best_closing_tag}')
            return content if content else None
        
        logger.warning(f'Could not find suitable closing tag for <{target_tag}>')
        return None
        
    except Exception as e:
        logger.error(f'Error extracting content with mismatched tags: {e}')
        return None

def check_report_tags_present(response_str: str) -> bool:
    """Check if report tags are present, with resilience to typos"""
    # Check for exact match first
    if '<report>' in response_str.lower() and '</report>' in response_str.lower():
        return True
    
    # Check for common typos
    report_variants = ['report', 'repoort', 'repport', 'reporrt']
    
    for variant in report_variants:
        if f'<{variant}>' in response_str.lower() and f'</{variant}>' in response_str.lower():
            logger.info(f"Found report tags with variant: {variant}")
            return True
    
    # Check for partial matches (mismatched opening/closing)
    opening_pattern = r'<(repo[rpt]+)>'
    closing_pattern = r'</(repo[rpt]+)>'
    
    opening_matches = re.findall(opening_pattern, response_str.lower())
    closing_matches = re.findall(closing_pattern, response_str.lower())
    
    if opening_matches or closing_matches:
        logger.info(f"Found partial report tags: opening={opening_matches}, closing={closing_matches}")
        return True
    
    return False

def extract_all_xml_tags(response_str: str) -> List[str]:
    """Extract all XML tags from response for debugging purposes"""
    tag_pattern = r'</?(\w+)[^>]*?>'
    all_tags = re.findall(tag_pattern, response_str.lower())
    return list(set(all_tags))  # Remove duplicates

def generate_parsing_report(report_data: Dict[str, Any], parsing_corrections: List[Tuple[str, str]]) -> str:
    """Generate a detailed report of parsing success and corrections made"""
    lines = []
    lines.append("=" * 50)
    lines.append("PARSER RESILIENCE REPORT")
    lines.append("=" * 50)
    
    if parsing_corrections:
        lines.append(f"🔧 CORRECTIONS MADE: {len(parsing_corrections)}")
        lines.append("-" * 30)
        for original, corrected in parsing_corrections:
            lines.append(f"  '{original}' → '{corrected}'")
        lines.append("")
    
    lines.append(f"📊 SECTIONS PARSED: {len(report_data)}")
    lines.append("-" * 30)
    for section, content in report_data.items():
        content_length = len(content) if isinstance(content, str) else 0
        status = "✓" if content_length > 0 else "✗"
        lines.append(f"  {status} {section}: {content_length} chars")
    
    lines.append("")
    lines.append("=" * 50)
    return "\n".join(lines)

def parse_nested_xml_tags(response_str: str, parent_tag: str) -> Dict[str, str]:
    """
    DEPRECATED: Parse nested XML tags within a parent tag
    
    This function is deprecated as the new XML structure uses simple narrative text
    instead of nested tags. Kept for backward compatibility only.
    
    Args:
        response_str: Model response string
        parent_tag: Parent tag containing nested tags
        
    Returns:
        Dictionary with nested tag contents
    """
    logger.warning(f"parse_nested_xml_tags is deprecated. Use parse_simple_xml_tag for tag '{parent_tag}'")
    result = {}
    
    try:
        # Extract parent tag content
        parent_content = parse_simple_xml_tag(response_str, parent_tag)
        if not parent_content:
            return result
        
        # Find all nested tags
        tag_pattern = r'<(\w+)>(.*?)</\1>'
        matches = re.findall(tag_pattern, parent_content, re.DOTALL)
        
        for tag_name, content in matches:
            result[tag_name] = content.strip()
            
    except Exception as e:
        logger.error(f'Error parsing nested tags in <{parent_tag}>: {e}')
    
    return result

def parse_student_report(response_str: str) -> Optional[Dict[str, Any]]:
    """
    Parse student performance report from model response with simplified XML structure
    
    Expected structure:
    <report>
      <executive_summary>...</executive_summary>
      <findings>...</findings>  
      <progression>...</progression>  
      <recommendations>...</recommendations>  
      <priority_focus>...</priority_focus>  
      <notes>...</notes>
    </report>
    
    All sections contain narrative text, no nested sub-tags.
    
    Args:
        response_str: Raw model response containing XML report
        
    Returns:
        Structured dictionary with report data or None if parsing failed
    """
    try:
        logger.info("Parsing student performance report with simplified XML structure...")
        
        # Check if response contains report tags (with resilience)
        if not check_report_tags_present(response_str):
            logger.error("No <report> tags found in response")
            return None
        
        report_data = {}
        
        # Parse all sections as simple narrative text
        sections = ['executive_summary', 'findings', 'progression', 'recommendations', 'priority_focus', 'notes']
        parsing_stats = {'successful': 0, 'failed': 0, 'typo_corrected': 0}
        
        for section in sections:
            logger.debug(f"Attempting to parse section: {section}")
            content = parse_simple_xml_tag(response_str, section)
            
            if content:
                report_data[section] = content.strip()
                parsing_stats['successful'] += 1
                logger.debug(f"✓ Successfully parsed {section} ({len(content)} chars)")
            else:
                parsing_stats['failed'] += 1
                logger.debug(f"✗ Failed to parse {section}")
        
        # Log parsing statistics
        logger.info(f"Parsing stats: {parsing_stats['successful']} successful, {parsing_stats['failed']} failed")
        
        # Validate that we have essential sections
        required_sections = ['executive_summary', 'findings', 'progression', 'recommendations', 'priority_focus']
        present_sections = [sec for sec in required_sections if sec in report_data and report_data[sec]]
        missing_sections = [sec for sec in required_sections if sec not in present_sections]
        
        if missing_sections:
            logger.warning(f"Missing required sections: {missing_sections}")
            # Log available tags to help debug
            available_tags = extract_all_xml_tags(response_str)
            logger.info(f"Available XML tags in response: {available_tags}")
        
        # Check if we have any meaningful data
        if not report_data or len(present_sections) < 2:
            logger.error("Insufficient data parsed from report")
            # Show a snippet of the response for debugging
            response_snippet = response_str[:500] + "..." if len(response_str) > 500 else response_str
            logger.debug(f"Response snippet: {response_snippet}")
            return None
        
        logger.info(f"Successfully parsed report with {len(present_sections)}/{len(required_sections)} required sections")
        return report_data
        
    except Exception as e:
        logger.error(f'Error parsing student report: {e}')
        return None

def check_report_requirements(report_data: Dict[str, Any]) -> List[str]:
    """
    Check which required sections are missing from the report (simplified structure)
    
    Args:
        report_data: Parsed report dictionary
        
    Returns:
        List of missing section names
    """
    required_sections = ['executive_summary', 'findings', 'progression', 'recommendations', 'priority_focus']
    missing = []
    
    for section in required_sections:
        if section not in report_data or not report_data[section]:
            missing.append(section)
        elif not isinstance(report_data[section], str) or not report_data[section].strip():
            # All sections should be non-empty strings in the new structure
            missing.append(section)
    
    return missing

def merge_report_sections(existing_report: Dict[str, Any], new_report: Dict[str, Any], missing_sections: List[str]) -> Dict[str, Any]:
    """
    Merge only the missing sections from new report into existing report
    
    Args:
        existing_report: Current report data
        new_report: New report data with potentially missing sections
        missing_sections: List of section names that are missing
        
    Returns:
        Updated report with merged sections
    """
    for section in missing_sections:
        if section in new_report and new_report[section]:
            existing_report[section] = new_report[section]
            logger.info(f"✓ Merged missing section: {section}")
    
    return existing_report

def validate_report_completeness(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and assess completeness of parsed report data with simplified structure
    
    Args:
        report_data: Parsed report dictionary
        
    Returns:
        Validation results with completeness score and missing elements
    """
    try:
        required_sections = [
            'executive_summary',
            'findings',
            'progression', 
            'recommendations',
            'priority_focus'
        ]
        
        present_sections = []
        missing_sections = check_report_requirements(report_data)
        
        for section in required_sections:
            if section not in missing_sections:
                present_sections.append(section)
        
        completeness_score = len(present_sections) / len(required_sections) * 100
        
        # Content quality analysis for simplified structure
        content_analysis = {}
        
        for section in present_sections:
            if section in report_data:
                content = report_data[section]
                word_count = len(content.split()) if isinstance(content, str) else 0
                char_count = len(content) if isinstance(content, str) else 0
                
                content_analysis[section] = {
                    'word_count': word_count,
                    'char_count': char_count,
                    'has_content': word_count > 10  # Minimum meaningful content
                }
        
        # Check for optional notes section
        if 'notes' in report_data and report_data['notes']:
            content_analysis['notes'] = {
                'word_count': len(report_data['notes'].split()),
                'char_count': len(report_data['notes']),
                'has_content': len(report_data['notes'].split()) > 5
            }
        
        return {
            'completeness_score': round(completeness_score, 1),
            'present_sections': present_sections,
            'missing_sections': missing_sections,
            'content_analysis': content_analysis,
            'is_valid': completeness_score >= 80,  # At least 80% complete for simplified structure
            'total_sections': len(required_sections)
        }
        
    except Exception as e:
        logger.error(f'Error validating report completeness: {e}')
        return {
            'completeness_score': 0,
            'present_sections': [],
            'missing_sections': [],
            'content_analysis': {},
            'is_valid': False,
            'error': str(e)
        } 