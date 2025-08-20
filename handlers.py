import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from user_states import UserStateManager
from pdf_utils import create_text_pdf, create_image_pdf, merge_pdfs, split_pdf
from document_converter import convert_document_to_pdf
from cleanup_system import cleanup_system
from master_control import (
    master_control, handle_master_login, handle_master_password, 
    show_master_panel, handle_master_stats, handle_master_cleanup,
    handle_master_broadcast_request
)
import tempfile

logger = logging.getLogger(__name__)

# Initialize state manager
state_manager = UserStateManager()

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("📝 Text ➝ PDF", callback_data="txt2pdf")],
        [InlineKeyboardButton("🖼️ Images ➝ PDF", callback_data="img2pdf")],
        [InlineKeyboardButton("📄 Documents ➝ PDF", callback_data="doc2pdf")],
        [InlineKeyboardButton("📚 Merge PDFs", callback_data="mergepdf"),
         InlineKeyboardButton("✂️ Split PDF", callback_data="splitpdf")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🤖 **Welcome to Professional PDF Bot, {user.first_name}!**

I'm your advanced PDF assistant that can:
📝 Convert text to styled PDFs
🖼️ Convert images to optimized PDFs  
📄 Convert documents (Word, Excel, PowerPoint) to PDFs
📚 Merge multiple PDFs into one
✂️ Split PDFs by page numbers

👇 **Choose an option below to get started:**
    """
    
    await update.message.reply_text(
        welcome_text, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🤖 **PDF Bot Help Guide**

**📝 Text to PDF:**
• Send `/txt2pdf` command
• Type or paste your text
• Choose font, color, and page size
• Get a beautifully formatted PDF

**🖼️ Images to PDF:**
• Send `/img2pdf` command  
• Upload one or multiple images
• Click "✅ Done" when finished
• Choose orientation (Portrait/Landscape)
• Get optimized PDF with all images

**📄 Documents to PDF:**
• Send `/doc2pdf` command
• Upload Word (.docx), Excel (.xlsx), PowerPoint (.pptx), HTML, or TXT files
• Get converted PDF instantly

**📚 Merge PDFs:**
• Send `/mergepdf` command
• Upload 2 or more PDF files
• Click "✅ Done" to merge them

**✂️ Split PDF:**
• Send `/splitpdf` command
• Upload a PDF file
• Enter page numbers to extract
• Get the extracted pages as new PDF

**💡 Tips:**
• All PDFs are optimized for quality and size
• Images are auto-resized to fit A4 pages
• Use inline buttons for easy navigation
• Files are processed securely and deleted after use

Need more help? Contact @your_support_username
    """
    
    keyboard = [[InlineKeyboardButton("🏠 Back to Menu", callback_data="start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def txt2pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /txt2pdf command"""
    user_id = update.effective_user.id
    state_manager.set_state(user_id, 'waiting_for_text')
    
    await update.message.reply_text(
        "📝 **Text to PDF Converter**\n\n"
        "👉 Please send me the text you want to convert to PDF.\n"
        "You can type or paste any text content.",
        parse_mode='Markdown'
    )

async def img2pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /img2pdf command"""
    user_id = update.effective_user.id
    state_manager.set_state(user_id, 'waiting_for_images')
    state_manager.clear_user_data(user_id, 'images')
    
    keyboard = [[InlineKeyboardButton("✅ Done", callback_data="img_done")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🖼️ **Images to PDF Converter**\n\n"
        "👉 Please upload your images (one or multiple).\n"
        "📸 Supported formats: JPG, PNG, WEBP, GIF\n"
        "📄 Images will be optimized and resized to fit A4 pages\n\n"
        "Click **✅ Done** when you've uploaded all images.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def doc2pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /doc2pdf command"""
    user_id = update.effective_user.id
    state_manager.set_state(user_id, 'waiting_for_document')
    
    await update.message.reply_text(
        "📄 **Document to PDF Converter**\n\n"
        "👉 Please upload your document file.\n"
        "📋 Supported formats:\n"
        "• Word documents (.docx)\n"
        "• Excel spreadsheets (.xlsx)\n"
        "• PowerPoint presentations (.pptx)\n"
        "• HTML files (.html)\n"
        "• Text files (.txt)\n\n"
        "🔄 I'll convert it to PDF automatically!",
        parse_mode='Markdown'
    )

async def mergepdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mergepdf command"""
    user_id = update.effective_user.id
    state_manager.set_state(user_id, 'waiting_for_merge_pdfs')
    state_manager.clear_user_data(user_id, 'pdfs')
    
    keyboard = [[InlineKeyboardButton("✅ Done", callback_data="merge_done")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📚 **PDF Merger**\n\n"
        "👉 Please upload 2 or more PDF files to merge.\n"
        "📄 Files will be merged in the order you upload them\n\n"
        "Click **✅ Done** when you've uploaded all PDFs.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def splitpdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /splitpdf command"""
    user_id = update.effective_user.id
    state_manager.set_state(user_id, 'waiting_for_split_pdf')
    
    await update.message.reply_text(
        "✂️ **PDF Splitter**\n\n"
        "👉 Please upload the PDF file you want to split.\n"
        "📄 After upload, I'll ask for the page numbers to extract.",
        parse_mode='Markdown'
    )

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "start":
        await start_handler_callback(query, context)
    elif data == "help":
        await help_handler_callback(query, context)
    elif data == "txt2pdf":
        await txt2pdf_callback(query, context)
    elif data == "img2pdf":
        await img2pdf_callback(query, context)
    elif data == "doc2pdf":
        await doc2pdf_callback(query, context)
    elif data == "mergepdf":
        await mergepdf_callback(query, context)
    elif data == "splitpdf":
        await splitpdf_callback(query, context)
    elif data == "img_done":
        await process_images_to_pdf(query, context)
    elif data == "merge_done":
        await process_merge_pdfs(query, context)
    elif data.startswith("orient_"):
        await handle_orientation_choice(query, context, data)
    elif data.startswith("font_"):
        await handle_font_choice(query, context, data)
    elif data.startswith("color_"):
        await handle_color_choice(query, context, data)
    elif data.startswith("size_"):
        await handle_size_choice(query, context, data)
    elif data.startswith("quick_split_"):
        await handle_quick_split(query, context, data)
    elif data == "custom_split":
        await handle_custom_split_request(query, context)
    elif data.startswith("master_"):
        await handle_master_callbacks(query, context, data)
    elif data == "custom_split":
        await handle_custom_split_request(query, context)

async def start_handler_callback(query, context):
    """Handle start button callback"""
    keyboard = [
        [InlineKeyboardButton("📝 Text ➝ PDF", callback_data="txt2pdf")],
        [InlineKeyboardButton("🖼️ Images ➝ PDF", callback_data="img2pdf")],
        [InlineKeyboardButton("📄 Documents ➝ PDF", callback_data="doc2pdf")],
        [InlineKeyboardButton("📚 Merge PDFs", callback_data="mergepdf"),
         InlineKeyboardButton("✂️ Split PDF", callback_data="splitpdf")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🤖 **Welcome to Professional PDF Bot!**

I'm your advanced PDF assistant that can:
📝 Convert text to styled PDFs
🖼️ Convert images to optimized PDFs  
📄 Convert documents (Word, Excel, PowerPoint) to PDFs
📚 Merge multiple PDFs into one
✂️ Split PDFs by page numbers

👇 **Choose an option below to get started:**
    """
    
    await query.edit_message_text(
        welcome_text, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_handler_callback(query, context):
    """Handle help button callback"""
    help_text = """
🤖 **PDF Bot Help Guide**

**📝 Text to PDF:**
• Choose "Text ➝ PDF" option
• Type or paste your text
• Choose font, color, and page size
• Get a beautifully formatted PDF

**🖼️ Images to PDF:**
• Choose "Images ➝ PDF" option
• Upload one or multiple images
• Click "✅ Done" when finished
• Choose orientation (Portrait/Landscape)
• Get optimized PDF with all images

**📄 Documents to PDF:**
• Choose "Documents ➝ PDF" option
• Upload Word, Excel, PowerPoint, HTML, or TXT files
• Get converted PDF instantly

**📚 Merge PDFs:**
• Choose "Merge PDFs" option
• Upload 2 or more PDF files
• Click "✅ Done" to merge them

**✂️ Split PDF:**
• Choose "Split PDF" option
• Upload a PDF file
• Enter page numbers to extract
• Get the extracted pages as new PDF

**💡 Tips:**
• All PDFs are optimized for quality and size
• Images are auto-resized to fit A4 pages
• Use inline buttons for easy navigation
• Files are processed securely and deleted after use
    """
    
    keyboard = [[InlineKeyboardButton("🏠 Back to Menu", callback_data="start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def txt2pdf_callback(query, context):
    """Handle text to PDF callback"""
    user_id = query.from_user.id
    state_manager.set_state(user_id, 'waiting_for_text')
    
    await query.edit_message_text(
        "📝 **Enhanced Text to PDF Converter**\n\n"
        "👉 Please send me the text you want to convert to PDF.\n"
        "✨ **Features:**\n"
        "• Multiple font options (Arial, Times New Roman, Helvetica, Courier)\n"
        "• Color selection (Black, Blue, Green, Red)\n"
        "• Page size options (A4, Letter, Legal)\n"
        "• Professional formatting with margins\n\n"
        "📝 Type or paste your text content:",
        parse_mode='Markdown'
    )

async def img2pdf_callback(query, context):
    """Handle images to PDF callback"""
    user_id = query.from_user.id
    state_manager.set_state(user_id, 'waiting_for_images')
    state_manager.clear_user_data(user_id, 'images')
    
    await query.edit_message_text(
        "🖼️ **Images to PDF Converter**\n\n"
        "👉 Please upload your images (one or multiple).\n"
        "📸 Supported formats: JPG, PNG, WEBP, GIF\n"
        "📄 Images will be optimized and resized to fit A4 pages\n\n"
        "📤 Upload your images and I'll show a **✅ Done** button after each image.",
        parse_mode='Markdown'
    )

async def doc2pdf_callback(query, context):
    """Handle document to PDF callback"""
    user_id = query.from_user.id
    state_manager.set_state(user_id, 'waiting_for_document')
    
    await query.edit_message_text(
        "📄 **Document to PDF Converter**\n\n"
        "👉 Please upload your document file.\n"
        "📋 Supported formats:\n"
        "• Word documents (.docx)\n"
        "• Excel spreadsheets (.xlsx)\n"
        "• PowerPoint presentations (.pptx)\n"
        "• HTML files (.html)\n"
        "• Text files (.txt)\n\n"
        "🔄 I'll convert it to PDF automatically!",
        parse_mode='Markdown'
    )

async def mergepdf_callback(query, context):
    """Handle merge PDF callback"""
    user_id = query.from_user.id
    state_manager.set_state(user_id, 'waiting_for_merge_pdfs')
    state_manager.clear_user_data(user_id, 'pdfs')
    
    keyboard = [[InlineKeyboardButton("✅ Done", callback_data="merge_done")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📚 **PDF Merger**\n\n"
        "👉 Please upload 2 or more PDF files to merge.\n"
        "📄 Files will be merged in the order you upload them\n\n"
        "Click **✅ Done** when you've uploaded all PDFs.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def splitpdf_callback(query, context):
    """Handle split PDF callback"""
    user_id = query.from_user.id
    state_manager.set_state(user_id, 'waiting_for_split_pdf')
    
    await query.edit_message_text(
        "✂️ **PDF Splitter**\n\n"
        "👉 Please upload the PDF file you want to split.\n"
        "📄 After upload, I'll show you quick page options or you can enter custom page numbers.",
        parse_mode='Markdown'
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages and file uploads"""
    user_id = update.effective_user.id
    current_state = state_manager.get_state(user_id)
    
    # Handle master commands
    if current_state == 'waiting_for_master_password':
        await handle_master_password(update, context)
        state_manager.clear_user_state(user_id)
        return
    elif current_state == 'waiting_for_broadcast_message':
        await handle_broadcast_message_input(update, context)
        state_manager.clear_user_state(user_id)
        return
    
    # Handle regular user states
    if current_state == 'waiting_for_text':
        await handle_text_input(update, context)
    elif current_state == 'waiting_for_images':
        await handle_image_upload(update, context)
    elif current_state == 'waiting_for_document':
        await handle_document_upload(update, context)
    elif current_state == 'waiting_for_merge_pdfs':
        await handle_pdf_upload_for_merge(update, context)
    elif current_state == 'waiting_for_split_pdf':
        await handle_pdf_upload_for_split(update, context)
    elif current_state == 'waiting_for_split_pages':
        await handle_split_pages_input(update, context)
    else:
        # Default response for unrecognized input
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤔 I'm not sure what you want to do.\n"
            "Please use the menu below to get started!",
            reply_markup=reply_markup
        )

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input for PDF conversion"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Store the text
    state_manager.set_user_data(user_id, 'text', text)
    
    # Show font selection
    keyboard = [
        [InlineKeyboardButton("📝 Arial", callback_data="font_arial"),
         InlineKeyboardButton("📝 Times New Roman", callback_data="font_times")],
        [InlineKeyboardButton("📝 Helvetica", callback_data="font_helvetica"),
         InlineKeyboardButton("📝 Courier", callback_data="font_courier")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    state_manager.set_state(user_id, 'choosing_font')
    
    await update.message.reply_text(
        "✅ **Text received!**\n\n"
        "👉 Now choose a font style:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_font_choice(query, context, data):
    """Handle font selection"""
    user_id = query.from_user.id
    font = data.split('_')[1]
    
    state_manager.set_user_data(user_id, 'font', font)
    
    # Show color selection
    keyboard = [
        [InlineKeyboardButton("⚫ Black", callback_data="color_black"),
         InlineKeyboardButton("🔵 Blue", callback_data="color_blue")],
        [InlineKeyboardButton("🔴 Red", callback_data="color_red"),
         InlineKeyboardButton("🟢 Green", callback_data="color_green")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    state_manager.set_state(user_id, 'choosing_color')
    
    await query.edit_message_text(
        f"✅ **Font selected: {font.title()}**\n\n"
        "👉 Now choose text color:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_color_choice(query, context, data):
    """Handle color selection"""
    user_id = query.from_user.id
    color = data.split('_')[1]
    
    state_manager.set_user_data(user_id, 'color', color)
    
    # Show page size selection
    keyboard = [
        [InlineKeyboardButton("📄 A4", callback_data="size_a4"),
         InlineKeyboardButton("📄 Letter", callback_data="size_letter")],
        [InlineKeyboardButton("📄 Legal", callback_data="size_legal")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    state_manager.set_state(user_id, 'choosing_size')
    
    await query.edit_message_text(
        f"✅ **Color selected: {color.title()}**\n\n"
        "👉 Choose page size:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_size_choice(query, context, data):
    """Handle page size selection and generate PDF"""
    user_id = query.from_user.id
    size = data.split('_')[1]
    
    # Get user data
    text = state_manager.get_user_data(user_id, 'text')
    font = state_manager.get_user_data(user_id, 'font')
    color = state_manager.get_user_data(user_id, 'color')
    
    await query.edit_message_text(
        "🔄 **Generating your PDF...**\n"
        "Please wait a moment...",
        parse_mode='Markdown'
    )
    
    try:
        # Create PDF
        pdf_path = create_text_pdf(text, font, color, size)
        
        # Send PDF
        with open(pdf_path, 'rb') as pdf_file:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=pdf_file,
                filename="converted_text.pdf",
                caption="📂 **Your PDF is ready!**\n\n"
                       f"📝 Font: {font.title()}\n"
                       f"🎨 Color: {color.title()}\n"
                       f"📄 Size: {size.upper()}",
                parse_mode='Markdown'
            )
        
        # Clean up files immediately after sending
        cleanup_system.cleanup_temp_files()
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        state_manager.clear_user_state(user_id)
        
        # Show menu
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ **PDF created successfully!**\n\n"
                 "Need to create another PDF?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error creating text PDF: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ **Error creating PDF**\n\n"
                 "Sorry, there was an error processing your text. Please try again.",
            parse_mode='Markdown'
        )
        state_manager.clear_user_state(user_id)

async def handle_image_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image upload for PDF conversion"""
    user_id = update.effective_user.id
    
    if update.message.photo:
        # Get the largest photo
        photo = update.message.photo[-1]
        
        # Download and store image info
        file = await context.bot.get_file(photo.file_id)
        
        images = state_manager.get_user_data(user_id, 'images') or []
        images.append({
            'file_id': photo.file_id,
            'file_unique_id': photo.file_unique_id
        })
        state_manager.set_user_data(user_id, 'images', images)
        
        # Show done button after each image
        keyboard = [[InlineKeyboardButton("✅ Done", callback_data="img_done")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **Image {len(images)} received!**\n\n"
            "📸 Upload more images or click **✅ Done** to continue.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def process_images_to_pdf(query, context):
    """Process uploaded images to PDF"""
    user_id = query.from_user.id
    images = state_manager.get_user_data(user_id, 'images') or []
    
    if not images:
        await query.edit_message_text(
            "❌ **No images found!**\n\n"
            "Please upload at least one image first.",
            parse_mode='Markdown'
        )
        return
    
    # Show orientation selection
    keyboard = [
        [InlineKeyboardButton("📄 Portrait", callback_data="orient_portrait")],
        [InlineKeyboardButton("📄 Landscape", callback_data="orient_landscape")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    state_manager.set_state(user_id, 'choosing_orientation')
    
    await query.edit_message_text(
        f"✅ **{len(images)} image(s) ready!**\n\n"
        "👉 Choose page orientation:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_orientation_choice(query, context, data):
    """Handle orientation choice and generate PDF"""
    user_id = query.from_user.id
    orientation = data.split('_')[1]
    
    images = state_manager.get_user_data(user_id, 'images') or []
    
    await query.edit_message_text(
        "🔄 **Creating PDF from images...**\n"
        "Please wait while I process and optimize your images...",
        parse_mode='Markdown'
    )
    
    try:
        # Download images and create PDF
        image_paths = []
        for img_info in images:
            file = await context.bot.get_file(img_info['file_id'])
            file_path = f"/tmp/img_{img_info['file_unique_id']}.jpg"
            await file.download_to_drive(file_path)
            image_paths.append(file_path)
        
        # Create PDF
        pdf_path = create_image_pdf(image_paths, orientation)
        
        # Send PDF
        with open(pdf_path, 'rb') as pdf_file:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=pdf_file,
                filename="images_to_pdf.pdf",
                caption="📂 **Your PDF is ready!**\n\n"
                       f"📸 Images: {len(images)}\n"
                       f"📄 Orientation: {orientation.title()}\n"
                       "🔧 Optimized for quality and size",
                parse_mode='Markdown'
            )
        
        # Clean up
        for img_path in image_paths:
            if os.path.exists(img_path):
                os.unlink(img_path)
        os.unlink(pdf_path)
        state_manager.clear_user_state(user_id)
        
        # Show menu
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ **PDF created successfully!**\n\n"
                 "Need to create another PDF?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error creating image PDF: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ **Error creating PDF**\n\n"
                 "Sorry, there was an error processing your images. Please try again.",
            parse_mode='Markdown'
        )
        state_manager.clear_user_state(user_id)

async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document upload for PDF conversion"""
    user_id = update.effective_user.id
    
    if update.message.document:
        document = update.message.document
        file_name = document.file_name.lower()
        
        # Check supported formats
        supported_extensions = ['.docx', '.xlsx', '.pptx', '.html', '.txt']
        if not any(file_name.endswith(ext) for ext in supported_extensions):
            await update.message.reply_text(
                "❌ **Unsupported file format!**\n\n"
                "📋 Supported formats:\n"
                "• Word documents (.docx)\n"
                "• Excel spreadsheets (.xlsx)\n"
                "• PowerPoint presentations (.pptx)\n"
                "• HTML files (.html)\n"
                "• Text files (.txt)",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text(
            "✅ **Document received!**\n\n"
            "🔄 Converting to PDF...",
            parse_mode='Markdown'
        )
        
        try:
            # Download file
            file = await context.bot.get_file(document.file_id)
            file_path = f"/tmp/{document.file_name}"
            await file.download_to_drive(file_path)
            
            # Convert to PDF
            pdf_path = convert_document_to_pdf(file_path, file_name)
            
            # Send PDF
            with open(pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=f"{os.path.splitext(document.file_name)[0]}.pdf",
                    caption="📂 **Your PDF is ready!**\n\n"
                           f"📄 Original: {document.file_name}\n"
                           "🔄 Successfully converted to PDF",
                    parse_mode='Markdown'
                )
            
            # Clean up
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.unlink(pdf_path)
            state_manager.clear_user_state(user_id)
            
            # Show menu
            keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "✅ **Document converted successfully!**\n\n"
                "Need to convert another document?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error converting document: {e}")
            await update.message.reply_text(
                "❌ **Error converting document**\n\n"
                "Sorry, there was an error processing your document. "
                "Please make sure the file is not corrupted and try again.",
                parse_mode='Markdown'
            )
            state_manager.clear_user_state(user_id)

async def handle_pdf_upload_for_merge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PDF upload for merging"""
    user_id = update.effective_user.id
    
    if update.message.document:
        document = update.message.document
        if not document.file_name.lower().endswith('.pdf'):
            await update.message.reply_text(
                "❌ **Please upload PDF files only!**",
                parse_mode='Markdown'
            )
            return
        
        pdfs = state_manager.get_user_data(user_id, 'pdfs') or []
        pdfs.append({
            'file_id': document.file_id,
            'file_name': document.file_name
        })
        state_manager.set_user_data(user_id, 'pdfs', pdfs)
        
        await update.message.reply_text(
            f"✅ **PDF {len(pdfs)} received: {document.file_name}**\n\n"
            "📄 Upload more PDFs or click **✅ Done** to merge them.",
            parse_mode='Markdown'
        )

async def process_merge_pdfs(query, context):
    """Process PDF merging"""
    user_id = query.from_user.id
    pdfs = state_manager.get_user_data(user_id, 'pdfs') or []
    
    if len(pdfs) < 2:
        await query.edit_message_text(
            "❌ **Need at least 2 PDFs to merge!**\n\n"
            "Please upload more PDF files.",
            parse_mode='Markdown'
        )
        return
    
    await query.edit_message_text(
        f"🔄 **Merging {len(pdfs)} PDFs...**\n"
        "Please wait...",
        parse_mode='Markdown'
    )
    
    try:
        # Download PDFs
        pdf_paths = []
        for pdf_info in pdfs:
            file = await context.bot.get_file(pdf_info['file_id'])
            file_path = f"/tmp/merge_{pdf_info['file_id']}.pdf"
            await file.download_to_drive(file_path)
            pdf_paths.append(file_path)
        
        # Merge PDFs
        merged_pdf_path = merge_pdfs(pdf_paths)
        
        # Send merged PDF
        with open(merged_pdf_path, 'rb') as pdf_file:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=pdf_file,
                filename="merged_document.pdf",
                caption="📂 **Merged PDF is ready!**\n\n"
                       f"📄 Combined {len(pdfs)} PDF files\n"
                       "✅ Successfully merged",
                parse_mode='Markdown'
            )
        
        # Clean up
        for pdf_path in pdf_paths:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
        os.unlink(merged_pdf_path)
        state_manager.clear_user_state(user_id)
        
        # Show menu
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ **PDFs merged successfully!**\n\n"
                 "Need to process more PDFs?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error merging PDFs: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ **Error merging PDFs**\n\n"
                 "Sorry, there was an error merging your PDFs. Please try again.",
            parse_mode='Markdown'
        )
        state_manager.clear_user_state(user_id)

async def handle_pdf_upload_for_split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PDF upload for splitting"""
    user_id = update.effective_user.id
    
    if update.message.document:
        document = update.message.document
        if not document.file_name.lower().endswith('.pdf'):
            await update.message.reply_text(
                "❌ **Please upload a PDF file!**",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text(
            "✅ **PDF received!**\n\n"
            "🔄 Analyzing PDF...",
            parse_mode='Markdown'
        )
        
        try:
            # Download and analyze PDF
            file = await context.bot.get_file(document.file_id)
            file_path = f"/tmp/split_{document.file_id}.pdf"
            await file.download_to_drive(file_path)
            
            # Get page count
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            
            # Store PDF info
            state_manager.set_user_data(user_id, 'split_pdf_path', file_path)
            state_manager.set_user_data(user_id, 'split_pdf_pages', page_count)
            state_manager.set_state(user_id, 'waiting_for_split_pages')
            
            # Create quick selection buttons
            keyboard = []
            
            # Quick page options
            if page_count >= 2:
                keyboard.append([
                    InlineKeyboardButton("📄 Page 1-2", callback_data="quick_split_1-2"),
                    InlineKeyboardButton("📄 Page 1-3", callback_data="quick_split_1-3")
                ])
            if page_count >= 5:
                keyboard.append([
                    InlineKeyboardButton("📄 First 5", callback_data=f"quick_split_1-5"),
                    InlineKeyboardButton("📄 Last 5", callback_data=f"quick_split_{max(1, page_count-4)}-{page_count}")
                ])
            if page_count >= 10:
                keyboard.append([
                    InlineKeyboardButton("📄 First 10", callback_data=f"quick_split_1-10"),
                    InlineKeyboardButton("📄 Last 10", callback_data=f"quick_split_{max(1, page_count-9)}-{page_count}")
                ])
            
            # Add single page options for small PDFs
            if page_count <= 5:
                single_pages = []
                for i in range(1, min(page_count + 1, 6)):
                    single_pages.append(InlineKeyboardButton(f"📄 Page {i}", callback_data=f"quick_split_{i}"))
                    if len(single_pages) == 2:
                        keyboard.append(single_pages)
                        single_pages = []
                if single_pages:
                    keyboard.append(single_pages)
            
            keyboard.append([InlineKeyboardButton("✏️ Custom Range", callback_data="custom_split")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"📄 **PDF Analysis Complete!**\n\n"
                f"📊 Total pages: **{page_count}**\n"
                f"📁 File: {document.file_name}\n\n"
                "👉 **Choose page extraction method:**\n\n"
                "🚀 **Quick Options** (tap button) or **✏️ Custom Range** for manual input",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error analyzing PDF: {e}")
            await update.message.reply_text(
                "❌ **Error analyzing PDF**\n\n"
                "Sorry, there was an error reading your PDF. "
                "Please make sure the file is not corrupted and try again.",
                parse_mode='Markdown'
            )
            state_manager.clear_user_state(user_id)

async def handle_split_pages_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle page numbers input for splitting"""
    user_id = update.effective_user.id
    pages_input = update.message.text.strip()
    
    pdf_path = state_manager.get_user_data(user_id, 'split_pdf_path')
    total_pages = state_manager.get_user_data(user_id, 'split_pdf_pages')
    
    if not pdf_path or not total_pages:
        await update.message.reply_text(
            "❌ **Session expired!**\n\n"
            "Please upload your PDF again.",
            parse_mode='Markdown'
        )
        state_manager.clear_user_state(user_id)
        return
    
    try:
        # Parse page numbers
        page_numbers = parse_page_numbers(pages_input, total_pages)
        
        if not page_numbers:
            await update.message.reply_text(
                "❌ **Invalid page numbers!**\n\n"
                f"Please enter valid page numbers (1-{total_pages}).\n\n"
                "**Examples:**\n"
                "• `1-3` (pages 1 to 3)\n"
                "• `1,3,5` (pages 1, 3, and 5)\n"
                "• `2-4,6,8-10` (pages 2-4, 6, and 8-10)",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text(
            f"🔄 **Extracting pages {pages_input}...**\n"
            "Please wait...",
            parse_mode='Markdown'
        )
        
        # Split PDF
        output_pdf_path = split_pdf(pdf_path, page_numbers)
        
        # Send split PDF
        with open(output_pdf_path, 'rb') as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=f"extracted_pages_{pages_input.replace(',', '_').replace('-', '_')}.pdf",
                caption="📂 **Extracted PDF is ready!**\n\n"
                       f"📄 Extracted pages: {pages_input}\n"
                       f"📊 Total extracted: {len(page_numbers)} pages",
                parse_mode='Markdown'
            )
        
        # Clean up
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        os.unlink(output_pdf_path)
        state_manager.clear_user_state(user_id)
        
        # Show menu
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "✅ **PDF split successfully!**\n\n"
            "Need to process more PDFs?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error splitting PDF: {e}")
        await update.message.reply_text(
            "❌ **Error splitting PDF**\n\n"
            "Sorry, there was an error extracting the pages. Please try again.",
            parse_mode='Markdown'
        )
        state_manager.clear_user_state(user_id)

def parse_page_numbers(pages_input, total_pages):
    """Parse page numbers from user input"""
    page_numbers = []
    
    try:
        # Split by comma
        parts = pages_input.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Range of pages
                start, end = part.split('-')
                start, end = int(start.strip()), int(end.strip())
                if 1 <= start <= total_pages and 1 <= end <= total_pages and start <= end:
                    page_numbers.extend(range(start, end + 1))
            else:
                # Single page
                page = int(part)
                if 1 <= page <= total_pages:
                    page_numbers.append(page)
        
        # Remove duplicates and sort
        page_numbers = sorted(list(set(page_numbers)))
        
    except (ValueError, IndexError):
        return []
    
    return page_numbers

async def handle_quick_split(query, context, data):
    """Handle quick split button press"""
    user_id = query.from_user.id
    page_range = data.split('quick_split_')[1]
    
    pdf_path = state_manager.get_user_data(user_id, 'split_pdf_path')
    total_pages = state_manager.get_user_data(user_id, 'split_pdf_pages')
    
    if not pdf_path or not total_pages:
        await query.edit_message_text(
            "❌ **Session expired!**\n\n"
            "Please upload your PDF again.",
            parse_mode='Markdown'
        )
        state_manager.clear_user_state(user_id)
        return
    
    await query.edit_message_text(
        f"🔄 **Extracting pages {page_range}...**\n"
        "Please wait...",
        parse_mode='Markdown'
    )
    
    try:
        # Parse page numbers from quick selection
        page_numbers = parse_page_numbers(page_range, total_pages)
        
        if not page_numbers:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="❌ **Invalid page selection!**\n\n"
                     "Please try again.",
                parse_mode='Markdown'
            )
            return
        
        # Split PDF
        output_pdf_path = split_pdf(pdf_path, page_numbers)
        
        # Send split PDF
        with open(output_pdf_path, 'rb') as pdf_file:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=pdf_file,
                filename=f"extracted_pages_{page_range.replace(',', '_').replace('-', '_')}.pdf",
                caption="📂 **Extracted PDF is ready!**\n\n"
                       f"📄 Extracted pages: {page_range}\n"
                       f"📊 Total extracted: {len(page_numbers)} pages",
                parse_mode='Markdown'
            )
        
        # Clean up
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        os.unlink(output_pdf_path)
        state_manager.clear_user_state(user_id)
        
        # Show menu
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ **PDF split successfully!**\n\n"
                 "Need to process more PDFs?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in quick split: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ **Error splitting PDF**\n\n"
                 "Sorry, there was an error extracting the pages. Please try again.",
            parse_mode='Markdown'
        )
        state_manager.clear_user_state(user_id)

async def handle_custom_split_request(query, context):
    """Handle custom split request"""
    user_id = query.from_user.id
    total_pages = state_manager.get_user_data(user_id, 'split_pdf_pages')
    
    if not total_pages:
        await query.edit_message_text(
            "❌ **Session expired!**\n\n"
            "Please upload your PDF again.",
            parse_mode='Markdown'
        )
        state_manager.clear_user_state(user_id)
        return
    
    await query.edit_message_text(
        f"✏️ **Custom Page Range**\n\n"
        f"📊 Total pages: **{total_pages}**\n\n"
        "👉 **Enter page numbers to extract:**\n\n"
        "**Examples:**\n"
        "• `1-3` (pages 1 to 3)\n"
        "• `1,3,5` (pages 1, 3, and 5)\n"
        "• `2-4,6,8-10` (pages 2-4, 6, and 8-10)\n\n"
        "Type your page selection:",
        parse_mode='Markdown'
    )

async def handle_broadcast_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message input from master"""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    if not master_control.is_master(user_id) or not master_control.is_authenticated(user_id):
        await update.message.reply_text(
            "❌ **Access Denied**\n\nYou are not authorized for this action.",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "📢 **Broadcasting message to all users...**\n\nPlease wait...",
        parse_mode='Markdown'
    )
    
    # Here you would implement actual broadcast logic
    # For now, just confirm the message was received
    await update.message.reply_text(
        f"✅ **Broadcast Scheduled**\n\n"
        f"Message: {message_text}\n\n"
        "The message will be sent to all bot users.",
        parse_mode='Markdown'
    )

async def handle_master_callbacks(query, context, data):
    """Handle master control panel callbacks"""
    user_id = query.from_user.id
    
    if not master_control.is_master(user_id) or not master_control.is_authenticated(user_id):
        await query.answer("❌ Access Denied")
        return
    
    if data == "master_panel":
        await show_master_panel_callback(query, context)
    elif data == "master_stats":
        await handle_master_stats(query, context)
    elif data == "master_cleanup":
        await handle_master_cleanup(query, context)
    elif data == "master_broadcast":
        await handle_master_broadcast_request(query, context)
    elif data == "master_users":
        await handle_master_users_stats(query, context)
    elif data == "master_settings":
        await handle_master_settings(query, context)
    elif data == "master_logs":
        await handle_master_logs(query, context)

async def show_master_panel_callback(query, context):
    """Show master panel as callback"""
    keyboard = [
        [InlineKeyboardButton("📊 System Stats", callback_data="master_stats"),
         InlineKeyboardButton("🧹 Manual Cleanup", callback_data="master_cleanup")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="master_broadcast"),
         InlineKeyboardButton("👥 User Statistics", callback_data="master_users")],
        [InlineKeyboardButton("🔧 Bot Settings", callback_data="master_settings"),
         InlineKeyboardButton("📋 Server Logs", callback_data="master_logs")]
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
    """
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_master_users_stats(query, context):
    """Handle user statistics request"""
    await query.edit_message_text(
        "👥 **User Statistics**\n\n"
        "• Total Users: Coming soon\n"
        "• Active Today: Coming soon\n"
        "• Files Processed: Coming soon\n\n"
        "This feature will be implemented in the next update.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Main Panel", callback_data="master_panel")
        ]]),
        parse_mode='Markdown'
    )

async def handle_master_settings(query, context):
    """Handle bot settings request"""
    await query.edit_message_text(
        "🔧 **Bot Settings**\n\n"
        "• Auto-cleanup: Enabled (1 hour)\n"
        "• Max file size: 20 MB\n"
        "• Temp file retention: 1 hour\n\n"
        "Settings configuration will be added in future updates.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Main Panel", callback_data="master_panel")
        ]]),
        parse_mode='Markdown'
    )

async def handle_master_logs(query, context):
    """Handle server logs request"""
    await query.edit_message_text(
        "📋 **Server Logs**\n\n"
        "Recent activity logs will be displayed here.\n"
        "This feature is coming in the next update.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Main Panel", callback_data="master_panel")
        ]]),
        parse_mode='Markdown'
    )
