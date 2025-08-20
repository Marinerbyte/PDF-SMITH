import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from user_states import UserStateManager
from cleanup_system import cleanup_system
import psutil

logger = logging.getLogger(__name__)

# Master control configuration
MASTER_ID = os.environ.get("MASTER_ID")  # Set in environment variables
MASTER_PASSWORD = os.environ.get("MASTER_PASSWORD", "admin123")  # Default password

class MasterControl:
    def __init__(self):
        self.authenticated_masters = set()
        self.user_stats = {}
    
    def is_master(self, user_id):
        """Check if user is master"""
        return str(user_id) == MASTER_ID
    
    def is_authenticated(self, user_id):
        """Check if master is authenticated"""
        return user_id in self.authenticated_masters
    
    def authenticate_master(self, user_id):
        """Authenticate master user"""
        self.authenticated_masters.add(user_id)
    
    def get_system_stats(self):
        """Get system statistics"""
        try:
            # CPU and Memory stats
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Temp file stats
            temp_files, temp_size = cleanup_system.get_temp_stats()
            
            stats = {
                'cpu_percent': cpu_percent,
                'memory_used': memory.used,
                'memory_total': memory.total,
                'memory_percent': memory.percent,
                'disk_used': disk.used,
                'disk_total': disk.total,
                'disk_percent': (disk.used / disk.total) * 100,
                'temp_files': temp_files,
                'temp_size': temp_size
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return None

# Global master control instance
master_control = MasterControl()

async def handle_master_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle master login command"""
    user_id = update.effective_user.id
    
    if not master_control.is_master(user_id):
        await update.message.reply_text(
            "❌ **Access Denied**\n\nYou are not authorized to use master commands.",
            parse_mode='Markdown'
        )
        return
    
    if master_control.is_authenticated(user_id):
        await show_master_panel(update, context)
        return
    
    # Request password
    state_manager = UserStateManager()
    state_manager.set_state(user_id, 'waiting_for_master_password')
    
    await update.message.reply_text(
        "🔐 **Master Authentication Required**\n\n"
        "Please enter the master password:",
        parse_mode='Markdown'
    )

async def handle_master_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle master password input"""
    user_id = update.effective_user.id
    password = update.message.text.strip()
    
    if password == MASTER_PASSWORD:
        master_control.authenticate_master(user_id)
        await update.message.reply_text(
            "✅ **Authentication Successful**\n\nWelcome to Master Control Panel!",
            parse_mode='Markdown'
        )
        await show_master_panel(update, context)
    else:
        await update.message.reply_text(
            "❌ **Invalid Password**\n\nAccess denied. Please try again.",
            parse_mode='Markdown'
        )

async def show_master_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show master control panel"""
    keyboard = [
        [InlineKeyboardButton("📊 System Stats", callback_data="master_stats"),
         InlineKeyboardButton("🧹 Manual Cleanup", callback_data="master_cleanup")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="master_broadcast"),
         InlineKeyboardButton("👥 User Statistics", callback_data="master_users")],
        [InlineKeyboardButton("🔧 Bot Settings", callback_data="master_settings"),
         InlineKeyboardButton("📋 Server Logs", callback_data="master_logs")],
        [InlineKeyboardButton("🔄 Restart Bot", callback_data="master_restart"),
         InlineKeyboardButton("🚫 Shutdown Bot", callback_data="master_shutdown")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
🎛️ **Master Control Panel**

Welcome to the bot administration interface. Choose an option below:

📊 **System Stats** - View server performance
🧹 **Manual Cleanup** - Clean temporary files now
📢 **Broadcast** - Send message to all users
👥 **User Stats** - View user activity
🔧 **Bot Settings** - Configure bot parameters
📋 **Server Logs** - View recent logs
🔄 **Restart Bot** - Restart bot service
🚫 **Shutdown** - Emergency shutdown
    """
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def handle_master_stats(query, context):
    """Handle system stats request"""
    await query.edit_message_text(
        "📊 **Loading System Statistics...**\n\nPlease wait...",
        parse_mode='Markdown'
    )
    
    stats = master_control.get_system_stats()
    
    if stats:
        text = f"""
📊 **System Statistics**

**💻 Server Performance:**
• CPU Usage: {stats['cpu_percent']:.1f}%
• Memory: {stats['memory_used']/1024/1024/1024:.1f}GB / {stats['memory_total']/1024/1024/1024:.1f}GB ({stats['memory_percent']:.1f}%)
• Disk: {stats['disk_used']/1024/1024/1024:.1f}GB / {stats['disk_total']/1024/1024/1024:.1f}GB ({stats['disk_percent']:.1f}%)

**🗂️ Temporary Files:**
• Count: {stats['temp_files']} files
• Size: {stats['temp_size']/1024/1024:.2f} MB

**⏰ Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
    else:
        text = "❌ **Error loading system statistics**\n\nPlease try again later."
    
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="master_stats"),
                 InlineKeyboardButton("🏠 Main Panel", callback_data="master_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_master_cleanup(query, context):
    """Handle manual cleanup request"""
    await query.edit_message_text(
        "🧹 **Running Manual Cleanup...**\n\nPlease wait...",
        parse_mode='Markdown'
    )
    
    deleted_count, size_freed = cleanup_system.cleanup_temp_files()
    
    text = f"""
🧹 **Cleanup Completed**

**Results:**
• Files deleted: {deleted_count}
• Space freed: {size_freed/1024/1024:.2f} MB
• Cleanup time: {datetime.now().strftime('%H:%M:%S')}

The server has been cleaned successfully!
    """
    
    keyboard = [[InlineKeyboardButton("🧹 Run Again", callback_data="master_cleanup"),
                 InlineKeyboardButton("🏠 Main Panel", callback_data="master_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_master_broadcast_request(query, context):
    """Handle broadcast message request"""
    user_id = query.from_user.id
    state_manager = UserStateManager()
    state_manager.set_state(user_id, 'waiting_for_broadcast_message')
    
    await query.edit_message_text(
        "📢 **Broadcast Message**\n\n"
        "Type the message you want to send to all bot users:\n\n"
        "**Note:** This will be sent to everyone who has used the bot.",
        parse_mode='Markdown'
    )

from datetime import datetime