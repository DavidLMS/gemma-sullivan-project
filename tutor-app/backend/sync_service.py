"""
Sync Service for Tutor-App
Handles discovery, connection, and synchronization with student-app instances
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import aiofiles
from fastapi import HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class SyncRequest(BaseModel):
    student_id: str
    student_data: Dict
    logs: str
    content_data: Dict

class SyncResponse(BaseModel):
    success: bool
    message: str
    assigned_content: List[str]
    removed_content: List[str]

class SyncService:
    def __init__(self, students_dir: Path, content_dir: Path):
        self.students_dir = students_dir
        self.content_dir = content_dir
        self.is_discovery_active = False
        
    def start_discovery_service(self) -> bool:
        """Start the network discovery service"""
        try:
            self.is_discovery_active = True
            logger.info("Network discovery service started")
            return True
        except Exception as e:
            logger.error(f"Failed to start discovery service: {e}")
            return False
    
    def stop_discovery_service(self) -> bool:
        """Stop the network discovery service"""
        try:
            self.is_discovery_active = False
            logger.info("Network discovery service stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop discovery service: {e}")
            return False
    
    def is_discovery_running(self) -> bool:
        """Check if discovery service is running"""
        return self.is_discovery_active
    
    async def sync_from_student(self, sync_request: SyncRequest) -> SyncResponse:
        """
        Sync data from student to tutor
        Copies logs, generated content, submissions, and discovery data
        """
        try:
            student_id = sync_request.student_id
            
            # Debug logging for student creation investigation
            logger.info(f"🔍 Sync request received from student:")
            logger.info(f"  🆔 Student ID: {student_id}")
            logger.info(f"  👤 Student Data: {sync_request.student_data}")
            logger.info(f"  📊 Student Data Keys: {list(sync_request.student_data.keys()) if sync_request.student_data else 'None'}")
            
            # Ensure student is registered in tutor-app
            await self._ensure_student_registered(student_id, sync_request.student_data)
            
            # Create student directory structure
            student_base_dir = self.students_dir / student_id
            student_content_dir = student_base_dir / "content"
            student_logs_dir = student_base_dir / "logs"
            student_generated_dir = student_base_dir / "generated"
            student_submissions_dir = student_base_dir / "submissions"
            student_discovery_dir = student_base_dir / "discovery"
            
            # Ensure directories exist
            for dir_path in [student_content_dir, student_logs_dir, student_generated_dir, 
                           student_submissions_dir, student_discovery_dir]:
                dir_path.mkdir(parents=True, exist_ok=True)
            
            # Save student logs (single file, overwrite to avoid duplicates)
            if sync_request.logs:
                log_file_path = student_logs_dir / "student.log"
                async with aiofiles.open(log_file_path, 'w', encoding='utf-8') as f:
                    await f.write(sync_request.logs)
                logger.info(f"Updated student logs at {log_file_path}")
            
            # NOTE: Removed sync_data file generation - data is processed and saved in specific structures below
            
            # Process specific content types
            if 'generated' in sync_request.content_data:
                await self._save_generated_content(student_generated_dir, sync_request.content_data['generated'])
            
            if 'submissions' in sync_request.content_data:
                await self._save_submissions(student_submissions_dir, sync_request.content_data['submissions'])
            
            if 'discovery' in sync_request.content_data:
                await self._save_discovery_data(student_discovery_dir, sync_request.content_data['discovery'])
            
            # Get assigned content for this student
            assigned_content = await self._get_assigned_content(student_id)
            
            # Get content that should be removed (no longer assigned)
            removed_content = await self._get_removed_content(student_id, sync_request.content_data.get('current_content', []))
            
            # Prepare sync response 
            sync_response = SyncResponse(
                success=True,
                message=f"Successfully synced data for student {student_id}",
                assigned_content=assigned_content,
                removed_content=removed_content
            )
            
            # Generate performance report in background (don't block sync response)
            # Using asyncio.create_task to run it asynchronously without awaiting
            
            # Create background task with proper error handling
            task = asyncio.create_task(self._generate_performance_report_async(student_id, student_logs_dir))
            
            # Add task completion callback for monitoring (optional)
            def task_done_callback(task_result):
                if task_result.exception():
                    logger.error(f"🔥 Background report task failed with exception: {task_result.exception()}")
                else:
                    logger.debug(f"🎯 Background report task completed cleanly for student {student_id}")
            
            task.add_done_callback(task_done_callback)
            logger.info(f"🚀 Performance report generation started in background for student {student_id}")
            logger.info(f"📈 Sync response will be returned immediately without waiting for report")
            
            return sync_response
            
        except Exception as e:
            logger.error(f"Error syncing from student {sync_request.student_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
    
    async def _save_generated_content(self, generated_dir: Path, generated_data: Dict):
        """Save generated content (questions, challenges, stories, etc.)"""
        for content_type, data in generated_data.items():
            type_dir = generated_dir / content_type
            type_dir.mkdir(exist_ok=True)
            
            if isinstance(data, dict):
                for item_id, item_data in data.items():
                    item_file = type_dir / f"{item_id}.json"
                    async with aiofiles.open(item_file, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(item_data, indent=2, ensure_ascii=False))
    
    async def _save_submissions(self, submissions_dir: Path, submissions_data: Dict):
        """Save student submissions including files"""
        for submission_type, submissions in submissions_data.items():
            type_dir = submissions_dir / submission_type
            type_dir.mkdir(exist_ok=True)
            
            if submission_type == 'metadata' and isinstance(submissions, list):
                # Save submission metadata (JSON files)
                for i, submission in enumerate(submissions):
                    submission_file = type_dir / f"submission_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    async with aiofiles.open(submission_file, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(submission, indent=2, ensure_ascii=False))
            
            elif submission_type == 'files' and isinstance(submissions, dict):
                # Save submission files (images, canvas, etc.)
                await self._save_submission_files(type_dir, submissions)
    
    async def _save_submission_files(self, files_dir: Path, files_data: Dict):
        """Save submission files (images, canvas, etc.)"""
        for submission_id, versions in files_data.items():
            submission_dir = files_dir / submission_id
            submission_dir.mkdir(exist_ok=True)
            
            for version_num, version_files in versions.items():
                version_dir = submission_dir / version_num
                version_files_dir = version_dir / "files"
                version_files_dir.mkdir(parents=True, exist_ok=True)
                
                for filename, file_info in version_files.items():
                    file_path = version_files_dir / filename
                    try:
                        import base64
                        file_data = base64.b64decode(file_info['data'])
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(file_data)
                        logger.info(f"Saved submission file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error saving submission file {file_path}: {e}")

    async def _save_discovery_data(self, discovery_dir: Path, discovery_data: Dict):
        """Save discovery session data including images"""
        # Save session JSON files
        sessions_data = discovery_data.get('sessions', {})
        for session_id, session_data in sessions_data.items():
            session_file = discovery_dir / f"{session_id}.json"
            async with aiofiles.open(session_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(session_data, indent=2, ensure_ascii=False))
        
        # Save discovery images
        images_data = discovery_data.get('images', {})
        if images_data:
            images_dir = discovery_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            for image_id, image_info in images_data.items():
                image_path = images_dir / image_info['filename']
                try:
                    import base64
                    image_data = base64.b64decode(image_info['data'])
                    async with aiofiles.open(image_path, 'wb') as f:
                        await f.write(image_data)
                    logger.info(f"Saved discovery image: {image_path}")
                except Exception as e:
                    logger.error(f"Error saving discovery image {image_path}: {e}")
    
    async def _get_assigned_content(self, student_id: str) -> List[str]:
        """Get list of content files assigned to student"""
        try:
            student_file = self.students_dir / f"{student_id}.json"
            logger.debug(f"📂 Looking for student file: {student_file}")
            
            if student_file.exists():
                async with aiofiles.open(student_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                student_data = json.loads(content)
                assigned_files = student_data.get('assigned_files', [])
                logger.debug(f"📚 Found assigned files for {student_id}: {assigned_files}")
                return assigned_files
            else:
                logger.warning(f"⚠️ Student file not found: {student_file}")
                return []
        except Exception as e:
            logger.error(f"❌ Error getting assigned content for {student_id}: {e}")
            import traceback
            logger.error(f"🔍 Full traceback:\n{traceback.format_exc()}")
            return []
    
    async def _get_removed_content(self, student_id: str, current_content: List[str]) -> List[str]:
        """Get list of content that should be removed from student"""
        try:
            logger.info(f"🔍 Checking content removal for student {student_id}")
            logger.info(f"📋 Student current content: {current_content}")
            
            assigned_content = await self._get_assigned_content(student_id)
            logger.info(f"📚 Student assigned content: {assigned_content}")
            
            # Content that student has but is no longer assigned
            removed = [content for content in current_content if content not in assigned_content]
            
            if removed:
                logger.info(f"🗑️ Content to be REMOVED from student {student_id}: {removed}")
            else:
                logger.info(f"✅ No content to remove for student {student_id}")
            
            return removed
        except Exception as e:
            logger.error(f"❌ Error getting removed content for {student_id}: {e}")
            import traceback
            logger.error(f"🔍 Full traceback:\n{traceback.format_exc()}")
            return []
    
    def _get_filter_settings(self) -> Tuple[int, int]:
        """
        Get log filtering settings from environment variables.
        
        Returns:
            Tuple of (max_records, days_back)
        """
        try:
            # Get max records setting
            max_records_str = os.getenv('LOG_FILTER_MAX_RECORDS', '50')
            max_records = int(max_records_str)
            if max_records <= 0:
                logger.warning(f"Invalid LOG_FILTER_MAX_RECORDS value: {max_records_str}, using default: 50")
                max_records = 50
            
            # Get days back setting
            days_back_str = os.getenv('LOG_FILTER_DAYS_BACK', '15')
            days_back = int(days_back_str)
            if days_back <= 0:
                logger.warning(f"Invalid LOG_FILTER_DAYS_BACK value: {days_back_str}, using default: 15")
                days_back = 15
            
            return max_records, days_back
            
        except ValueError as e:
            logger.error(f"Error parsing filter settings from environment: {e}, using defaults")
            return 50, 15
    
    def _filter_student_logs(self, student_logs: str) -> Tuple[str, str, str]:
        """
        Filter student logs based on volume and recency.
        
        Args:
            student_logs: Raw log content as string
            
        Returns:
            Tuple of (filtered_logs, start_date, end_date)
        """
        if not student_logs.strip():
            return student_logs, "", ""
        
        # Get filter settings from environment
        max_records, days_back = self._get_filter_settings()
        
        try:
            # Parse each line as JSON to extract timestamps
            log_lines = []
            timestamps = []
            
            for line in student_logs.strip().split('\n'):
                if not line.strip():
                    continue
                    
                try:
                    log_entry = json.loads(line)
                    timestamp_str = log_entry.get('timestamp')
                    
                    if timestamp_str:
                        # Parse ISO 8601 timestamp
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        log_lines.append((line, timestamp))
                        timestamps.append(timestamp)
                    else:
                        # Include lines without timestamp at the end
                        log_lines.append((line, None))
                        
                except (json.JSONDecodeError, ValueError) as e:
                    # Include malformed lines as-is
                    logger.warning(f"Could not parse log line as JSON: {e}")
                    log_lines.append((line, None))
                    continue
            
            if not log_lines:
                return student_logs, "", ""
            
            # Sort by timestamp (None timestamps go to the end)
            log_lines.sort(key=lambda x: x[1] if x[1] else datetime.min)
            
            # Filter based on count
            total_records = len(log_lines)
            
            if total_records <= max_records:
                # Use all logs
                filtered_lines = [line for line, _ in log_lines]
                valid_timestamps = [ts for ts in timestamps if ts]
                
                if valid_timestamps:
                    start_date = min(valid_timestamps).strftime('%Y-%m-%d')
                    end_date = max(valid_timestamps).strftime('%Y-%m-%d')
                else:
                    start_date = end_date = "Unknown"
                    
            else:
                # Use only last N days (configurable)
                if not timestamps:
                    # No valid timestamps, return all logs
                    filtered_lines = [line for line, _ in log_lines]
                    start_date = end_date = "Unknown"
                else:
                    # Find the most recent timestamp
                    latest_timestamp = max(timestamps)
                    cutoff_date = latest_timestamp - timedelta(days=days_back)
                    
                    # Filter logs from last N days
                    filtered_entries = []
                    filtered_timestamps = []
                    
                    for line, timestamp in log_lines:
                        if timestamp is None or timestamp >= cutoff_date:
                            filtered_entries.append(line)
                            if timestamp:
                                filtered_timestamps.append(timestamp)
                    
                    filtered_lines = filtered_entries
                    
                    if filtered_timestamps:
                        start_date = min(filtered_timestamps).strftime('%Y-%m-%d')
                        end_date = max(filtered_timestamps).strftime('%Y-%m-%d')
                    else:
                        start_date = end_date = "Unknown"
            
            filtered_logs = '\n'.join(filtered_lines)
            
            logger.info(f"Filtered logs: {total_records} total records, {len(filtered_lines)} selected, period: {start_date} to {end_date} (max_records={max_records}, days_back={days_back})")
            
            return filtered_logs, start_date, end_date
            
        except Exception as e:
            logger.error(f"Error filtering student logs: {e}")
            # Return original logs on error
            return student_logs, "Unknown", "Unknown"
    
    async def _generate_performance_report(self, student_id: str, student_logs_dir: Path):
        """Generate AI-powered performance report for student after sync"""
        try:
            logger.info(f"Generating performance report for student {student_id}")
            
            # Read student logs
            student_log_file = student_logs_dir / "student.log"
            if not student_log_file.exists():
                logger.warning(f"No student logs found for {student_id}, skipping report generation")
                return
            
            # Read logs content
            async with aiofiles.open(student_log_file, 'r', encoding='utf-8') as f:
                raw_student_logs = await f.read()
            
            if not raw_student_logs.strip():
                logger.warning(f"Empty student logs for {student_id}, skipping report generation")
                return
            
            # Filter logs based on volume and recency
            filtered_logs, start_date, end_date = self._filter_student_logs(raw_student_logs)
            
            if not filtered_logs.strip():
                logger.warning(f"No logs remaining after filtering for {student_id}, skipping report generation")
                return
            
            # Get student data
            logger.info(f"🔍 Getting student data for {student_id}")
            student_data = await self._get_student_data(student_id)
            student_name = student_data.get('name', f'Student {student_id}')
            logger.info(f"👤 Student name: {student_name}")
            
            # Initialize report generation service
            try:
                logger.info(f"🔧 Initializing report generation service")
                from report_service_factory import get_report_service, test_service_connection, get_service_info
                
                # Get the configured service (OpenRouter or Ollama)
                service = get_report_service()
                if not service:
                    logger.warning("No report generation service available, skipping report generation")
                    return
                
                # Log service information
                service_info = get_service_info()
                logger.info(f"Using {service_info['primary_service']} service for report generation")
                
                # Test connection first
                logger.info(f"🔌 Testing connection to {service_info['primary_service']}")
                connection_ok = await test_service_connection(service)
                if not connection_ok:
                    logger.warning(f"❌ {service_info['primary_service']} connection failed, skipping report generation")
                    return
                
                logger.info(f"✅ Connection to {service_info['primary_service']} successful")
                
                # Generate report
                logger.info(f"🤖 Calling {service_info['primary_service']} to generate report for {student_id}")
                
                # Create enhanced logs with period information
                report_period = f"{start_date} to {end_date}" if start_date != "Unknown" else "Full history"
                total_records = len(filtered_logs.split('\n')) if filtered_logs else 0
                
                enhanced_student_logs = f"""STUDENT DATA:
- ID: {student_id}
- Name: {student_name}
- Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Report Period: {report_period} ({total_records} records)
- Data Volume: {len(filtered_logs)} characters of activity

xAPI LOGS TO ANALYZE:
{filtered_logs}"""
                
                report_result = await service.generate_student_report(
                    student_logs=enhanced_student_logs,
                    student_id=student_id,
                    student_name=student_name
                )
                
                if report_result["success"]:
                    # Save report
                    await self._save_performance_report(student_id, report_result)
                    logger.info(f"✅ Performance report generated and saved for student {student_id}")
                    return True  # Indicate success
                else:
                    logger.error(f"❌ Failed to generate report for {student_id}: {report_result.get('error', 'Unknown error')}")
                    # Log additional debug information
                    logger.error(f"   Report result details: {report_result}")
                    return False  # Indicate failure
                    
            except ImportError:
                logger.warning("❌ Report generation service not available, skipping report generation")
                return False
            except Exception as service_error:
                logger.error(f"❌ Error with report generation service: {service_error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error generating performance report for {student_id}: {e}")
            return False
    
    async def _generate_performance_report_async(self, student_id: str, student_logs_dir: Path):
        """Generate performance report asynchronously without blocking sync response"""
        try:
            logger.info(f"📊 Starting background performance report generation for student {student_id}")
            logger.info(f"🔍 Current event loop: {asyncio.current_task()}")
            
            # Add timeout to prevent hanging indefinitely
            timeout_seconds = int(os.getenv("TIMEOUT_SECONDS", "300"))  # 5 minutes default
            logger.info(f"⏱️ Report generation timeout set to {timeout_seconds} seconds")
            
            success = await asyncio.wait_for(
                self._generate_performance_report(student_id, student_logs_dir),
                timeout=timeout_seconds
            )
            
            if success:
                logger.info(f"✅ Background performance report completed successfully for student {student_id}")
            else:
                logger.error(f"❌ Background performance report failed for student {student_id}")
                
        except asyncio.TimeoutError:
            logger.error(f"⏰ Background performance report timed out after {timeout_seconds}s for student {student_id}")
        except Exception as e:
            logger.error(f"❌ Background performance report failed for student {student_id}: {e}")
            # Don't re-raise - this is background task, shouldn't affect sync
    
    async def _ensure_student_registered(self, student_id: str, student_data: Dict):
        """Ensure student is registered in tutor-app, create if not exists"""
        try:
            student_file = self.students_dir / f"{student_id}.json"
            
            # Debug logging for student creation investigation
            logger.info(f"🔍 Checking student registration:")
            logger.info(f"  🆔 Student ID: {student_id}")
            logger.info(f"  📁 Student file path: {student_file}")
            logger.info(f"  📄 File exists: {student_file.exists()}")
            
            if not student_file.exists():
                # Student doesn't exist, create registration
                logger.info(f"🆕 Creating new student registration for: {student_id}")
                
                # Get all available content files
                available_content = await self._get_available_content_files()
                
                # Create default student configuration
                new_student_config = {
                    "id": student_id,
                    "name": student_data.get("name", f"Student {student_id}"),
                    "created_at": datetime.now().isoformat(),
                    "last_sync": datetime.now().isoformat(),
                    "assigned_files": available_content,  # Assign all available content by default
                    "status": "active",
                    "auto_created": True,
                    "sync_history": [
                        {
                            "timestamp": datetime.now().isoformat(),
                            "type": "initial_registration",
                            "source": "sync_from_student"
                        }
                    ]
                }
                
                # Save student configuration
                async with aiofiles.open(student_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(new_student_config, indent=2, ensure_ascii=False))
                
                # Create student reports directory (consistent with manual student creation)
                from pathlib import Path
                reports_dir = Path("reports") / student_id
                reports_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"📁 Created reports directory: {reports_dir}")
                
                logger.info(f"✅ Student {student_id} registered successfully")
                logger.info(f"📝 Name: {new_student_config['name']}")
                logger.info(f"📚 Assigned content: {len(new_student_config['assigned_files'])} files")
                
            else:
                # Student exists, update last sync time and name if provided
                async with aiofiles.open(student_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                existing_config = json.loads(content)
                
                # Update last sync time
                existing_config["last_sync"] = datetime.now().isoformat()
                
                # Update name if provided and different
                new_name = student_data.get("name")
                if new_name and new_name != existing_config.get("name"):
                    logger.info(f"📝 Updating student name: {existing_config.get('name')} → {new_name}")
                    existing_config["name"] = new_name
                
                # Add sync history entry
                if "sync_history" not in existing_config:
                    existing_config["sync_history"] = []
                
                existing_config["sync_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "sync_update",
                    "source": "sync_from_student"
                })
                
                # Keep only last 10 sync history entries
                existing_config["sync_history"] = existing_config["sync_history"][-10:]
                
                # Save updated configuration
                async with aiofiles.open(student_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(existing_config, indent=2, ensure_ascii=False))
                
                logger.debug(f"🔄 Updated sync info for student {student_id}")
                
        except Exception as e:
            logger.error(f"❌ Error ensuring student registration for {student_id}: {e}")
            # Don't raise exception - continue with sync even if registration fails
    
    async def _get_available_content_files(self) -> List[str]:
        """Get list of all available content files in tutor-app"""
        try:
            content_files = []
            if self.content_dir.exists():
                for content_file in self.content_dir.glob("*.txt"):
                    content_files.append(content_file.name)
            
            logger.info(f"📚 Found {len(content_files)} available content files: {content_files}")
            return sorted(content_files)  # Return sorted list for consistency
            
        except Exception as e:
            logger.error(f"Error getting available content files: {e}")
            # Return default list as fallback
            return [
                "photosynthesis.txt",
                "argumentative_essay.txt", 
                "emergency_blackout_response.txt",
                "quanzhou_site_of_encounter.txt",
                "scale_drawings.txt"
            ]
    
    async def _get_student_data(self, student_id: str) -> Dict:
        """Get student data from JSON file"""
        try:
            student_file = self.students_dir / f"{student_id}.json"
            if student_file.exists():
                async with aiofiles.open(student_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                return json.loads(content)
            return {}
        except Exception as e:
            logger.error(f"Error getting student data for {student_id}: {e}")
            return {}
    
    async def _save_performance_report(self, student_id: str, report_result: Dict):
        """Save generated performance report as human-readable text file"""
        try:
            # Create reports directory
            reports_dir = Path("reports") / student_id
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Create report filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = reports_dir / f"performance_report_{timestamp}.txt"
            
            # Format report as human-readable text
            report_text = self._format_report_as_text(student_id, report_result)
            
            # Save to text file
            async with aiofiles.open(report_file, 'w', encoding='utf-8') as f:
                await f.write(report_text)
            
            logger.info(f"Performance report saved to: {report_file}")
            
        except Exception as e:
            logger.error(f"Error saving performance report for {student_id}: {e}")
    
    def _format_report_as_text(self, student_id: str, report_result: Dict) -> str:
        """Format parsed report data as human-readable text (simplified structure)"""
        lines = []
        
        # Header with metadata
        lines.append("=" * 80)
        lines.append("STUDENT PERFORMANCE REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Student ID: {student_id}")
        lines.append(f"Student Name: {report_result.get('student_name', 'Unknown')}")
        lines.append(f"Generated: {report_result.get('report_date', 'Unknown')}")
        lines.append("")
        
        # Check if parsing was successful
        parsed_data = report_result.get("parsed")
        if not parsed_data:
            lines.append("⚠️  PARSING FAILED - RAW MODEL RESPONSE:")
            lines.append("-" * 50)
            lines.append(report_result.get("response", "No response available"))
            return "\n".join(lines)
        
        
        # New simplified structure sections
        
        # Executive Summary
        if 'executive_summary' in parsed_data:
            lines.append("📋 EXECUTIVE SUMMARY")
            lines.append("-" * 40)
            lines.append(self._format_narrative_text(parsed_data['executive_summary']))
            lines.append("")
        
        # Findings
        if 'findings' in parsed_data:
            lines.append("🔍 FINDINGS")
            lines.append("-" * 40)
            lines.append(self._format_narrative_text(parsed_data['findings']))
            lines.append("")
        
        # Progression
        if 'progression' in parsed_data:
            lines.append("📈 PROGRESSION")
            lines.append("-" * 40)
            lines.append(self._format_narrative_text(parsed_data['progression']))
            lines.append("")
        
        # Recommendations
        if 'recommendations' in parsed_data:
            lines.append("💡 RECOMMENDATIONS")
            lines.append("-" * 40)
            lines.append(self._format_narrative_text(parsed_data['recommendations']))
            lines.append("")
        
        # Priority Focus
        if 'priority_focus' in parsed_data:
            lines.append("🎯 PRIORITY FOCUS")
            lines.append("-" * 40)
            lines.append(self._format_narrative_text(parsed_data['priority_focus']))
            lines.append("")
        
        # Notes (optional section)
        if 'notes' in parsed_data and parsed_data['notes'].strip():
            lines.append("📝 NOTES")
            lines.append("-" * 40)
            lines.append(self._format_narrative_text(parsed_data['notes']))
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _format_narrative_text(self, text: str) -> str:
        """Format narrative text for better readability in reports"""
        if not text or not isinstance(text, str):
            return "No content available"
        
        # Clean up the text
        text = text.strip()
        
        # Handle bullet points - if text contains markdown bullets, preserve them
        if '•' in text or '- ' in text or '* ' in text:
            lines = text.split('\n')
            formatted_lines = []
            for line in lines:
                line = line.strip()
                if line:
                    # Indent bullet points
                    if line.startswith(('•', '-', '*')):
                        formatted_lines.append(f"  {line}")
                    else:
                        formatted_lines.append(line)
            return '\n'.join(formatted_lines)
        
        # For regular narrative text, ensure proper line breaks for readability
        # Split long paragraphs if they exceed reasonable length
        paragraphs = text.split('\n\n')
        formatted_paragraphs = []
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph:
                # Wrap very long paragraphs
                if len(paragraph) > 500:
                    # Try to find natural break points (sentences)
                    sentences = paragraph.split('. ')
                    if len(sentences) > 1:
                        # Group sentences into smaller chunks
                        chunks = []
                        current_chunk = []
                        current_length = 0
                        
                        for sentence in sentences:
                            sentence = sentence.strip()
                            if not sentence.endswith('.') and sentence != sentences[-1]:
                                sentence += '.'
                            
                            if current_length + len(sentence) > 250 and current_chunk:
                                chunks.append(' '.join(current_chunk))
                                current_chunk = [sentence]
                                current_length = len(sentence)
                            else:
                                current_chunk.append(sentence)
                                current_length += len(sentence)
                        
                        if current_chunk:
                            chunks.append(' '.join(current_chunk))
                        
                        formatted_paragraphs.extend(chunks)
                    else:
                        formatted_paragraphs.append(paragraph)
                else:
                    formatted_paragraphs.append(paragraph)
        
        return '\n\n'.join(formatted_paragraphs)
    
    async def get_content_for_student(self, student_id: str) -> Dict:
        """Get content files that should be sent to student"""
        try:
            assigned_files = await self._get_assigned_content(student_id)
            content_data = {}
            
            for filename in assigned_files:
                content_file = self.content_dir / filename
                if content_file.exists():
                    async with aiofiles.open(content_file, 'r', encoding='utf-8') as f:
                        content = await f.read()
                    content_data[filename] = content
            
            return {
                'assigned_files': assigned_files,
                'content_data': content_data
            }
        except Exception as e:
            logger.error(f"Error getting content for student {student_id}: {e}")
            return {'assigned_files': [], 'content_data': {}}