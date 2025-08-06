"""
Module for parsing model outputs with XML-based structured formats.
"""

import logging
import re

def parse_simple_xml_tag(response_str, tag_name):
    """
    Parse a simple XML tag from model response
    
    Args:
        response_str (str): Model response string
        tag_name (str): Name of the XML tag to extract
        
    Returns:
        str or None: Extracted content or None if parsing failed
    """
    try:
        start_tag = f"<{tag_name}>"
        end_tag = f"</{tag_name}>"
        
        start_index = response_str.find(start_tag)
        end_index = response_str.find(end_tag)
        
        if start_index == -1 or end_index == -1:
            logging.error(f'Tags <{tag_name}> not found in response')
            return None
            
        start_index += len(start_tag)
        content = response_str[start_index:end_index].strip()
        
        return content if content else None
        
    except Exception as e:
        logging.error(f'Error parsing {tag_name}: {e}')
        return None



def parse_evaluation_response(response_str):
    """
    Parse evaluation response with multiple criteria
    
    Expected XML structure:
    <evaluation>
        <score>85</score>
        <strengths>Strong points</strengths>
        <weaknesses>Areas for improvement</weaknesses>
        <recommendations>Suggestions</recommendations>
    </evaluation>
    
    Args:
        response_str (str): Model response string
        
    Returns:
        dict or None: Parsed evaluation with score, strengths, weaknesses, recommendations
    """
    try:
        # Find the evaluation block
        eval_match = re.search(r'<evaluation>(.*?)</evaluation>', response_str, re.DOTALL)
        
        if not eval_match:
            logging.error('Tag <evaluation> not found in response')
            return None
            
        eval_content = eval_match.group(1)
        
        # Extract score (numeric)
        score_str = parse_simple_xml_tag(eval_content, "score")
        try:
            score = int(score_str) if score_str else None
        except ValueError:
            score = None
        
        # Extract text fields
        strengths = parse_simple_xml_tag(eval_content, "strengths")
        weaknesses = parse_simple_xml_tag(eval_content, "weaknesses")
        recommendations = parse_simple_xml_tag(eval_content, "recommendations")
        
        # Validate required fields
        if score is None or not strengths:
            logging.error('Missing required fields in evaluation response')
            return None
        
        return {
            'score': score,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommendations': recommendations
        }
        
    except Exception as e:
        logging.error(f'Error parsing evaluation_response: {e}')
        return None


def parse_question_answer_pairs(response_str):
    """
    Parse question-answer pairs from model response
    
    Expected XML structure:
    <qa_pairs>
        <qa>
            <question>What is...?</question>
            <answer>The answer is...</answer>
        </qa>
        <qa>
            <question>How does...?</question>
            <answer>It works by...</answer>
        </qa>
    </qa_pairs>
    
    Args:
        response_str (str): Model response string
        
    Returns:
        list or None: List of dicts with question/answer pairs
    """
    try:
        # Find the qa_pairs block
        qa_match = re.search(r'<qa_pairs>(.*?)</qa_pairs>', response_str, re.DOTALL)
        
        if not qa_match:
            logging.error('Tag <qa_pairs> not found in response')
            return None
            
        qa_content = qa_match.group(1)
        
        # Find all qa blocks
        qa_matches = re.finditer(r'<qa>(.*?)</qa>', qa_content, re.DOTALL)
        
        qa_pairs = []
        for qa_match in qa_matches:
            qa_block = qa_match.group(1)
            
            question = parse_simple_xml_tag(qa_block, "question")
            answer = parse_simple_xml_tag(qa_block, "answer")
            
            if question and answer:
                qa_pairs.append({
                    'question': question,
                    'answer': answer
                })
        
        if not qa_pairs:
            logging.error('No valid QA pairs found')
            return None
        
        return qa_pairs
        
    except Exception as e:
        logging.error(f'Error parsing question_answer_pairs: {e}')
        return None


def parse_classification_response(response_str):
    """
    Parse classification response with category and confidence
    
    Expected XML structure:
    <classification>
        <category>Mathematics</category>
        <subcategory>Algebra</subcategory>
        <confidence>0.95</confidence>
        <reasoning>The content discusses...</reasoning>
    </classification>
    
    Args:
        response_str (str): Model response string
        
    Returns:
        dict or None: Parsed classification with category, subcategory, confidence, reasoning
    """
    try:
        # Find the classification block
        class_match = re.search(r'<classification>(.*?)</classification>', response_str, re.DOTALL)
        
        if not class_match:
            logging.error('Tag <classification> not found in response')
            return None
            
        class_content = class_match.group(1)
        
        # Extract fields
        category = parse_simple_xml_tag(class_content, "category")
        subcategory = parse_simple_xml_tag(class_content, "subcategory")
        reasoning = parse_simple_xml_tag(class_content, "reasoning")
        
        # Extract confidence (float)
        confidence_str = parse_simple_xml_tag(class_content, "confidence")
        try:
            confidence = float(confidence_str) if confidence_str else None
        except ValueError:
            confidence = None
        
        # Validate required fields
        if not category:
            logging.error('Missing required category in classification response')
            return None
        
        return {
            'category': category,
            'subcategory': subcategory,
            'confidence': confidence,
            'reasoning': reasoning
        }
        
    except Exception as e:
        logging.error(f'Error parsing classification_response: {e}')
        return None


def _parse_sections_intelligently(content, max_sections=10):
    """
    Intelligent section parser that handles both properly closed and unclosed section tags
    
    Strategy:
    1. Find all <section_X> opening tags
    2. For each section, try to find corresponding </section_X> closing tag
    3. If closing tag exists: use content between tags (standard behavior)
    4. If closing tag missing: use content from opening tag to next section or end
    5. Renumber sections sequentially 1, 2, 3, ... N
    
    Args:
        content (str): Content within textbook/story wrapper tags
        max_sections (int): Maximum number of sections to look for
        
    Returns:
        list: List of section dictionaries with sequential numbering
    """
    import re
    
    sections = []
    
    # Find all section opening tags with their numbers
    section_pattern = r'<section_(\d+)>'
    section_matches = list(re.finditer(section_pattern, content))
    
    if not section_matches:
        return sections
    
    for i, match in enumerate(section_matches):
        section_num = int(match.group(1))
        start_pos = match.end()  # Position after opening tag
        
        # Try to find corresponding closing tag
        closing_tag = f"</section_{section_num}>"
        closing_pos = content.find(closing_tag, start_pos)
        
        if closing_pos != -1:
            # Found closing tag - use standard extraction
            section_content = content[start_pos:closing_pos].strip()
        else:
            # No closing tag - extract to next section or end
            if i + 1 < len(section_matches):
                # Extract to next section
                next_section_start = section_matches[i + 1].start()
                section_content = content[start_pos:next_section_start].strip()
            else:
                # Extract to end of content
                section_content = content[start_pos:].strip()
        
        # Clean up content (remove any remaining tags)
        section_content = re.sub(r'</?section_\d+>', '', section_content).strip()
        
        if section_content:
            sections.append({
                'section_number': len(sections) + 1,  # Sequential numbering starting from 1
                'content': section_content
            })
    
    return sections


def parse_educational_textbook(response_str):
    """
    Parse educational textbook response with intelligent section handling
    
    Handles both properly formatted and malformed section tags:
    - <section_1>Content</section_1> (properly closed)
    - <section_1>Content<section_2> (unclosed, content extracted to next section)
    
    Args:
        response_str (str): Model response string
        
    Returns:
        dict or None: Parsed textbook with sequentially numbered sections
    """
    try:
        # Find the textbook block
        textbook_match = re.search(r'<textbook>(.*?)</textbook>', response_str, re.DOTALL)
        
        if not textbook_match:
            logging.error('Tag <textbook> not found in response - triggering retry')
            return None
            
        textbook_content = textbook_match.group(1)
        
        # Use intelligent section parsing
        sections = _parse_sections_intelligently(textbook_content)
        
        if not sections:
            logging.error('No textbook sections found - triggering retry')
            return None
        
        logging.info(f'✓ Parsed {len(sections)} textbook sections (intelligently handled)')
        
        return {
            'type': 'textbook',
            'total_sections': len(sections),
            'sections': sections
        }
        
    except Exception as e:
        logging.error(f'Exception parsing educational_textbook: {e} - triggering retry')
        return None


def parse_educational_story(response_str):
    """
    Parse educational story response with intelligent section handling
    
    Handles both properly formatted and malformed section tags:
    - <section_1>Content</section_1> (properly closed)
    - <section_1>Content<section_2> (unclosed, content extracted to next section)
    
    Args:
        response_str (str): Model response string
        
    Returns:
        dict or None: Parsed story with sequentially numbered sections
    """
    try:
        # Find the story block
        story_match = re.search(r'<story>(.*?)</story>', response_str, re.DOTALL)
        
        if not story_match:
            logging.error('Tag <story> not found in response - triggering retry')
            return None
            
        story_content = story_match.group(1)
        
        # Use intelligent section parsing
        sections = _parse_sections_intelligently(story_content)
        
        if not sections:
            logging.error('No story sections found - triggering retry')
            return None
        
        logging.info(f'✓ Parsed {len(sections)} story sections (intelligently handled)')
        
        return {
            'type': 'story',
            'total_sections': len(sections),
            'sections': sections
        }
        
    except Exception as e:
        logging.error(f'Exception parsing educational_story: {e} - triggering retry')
        return None


def parse_questions(response_str):
    """
    Parse questions response with different question types (simplified XML)
    
    Expected XML structure:
    <questions>
        <multiple_choice>
            <question>
                <text>Question text</text>
                <options>
                    <option_a>Option A</option_a>
                    <option_b>Option B</option_b>
                    <option_c>Option C</option_c>
                    <option_d>Option D</option_d>
                </options>
                <answer>a</answer>
            </question>
        </multiple_choice>
        <true_false>
            <question>
                <text>True/false statement</text>
                <answer>true</answer>
            </question>
        </true_false>
        <fill_blank>
            <question>
                <text>Text with _____ blank</text>
                <answer>correct answer</answer>
            </question>
        </fill_blank>
        <short_answer>
            <question>
                <text>Short answer question</text>
                <answer>Expected answer</answer>
            </question>
        </short_answer>
        <free_recall>
            <question>
                <text>Free recall question</text>
                <answer>Expected comprehensive answer</answer>
            </question>
        </free_recall>
    </questions>
    
    Args:
        response_str (str): Model response string
        
    Returns:
        dict or None: Parsed questions organized by type
    """
    try:
        # Use the entire response as content (no wrapper tag needed)
        questions_content = response_str
        
        result = {
            'type': 'questions',
            'multiple_choice': [],
            'true_false': [],
            'fill_blank': [],
            'short_answer': [],
            'free_recall': []
        }
        
        # Parse multiple choice questions
        mc_match = re.search(r'<multiple_choice>(.*?)</multiple_choice>', questions_content, re.DOTALL)
        if mc_match:
            result['multiple_choice'] = _parse_multiple_choice_questions(mc_match.group(1))
        
        # Parse true/false questions
        tf_match = re.search(r'<true_false>(.*?)</true_false>', questions_content, re.DOTALL)
        if tf_match:
            result['true_false'] = _parse_true_false_questions(tf_match.group(1))
        
        # Parse fill blank questions
        fb_match = re.search(r'<fill_blank>(.*?)</fill_blank>', questions_content, re.DOTALL)
        if fb_match:
            result['fill_blank'] = _parse_fill_blank_questions(fb_match.group(1))
        
        # Parse short answer questions
        sa_match = re.search(r'<short_answer>(.*?)</short_answer>', questions_content, re.DOTALL)
        if sa_match:
            result['short_answer'] = _parse_short_answer_questions(sa_match.group(1))
        
        # Parse free recall questions
        fr_match = re.search(r'<free_recall>(.*?)</free_recall>', questions_content, re.DOTALL)
        if fr_match:
            result['free_recall'] = _parse_free_recall_questions(fr_match.group(1))
        
        # Calculate totals
        total_questions = (len(result['multiple_choice']) + len(result['true_false']) + 
                          len(result['fill_blank']) + len(result['short_answer']) + 
                          len(result['free_recall']))
        
        if total_questions == 0:
            logging.error('No questions found in any category')
            return None
        
        result['total_questions'] = total_questions
        return result
        
    except Exception as e:
        logging.error(f'Error parsing questions: {e}')
        return None


def _validate_multiple_choice_question(question_data):
    """
    Validate a multiple choice question to ensure correct_answer exists in options
    
    Args:
        question_data (dict): Question dictionary with 'options' and 'correct_answer'
        
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    options = question_data.get('options', {})
    correct_answer = question_data.get('correct_answer', '')
    
    if not options:
        return False, "No options provided"
    
    if not correct_answer:
        return False, "No correct answer provided"
    
    # Check if correct_answer exists as a key in options
    if correct_answer not in options:
        available_keys = list(options.keys())
        return False, f"Correct answer '{correct_answer}' not found in available options {available_keys}"
    
    # Check if the option value is not empty
    if not options[correct_answer]:
        return False, f"Option '{correct_answer}' exists but has empty content"
    
    return True, None


def _parse_multiple_choice_questions(content):
    """Parse multiple choice questions from content with validation"""
    questions = []
    question_matches = re.finditer(r'<question>(.*?)</question>', content, re.DOTALL)
    
    total_parsed = 0
    valid_questions = 0
    invalid_questions = 0
    
    for i, match in enumerate(question_matches, 1):
        question_content = match.group(1)
        total_parsed += 1
        
        text = parse_simple_xml_tag(question_content, "text")
        correct_answer = parse_simple_xml_tag(question_content, "answer")
        
        # Parse options
        options_match = re.search(r'<options>(.*?)</options>', question_content, re.DOTALL)
        options = {}
        if options_match:
            option_content = options_match.group(1)
            options['a'] = parse_simple_xml_tag(option_content, "option_a")
            options['b'] = parse_simple_xml_tag(option_content, "option_b")
            options['c'] = parse_simple_xml_tag(option_content, "option_c")
            options['d'] = parse_simple_xml_tag(option_content, "option_d")
            # Remove None values
            options = {k: v for k, v in options.items() if v}
        
        if text and correct_answer and options:
            # Create question data for validation
            question_data = {
                'id': str(i),
                'text': text,
                'options': options,
                'correct_answer': correct_answer,
                'type': 'multiple_choice'
            }
            
            # Validate the question
            is_valid, error_message = _validate_multiple_choice_question(question_data)
            
            if is_valid:
                questions.append(question_data)
                valid_questions += 1
                logging.info(f"✓ Multiple choice question {i} validated successfully")
            else:
                invalid_questions += 1
                logging.warning(f"✗ Multiple choice question {i} failed validation: {error_message}")
                logging.warning(f"  Question text: {text[:100]}...")
                logging.warning(f"  Available options: {list(options.keys())}")
                logging.warning(f"  Correct answer: '{correct_answer}'")
        else:
            invalid_questions += 1
            missing_fields = []
            if not text: missing_fields.append("text")
            if not correct_answer: missing_fields.append("correct_answer") 
            if not options: missing_fields.append("options")
            logging.warning(f"✗ Multiple choice question {i} missing required fields: {missing_fields}")
    
    # Log summary statistics
    if total_parsed > 0:
        logging.info(f"Multiple choice parsing summary: {valid_questions}/{total_parsed} questions valid ({invalid_questions} discarded)")
    
    return questions


def _parse_true_false_questions(content):
    """Parse true/false questions from content"""
    questions = []
    question_matches = re.finditer(r'<question>(.*?)</question>', content, re.DOTALL)
    
    for i, match in enumerate(question_matches, 1):
        question_content = match.group(1)
        
        text = parse_simple_xml_tag(question_content, "text")
        correct_answer = parse_simple_xml_tag(question_content, "answer")
        
        if text and correct_answer:
            questions.append({
                'id': str(i),
                'text': text,
                'correct_answer': correct_answer.lower() == 'true',
                'type': 'true_false'
            })
    
    return questions


def _parse_fill_blank_questions(content):
    """Parse fill in the blank questions from content"""
    questions = []
    question_matches = re.finditer(r'<question>(.*?)</question>', content, re.DOTALL)
    
    for i, match in enumerate(question_matches, 1):
        question_content = match.group(1)
        
        text = parse_simple_xml_tag(question_content, "text")
        correct_answer = parse_simple_xml_tag(question_content, "answer")
        
        if text and correct_answer:
            questions.append({
                'id': str(i),
                'text': text,
                'correct_answer': correct_answer,
                'type': 'fill_blank'
            })
    
    return questions


def _parse_short_answer_questions(content):
    """Parse short answer questions from content"""
    questions = []
    question_matches = re.finditer(r'<question>(.*?)</question>', content, re.DOTALL)
    
    for i, match in enumerate(question_matches, 1):
        question_content = match.group(1)
        
        text = parse_simple_xml_tag(question_content, "text")
        sample_answer = parse_simple_xml_tag(question_content, "answer")
        
        if text and sample_answer:
            questions.append({
                'id': str(i),
                'text': text,
                'sample_answer': sample_answer,
                'type': 'short_answer'
            })
    
    return questions


def _parse_free_recall_questions(content):
    """Parse free recall questions from content"""
    questions = []
    question_matches = re.finditer(r'<question>(.*?)</question>', content, re.DOTALL)
    
    for i, match in enumerate(question_matches, 1):
        question_content = match.group(1)
        
        text = parse_simple_xml_tag(question_content, "text")
        sample_answer = parse_simple_xml_tag(question_content, "answer")
        
        if text and sample_answer:
            questions.append({
                'id': str(i),
                'text': text,
                'sample_answer': sample_answer,
                'type': 'free_recall'
            })
    
    return questions


def parse_challenges(response_str):
    """
    Parse challenges response for experimental activities
    
    Expected XML structure:
    <challenges>
        <challenge>
            <title>Challenge title</title>
            <description>Detailed instructions</description>
            <learning_goals>Educational objectives</learning_goals>
            <deliverables>Expected outputs</deliverables>
        </challenge>
    </challenges>
    
    Args:
        response_str (str): Model response string
        
    Returns:
        dict or None: Parsed challenges organized by structure
    """
    try:
        # Use the entire response as content (no wrapper tag needed)
        challenges_content = response_str
        
        result = {
            'type': 'challenges',
            'challenges': []
        }
        
        # Parse challenge sections
        challenge_match = re.search(r'<challenges>(.*?)</challenges>', challenges_content, re.DOTALL)
        if challenge_match:
            challenges_section = challenge_match.group(1)
            
            # Find all individual challenges
            challenge_matches = re.finditer(r'<challenge>(.*?)</challenge>', challenges_section, re.DOTALL)
            
            for i, match in enumerate(challenge_matches, 1):
                challenge_content = match.group(1)
                
                title = parse_simple_xml_tag(challenge_content, "title")
                description = parse_simple_xml_tag(challenge_content, "description")
                learning_goals = parse_simple_xml_tag(challenge_content, "learning_goals")
                deliverables = parse_simple_xml_tag(challenge_content, "deliverables")
                
                if title and description and learning_goals and deliverables:
                    result['challenges'].append({
                        'id': str(i),
                        'title': title,
                        'description': description,
                        'learning_goals': learning_goals,
                        'deliverables': deliverables,
                        'type': 'experimental_challenge'
                    })
        
        if not result['challenges']:
            logging.error('No valid challenges found')
            return None
        
        result['total_challenges'] = len(result['challenges'])
        return result
        
    except Exception as e:
        logging.error(f'Error parsing challenges: {e}')
        return None


def parse_content_summary(response_str):
    """
    Simple parser for content summary - just verify it contains summary content
    
    Args:
        response_str (str): Model response string
        
    Returns:
        str or None: The full response if valid, None if empty/invalid
    """
    try:
        # Just check if response contains summary tag and has content
        if '<summary>' in response_str and len(response_str.strip()) > 20:
            return response_str.strip()
        else:
            logging.error('No valid summary content found')
            return None
        
    except Exception as e:
        logging.error(f'Error parsing content summary: {e}')
        return None


def parse_answer_evaluation(response_str):
    """
    Parse AI answer evaluation response
    
    Expected XML structure:
    <is_correct>yes or no</is_correct>
    <feedback>message</feedback>
    
    Returns:
        dict: Dictionary with 'is_correct' (bool) and 'feedback' (str)
        None: If parsing fails (triggers retry in model_service)
    """
    try:
        # Validate response is not empty or too short
        if not response_str or len(response_str.strip()) < 10:
            logging.error("Response too short or empty for evaluation - triggering retry")
            return None
        
        # Extract required tags
        is_correct_str = parse_simple_xml_tag(response_str, 'is_correct')
        feedback = parse_simple_xml_tag(response_str, 'feedback')
        
        # If either required tag is missing, fail to trigger retry
        if not is_correct_str:
            logging.error("Missing <is_correct> tag - triggering retry")
            return None
            
        if not feedback:
            logging.error("Missing <feedback> tag - triggering retry") 
            return None
        
        # Validate is_correct content
        is_correct_clean = is_correct_str.lower().strip()
        if is_correct_clean not in ['yes', 'no', 'sí', 'si', 'true', 'false', '1', '0']:
            logging.error(f"Invalid is_correct value: '{is_correct_str}' - triggering retry")
            return None
        
        # All validations passed - build result
        result = {
            'is_correct': is_correct_clean in ['yes', 'sí', 'si', 'true', '1'],
            'feedback': feedback.strip()
        }
        
        logging.info(f"✓ Successfully parsed answer evaluation: correct={result['is_correct']}, feedback_length={len(result['feedback'])}")
        return result
        
    except Exception as e:
        logging.error(f'Exception parsing answer evaluation: {e} - triggering retry')
        return None


def parse_challenge_feedback(response_str):
    """
    Parse challenge feedback from model response
    
    Expected XML structure:
    <challenge_feedback>
        <strengths>What the student did well</strengths>
        <areas_for_improvement>Areas that could be enhanced</areas_for_improvement>
        <suggestions>Concrete suggestions for improvement</suggestions>
        <overall_assessment>Overall evaluation</overall_assessment>
        <ready_to_submit>yes or no</ready_to_submit>
    </challenge_feedback>
    
    Args:
        response_str (str): Model response string
        
    Returns:
        dict or None: Parsed feedback structure
    """
    try:
        logging.info("Starting challenge feedback parsing")
        
        # Find the challenge_feedback block
        feedback_match = re.search(r'<challenge_feedback>(.*?)</challenge_feedback>', response_str, re.DOTALL)
        
        if not feedback_match:
            logging.error('Tag <challenge_feedback> not found in response')
            return None
            
        feedback_content = feedback_match.group(1)
        logging.info("Found challenge_feedback block")
        
        # Extract each component
        delivered = parse_simple_xml_tag(feedback_content, 'delivered')
        strengths = parse_simple_xml_tag(feedback_content, 'strengths')
        areas_for_improvement = parse_simple_xml_tag(feedback_content, 'areas_for_improvement')
        suggestions = parse_simple_xml_tag(feedback_content, 'suggestions')
        overall_assessment = parse_simple_xml_tag(feedback_content, 'overall_assessment')
        ready_to_submit_str = parse_simple_xml_tag(feedback_content, 'ready_to_submit')
        
        if not all([delivered, strengths, areas_for_improvement, suggestions, overall_assessment, ready_to_submit_str]):
            logging.error('Missing required fields in challenge feedback')
            return None
        
        # Parse ready_to_submit as boolean
        ready_to_submit = ready_to_submit_str.lower().strip() == 'yes'
        
        result = {
            'delivered': delivered.strip(),
            'strengths': strengths.strip(),
            'areas_for_improvement': areas_for_improvement.strip(),
            'suggestions': suggestions.strip(),
            'overall_assessment': overall_assessment.strip(),
            'ready_to_submit': ready_to_submit
        }
        
        logging.info(f"✓ Successfully parsed challenge feedback: ready_to_submit={ready_to_submit}")
        return result
        
    except Exception as e:
        logging.error(f'Exception parsing challenge feedback: {e} - triggering retry')
        return None


def parse_discovery_initial(response_str):
    """
    Parse discovery initial response from photo + question with internal answers
    
    Expected XML structure:
    <discovery_initial>
        <subject_identified>Brief description of what is shown in image</subject_identified>
        <learning_intent>What the student wants to understand</learning_intent>
        <internal_answers>
            <option_1>First most likely answer</option_1>
            <option_2>Second most likely answer</option_2>
            <option_3>Third most likely answer</option_3>
            <option_4>Fourth most likely answer</option_4>
            <option_5>Fifth most likely answer</option_5>
        </internal_answers>
        <contextual_intro>Enthusiastic introduction</contextual_intro>
        <guiding_questions>
            <question_1>First guiding question</question_1>
            <question_2>Second question</question_2>
            <question_3>Third question</question_3>
            <question_4>Fourth question</question_4>
        </guiding_questions>
    </discovery_initial>
    
    Args:
        response_str (str): Model response string
        
    Returns:
        dict or None: Parsed discovery initial structure
    """
    try:
        logging.info("Starting discovery initial parsing")
        
        # Find the discovery_initial block
        initial_match = re.search(r'<discovery_initial>(.*?)</discovery_initial>', response_str, re.DOTALL)
        
        if not initial_match:
            logging.error('Tag <discovery_initial> not found in response')
            return None
            
        initial_content = initial_match.group(1)
        logging.info("Found discovery_initial block")
        
        # Extract main components
        subject_identified = parse_simple_xml_tag(initial_content, 'subject_identified')
        learning_intent = parse_simple_xml_tag(initial_content, 'learning_intent')
        contextual_intro = parse_simple_xml_tag(initial_content, 'contextual_intro')
        
        # Extract internal answers
        internal_answers = []
        answers_match = re.search(r'<internal_answers>(.*?)</internal_answers>', initial_content, re.DOTALL)
        
        if answers_match:
            answers_content = answers_match.group(1)
            for i in range(1, 6):  # option_1 to option_5
                option = parse_simple_xml_tag(answers_content, f'option_{i}')
                if option:
                    internal_answers.append(option.strip())
        
        # Extract guiding questions
        questions = []
        questions_match = re.search(r'<guiding_questions>(.*?)</guiding_questions>', initial_content, re.DOTALL)
        
        if questions_match:
            questions_content = questions_match.group(1)
            for i in range(1, 5):  # question_1 to question_4
                question = parse_simple_xml_tag(questions_content, f'question_{i}')
                if question:
                    questions.append(question.strip())
        
        # Validate required fields
        if not all([subject_identified, learning_intent, contextual_intro]) or not questions or not internal_answers:
            logging.error('Missing required fields in discovery initial')
            missing = []
            if not subject_identified: missing.append('subject_identified')
            if not learning_intent: missing.append('learning_intent')
            if not contextual_intro: missing.append('contextual_intro')
            if not questions: missing.append('guiding_questions')
            if not internal_answers: missing.append('internal_answers')
            logging.error(f'Missing fields: {missing}')
            return None
        
        result = {
            'subject_identified': subject_identified.strip(),
            'learning_intent': learning_intent.strip(),
            'contextual_intro': contextual_intro.strip(),
            'internal_answers': internal_answers,
            'guiding_questions': questions
        }
        
        logging.info(f"✓ Successfully parsed discovery initial: {len(questions)} questions, {len(internal_answers)} internal answers")
        return result
        
    except Exception as e:
        logging.error(f'Exception parsing discovery initial: {e} - triggering retry')
        return None


def parse_discovery_question(response_str):
    """
    Parse discovery question response for button-based question flow
    
    Expected XML structure:
    <discovery_question>
        <encouragement>Brief positive acknowledgment of question choice</encouragement>
        <guiding_questions>
            <question_1>Follow-up question building on selected question</question_1>
            <question_2>Second question focusing on distinguishing characteristics</question_2>
            <question_3>Third question about specific details</question_3>
            <question_4>Fourth question encouraging closer examination</question_4>
        </guiding_questions>
    </discovery_question>
    
    Args:
        response_str (str): Model response string
        
    Returns:
        dict or None: Parsed discovery question structure
    """
    try:
        logging.info("Starting discovery question parsing")
        
        # Find the discovery_question block
        question_match = re.search(r'<discovery_question>(.*?)</discovery_question>', response_str, re.DOTALL)
        
        if not question_match:
            logging.error('Tag <discovery_question> not found in response')
            return None
            
        question_content = question_match.group(1)
        logging.info("Found discovery_question block")
        
        # Extract main components
        encouragement = parse_simple_xml_tag(question_content, 'encouragement')
        
        # Extract guiding questions
        questions = []
        questions_match = re.search(r'<guiding_questions>(.*?)</guiding_questions>', question_content, re.DOTALL)
        
        if questions_match:
            questions_content = questions_match.group(1)
            for i in range(1, 5):  # question_1 to question_4
                question = parse_simple_xml_tag(questions_content, f'question_{i}')
                if question:
                    questions.append(question.strip())
        
        # Validate required fields
        if not encouragement or not questions:
            logging.error('Missing required fields in discovery question')
            missing = []
            if not encouragement: missing.append('encouragement')
            if not questions: missing.append('guiding_questions')
            logging.error(f'Missing fields: {missing}')
            return None
        
        result = {
            'encouragement': encouragement.strip(),
            'guiding_questions': questions
        }
        
        logging.info(f"✓ Successfully parsed discovery question: {len(questions)} questions generated")
        return result
        
    except Exception as e:
        logging.error(f'Exception parsing discovery question: {e} - triggering retry')
        return None


def parse_discovery_reveal(response_str):
    """
    Parse discovery reveal response for final answer options
    
    Expected XML structure:
    <discovery_reveal>
        <conclusion_intro>Encouraging message about investigation</conclusion_intro>
        <answer_options>
            <option_1>
                <name>First possible answer</name>
                <description>Detailed description</description>
            </option_1>
            <option_2>
                <name>Second possible answer</name>
                <description>Detailed description</description>
            </option_2>
            <option_3>
                <name>Third possible answer</name>
                <description>Detailed description</description>
            </option_3>
            <option_4>
                <name>Fourth possible answer</name>
                <description>Detailed description</description>
            </option_4>
            <option_5>
                <name>Fifth possible answer</name>
                <description>Detailed description</description>
            </option_5>
        </answer_options>
        <completion_message>Encouraging message about discovery process</completion_message>
    </discovery_reveal>
    
    Args:
        response_str (str): Model response string
        
    Returns:
        dict or None: Parsed discovery reveal structure
    """
    try:
        logging.info("Starting discovery reveal parsing")
        
        # Find the discovery_reveal block
        reveal_match = re.search(r'<discovery_reveal>(.*?)</discovery_reveal>', response_str, re.DOTALL)
        
        if not reveal_match:
            logging.error('Tag <discovery_reveal> not found in response')
            return None
            
        reveal_content = reveal_match.group(1)
        logging.info("Found discovery_reveal block")
        
        # Extract main components
        conclusion_intro = parse_simple_xml_tag(reveal_content, 'conclusion_intro')
        completion_message = parse_simple_xml_tag(reveal_content, 'completion_message')
        
        # Extract answer options
        options = []
        options_match = re.search(r'<answer_options>(.*?)</answer_options>', reveal_content, re.DOTALL)
        
        if options_match:
            options_content = options_match.group(1)
            for i in range(1, 6):  # option_1 to option_5
                option_match = re.search(f'<option_{i}>(.*?)</option_{i}>', options_content, re.DOTALL)
                if option_match:
                    option_content = option_match.group(1)
                    name = parse_simple_xml_tag(option_content, 'name')
                    description = parse_simple_xml_tag(option_content, 'description')
                    
                    if name and description:
                        options.append({
                            'name': name.strip(),
                            'description': description.strip()
                        })
        
        # Validate required fields
        if not conclusion_intro or not completion_message or not options:
            logging.error('Missing required fields in discovery reveal')
            missing = []
            if not conclusion_intro: missing.append('conclusion_intro')
            if not completion_message: missing.append('completion_message')
            if not options: missing.append('answer_options')
            logging.error(f'Missing fields: {missing}')
            return None
        
        result = {
            'conclusion_intro': conclusion_intro.strip(),
            'answer_options': options,
            'completion_message': completion_message.strip()
        }
        
        logging.info(f"✓ Successfully parsed discovery reveal: {len(options)} answer options")
        return result
        
    except Exception as e:
        logging.error(f'Exception parsing discovery reveal: {e} - triggering retry')
        return None


# Registry of available parsers
PARSERS = {
    'simple_xml': parse_simple_xml_tag,
    'evaluation': parse_evaluation_response,
    'qa_pairs': parse_question_answer_pairs,
    'classification': parse_classification_response,
    'educational_textbook': parse_educational_textbook,
    'educational_story': parse_educational_story,
    'questions': parse_questions,
    'challenges': parse_challenges,
    'content_summary': parse_content_summary,
    'answer_evaluation': parse_answer_evaluation,
    'challenge_feedback': parse_challenge_feedback,
    'discovery_initial': parse_discovery_initial,
    'discovery_question': parse_discovery_question,
    'discovery_reveal': parse_discovery_reveal
}

def get_parser(parser_name):
    """
    Get parser function by name
    
    Args:
        parser_name (str): Name of the parser
        
    Returns:
        callable or None: Parser function
    """
    return PARSERS.get(parser_name)