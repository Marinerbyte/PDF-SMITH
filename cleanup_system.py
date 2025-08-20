import os
import tempfile
import time
import logging
import schedule
import threading
from datetime import datetime, timedelta
import glob

logger = logging.getLogger(__name__)

class CleanupSystem:
    def __init__(self):
        self.temp_dirs = [tempfile.gettempdir(), '/tmp']
        self.max_file_age_hours = 1  # Files older than 1 hour will be deleted
        self.cleanup_patterns = [
            'split_*.pdf',
            'merge_*.pdf', 
            'img_*.pdf',
            'doc_*.pdf',
            'text_*.pdf',
            '*.tmp',
            'temp_*'
        ]
    
    def cleanup_temp_files(self):
        """Clean up temporary files older than specified time"""
        try:
            deleted_count = 0
            total_size_freed = 0
            cutoff_time = time.time() - (self.max_file_age_hours * 3600)
            
            for temp_dir in self.temp_dirs:
                if not os.path.exists(temp_dir):
                    continue
                    
                for pattern in self.cleanup_patterns:
                    file_pattern = os.path.join(temp_dir, pattern)
                    for file_path in glob.glob(file_pattern):
                        try:
                            file_stat = os.stat(file_path)
                            if file_stat.st_mtime < cutoff_time:
                                file_size = file_stat.st_size
                                os.unlink(file_path)
                                deleted_count += 1
                                total_size_freed += file_size
                                logger.info(f"Deleted temp file: {file_path}")
                        except (OSError, FileNotFoundError):
                            continue
            
            logger.info(f"Cleanup completed: {deleted_count} files deleted, {total_size_freed/1024/1024:.2f} MB freed")
            return deleted_count, total_size_freed
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0, 0
    
    def get_temp_stats(self):
        """Get statistics about temporary files"""
        try:
            total_files = 0
            total_size = 0
            
            for temp_dir in self.temp_dirs:
                if not os.path.exists(temp_dir):
                    continue
                    
                for pattern in self.cleanup_patterns:
                    file_pattern = os.path.join(temp_dir, pattern)
                    for file_path in glob.glob(file_pattern):
                        try:
                            file_stat = os.stat(file_path)
                            total_files += 1
                            total_size += file_stat.st_size
                        except (OSError, FileNotFoundError):
                            continue
            
            return total_files, total_size
            
        except Exception as e:
            logger.error(f"Error getting temp stats: {e}")
            return 0, 0
    
    def schedule_cleanup(self):
        """Schedule automatic cleanup every hour"""
        schedule.every().hour.do(self.cleanup_temp_files)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        # Run scheduler in background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Automatic cleanup scheduled every hour")

# Global cleanup system instance
cleanup_system = CleanupSystem()