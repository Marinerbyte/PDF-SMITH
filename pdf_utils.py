import os
import tempfile
from fpdf import FPDF
from reportlab.lib.pagesizes import letter, A4, legal
from reportlab.lib.colors import black, blue, red, green
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from PyPDF2 import PdfWriter, PdfReader
from PIL import Image
import logging

logger = logging.getLogger(__name__)

def create_text_pdf(text, font='arial', color='black', size='a4'):
    """Create a PDF from text with styling options"""
    
    # Create temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
    os.close(temp_fd)
    
    try:
        # Define page sizes
        page_sizes = {
            'a4': A4,
            'letter': letter,
            'legal': legal
        }
        
        # Define colors
        color_map = {
            'black': black,
            'blue': blue,
            'red': red,
            'green': green
        }
        
        # Create document
        doc = SimpleDocTemplate(
            temp_path,
            pagesize=page_sizes.get(size, A4),
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Define font mapping (ReportLab uses specific font names)
        font_map = {
            'arial': 'Helvetica',  # Arial maps to Helvetica in ReportLab
            'helvetica': 'Helvetica',
            'times': 'Times-Roman',
            'times new roman': 'Times-Roman',
            'courier': 'Courier'
        }
        
        # Create custom style
        custom_style = ParagraphStyle(
            'CustomStyle',
            parent=styles['Normal'],
            fontName=font_map.get(font.lower(), 'Helvetica'),
            fontSize=12,
            textColor=color_map.get(color, black),
            spaceAfter=12,
            alignment=0  # Left alignment
        )
        
        # Create story (content)
        story = []
        
        # Split text into paragraphs
        paragraphs = text.split('\n')
        
        for para_text in paragraphs:
            if para_text.strip():
                # Create paragraph
                para = Paragraph(para_text.strip(), custom_style)
                story.append(para)
                story.append(Spacer(1, 6))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"Text PDF created successfully: {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"Error creating text PDF: {e}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

def create_image_pdf(image_paths, orientation='portrait'):
    """Create a PDF from multiple images with optimization"""
    
    # Create temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
    os.close(temp_fd)
    
    try:
        # Create FPDF instance
        pdf = FPDF(orientation='P' if orientation == 'portrait' else 'L', unit='mm', format='A4')
        
        # A4 dimensions in mm
        if orientation == 'portrait':
            page_width, page_height = 210, 297
        else:
            page_width, page_height = 297, 210
        
        # Margins
        margin = 10
        usable_width = page_width - 2 * margin
        usable_height = page_height - 2 * margin
        
        for image_path in image_paths:
            try:
                # Open and process image
                with Image.open(image_path) as img:
                    # Convert to RGB if needed
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Auto-rotate based on EXIF data
                    try:
                        from PIL import ExifTags
                        if hasattr(img, 'getexif'):
                            exif = img.getexif()
                            if exif is not None:
                                orientation = exif.get(ExifTags.ORIENTATION)
                                if orientation == 3:
                                    img = img.rotate(180, expand=True)
                                elif orientation == 6:
                                    img = img.rotate(270, expand=True)
                                elif orientation == 8:
                                    img = img.rotate(90, expand=True)
                    except:
                        pass  # Skip if EXIF processing fails
                    
                    # Calculate scaling to fit page
                    img_width, img_height = img.size
                    scale_width = usable_width / (img_width * 0.264583)  # Convert pixels to mm
                    scale_height = usable_height / (img_height * 0.264583)
                    scale = min(scale_width, scale_height, 1.0)  # Don't upscale
                    
                    # Calculate final dimensions
                    final_width = img_width * 0.264583 * scale
                    final_height = img_height * 0.264583 * scale
                    
                    # Center the image
                    x = (page_width - final_width) / 2
                    y = (page_height - final_height) / 2
                    
                    # Optimize image quality
                    if scale < 1.0:
                        new_width = int(img_width * scale)
                        new_height = int(img_height * scale)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Save optimized image temporarily
                    optimized_path = f"{image_path}_optimized.jpg"
                    img.save(optimized_path, 'JPEG', quality=85, optimize=True)
                    
                    # Add page and image to PDF
                    pdf.add_page()
                    pdf.image(optimized_path, x=x, y=y, w=final_width, h=final_height)
                    
                    # Clean up optimized image
                    if os.path.exists(optimized_path):
                        os.unlink(optimized_path)
                        
            except Exception as e:
                logger.error(f"Error processing image {image_path}: {e}")
                continue
        
        # Output PDF
        pdf.output(temp_path)
        
        logger.info(f"Image PDF created successfully: {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"Error creating image PDF: {e}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

def merge_pdfs(pdf_paths):
    """Merge multiple PDF files"""
    
    # Create temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
    os.close(temp_fd)
    
    try:
        writer = PdfWriter()
        
        for pdf_path in pdf_paths:
            try:
                with open(pdf_path, 'rb') as pdf_file:
                    reader = PdfReader(pdf_file)
                    
                    # Add all pages from the current PDF
                    for page in reader.pages:
                        writer.add_page(page)
                        
            except Exception as e:
                logger.error(f"Error reading PDF {pdf_path}: {e}")
                continue
        
        # Write merged PDF
        with open(temp_path, 'wb') as output_file:
            writer.write(output_file)
        
        logger.info(f"PDFs merged successfully: {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"Error merging PDFs: {e}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

def split_pdf(pdf_path, page_numbers):
    """Split PDF and extract specific pages"""
    
    # Create temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
    os.close(temp_fd)
    
    try:
        writer = PdfWriter()
        
        with open(pdf_path, 'rb') as pdf_file:
            reader = PdfReader(pdf_file)
            
            # Add specified pages (convert to 0-based indexing)
            for page_num in page_numbers:
                if 1 <= page_num <= len(reader.pages):
                    writer.add_page(reader.pages[page_num - 1])
        
        # Write split PDF
        with open(temp_path, 'wb') as output_file:
            writer.write(output_file)
        
        logger.info(f"PDF split successfully: {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"Error splitting PDF: {e}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise
