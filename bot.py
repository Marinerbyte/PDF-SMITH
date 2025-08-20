import os
import logging
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers import (
    start_handler, help_handler, txt2pdf_handler, img2pdf_handler, 
    doc2pdf_handler, mergepdf_handler, splitpdf_handler,
    button_callback_handler, message_handler
)
from master_control import handle_master_login
from cleanup_system import cleanup_system

logger = logging.getLogger(__name__)

def setup_bot():
    """Setup and configure the Telegram bot"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    
    # Create bot instance
    bot = Bot(token=token)
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("txt2pdf", txt2pdf_handler))
    application.add_handler(CommandHandler("img2pdf", img2pdf_handler))
    application.add_handler(CommandHandler("doc2pdf", doc2pdf_handler))
    application.add_handler(CommandHandler("mergepdf", mergepdf_handler))
    application.add_handler(CommandHandler("splitpdf", splitpdf_handler))
    
    # Master control commands
    application.add_handler(CommandHandler("master", handle_master_login))
    application.add_handler(CommandHandler("admin", handle_master_login))
    
    # Callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    
    # Message handler for file uploads and text
    application.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.Document.ALL, 
        message_handler
    ))
    
    # Initialize cleanup system
    cleanup_system.schedule_cleanup()
    logger.info("Cleanup system initialized with hourly schedule")
    
    return application

import threading
import queue

# Global application instance
_application_instance = None
_update_queue = queue.Queue()
_processing_thread = None

def start_update_processor():
    """Start a background thread to process updates"""
    global _processing_thread
    if _processing_thread is None or not _processing_thread.is_alive():
        _processing_thread = threading.Thread(target=_update_processor, daemon=True)
        _processing_thread.start()

def _update_processor():
    """Background thread function to process updates"""
    import asyncio
    
    async def process_updates():
        global _application_instance
        if _application_instance and not _application_instance.running:
            await _application_instance.initialize()
            
        while True:
            try:
                # Get update from queue (blocking)
                update_data = _update_queue.get(timeout=1)
                if _application_instance:
                    update = Update.de_json(update_data, _application_instance.bot)
                    if update:
                        await _application_instance.process_update(update)
                _update_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in update processor: {e}")
    
    # Run the async processing loop
    asyncio.run(process_updates())

def process_update(application, update_data):
    """Queue incoming Telegram update for processing"""
    global _application_instance, _update_queue
    
    try:
        # Set the global application instance
        _application_instance = application
        
        # Start the update processor if not running
        start_update_processor()
        
        # Add update to queue for processing
        _update_queue.put(update_data)
        
    except Exception as e:
        logger.error(f"Error queuing update: {e}")
