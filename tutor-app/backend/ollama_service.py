"""
Ollama Model Service for Tutor App
Provides AI-powered student performance analysis using Gemma3n via Ollama
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logging.warning("Ollama not available. Install with: pip install ollama")

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging handlers based on environment
handlers = [logging.StreamHandler()]  # Always include console output
if os.getenv("ENABLE_MODEL_LOG_FILE", "true").lower() == "true":
    handlers.append(logging.FileHandler('logs/model_interactions.log'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

class OllamaService:
    """Service for generating student performance reports using Ollama + Gemma3n"""
    
    def __init__(self, model_name: str = "gemma3n"):
        """
        Initialize Ollama service
        
        Args:
            model_name: Name of the Ollama model to use (default: gemma3n)
        """
        if not OLLAMA_AVAILABLE:
            raise ImportError("Ollama library not available. Install with: pip install ollama")
        
        self.model_name = model_name
        self.client = ollama.AsyncClient()
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.timeout = 300  # 5 minutes timeout for complex analysis
        
        logger.info(f"Initialized Ollama service with model: {model_name}")
    
    async def generate(self, prompt_template: str, variables: Optional[Dict[str, Any]] = None, 
                      parser_func: Optional[callable] = None, max_retries: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate text using Ollama model with template substitution and parsing
        
        Args:
            prompt_template: Template string with {variable} placeholders
            variables: Dictionary of variables to substitute in template
            parser_func: Optional function to parse the model response
            max_retries: Number of retry attempts
            
        Returns:
            Dictionary with generated content and metadata
        """
        start_time = datetime.now()
        retries = max_retries or self.max_retries
        variables = variables or {}
        
        # Substitute variables in prompt template
        try:
            prompt = prompt_template.format(**variables)
            logger.info(prompt)  # Log the formatted prompt
        except KeyError as e:
            logger.error(f"Missing variable in prompt template: {e}")
            return {"success": False, "error": f"Missing variable: {e}"}
        
        for attempt in range(retries + 1):
            try:
                logger.info(f"Generating with Ollama model: {self.model_name} (attempt {attempt + 1}/{retries + 1})")
                
                # Generate response with Ollama
                max_tokens = int(os.getenv("OLLAMA_MAX_TOKENS", "4096"))
                response = await self.client.generate(
                    model=self.model_name,
                    prompt=prompt,
                    options={
                        'temperature': 0.7,
                        'top_p': 0.9,
                        'repeat_penalty': 1.1,
                        'num_predict': max_tokens  # Increase from default 128 to allow complete reports
                    }
                )
                
                raw_response = response['response']
                logger.info(raw_response)  # Log the raw response
                generation_time = (datetime.now() - start_time).total_seconds()
                
                logger.info(f"Generation completed in {generation_time:.2f}s")
                logger.debug(f"Raw response length: {len(raw_response)} characters")
                
                # Parse response if parser function provided
                parsed_result = None
                if parser_func:
                    try:
                        parsed_result = parser_func(raw_response)
                        if parsed_result:
                            logger.info("Response parsed successfully")
                        else:
                            logger.warning("Parser returned None or empty result")
                            if attempt < retries:
                                logger.info(f"Retrying due to failed parsing (attempt {attempt + 1}/{retries + 1})")
                                continue
                    except Exception as parse_error:
                        logger.error(f"Parser error: {parse_error}")
                        if attempt < retries:
                            logger.info(f"Retrying due to parser error (attempt {attempt + 1}/{retries + 1})")
                            continue
                
                return {
                    "success": True,
                    "response": raw_response,
                    "parsed": parsed_result,
                    "model": self.model_name,
                    "generation_time": generation_time,
                    "attempt": attempt + 1
                }
                
            except Exception as e:
                logger.error(f"Ollama generation error (attempt {attempt + 1}): {e}")
                if attempt < retries:
                    logger.info(f"Retrying in 2 seconds...")
                    await asyncio.sleep(2)
                    continue
                else:
                    return {
                        "success": False,
                        "error": str(e),
                        "model": self.model_name,
                        "attempts": retries + 1
                    }
        
        return {"success": False, "error": "Max retries exceeded"}
    
    async def generate_student_report(self, student_logs: str, student_id: str, student_name: str) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report for a student based on their xAPI logs
        
        Args:
            student_logs: Raw xAPI log content from student.log
            student_id: Student identifier
            student_name: Student display name
            
        Returns:
            Dictionary with report data and metadata
        """
        try:
            # Load prompt template
            prompt_file = Path(__file__).parent / "prompts" / "student_performance_report.txt"
            if not prompt_file.exists():
                logger.error(f"Prompt template not found: {prompt_file}")
                return {"success": False, "error": "Prompt template not found"}
            
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            # Import parser functions
            from parsers import parse_student_report, check_report_requirements, merge_report_sections
            
            # Prepare variables with new report_language
            variables = {
                "student_id": student_id,
                "student_name": student_name,
                "student_logs": student_logs,
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "log_length": len(student_logs),
                "report_language": os.getenv("REPORT_LANGUAGE", "English")
            }
            
            # Generate report with retry system for missing sections
            logger.info(f"Generating performance report for student {student_id} ({student_name})")
            
            final_result = None
            generation_attempt = 1
            max_attempts = self.max_retries
            
            while generation_attempt <= max_attempts:
                logger.info(f"Report generation attempt #{generation_attempt}")
                
                # Generate report
                result = await self.generate(
                    prompt_template=prompt_template,
                    variables=variables,
                    parser_func=parse_student_report,
                    max_retries=1  # Single retry per call, manual control here
                )
                
                if not result["success"] or not result.get("parsed"):
                    logger.error(f"✗ Generation attempt #{generation_attempt} failed")
                    generation_attempt += 1
                    continue
                
                logger.info(f"✓ Generated report data in attempt #{generation_attempt}")
                
                # Merge with previous results if this isn't the first attempt
                if final_result is not None:
                    # Get current missing requirements before merging
                    missing_before_merge = check_report_requirements(final_result)
                    
                    if missing_before_merge:
                        final_result = merge_report_sections(final_result, result["parsed"], missing_before_merge)
                        logger.info(f"✓ Merged report sections. Missing before: {missing_before_merge}")
                    else:
                        # No missing sections, we're done
                        break
                else:
                    final_result = result["parsed"]
                
                # Check if we have all required sections
                missing_sections = check_report_requirements(final_result)
                
                if not missing_sections:
                    logger.info("✓ All required report sections generated!")
                    break
                else:
                    logger.info(f"Still missing sections: {missing_sections}")
                    generation_attempt += 1
            
            if final_result is None:
                logger.error("✗ All report generation attempts failed")
                result = {"success": False, "error": "All generation attempts failed"}
            else:
                # Create successful result with final merged data
                result = {
                    "success": True,
                    "parsed": final_result,
                    "raw_response": "Multiple attempts merged",
                    "generation_attempts": generation_attempt
                }
            
            if result["success"]:
                logger.info(f"Successfully generated performance report for {student_id}")
                return {
                    **result,
                    "student_id": student_id,
                    "student_name": student_name,
                    "report_date": datetime.now().isoformat()
                }
            else:
                logger.error(f"Failed to generate report for {student_id}: {result.get('error')}")
                return result
                
        except Exception as e:
            logger.error(f"Error generating student report: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_connection(self) -> bool:
        """
        Test connection to Ollama service
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Testing Ollama connection with model: {self.model_name}")
            response = await self.client.generate(
                model=self.model_name,
                prompt="Test connection. Respond with 'OK'.",
                options={'temperature': 0}
            )
            
            is_ok = 'OK' in response['response'].upper()
            logger.info(f"Ollama connection test: {'SUCCESS' if is_ok else 'FAILED'}")
            return is_ok
            
        except Exception as e:
            logger.error(f"Ollama connection test failed: {e}")
            return False

# Global instance
ollama_service = OllamaService()