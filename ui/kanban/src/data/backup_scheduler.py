"""
Automated Backup Scheduler for Evidence Management System.

This module provides automated backup scheduling capabilities for the
Evidence Management System, ensuring data is regularly backed up.
"""
import os
import logging
import json
import time
import shutil
import tempfile
import zipfile
import tarfile
import threading
import schedule
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from datetime import datetime, timedelta

from ..utils.exceptions import StorageError
from ..config.settings import get_project_root, load_config

# Configure module logger
logger = logging.getLogger(__name__)


class BackupJob:
    """Represents a scheduled backup job."""
    
    def __init__(self, 
                 name: str,
                 schedule_type: str,
                 source_dirs: List[str],
                 target_dir: str,
                 retention_days: int = 30,
                 compression: bool = True,
                 incremental: bool = True):
        """
        Initialize a backup job.
        
        Args:
            name: Name of the backup job
            schedule_type: Type of schedule (daily, weekly, monthly)
            source_dirs: List of directories to back up
            target_dir: Directory to store backups
            retention_days: Number of days to retain backups
            compression: Whether to compress backups
            incremental: Whether to use incremental backups
        """
        self.name = name
        self.schedule_type = schedule_type
        self.source_dirs = [Path(d) for d in source_dirs]
        self.target_dir = Path(target_dir)
        self.retention_days = retention_days
        self.compression = compression
        self.incremental = incremental
        
        # Status fields
        self.last_run = None
        self.next_run = None
        self.status = "scheduled"
        self.last_error = None
        self.last_size = 0
        self.history = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "schedule_type": self.schedule_type,
            "source_dirs": [str(d) for d in self.source_dirs],
            "target_dir": str(self.target_dir),
            "retention_days": self.retention_days,
            "compression": self.compression,
            "incremental": self.incremental,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "status": self.status,
            "last_error": self.last_error,
            "last_size": self.last_size,
            "history": self.history
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupJob':
        """Create a BackupJob instance from a dictionary."""
        job = cls(
            name=data["name"],
            schedule_type=data["schedule_type"],
            source_dirs=data["source_dirs"],
            target_dir=data["target_dir"],
            retention_days=data.get("retention_days", 30),
            compression=data.get("compression", True),
            incremental=data.get("incremental", True)
        )
        
        job.last_run = data.get("last_run")
        job.next_run = data.get("next_run")
        job.status = data.get("status", "scheduled")
        job.last_error = data.get("last_error")
        job.last_size = data.get("last_size", 0)
        job.history = data.get("history", [])
        
        return job


class BackupScheduler:
    """
    Manages scheduled backups for the Evidence Management System.
    
    This class provides automated backup scheduling capabilities, ensuring
    that evidence data is regularly backed up according to configurable
    schedules.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize the backup scheduler.
        
        Args:
            storage_dir: Optional directory for backup storage
        """
        self.config = load_config()
        self.project_root = get_project_root()
        
        # Set up storage directory
        if storage_dir:
            self.storage_dir = storage_dir
        else:
            data_dir = self.project_root / self.config['paths'].get('data', 'data')
            self.storage_dir = data_dir / 'evidence'
            
        # Set up backup directory
        self.backup_dir = self.storage_dir / 'backups'
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Set up backup config
        self.config_file = self.backup_dir / 'backup_schedule.json'
        self.backup_jobs = self._load_jobs()
        
        # Schedule objects
        self.scheduler = schedule.Scheduler()
        self._setup_schedules()
        
        # Background thread for scheduler
        self.scheduler_thread = None
        self.running = False
        
        logger.info(f"Initialized backup scheduler with {len(self.backup_jobs)} jobs")
    
    def _load_jobs(self) -> Dict[str, BackupJob]:
        """
        Load backup jobs from configuration.
        
        Returns:
            Dictionary of backup jobs
        """
        if not self.config_file.exists():
            # Create default backup jobs
            default_jobs = self._create_default_jobs()
            self._save_jobs(default_jobs)
            return default_jobs
        
        try:
            with open(self.config_file, 'r') as f:
                job_data = json.load(f)
                
            jobs = {}
            for name, data in job_data.items():
                jobs[name] = BackupJob.from_dict(data)
                
            return jobs
        except Exception as e:
            logger.error(f"Failed to load backup jobs: {str(e)}")
            # Return default jobs if load fails
            default_jobs = self._create_default_jobs()
            self._save_jobs(default_jobs)
            return default_jobs
    
    def _create_default_jobs(self) -> Dict[str, BackupJob]:
        """
        Create default backup jobs.
        
        Returns:
            Dictionary of default backup jobs
        """
        evidence_dir = self.storage_dir
        attachments_dir = self.storage_dir / 'attachments'
        
        # Create backup directories
        daily_dir = self.backup_dir / 'daily'
        weekly_dir = self.backup_dir / 'weekly'
        monthly_dir = self.backup_dir / 'monthly'
        
        os.makedirs(daily_dir, exist_ok=True)
        os.makedirs(weekly_dir, exist_ok=True)
        os.makedirs(monthly_dir, exist_ok=True)
        
        # Create default jobs
        jobs = {}
        
        # Daily backup of evidence
        jobs["daily_evidence"] = BackupJob(
            name="daily_evidence",
            schedule_type="daily",
            source_dirs=[str(evidence_dir)],
            target_dir=str(daily_dir),
            retention_days=7,
            compression=True,
            incremental=True
        )
        
        # Weekly backup of everything
        jobs["weekly_full"] = BackupJob(
            name="weekly_full",
            schedule_type="weekly",
            source_dirs=[str(evidence_dir), str(attachments_dir)],
            target_dir=str(weekly_dir),
            retention_days=30,
            compression=True,
            incremental=False
        )
        
        # Monthly backup for long-term storage
        jobs["monthly_archive"] = BackupJob(
            name="monthly_archive",
            schedule_type="monthly",
            source_dirs=[str(evidence_dir), str(attachments_dir)],
            target_dir=str(monthly_dir),
            retention_days=365,
            compression=True,
            incremental=False
        )
        
        return jobs
    
    def _save_jobs(self, jobs: Dict[str, BackupJob]) -> None:
        """
        Save backup jobs to configuration.
        
        Args:
            jobs: Dictionary of backup jobs
        """
        try:
            job_data = {name: job.to_dict() for name, job in jobs.items()}
            
            with open(self.config_file, 'w') as f:
                json.dump(job_data, f, indent=2)
                
            logger.info(f"Saved {len(jobs)} backup jobs to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save backup jobs: {str(e)}")
    
    def _setup_schedules(self) -> None:
        """Set up schedules for all backup jobs."""
        self.scheduler = schedule.Scheduler()
        
        for name, job in self.backup_jobs.items():
            if job.schedule_type == "daily":
                # Run daily at 1 AM
                self.scheduler.every().day.at("01:00").do(self._run_backup_job, name)
                next_run = self.scheduler.next_run()
                job.next_run = next_run.isoformat() if next_run else None
                
            elif job.schedule_type == "weekly":
                # Run weekly on Sunday at 2 AM
                self.scheduler.every().sunday.at("02:00").do(self._run_backup_job, name)
                next_run = self.scheduler.next_run()
                job.next_run = next_run.isoformat() if next_run else None
                
            elif job.schedule_type == "monthly":
                # Run monthly on the 1st at 3 AM
                self.scheduler.every().month_on_day(1).at("03:00").do(self._run_backup_job, name)
                next_run = self.scheduler.next_run()
                job.next_run = next_run.isoformat() if next_run else None
        
        # Save updated jobs with next_run times
        self._save_jobs(self.backup_jobs)
    
    def _run_backup_job(self, job_name: str) -> bool:
        """
        Run a backup job.
        
        Args:
            job_name: Name of the job to run
            
        Returns:
            True if backup was successful, False otherwise
        """
        if job_name not in self.backup_jobs:
            logger.error(f"Backup job not found: {job_name}")
            return False
        
        job = self.backup_jobs[job_name]
        logger.info(f"Starting backup job: {job_name}")
        
        # Update job status
        job.status = "running"
        job.last_run = datetime.now().isoformat()
        self._save_jobs(self.backup_jobs)
        
        try:
            # Create timestamp for this backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create backup directory
            backup_name = f"{job_name}_{timestamp}"
            job_target_dir = Path(job.target_dir)
            backup_path = job_target_dir / backup_name
            
            if job.compression:
                if job.incremental and job.last_run:
                    # Incremental backup
                    self._create_incremental_backup(job, backup_path)
                else:
                    # Full backup with compression
                    self._create_compressed_backup(job, backup_path)
            else:
                # Full backup without compression
                self._create_uncompressed_backup(job, backup_path)
            
            # Clean up old backups
            self._cleanup_old_backups(job)
            
            # Update job status
            job.status = "completed"
            job.last_error = None
            
            # Update next run time
            next_run = self.scheduler.next_run()
            job.next_run = next_run.isoformat() if next_run else None
            
            # Add to history
            job.history.append({
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
                "size": job.last_size
            })
            
            # Keep history manageable
            if len(job.history) > 100:
                job.history = job.history[-100:]
            
            self._save_jobs(self.backup_jobs)
            logger.info(f"Backup job completed: {job_name}")
            return True
            
        except Exception as e:
            error_msg = f"Backup job failed: {str(e)}"
            logger.error(error_msg)
            
            # Update job status
            job.status = "failed"
            job.last_error = error_msg
            
            # Add to history
            job.history.append({
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": error_msg
            })
            
            # Keep history manageable
            if len(job.history) > 100:
                job.history = job.history[-100:]
            
            self._save_jobs(self.backup_jobs)
            return False
    
    def _create_compressed_backup(self, job: BackupJob, backup_path: Path) -> None:
        """
        Create a compressed backup.
        
        Args:
            job: Backup job
            backup_path: Path to store the backup
        """
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Copy source directories to temp directory
            for source_dir in job.source_dirs:
                if source_dir.exists():
                    target_dir = temp_dir_path / source_dir.name
                    shutil.copytree(source_dir, target_dir)
            
            # Create compressed archive
            archive_path = str(backup_path) + ".tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(temp_dir, arcname="")
            
            # Get size of backup
            job.last_size = os.path.getsize(archive_path)
            
            logger.info(f"Created compressed backup: {archive_path} ({job.last_size} bytes)")
    
    def _create_uncompressed_backup(self, job: BackupJob, backup_path: Path) -> None:
        """
        Create an uncompressed backup.
        
        Args:
            job: Backup job
            backup_path: Path to store the backup
        """
        # Create backup directory
        os.makedirs(backup_path, exist_ok=True)
        
        # Copy source directories
        total_size = 0
        for source_dir in job.source_dirs:
            if source_dir.exists():
                target_dir = backup_path / source_dir.name
                shutil.copytree(source_dir, target_dir)
                
                # Calculate size
                for root, dirs, files in os.walk(target_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
        
        # Update job size
        job.last_size = total_size
        
        logger.info(f"Created uncompressed backup: {backup_path} ({total_size} bytes)")
    
    def _create_incremental_backup(self, job: BackupJob, backup_path: Path) -> None:
        """
        Create an incremental backup.
        
        Args:
            job: Backup job
            backup_path: Path to store the backup
        """
        # Find latest backup
        job_target_dir = Path(job.target_dir)
        latest_backup = None
        latest_time = datetime.min
        
        for item in job_target_dir.glob(f"{job.name}_*"):
            if item.is_dir() or (item.is_file() and item.suffix in ['.zip', '.tar.gz']):
                # Parse timestamp from name
                try:
                    name_parts = item.name.split('_')
                    timestamp_str = '_'.join(name_parts[1:])
                    timestamp = datetime.strptime(timestamp_str.split('.')[0], "%Y%m%d_%H%M%S")
                    
                    if timestamp > latest_time:
                        latest_time = timestamp
                        latest_backup = item
                except (ValueError, IndexError):
                    continue
        
        # If no previous backup, create a full backup
        if latest_backup is None:
            logger.info(f"No previous backup found for {job.name}, creating full backup")
            return self._create_compressed_backup(job, backup_path)
        
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Extract previous backup if it's compressed
            if latest_backup.is_file() and latest_backup.suffix in ['.zip', '.tar.gz']:
                with tarfile.open(latest_backup, "r:*") as tar:
                    tar.extractall(path=temp_dir_path)
            
            # Create incremental backup
            archive_path = str(backup_path) + ".tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                # For each source directory
                for source_dir in job.source_dirs:
                    if source_dir.exists():
                        # Compare with previous backup and only add changed/new files
                        prev_dir = temp_dir_path / source_dir.name
                        
                        for root, dirs, files in os.walk(source_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                rel_path = os.path.relpath(file_path, source_dir)
                                prev_file = prev_dir / rel_path
                                
                                # Add file if it's new or modified
                                if not prev_file.exists() or os.path.getmtime(file_path) > os.path.getmtime(prev_file):
                                    tar.add(file_path, arcname=os.path.join(source_dir.name, rel_path))
            
            # Get size of backup
            job.last_size = os.path.getsize(archive_path)
            
            logger.info(f"Created incremental backup: {archive_path} ({job.last_size} bytes)")
    
    def _cleanup_old_backups(self, job: BackupJob) -> None:
        """
        Clean up old backups based on retention policy.
        
        Args:
            job: Backup job
        """
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=job.retention_days)
        job_target_dir = Path(job.target_dir)
        
        # Find and delete old backups
        for item in job_target_dir.glob(f"{job.name}_*"):
            if item.is_dir() or (item.is_file() and item.suffix in ['.zip', '.tar.gz']):
                # Parse timestamp from name
                try:
                    name_parts = item.name.split('_')
                    timestamp_str = '_'.join(name_parts[1:])
                    timestamp = datetime.strptime(timestamp_str.split('.')[0], "%Y%m%d_%H%M%S")
                    
                    if timestamp < cutoff_date:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            os.remove(item)
                        logger.info(f"Deleted old backup: {item}")
                except (ValueError, IndexError):
                    continue
    
    def start(self) -> None:
        """Start the backup scheduler in a background thread."""
        if self.running:
            logger.warning("Backup scheduler is already running")
            return
        
        self.running = True
        
        def run_scheduler():
            logger.info("Backup scheduler thread started")
            while self.running:
                self.scheduler.run_pending()
                time.sleep(60)  # Check every minute
            logger.info("Backup scheduler thread stopped")
        
        self.scheduler_thread = threading.Thread(target=run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info("Backup scheduler started")
    
    def stop(self) -> None:
        """Stop the backup scheduler."""
        if not self.running:
            logger.warning("Backup scheduler is not running")
            return
        
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            self.scheduler_thread = None
        
        logger.info("Backup scheduler stopped")
    
    def get_job(self, job_name: str) -> Optional[BackupJob]:
        """
        Get a backup job by name.
        
        Args:
            job_name: Name of the job
            
        Returns:
            BackupJob or None if not found
        """
        return self.backup_jobs.get(job_name)
    
    def get_all_jobs(self) -> Dict[str, BackupJob]:
        """
        Get all backup jobs.
        
        Returns:
            Dictionary of backup jobs
        """
        return self.backup_jobs
    
    def add_job(self, job: BackupJob) -> None:
        """
        Add a new backup job.
        
        Args:
            job: Backup job to add
        """
        if job.name in self.backup_jobs:
            logger.warning(f"Backup job already exists: {job.name}")
            return
        
        self.backup_jobs[job.name] = job
        self._setup_schedules()
        self._save_jobs(self.backup_jobs)
        
        logger.info(f"Added backup job: {job.name}")
    
    def update_job(self, job: BackupJob) -> None:
        """
        Update an existing backup job.
        
        Args:
            job: Backup job to update
        """
        if job.name not in self.backup_jobs:
            logger.warning(f"Backup job not found: {job.name}")
            return
        
        self.backup_jobs[job.name] = job
        self._setup_schedules()
        self._save_jobs(self.backup_jobs)
        
        logger.info(f"Updated backup job: {job.name}")
    
    def delete_job(self, job_name: str) -> bool:
        """
        Delete a backup job.
        
        Args:
            job_name: Name of the job to delete
            
        Returns:
            True if deleted, False if not found
        """
        if job_name not in self.backup_jobs:
            logger.warning(f"Backup job not found: {job_name}")
            return False
        
        del self.backup_jobs[job_name]
        self._setup_schedules()
        self._save_jobs(self.backup_jobs)
        
        logger.info(f"Deleted backup job: {job_name}")
        return True
    
    def run_job_now(self, job_name: str) -> bool:
        """
        Run a backup job immediately.
        
        Args:
            job_name: Name of the job to run
            
        Returns:
            True if backup was successful, False otherwise
        """
        return self._run_backup_job(job_name)
    
    def verify_backup(self, backup_path: Union[str, Path]) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify backup integrity.
        
        Args:
            backup_path: Path to the backup
            
        Returns:
            Tuple of (is_valid, verification_info)
        """
        backup_path = Path(backup_path)
        result = {"valid": False, "errors": [], "info": {}}
        
        try:
            # Check if backup exists
            if not backup_path.exists():
                result["errors"].append(f"Backup not found: {backup_path}")
                return False, result
            
            # Check backup type
            if backup_path.is_file():
                # Compressed backup
                if backup_path.suffix in ['.zip']:
                    # Verify ZIP file
                    try:
                        with zipfile.ZipFile(backup_path, 'r') as zip_ref:
                            # Test for corruption
                            test_result = zip_ref.testzip()
                            if test_result is not None:
                                result["errors"].append(f"Corrupted file in ZIP: {test_result}")
                                return False, result
                            
                            # Get file list
                            result["info"]["files"] = len(zip_ref.namelist())
                            result["info"]["size"] = os.path.getsize(backup_path)
                            result["info"]["format"] = "zip"
                    except zipfile.BadZipFile:
                        result["errors"].append(f"Invalid ZIP file: {backup_path}")
                        return False, result
                    
                elif backup_path.suffix in ['.gz', '.bz2', '.xz'] or backup_path.name.endswith('.tar.gz'):
                    # Verify TAR file
                    try:
                        with tarfile.open(backup_path, 'r:*') as tar:
                            # Check for errors
                            try:
                                tar.getmembers()
                            except Exception as e:
                                result["errors"].append(f"Error reading TAR file: {str(e)}")
                                return False, result
                            
                            # Get file list
                            members = tar.getmembers()
                            result["info"]["files"] = len(members)
                            result["info"]["size"] = os.path.getsize(backup_path)
                            result["info"]["format"] = "tar"
                    except tarfile.ReadError:
                        result["errors"].append(f"Invalid TAR file: {backup_path}")
                        return False, result
                
                else:
                    result["errors"].append(f"Unsupported backup format: {backup_path}")
                    return False, result
            
            elif backup_path.is_dir():
                # Uncompressed backup
                file_count = 0
                total_size = 0
                
                for root, dirs, files in os.walk(backup_path):
                    file_count += len(files)
                    for file in files:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                
                result["info"]["files"] = file_count
                result["info"]["size"] = total_size
                result["info"]["format"] = "directory"
            
            else:
                result["errors"].append(f"Unsupported backup type: {backup_path}")
                return False, result
            
            # Add more info
            if backup_path.is_file():
                created_time = datetime.fromtimestamp(os.path.getctime(backup_path))
            else:
                created_time = datetime.fromtimestamp(os.path.getctime(backup_path))
                
            result["info"]["created"] = created_time.isoformat()
            result["valid"] = True
            
            return True, result
            
        except Exception as e:
            result["errors"].append(f"Verification error: {str(e)}")
            return False, result


# Helper function to create a backup scheduler
def get_backup_scheduler() -> BackupScheduler:
    """Get a configured backup scheduler instance."""
    return BackupScheduler()
