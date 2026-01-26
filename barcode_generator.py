import qrcode
from PIL import Image, ImageDraw, ImageFont
import io
import streamlit as st
import uuid

class BarcodeGenerator:
    def __init__(self):
        self.base_url = "https://rooted-world-tour.streamlit.app"
    
    def generate_ticket_id(self, prefix="RWT"):
        """Generate unique ticket ID with prefix"""
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"{prefix}-{unique_id}"
    
    def create_registration_qr(self, ticket_id, registration_url=None):
        """Generate QR code for registration"""
        if registration_url is None:
            registration_url = f"{self.base_url}/?ticket={ticket_id}"
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        
        qr.add_data(registration_url)
        qr.make(fit=True)
        
        # Get QR code image as RGB
        qr_img = qr.make_image(fill_color="#4CAF50", back_color="white").convert('RGB')
        
        # Get QR code dimensions
        qr_width, qr_height = qr_img.size
        
        # Create final image with exact dimensions
        final_width = max(300, qr_width + 100)  # Ensure minimum width
        final_height = qr_height + 150  # Add space for text
        
        final_img = Image.new('RGB', (final_width, final_height), color='white')
        
        # Calculate position to center the QR code
        qr_x = (final_width - qr_width) // 2
        qr_y = 20
        
        # Paste QR code at calculated position
        final_img.paste(qr_img, (qr_x, qr_y))
        
        # Add text
        draw = ImageDraw.Draw(final_img)
        
        # Try to load font
        try:
            font_large = ImageFont.truetype("Arial.ttf", 20)
            font_medium = ImageFont.truetype("Arial.ttf", 16)
            font_small = ImageFont.truetype("Arial.ttf", 14)
        except:
            # Use default font if Arial not available
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Calculate text positions
        text_y = qr_y + qr_height + 20
        
        # Add ticket ID
        draw.text((final_width // 2, text_y), 
                 f"Ticket: {ticket_id}", 
                 fill="black", 
                 font=font_medium, 
                 anchor="mm")
        
        # Add instructions
        draw.text((final_width // 2, text_y + 30), 
                 "Scan to register", 
                 fill="#4CAF50", 
                 font=font_large, 
                 anchor="mm")
        
        # Add branding
        draw.text((final_width // 2, text_y + 60), 
                 "Rooted World Tour", 
                 fill="#666666", 
                 font=font_small, 
                 anchor="mm")
        
        return final_img
    
    def img_to_bytes(self, img):
        """Convert PIL image to bytes for Streamlit display"""
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    
    def create_checkin_qr(self, ticket_id):
        """Generate QR code for check-in station"""
        checkin_url = f"{self.base_url}/checkin?ticket={ticket_id}"
        return self.create_registration_qr(ticket_id, checkin_url)
    
    def generate_bulk_qr_codes(self, count, event_name):
        """Generate multiple QR codes for print"""
        tickets = []
        for i in range(count):
            ticket_id = self.generate_ticket_id()
            qr_img = self.create_registration_qr(ticket_id)
            tickets.append({
                'ticket_id': ticket_id,
                'qr_image': qr_img,
                'download_link': f"?download_ticket={ticket_id}"
            })
        return tickets

# Fallback if qrcode library fails to install
class SimpleBarcodeGenerator:
    def __init__(self):
        self.base_url = "https://rooted-world-tour.streamlit.app"
    
    def generate_ticket_id(self, prefix="RWT"):
        """Generate unique ticket ID with prefix"""
        import uuid
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"{prefix}-{unique_id}"
    
    def create_registration_qr(self, ticket_id, registration_url=None):
        """Create a simple barcode-like image without QR code library"""
        from PIL import Image, ImageDraw
        import random
        
        # Create a simple barcode pattern
        width = 300
        height = 200
        
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw barcode-like lines
        line_width = 2
        x = 20
        for i in range(40):
            line_height = random.randint(50, 150)
            draw.rectangle([x, (height - line_height) // 2, 
                           x + line_width, (height + line_height) // 2], 
                          fill='black' if random.random() > 0.3 else '#4CAF50')
            x += line_width + 1
        
        # Add text
        draw.text((width // 2, height - 40), 
                 f"TICKET: {ticket_id}", 
                 fill='black', 
                 anchor="mm")
        draw.text((width // 2, height - 20), 
                 "Rooted World Tour", 
                 fill='#4CAF50', 
                 anchor="mm")
        
        return img
    
    def img_to_bytes(self, img):
        """Convert PIL image to bytes"""
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

# Try to use the real QR code generator, fallback to simple if not available
try:
    # Test if qrcode is available
    import qrcode
    barcode_gen = BarcodeGenerator()
except ImportError:
    st.warning("⚠️ QR code library not installed. Using simple barcode generator.")
    barcode_gen = SimpleBarcodeGenerator()

# Export the generator
BarcodeGenerator = barcode_gen.__class__