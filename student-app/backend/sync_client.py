"""
Sync Client for Student-App
Handles discovery and synchronization with tutor-app instances
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class SyncClient:
    def __init__(self):
        self.tutor_url = os.getenv('TUTOR_SERVICE_URL', 'http://localhost:8001')
        self.check_interval = int(os.getenv('SYNC_CHECK_INTERVAL', '30'))
        
        # SyncClient is now dynamic - no cached student data
        logger.info("🔍 SyncClient initialized (dynamic profile loading)")
        
        # Paths
        self.content_dir = Path("content")
        self.inbox_dir = self.content_dir / "inbox"
        self.processed_dir = self.content_dir / "processed"
        self.generated_dir = self.content_dir / "generated"
        self.logs_dir = Path("logs")
        
        # Ensure directories exist
        for dir_path in [self.inbox_dir, self.processed_dir, self.generated_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _get_current_student_info(self) -> tuple[str, str]:
        """Get current student ID and name from profile"""
        from student_profile import get_current_student_profile
        
        profile = get_current_student_profile()
        
        if profile is None:
            # No profile available - use default values
            return "anonymous_student", "Anonymous Student"
        
        # Use actual profile data
        student_id = profile.get('student_id', 'unknown_id')
        student_name = profile.get('student_name', 'Unknown Student')
        
        return student_id, student_name
    
    def discover_tutor_service(self) -> bool:
        """Check if tutor service is available and accepting connections"""
        try:
            logger.info(f"Checking tutor service at: {self.tutor_url}/api/sync/discover")
            response = requests.get(f"{self.tutor_url}/api/sync/discover", timeout=5)
            logger.info(f"Tutor service response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                available = data.get('available', False)
                logger.info(f"Tutor service available: {available}, data: {data}")
                return available
            else:
                logger.warning(f"Tutor service returned status {response.status_code}: {response.text}")
                return False
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error to tutor service: {e}")
            return False
        except requests.exceptions.Timeout as e:
            logger.warning(f"Timeout connecting to tutor service: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking tutor service: {e}")
            return False
    
    def get_student_logs(self, since_timestamp: Optional[str] = None) -> str:
        """Collect ONLY xAPI student activity logs (exclude technical logs like model_interactions.log)"""
        logs_content = ""
        
        try:
            # Read ONLY xAPI logs from student.log
            xapi_log_file = self.logs_dir / "student.log"
            if xapi_log_file.exists():
                if since_timestamp:
                    # Read only logs since timestamp
                    logs_content = self._get_logs_since_timestamp(xapi_log_file, since_timestamp)
                else:
                    # Read all logs
                    with open(xapi_log_file, 'r', encoding='utf-8') as f:
                        logs_content = f.read()
        
            # Only xAPI logs (student.log) are sent to tutor for pedagogical analysis
        
        except Exception as e:
            logger.error(f"Error collecting xAPI logs: {e}")
        
        return logs_content
    
    def _get_logs_since_timestamp(self, log_file: Path, since_timestamp: str) -> str:
        """Get logs from file since the given timestamp"""
        filtered_logs = ""
        
        try:
            from dateutil.parser import parse as parse_date
            since_dt = parse_date(since_timestamp)
            
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Parse JSON line to get timestamp
                        log_entry = json.loads(line)
                        log_timestamp_str = log_entry.get('timestamp')
                        if log_timestamp_str:
                            log_dt = parse_date(log_timestamp_str)
                            if log_dt > since_dt:
                                filtered_logs += line + '\n'
                    except (json.JSONDecodeError, ValueError) as e:
                        # If we can't parse the line as JSON or timestamp, include it anyway
                        logger.debug(f"Could not parse log line timestamp: {e}")
                        filtered_logs += line + '\n'
        
        except Exception as e:
            logger.warning(f"Error filtering logs by timestamp, returning all logs: {e}")
            # Fallback to returning all logs
            with open(log_file, 'r', encoding='utf-8') as f:
                filtered_logs = f.read()
        
        return filtered_logs
    
    def collect_content_data(self) -> Dict:
        """Collect all generated content, submissions, and discovery data"""
        content_data = {
            'generated': {},
            'submissions': {},
            'discovery': {},
            'progress': {},
            'current_content': []
        }
        
        try:
            # Collect generated content
            if self.generated_dir.exists():
                content_data['generated'] = self._collect_generated_content()
            
            # Collect submissions
            submissions_patterns = [
                self.content_dir / "experiment_submissions",
                self.content_dir / "practice_submissions"
            ]
            
            for submissions_dir in submissions_patterns:
                if submissions_dir.exists():
                    submission_type = submissions_dir.name
                    content_data['submissions'][submission_type] = self._collect_submissions(submissions_dir)
            
            # Collect discovery data
            discovery_dir = self.content_dir / "discovery_data"
            if discovery_dir.exists():
                content_data['discovery'] = self._collect_discovery_data(discovery_dir)
            
            # Collect progress data
            progress_files = [
                self.content_dir / "progress.json",
                self.content_dir / "experiment_progress.json"
            ]
            
            for progress_file in progress_files:
                if progress_file.exists():
                    try:
                        with open(progress_file, 'r', encoding='utf-8') as f:
                            progress_data = json.load(f)
                        content_data['progress'][progress_file.stem] = progress_data
                    except Exception as e:
                        logger.warning(f"Could not read progress file {progress_file}: {e}")
            
            # Collect current content list
            content_data['current_content'] = self._get_current_content_list()
        
        except Exception as e:
            logger.error(f"Error collecting content data: {e}")
        
        return content_data
    
    def _collect_generated_content(self) -> Dict:
        """Collect all generated content (questions, challenges, stories, textbooks)"""
        generated_content = {}
        
        try:
            for content_type_dir in self.generated_dir.iterdir():
                if content_type_dir.is_dir():
                    content_type = content_type_dir.name
                    generated_content[content_type] = {}
                    
                    # Handle nested structure (e.g., learn/textbooks, learn/stories)
                    for item in content_type_dir.rglob("*.json"):
                        relative_path = item.relative_to(content_type_dir)
                        key = str(relative_path).replace('.json', '').replace('/', '_')
                        
                        try:
                            with open(item, 'r', encoding='utf-8') as f:
                                generated_content[content_type][key] = json.load(f)
                        except Exception as e:
                            logger.warning(f"Could not read generated content {item}: {e}")
        
        except Exception as e:
            logger.error(f"Error collecting generated content: {e}")
        
        return generated_content
    
    def _collect_submissions(self, submissions_dir: Path) -> Dict:
        """Collect submissions from a directory including associated files"""
        submissions_data = {
            'metadata': [],
            'files': {}
        }
        
        try:
            # Collect submission metadata (JSON files)
            for submission_file in submissions_dir.glob("*.json"):
                try:
                    with open(submission_file, 'r', encoding='utf-8') as f:
                        submission_data = json.load(f)
                    submissions_data['metadata'].append(submission_data)
                except Exception as e:
                    logger.warning(f"Could not read submission {submission_file}: {e}")
            
            # Collect submission files (directories with files/)
            for submission_dir in submissions_dir.iterdir():
                if submission_dir.is_dir():
                    submission_id = submission_dir.name
                    submission_files = {}
                    
                    # Look for numbered submission folders (01, 02, etc.)
                    for version_dir in submission_dir.iterdir():
                        if version_dir.is_dir() and version_dir.name.isdigit():
                            version_num = version_dir.name
                            files_dir = version_dir / "files"
                            
                            if files_dir.exists():
                                version_files = {}
                                for file_path in files_dir.iterdir():
                                    if file_path.is_file():
                                        try:
                                            with open(file_path, 'rb') as f:
                                                import base64
                                                file_data = base64.b64encode(f.read()).decode('utf-8')
                                                version_files[file_path.name] = {
                                                    'filename': file_path.name,
                                                    'data': file_data,
                                                    'format': file_path.suffix.lower()
                                                }
                                        except Exception as e:
                                            logger.warning(f"Could not read submission file {file_path}: {e}")
                                
                                if version_files:
                                    if submission_id not in submission_files:
                                        submission_files[submission_id] = {}
                                    submission_files[submission_id][version_num] = version_files
                    
                    if submission_files:
                        submissions_data['files'].update(submission_files)
        
        except Exception as e:
            logger.error(f"Error collecting submissions from {submissions_dir}: {e}")
        
        return submissions_data
    
    def _collect_discovery_data(self, discovery_dir: Path) -> Dict:
        """Collect discovery session data including images"""
        discovery_data = {
            'sessions': {},
            'images': {}
        }
        
        try:
            # Collect JSON session data
            for discovery_file in discovery_dir.glob("*.json"):
                session_id = discovery_file.stem
                try:
                    with open(discovery_file, 'r', encoding='utf-8') as f:
                        discovery_data['sessions'][session_id] = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not read discovery data {discovery_file}: {e}")
            
            # Collect images
            images_dir = discovery_dir / "images"
            if images_dir.exists():
                for image_file in images_dir.iterdir():
                    if image_file.is_file() and image_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                        image_id = image_file.stem
                        try:
                            with open(image_file, 'rb') as f:
                                import base64
                                image_data = base64.b64encode(f.read()).decode('utf-8')
                                discovery_data['images'][image_id] = {
                                    'filename': image_file.name,
                                    'data': image_data,
                                    'format': image_file.suffix.lower()
                                }
                        except Exception as e:
                            logger.warning(f"Could not read discovery image {image_file}: {e}")
        
        except Exception as e:
            logger.error(f"Error collecting discovery data: {e}")
        
        return discovery_data
    
    def _get_current_content_list(self) -> List[str]:
        """Get list of content files currently available to student"""
        current_content = []
        
        try:
            # Files in processed directory
            if self.processed_dir.exists():
                for content_file in self.processed_dir.glob("*.txt"):
                    current_content.append(content_file.name)
        
        except Exception as e:
            logger.error(f"Error getting current content list: {e}")
        
        return current_content
    
    async def sync_to_tutor(self, last_sync: Optional[str] = None) -> Dict:
        """Send student data to tutor service (with optional delta sync)"""
        try:
            # Get current student info dynamically
            student_id_to_use, student_name_to_use = self._get_current_student_info()
            logger.info(f"🔄 Sync using current profile: {student_name_to_use} ({student_id_to_use})")
            
            # Collect data with optional timestamp filtering
            logs = self.get_student_logs(since_timestamp=last_sync)
            
            # For content_data, only collect if this is initial sync or forced
            content_data = {}
            if not last_sync:
                # Full sync - include all content data
                content_data = self.collect_content_data()
                logger.info("Performing full sync with all content data")
            else:
                # Delta sync - only include logs, minimal content data
                content_data = {
                    'generated': {},
                    'submissions': {},
                    'discovery': {},
                    'progress': {},
                    'current_content': self._get_current_content_list()
                }
                logger.info(f"Performing delta sync since {last_sync}")
            
            # Prepare sync request (using reloaded profile data)
            sync_data = {
                'student_id': student_id_to_use,
                'student_data': {
                    'id': student_id_to_use,
                    'name': student_name_to_use,
                    'last_sync': datetime.now().isoformat()
                },
                'logs': logs,
                'content_data': content_data,
                'sync_type': 'delta' if last_sync else 'full'
            }
            
            # Send to tutor
            response = requests.post(
                f"{self.tutor_url}/api/sync/from-student",
                json=sync_data,
                timeout=30
            )
            
            if response.status_code == 200:
                sync_response = response.json()
                logger.info(f"Successfully synced to tutor: {sync_response.get('message', '')}")
                
                # Log the response details for debugging
                assigned_content = sync_response.get('assigned_content', [])
                removed_content = sync_response.get('removed_content', [])
                
                logger.info(f"📥 Sync response received:")
                logger.info(f"  📚 Assigned content: {assigned_content}")
                logger.info(f"  🗑️ Removed content: {removed_content}")
                
                # Process assigned content changes
                await self._process_content_changes(sync_response)
                
                return {
                    'success': True,
                    'message': 'Sync completed successfully',
                    'assigned_content': assigned_content,
                    'removed_content': removed_content
                }
            else:
                error_msg = f"Sync failed: {response.status_code} {response.text}"
                logger.error(error_msg)
                return {'success': False, 'message': error_msg}
        
        except Exception as e:
            error_msg = f"Sync error: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}
    
    async def _process_content_changes(self, sync_response: Dict):
        """Process content changes from tutor (new assignments, removals)"""
        try:
            assigned_content = sync_response.get('assigned_content', [])
            removed_content = sync_response.get('removed_content', [])
            
            logger.info(f"🔄 Processing content changes from tutor:")
            logger.info(f"  📚 New assignments: {assigned_content}")
            logger.info(f"  🗑️ Content to remove: {removed_content}")
            
            # Get new content from tutor
            if assigned_content:
                logger.info(f"⬇️ Fetching {len(assigned_content)} new content files...")
                await self._fetch_assigned_content(assigned_content)
            else:
                logger.info("📝 No new content to fetch")
            
            # Remove content that's no longer assigned
            if removed_content:
                logger.info(f"🗑️ Removing {len(removed_content)} unassigned content files...")
                await self._remove_unassigned_content(removed_content)
            else:
                logger.info("✅ No content to remove")
        
        except Exception as e:
            logger.error(f"❌ Error processing content changes: {e}")
            import traceback
            logger.error(f"🔍 Full traceback:\n{traceback.format_exc()}")
    
    async def _fetch_assigned_content(self, assigned_files: List[str]):
        """Fetch newly assigned content from tutor"""
        try:
            student_id, _ = self._get_current_student_info()
            response = requests.get(f"{self.tutor_url}/api/sync/content/{student_id}")
            
            if response.status_code == 200:
                content_data = response.json()
                content_files = content_data.get('content', {}).get('content_data', {})
                
                for filename, content in content_files.items():
                    # Check if file is new (not in processed)
                    processed_file = self.processed_dir / filename
                    inbox_file = self.inbox_dir / filename
                    
                    if not processed_file.exists():
                        # Save to inbox for new content
                        with open(inbox_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        logger.info(f"Added new content to inbox: {filename}")
                    else:
                        logger.debug(f"Content already exists: {filename}")
        
        except Exception as e:
            logger.error(f"Error fetching assigned content: {e}")
    
    async def _remove_unassigned_content(self, removed_files: List[str]):
        """Remove content that's no longer assigned"""
        try:
            logger.info(f"🗑️ Starting removal of unassigned content: {removed_files}")
            
            for filename in removed_files:
                logger.info(f"🎯 Processing removal of: {filename}")
                base_name = filename.replace('.txt', '')
                logger.info(f"📝 Base name: {base_name}")
                
                # Remove from processed
                processed_file = self.processed_dir / filename
                logger.info(f"🔍 Checking processed file: {processed_file}")
                if processed_file.exists():
                    processed_file.unlink()
                    logger.info(f"✅ Removed processed file: {processed_file}")
                else:
                    logger.warning(f"⚠️ Processed file not found: {processed_file}")
                
                # Remove associated generated content
                content_dirs_to_remove = [
                    # Practice content (whole directory)
                    self.generated_dir / "practice" / base_name,
                    # Learn content (individual files)
                    self.generated_dir / "learn" / "textbooks" / f"{base_name}.json",
                    self.generated_dir / "learn" / "stories" / f"{base_name}.json",
                    # Experiment content (whole directory)
                    self.generated_dir / "experiment" / base_name
                ]
                
                logger.info(f"🗂️ Checking {len(content_dirs_to_remove)} generated content paths:")
                
                for content_path in content_dirs_to_remove:
                    logger.info(f"🔍 Checking path: {content_path}")
                    if content_path.exists():
                        try:
                            if content_path.is_dir():
                                shutil.rmtree(content_path)
                                logger.info(f"✅ Removed directory: {content_path}")
                            else:
                                content_path.unlink()
                                logger.info(f"✅ Removed file: {content_path}")
                        except Exception as path_error:
                            logger.error(f"❌ Failed to remove {content_path}: {path_error}")
                    else:
                        logger.info(f"📝 Path doesn't exist (OK): {content_path}")
                
                # Remove experiment challenges associated with this content
                logger.info(f"🎯 Removing experiment challenges for: {base_name}")
                await self._remove_experiment_challenges_for_content(base_name)
                
                logger.info(f"✅ Completed removal processing for: {filename}")
        
        except Exception as e:
            logger.error(f"❌ Error removing unassigned content: {e}")
            import traceback
            logger.error(f"🔍 Full traceback:\n{traceback.format_exc()}")
    
    async def _remove_experiment_challenges_for_content(self, content_name: str):
        """Remove experiment challenges that were generated from the specified content"""
        try:
            challenges_registry_file = self.generated_dir / "experiment" / "challenges_registry.json"
            if not challenges_registry_file.exists():
                logger.info(f"No challenges registry found, skipping challenge cleanup for {content_name}")
                return
            
            # Load current registry
            with open(challenges_registry_file, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)
            
            challenges_to_remove = []
            updated_challenges = {}
            
            # Check each challenge to see if it should be removed or updated
            for challenge_uuid, challenge_info in registry_data.get("challenges", {}).items():
                source_contents = challenge_info.get("source_contents", [])
                
                if content_name in source_contents:
                    if len(source_contents) == 1:
                        # Challenge only depends on this content, remove it completely
                        challenges_to_remove.append(challenge_uuid)
                        logger.info(f"Marking challenge {challenge_uuid} for removal (only source: {content_name})")
                    else:
                        # Challenge is interdisciplinary, just remove this content from sources
                        updated_source_contents = [sc for sc in source_contents if sc != content_name]
                        challenge_info["source_contents"] = updated_source_contents
                        challenge_info["interdisciplinary"] = len(updated_source_contents) > 1
                        updated_challenges[challenge_uuid] = challenge_info
                        logger.info(f"Updated challenge {challenge_uuid} to remove source {content_name}, remaining sources: {updated_source_contents}")
                else:
                    # Challenge doesn't use this content, keep as is
                    updated_challenges[challenge_uuid] = challenge_info
            
            # Remove challenge files
            challenges_dir = self.generated_dir / "experiment" / "challenges"
            for challenge_uuid in challenges_to_remove:
                challenge_file = challenges_dir / f"{challenge_uuid}.json"
                if challenge_file.exists():
                    challenge_file.unlink()
                    logger.info(f"Removed challenge file: {challenge_file}")
            
            # Update registry
            if challenges_to_remove or len(updated_challenges) != len(registry_data.get("challenges", {})):
                registry_data["challenges"] = updated_challenges
                registry_data["metadata"]["total_challenges"] = len(updated_challenges)
                registry_data["metadata"]["last_updated"] = datetime.now().isoformat()
                
                # Update content sources in metadata
                all_sources = set()
                for challenge_info in updated_challenges.values():
                    all_sources.update(challenge_info.get("source_contents", []))
                registry_data["metadata"]["content_sources"] = sorted(list(all_sources))
                
                # Save updated registry
                with open(challenges_registry_file, 'w', encoding='utf-8') as f:
                    json.dump(registry_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Updated challenges registry: removed {len(challenges_to_remove)} challenges, updated {len(updated_challenges)} remaining")
        
        except Exception as e:
            logger.error(f"Error removing experiment challenges for content {content_name}: {e}")

# Global instance
sync_client = SyncClient()