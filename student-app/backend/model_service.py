"""
Gemma Model Service
Multi-framework model loading and text generation service for educational content.
Supports both Transformers (PyTorch/MPS) and MLX frameworks.
"""

import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoProcessor
from datetime import datetime
import time
import os
import base64
import io
from pathlib import Path
from dotenv import load_dotenv
from abc import ABC, abstractmethod

# Try to import multimodal model class
try:
    from transformers import Gemma3nForConditionalGeneration
    GEMMA3N_AVAILABLE = True
except ImportError:
    GEMMA3N_AVAILABLE = False

# Image processing imports
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Try to import MLX dependencies
try:
    import mlx_vlm
    from mlx_vlm import load as mlx_load, generate as mlx_generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False

# Load environment variables
load_dotenv()

# Configure logging handlers based on environment
handlers = [logging.StreamHandler()]  # Always include console output
if os.getenv("ENABLE_MODEL_LOG_FILE", "true").lower() == "true":
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    # Add file handler for model interactions
    handlers.append(logging.FileHandler('logs/model_interactions.log'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)


def process_image_inputs(images):
    """
    Process various image input formats into PIL Images
    
    Args:
        images (list): List of images in various formats:
            - PIL Image objects
            - Base64 encoded strings (with or without data URL prefix)
            - File paths (str or Path objects)
            
    Returns:
        list: List of PIL Image objects
    """
    if not images or not PIL_AVAILABLE:
        logger.info("No images to process or PIL not available")
        return []
    
    processed_images = []
    # Starting to process image inputs
    
    for i, img in enumerate(images):
        # Processing image
        
        try:
            if isinstance(img, Image.Image):
                # Already a PIL Image
                processed_images.append(img)
                logger.info(f"✅ Image {i+1}: Already PIL Image, added successfully")
                
            elif isinstance(img, str):
                # Determine if it's base64 data or file path
                is_data_url = img.startswith('data:image')
                is_long_string = len(img) > 100  # Increased threshold for better base64 detection
                looks_like_base64 = all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in img.replace('\n', '').replace('\r', '')[:100])
                is_file_path = '/' in img or '\\' in img or img.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))
                
                # Image analysis completed
                
                if is_data_url:
                    # Base64 data URL format: data:image/png;base64,iVBORw0KGgoAAAA...
                    logger.info(f"📷 Image {i+1}: Processing as data URL")
                    base64_data = img.split(',', 1)[1]
                    img_data = base64.b64decode(base64_data)
                    pil_image = Image.open(io.BytesIO(img_data))
                    processed_images.append(pil_image)
                    logger.info(f"✅ Image {i+1}: Data URL processed successfully")
                    
                elif is_long_string and looks_like_base64 and not is_file_path:
                    # Try to decode as raw base64 string (canvas data without prefix)
                    logger.info(f"📷 Image {i+1}: Processing as raw base64 string")
                    try:
                        img_data = base64.b64decode(img)
                        pil_image = Image.open(io.BytesIO(img_data))
                        processed_images.append(pil_image)
                        logger.info(f"✅ Image {i+1}: Raw base64 processed successfully ({len(img)} chars)")
                    except Exception as e:
                        logger.warning(f"❌ Image {i+1}: Failed to decode as raw base64: {e}")
                        # Fall through to file path handling
                        logger.info(f"📷 Image {i+1}: Falling back to file path processing")
                        file_path = Path(img)
                        if file_path.exists():
                            if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                                pil_image = Image.open(file_path)
                                processed_images.append(pil_image)
                                logger.info(f"✅ Image {i+1}: File path processed successfully: {file_path.name}")
                            else:
                                logger.warning(f"❌ Image {i+1}: Unsupported file extension: {file_path.suffix}")
                        else:
                            logger.warning(f"❌ Image {i+1}: File does not exist: {file_path}")
                
                elif is_file_path and not is_data_url:
                    # Process as file path (only if not already processed as data URL)
                    logger.info(f"📷 Image {i+1}: Processing as file path: {img}")
                    file_path = Path(img)
                    if file_path.exists():
                        if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                            pil_image = Image.open(file_path)
                            processed_images.append(pil_image)
                            logger.info(f"✅ Image {i+1}: File path processed successfully: {file_path.name}")
                        else:
                            logger.warning(f"❌ Image {i+1}: Unsupported file extension: {file_path.suffix}")
                    else:
                        logger.warning(f"❌ Image {i+1}: File does not exist: {file_path}")
                
                else:
                    logger.warning(f"❌ Image {i+1}: Could not determine image format for processing")
                        
            elif isinstance(img, Path):
                # File path as Path object
                logger.info(f"📷 Image {i+1}: Processing as Path object: {img}")
                if img.exists() and img.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                    pil_image = Image.open(img)
                    processed_images.append(pil_image)
                    logger.info(f"✅ Image {i+1}: Path object processed successfully: {img.name}")
                else:
                    if not img.exists():
                        logger.warning(f"❌ Image {i+1}: Path does not exist: {img}")
                    else:
                        logger.warning(f"❌ Image {i+1}: Unsupported Path extension: {img.suffix}")
            else:
                logger.warning(f"❌ Image {i+1}: Unsupported image type: {type(img)}")
                    
        except Exception as e:
            logger.error(f"❌ Image {i+1}: Failed to process image input with exception: {e}")
            import traceback
            logger.error(f"❌ Image {i+1}: Full traceback: {traceback.format_exc()}")
            continue
    
    logger.info(f"🎯 RESULT: Processed {len(processed_images)} images from {len(images)} inputs")
    if len(processed_images) != len(images):
        logger.warning(f"⚠️  WARNING: {len(images) - len(processed_images)} images were filtered out during processing")
    
    return processed_images


def convert_pil_to_base64(pil_image):
    """
    Convert PIL Image to base64 data URL for OpenRouter API
    
    Args:
        pil_image (PIL.Image): PIL Image object
        
    Returns:
        str: Base64 data URL (data:image/jpeg;base64,...)
    """
    import io
    import base64
    
    # Convert PIL to bytes
    buffer = io.BytesIO()
    # Convert to RGB if necessary (removes alpha channel)
    if pil_image.mode in ('RGBA', 'LA', 'P'):
        pil_image = pil_image.convert('RGB')
    
    # Save as JPEG to buffer
    pil_image.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    
    # Encode to base64
    img_bytes = buffer.getvalue()
    base64_string = base64.b64encode(img_bytes).decode('utf-8')
    
    # Return as data URL
    return f"data:image/jpeg;base64,{base64_string}"

class BaseModelService(ABC):
    """Abstract base class for model services"""
    
    def __init__(self, model_id=None):
        """Initialize base model service with configuration.
        
        Args:
            model_id: Model identifier. Uses MODEL_ID env var if None.
        """
        # Load configuration from environment
        self.model_id = model_id or os.getenv("MODEL_ID", "google/gemma-3n-E2B-it")
        self.max_input_tokens = int(os.getenv("MAX_INPUT_TOKENS", "12000"))
        self.max_output_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "4096"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        self.do_sample = os.getenv("DO_SAMPLE", "true").lower() == "true"
        self.repetition_penalty = float(os.getenv("REPETITION_PENALTY", "1.1"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("RETRY_DELAY", "0.5"))
        
        logger.info(f"Initializing model service for: {self.model_id}")
    
    @abstractmethod
    def load_model(self):
        """Load the model and tokenizer"""
        pass
    
    @abstractmethod
    def generate(self, prompt_template, variables=None, parser_func=None, max_tokens=None, max_retries=None):
        """Generate text using the model"""
        pass

class TransformersModelService(BaseModelService):
    """Transformers-based model service for PyTorch/MPS models with MLX support"""
    
    def __init__(self, model_id=None):
        """Initialize Transformers model service.
        
        Args:
            model_id: Model identifier. Uses MODEL_ID env var if None.
        """
        super().__init__(model_id)
        
        self.model = None
        self.tokenizer = None
        self.processor = None  # For multimodal models
        self.device = self._get_device()
        self.is_multimodal = False  # Track if model supports vision
        
        # MLX integration for MPS devices
        self.use_mlx = self._should_use_mlx()
        self.mlx_model = None
        self.mlx_processor = None
        self.mlx_config = None
        
        # Set up directories from config
        models_dir_name = os.getenv("MODELS_DIR", "models")
        self.models_dir = Path(models_dir_name)
        self.models_dir.mkdir(exist_ok=True)
        self.offload_dir = self.models_dir / "offload"
        self.offload_dir.mkdir(exist_ok=True)
        self.model_path = self.models_dir / f"models--{self.model_id.replace('/', '--')}"
        
        # Prompts directory
        self.prompts_dir = Path(os.getenv("PROMPTS_DIR", "prompts"))
        
        logger.info(f"Initializing Model Service")
        logger.info(f"Model ID: {self.model_id}")
        logger.info(f"Device: {self.device}")
        logger.info(f"Use MLX: {self.use_mlx}")
        logger.info(f"Max input tokens: {self.max_input_tokens}")
        logger.info(f"Max output tokens: {self.max_output_tokens}")
        logger.info(f"Model storage path: {self.model_path}")
        
    def _get_device(self):
        """Determine the best available device"""
        # Check if device is specified in config
        config_device = os.getenv("DEVICE", "").strip()
        if config_device:
            logger.info(f"Using configured device: {config_device}")
            return config_device
            
        # Auto-detect device
        if torch.cuda.is_available():
            device = "cuda"
            logger.info(f"CUDA available - GPU: {torch.cuda.get_device_name()}")
        elif torch.backends.mps.is_available():
            device = "mps"
            logger.info("MPS (Apple Silicon) available")
        else:
            device = "cpu"
            logger.info("Using CPU")
        
        return device
    
    def _should_use_mlx(self):
        """Determine if MLX should be used based on device, availability, and config"""
        # Check configuration setting first
        use_mlx_config = os.getenv("USE_MLX_VLM", "true").lower() == "true"
        
        if not use_mlx_config:
            logger.info("USE_MLX_VLM=false - forcing Transformers")
            return False
        
        # Original logic: Force use MLX if device is MPS and MLX is available
        if self.device == "mps" and MLX_AVAILABLE:
            logger.info("MLX available on MPS device - will use MLX for optimal performance")
            return True
        elif self.device == "mps" and not MLX_AVAILABLE:
            logger.warning("MPS device detected but MLX not available - falling back to Transformers")
            return False
        else:
            logger.info(f"Device {self.device} - using Transformers")
            return False
    
    def _get_memory_limits(self):
        """Get memory limits from configuration"""
        gpu_limit = os.getenv("MEMORY_LIMIT_GPU", "2.5GB")
        cpu_limit = os.getenv("MEMORY_LIMIT_CPU", "12GB")
        
        if self.device == "mps":
            return {0: gpu_limit, "cpu": cpu_limit}
        elif self.device == "cuda":
            return {0: gpu_limit, "cpu": cpu_limit}
        else:
            return {"cpu": cpu_limit}
    
    def _model_exists_locally(self):
        """Check if model is already downloaded locally in HF cache structure"""
        logger.info(f"Checking for model at: {self.model_path}")
        if not self.model_path.exists():
            logger.info(f"Model path does not exist: {self.model_path}")
            return False
        
        # Check for snapshots directory (HF cache structure)
        snapshots_dir = self.model_path / "snapshots"
        if not snapshots_dir.exists():
            logger.info(f"Snapshots directory not found: {snapshots_dir}")
            return False
        
        # Find the most recent snapshot
        snapshot_dirs = [d for d in snapshots_dir.iterdir() if d.is_dir()]
        if not snapshot_dirs:
            logger.info(f"No snapshot directories found in: {snapshots_dir}")
            return False
        
        # Use the first snapshot (or you could sort by modification time)
        snapshot_path = snapshot_dirs[0]
        logger.info(f"Checking snapshot: {snapshot_path}")
        
        # Check for essential files in the snapshot
        required_files = [
            "config.json",
            "tokenizer.json", 
            "tokenizer_config.json"
        ]
        
        for file in required_files:
            if not (snapshot_path / file).exists():
                logger.warning(f"Missing file in snapshot: {file}")
                return False
        
        # Check for model files (safetensors or pytorch)
        model_files = list(snapshot_path.glob("*.safetensors")) + list(snapshot_path.glob("pytorch_model*.bin"))
        if not model_files:
            logger.warning("No model weight files found in snapshot")
            return False
        
        logger.info(f"✓ Model found locally at: {snapshot_path}")
        return True

    def load_model(self):
        """Load the model and tokenizer (MLX or Transformers based on device)"""
        if self.use_mlx:
            return self._load_mlx_model()
        else:
            return self._load_transformers_model()
    
    def _load_mlx_model(self):
        """Load MLX model and processor (config comes from model.config)"""
        try:
            logger.info(f"Loading MLX model: {self.model_id}")
            self.mlx_model, self.mlx_processor = mlx_load(self.model_id)
            logger.info(f"✓ MLX model loaded successfully: {self.model_id}")
            
            # Config is available as model.config (not separate load_config call)
            self.mlx_config = self.mlx_model.config
            logger.info(f"✓ MLX model config obtained from model.config")
            
            return True
        except Exception as e:
            logger.error(f"Failed to load MLX model: {e}")
            return False
    
    def _load_transformers_model(self):
        """Load the Transformers model and tokenizer"""
        try:
            logger.info(f"Loading Transformers model: {self.model_id}")
            start_time = time.time()
            
            # Check if model exists locally (for logging purposes)
            if self._model_exists_locally():
                logger.info("Using locally cached model")
            else:
                logger.info("Model not found locally, will download and cache")
            
            # Always use model_id, let HuggingFace handle the cache
            model_source = self.model_id
            
            # Detect if this is a multimodal model (Gemma 3n)
            self.is_multimodal = (GEMMA3N_AVAILABLE and 
                                  ("gemma-3n" in self.model_id.lower() or 
                                   "gemma3n" in self.model_id.lower()))
            
            if self.is_multimodal:
                logger.info("Loading multimodal processor...")
                self.processor = AutoProcessor.from_pretrained(
                    model_source,
                    cache_dir=str(self.models_dir)
                )
                # Also load tokenizer for backwards compatibility
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_source,
                    cache_dir=str(self.models_dir)
                )
                logger.info("✓ Loaded multimodal processor and tokenizer")
            else:
                # Load tokenizer only for text models
                logger.info("Loading tokenizer...")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_source,
                    cache_dir=str(self.models_dir)
                )
            
            # Load model with optimal settings for Gemma 3n-E2B on Apple Silicon
            logger.info("Loading model...")
            
            # Configure dtype based on MPS support
            if self.device == "mps":
                # For Apple Silicon MPS, try bfloat16 first, fallback to float16
                try:
                    dtype = torch.bfloat16
                    logger.info("Using bfloat16 for MPS")
                except:
                    dtype = torch.float16
                    logger.info("Fallback to float16 for MPS compatibility")
            else:
                dtype = torch.bfloat16
            
            # Load appropriate model class
            if self.is_multimodal:
                logger.info("Loading Gemma3nForConditionalGeneration for multimodal support...")
                self.model = Gemma3nForConditionalGeneration.from_pretrained(
                    model_source,
                    cache_dir=str(self.models_dir),
                    torch_dtype=dtype,
                    device_map="auto",
                    low_cpu_mem_usage=True,
                    trust_remote_code=True,
                    offload_folder=str(self.offload_dir),
                    max_memory=self._get_memory_limits()
                ).eval()  # Set to eval mode as in the example
            else:
                logger.info("Loading AutoModelForCausalLM for text-only model...")
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_source,
                    cache_dir=str(self.models_dir),
                    torch_dtype=dtype,
                    device_map="auto",
                    low_cpu_mem_usage=True,
                    trust_remote_code=True,
                    offload_folder=str(self.offload_dir),
                    max_memory=self._get_memory_limits()
                )
            
            # Don't move model manually when using device_map="auto"
            # Accelerate handles the optimal placement automatically
            
            load_time = time.time() - start_time
            
            logger.info(f"✓ Model loaded successfully in {load_time:.2f} seconds")
            logger.info(f"Model parameters: {self.model.num_parameters():,}")
            logger.info(f"Multimodal support: {'Yes' if self.is_multimodal else 'No'}")
            
            # Log storage info
            try:
                import subprocess
                result = subprocess.run(['du', '-sh', str(self.models_dir)], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    size = result.stdout.strip().split()[0]
                    logger.info(f"Models directory size: {size}")
            except:
                pass  # Ignore if du command fails
            
            # Log memory usage if available
            if torch.cuda.is_available():
                memory_allocated = torch.cuda.memory_allocated() / 1024**3  # GB
                logger.info(f"GPU memory allocated: {memory_allocated:.2f} GB")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    def generate(self, prompt_template, variables=None, parser_func=None, max_tokens=None, max_retries=None, images=None):
        """
        Generic generation method with dynamic prompt variables, images, and parsing
        
        Args:
            prompt_template (str): Template string with {variable} placeholders
            variables (dict): Dictionary with variable values for substitution
            parser_func (callable): Function to parse the output, should return parsed result or None if failed
            max_tokens (int): Maximum tokens to generate (defaults to config)
            max_retries (int): Maximum retry attempts if parsing fails (defaults to config)
            images (list): List of images (PIL Images, file paths, or Base64 strings)
            
        Returns:
            str or parsed result: Raw generated content or parsed result if parser_func provided
        """
        if self.use_mlx:
            return self._generate_mlx(prompt_template, variables, parser_func, max_tokens, max_retries, images)
        else:
            return self._generate_transformers(prompt_template, variables, parser_func, max_tokens, max_retries, images)
    
    def _generate_mlx(self, prompt_template, variables=None, parser_func=None, max_tokens=None, max_retries=None, images=None):
        """Generate text using MLX model with optional image inputs"""
        if self.mlx_model is None or self.mlx_processor is None or self.mlx_config is None:
            raise RuntimeError("MLX model, processor, or config not loaded. Call load_model() first.")
        
        # Set generation parameters
        generation_max_tokens = max_tokens or self.max_output_tokens
        retries = max_retries or self.max_retries
        
        # Substitute variables in prompt template
        if variables:
            prompt = prompt_template.format(**variables)
        else:
            prompt = prompt_template
        
        # Process image inputs if provided
        processed_images = process_image_inputs(images) if images else []
        logger.info(f"Generating with MLX model: {self.model_id} (with {len(processed_images)} images)")
        
        for attempt in range(retries):
            try:
                logger.info(f"Generation attempt {attempt + 1}/{retries}")
                
                # Apply chat template (following README pattern)
                formatted_prompt = apply_chat_template(
                    self.mlx_processor, 
                    self.mlx_config, 
                    prompt
                )
                logger.info("Using chat template for MLX-VLM generation")
                
                # Log the full formatted prompt
                logger.info("=" * 50)
                logger.info("FULL PROMPT START")
                logger.info("=" * 50)
                logger.info(formatted_prompt)
                logger.info("=" * 50)
                logger.info("FULL PROMPT END")
                logger.info("=" * 50)
                
                # Generate with MLX-VLM (supports images if provided)
                start_time = time.time()
                
                if processed_images:
                    # Multimodal generation with images
                    logger.info(f"MLX multimodal generation with {len(processed_images)} images")
                    output = mlx_generate(
                        self.mlx_model,
                        self.mlx_processor,
                        formatted_prompt,
                        images=processed_images,
                        verbose=False
                    )
                else:
                    # Text-only generation
                    logger.info("MLX text-only generation")
                    output = mlx_generate(
                        self.mlx_model,
                        self.mlx_processor,
                        formatted_prompt,
                        verbose=False
                    )
                
                # Extract response text (output might be string directly or have attributes)
                if hasattr(output, 'text'):
                    response_text = output.text
                else:
                    response_text = str(output)
                
                generation_time = time.time() - start_time
                
                # Log the full response
                logger.info("=" * 50)
                logger.info("FULL RESPONSE START")
                logger.info("=" * 50)
                logger.info(response_text)
                logger.info("=" * 50)
                logger.info("FULL RESPONSE END")
                logger.info("=" * 50)
                
                logger.info(f"✓ Generated {len(response_text)} characters in {generation_time:.2f} seconds")
                
                # Apply parser if provided
                if parser_func:
                    parsed_result = parser_func(response_text)
                    if parsed_result is not None:
                        logger.info(f"✓ Parsing successful on attempt {attempt + 1}")
                        return parsed_result
                    else:
                        logger.warning(f"✗ Parsing failed on attempt {attempt + 1}")
                        if attempt < retries - 1:
                            logger.info("Retrying generation...")
                            time.sleep(self.retry_delay)
                            continue
                        else:
                            logger.error("All parsing attempts failed, returning raw content")
                            return response_text
                
                return response_text
                
            except Exception as e:
                logger.error(f"Generation attempt {attempt + 1} failed: {e}")
                if attempt == retries - 1:
                    raise
                time.sleep(self.retry_delay)
        
        raise RuntimeError(f"Failed to generate after {retries} attempts")
    
    def _generate_transformers(self, prompt_template, variables=None, parser_func=None, max_tokens=None, max_retries=None, images=None):
        """Generate text using Transformers model with optional image inputs"""
        if not self.model or not self.tokenizer:
            raise Exception("Model not loaded. Call load_model() first.")
        
        # Use config defaults if not specified
        max_tokens = max_tokens or self.max_output_tokens
        max_retries = max_retries or self.max_retries
        
        # Substitute variables in prompt template
        if variables:
            try:
                prompt = prompt_template.format(**variables)
            except KeyError as e:
                raise ValueError(f"Missing variable in template: {e}")
        else:
            prompt = prompt_template
        
        # Process image inputs if provided
        processed_images = process_image_inputs(images) if images else []
        logger.info(f"Generating with Transformers model: {self.model_id} (with {len(processed_images)} images)")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Generation attempt {attempt + 1}/{max_retries}")
                
                # Log the full prompt
                logger.info("=" * 50)
                logger.info("FULL PROMPT START")
                logger.info("=" * 50)
                logger.info(prompt)
                logger.info("=" * 50)
                logger.info("FULL PROMPT END")
                logger.info("=" * 50)
                
                # Prepare inputs (text + images if available)
                start_time = time.time()
                
                if processed_images and self.is_multimodal and self.processor:
                    # Multimodal input processing with chat format
                    logger.info(f"Using multimodal input processing with {len(processed_images)} images")
                    
                    # Create chat messages in the format expected by Gemma 3n
                    content = [{"type": "text", "text": prompt}]
                    for img in processed_images:
                        content.append({"type": "image", "image": img})
                    
                    messages = [{"role": "user", "content": content}]
                    
                    # Use processor.apply_chat_template for multimodal inputs
                    inputs = self.processor.apply_chat_template(
                        messages,
                        add_generation_prompt=True,
                        tokenize=True,
                        return_dict=True,
                        return_tensors="pt",
                    )
                    
                elif processed_images and not self.is_multimodal:
                    # Images provided but model doesn't support multimodal
                    logger.warning("Images provided but model doesn't support multimodal - falling back to text-only")
                    inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.max_input_tokens)
                    
                else:
                    # Text-only processing
                    inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.max_input_tokens)
                
                # Move inputs to the model's device
                model_device = self.model.device if hasattr(self.model, 'device') else next(self.model.parameters()).device
                inputs = {k: v.to(model_device) for k, v in inputs.items()}
                
                # Generate response
                logger.info("Generating response...")
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=max_tokens,
                        temperature=self.temperature,
                        do_sample=self.do_sample,
                        pad_token_id=self.tokenizer.eos_token_id,
                        repetition_penalty=self.repetition_penalty
                    )
                
                # Decode response - handle multimodal vs text-only differently
                if processed_images and self.is_multimodal and self.processor:
                    # For multimodal models, we need to handle the decoding differently
                    # The input doesn't contain the raw prompt, so we decode the full output
                    input_len = inputs['input_ids'].shape[1]
                    generated_tokens = outputs[0][input_len:]
                    generated_content = self.processor.decode(generated_tokens, skip_special_tokens=True).strip()
                else:
                    # For text-only models, use the original approach
                    full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                    generated_content = full_response[len(prompt):].strip()
                
                generation_time = time.time() - start_time
                
                # Log the full response
                logger.info("=" * 50)
                logger.info("FULL RESPONSE START")
                logger.info("=" * 50)
                logger.info(generated_content)
                logger.info("=" * 50)
                logger.info("FULL RESPONSE END")
                logger.info("=" * 50)
                
                logger.info(f"✓ Generated {len(generated_content)} characters in {generation_time:.2f} seconds")
                
                # Parse if parser function provided
                if parser_func:
                    parsed_result = parser_func(generated_content)
                    if parsed_result is not None:
                        logger.info(f"✓ Parsing successful on attempt {attempt + 1}")
                        return parsed_result
                    else:
                        logger.warning(f"✗ Parsing failed on attempt {attempt + 1}")
                        if attempt < max_retries - 1:
                            logger.info("Retrying generation...")
                            time.sleep(self.retry_delay)
                            continue
                        else:
                            logger.error("All parsing attempts failed, returning raw content")
                            return generated_content
                else:
                    return generated_content
                    
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.info("Retrying generation...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise
        
        raise Exception("All generation attempts failed")

    def load_prompt(self, prompt_name):
        """
        Load prompt template from file
        
        Args:
            prompt_name (str): Name of the prompt file (without .txt extension)
            
        Returns:
            str: Prompt template content
        """
        prompt_path = self.prompts_dir / f"{prompt_name}.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    def generate_educational_content(self, content_text, max_tokens=512):
        """
        Generate educational content based on input text
        
        Args:
            content_text (str): The input content from tutor
            max_tokens (int): Maximum tokens to generate
            
        Returns:
            str: Generated educational content
        """
        prompt_template = self.load_prompt("educational_content")
        return self.generate(
            prompt_template=prompt_template,
            variables={"content_text": content_text},
            max_tokens=max_tokens
        )
    
    def process_file_content(self, file_path, content_text):
        """
        Process content from a file and generate educational material
        
        Args:
            file_path (str): Path to the source file
            content_text (str): Content of the file
            
        Returns:
            str: Generated educational content
        """
        logger.info(f"Processing file: {file_path}")
        logger.info(f"Input content length: {len(content_text)} characters")
        
        timestamp = datetime.now().isoformat()
        
        # Log processing start
        logger.info(f"[{timestamp}] Starting content generation for: {file_path}")
        
        try:
            # Generate educational content
            result = self.generate_educational_content(content_text)
            
            # Log success
            logger.info(f"[{timestamp}] ✓ Successfully processed: {file_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"[{timestamp}] ✗ Failed to process: {file_path} - Error: {e}")
            raise

# Factory function to create the appropriate model service
def create_model_service(model_id=None):
    """Create local-only model service - cloud inference removed"""
    if model_id is None:
        model_id = os.getenv("MODEL_ID", "google/gemma-3n-E2B-it")
    
    # Only local inference supported - use TransformersModelService with automatic MLX integration
    logger.info(f"Using local TransformersModelService with MLX support for: {model_id}")
    return TransformersModelService(model_id)

# Backward compatibility alias
def GemmaModelService(model_id=None):
    """Backward compatibility wrapper"""
    return create_model_service(model_id)

def main():
    """Test the model service"""
    logger.info("Starting Model Service Test")
    
    # Initialize service using factory
    service = create_model_service()
    
    # Load model
    if not service.load_model():
        logger.error("Failed to load model")
        return
    
    # Test with sample content
    test_content = """
    Linear equations are mathematical statements that show equality between two expressions.
    A linear equation has the form ax + b = c, where a, b, and c are constants.
    To solve: isolate the variable by performing the same operation on both sides.
    """
    
    try:
        result = service.generate_educational_content(test_content)
        logger.info("Test successful!")
        logger.info(f"Generated content preview: {result[:200]}...")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    main()