import json
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Optional

class PosterGenerator:
    def __init__(self, template_path: str, dpi: int = 300):
        """
        Initialize the poster generator with a template JSON file.
        
        Args:
            template_path: Path to the template JSON file
            dpi: Resolution in dots per inch (default: 300)
        """
        self.dpi = dpi
        # A3 Portrait dimensions in mm: 297 x 420
        # Convert to pixels at given DPI
        self.width_px = int((297 / 25.4) * dpi)  # 3508 pixels at 300 DPI
        self.height_px = int((420 / 25.4) * dpi)  # 4961 pixels at 300 DPI
        
        # Load template
        with open(template_path, 'r') as f:
            self.template = json.load(f)
        
        # Default font specifications (can be overridden by user input)
        self.default_fonts = {
            'header': {'size': 80, 'color': (0, 0, 0)},  # Black
            'subtitle': {'size': 40, 'color': (50, 50, 50)}  # Dark gray
        }
    
    def _load_image(self, image_path: str, width: int, height: Optional[int] = None, 
                    mode: str = 'contain', keep_aspect: bool = True) -> Image.Image:
        """
        Load and resize an image according to specifications.
        
        Args:
            image_path: Path to the image file
            width: Target width in pixels
            height: Target height in pixels (None for aspect ratio preservation)
            mode: 'contain' or 'cover' for image fitting
            keep_aspect: Whether to maintain aspect ratio
            
        Returns:
            PIL Image object
        """
        img = Image.open(image_path).convert('RGBA')
        
        if keep_aspect and height is None:
            # Calculate height based on aspect ratio
            aspect_ratio = img.height / img.width
            height = int(width * aspect_ratio)
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        elif keep_aspect and mode == 'cover':
            # Cover mode: fill the entire area, crop if necessary
            img_aspect = img.width / img.height
            target_aspect = width / height
            
            if img_aspect > target_aspect:
                # Image is wider, fit to height
                new_height = height
                new_width = int(height * img_aspect)
            else:
                # Image is taller, fit to width
                new_width = width
                new_height = int(width / img_aspect)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Crop to target dimensions (center crop)
            left = (new_width - width) // 2
            top = (new_height - height) // 2
            img = img.crop((left, top, left + width, top + height))
        else:
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        return img
    
    def _get_font(self, font_type: str, custom_size: Optional[int] = None) -> ImageFont.FreeTypeFont:
        """
        Get a font object with appropriate size.
        
        Args:
            font_type: 'header' or 'subtitle'
            custom_size: Override default font size
            
        Returns:
            PIL Font object
        """
        size = custom_size if custom_size else self.default_fonts[font_type]['size']
        
        try:
            # Try to load a nice font (you may need to adjust path based on OS)
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", size)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
        
        return font
    
    def _draw_text(self, draw: ImageDraw.Draw, text: str, x: int, y: int, 
                   width: int, font: ImageFont.FreeTypeFont, color: tuple, 
                   align: str = 'center', multiline: bool = True) -> int:
        """
        Draw text on the image with proper alignment and wrapping.
        
        Args:
            draw: PIL ImageDraw object
            text: Text to draw
            x: X position in pixels
            y: Y position in pixels
            width: Maximum width for text
            font: Font object
            color: RGB color tuple
            align: Text alignment ('left', 'center', 'right')
            multiline: Whether to allow multiline text
            
        Returns:
            Height of the drawn text in pixels
        """
        if multiline:
            # Simple word wrapping
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                test_width = bbox[2] - bbox[0]
                
                if test_width <= width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw each line
            current_y = y
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                line_height = bbox[3] - bbox[1]
                
                if align == 'center':
                    line_x = x + (width - line_width) // 2
                elif align == 'right':
                    line_x = x + width - line_width
                else:
                    line_x = x
                
                draw.text((line_x, current_y), line, font=font, fill=color)
                current_y += line_height + 5  # 5px line spacing
            
            return current_y - y
        else:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            if align == 'center':
                text_x = x + (width - text_width) // 2
            elif align == 'right':
                text_x = x + width - text_width
            else:
                text_x = x
            
            draw.text((text_x, y), text, font=font, fill=color)
            return text_height
    
    def generate_poster(self, user_inputs: Dict[str, Any], output_path: str = 'output_poster.png'):
        """
        Generate the poster based on template and user inputs.
        
        Args:
            user_inputs: Dictionary containing image paths and text content
                Expected keys:
                - 'background_top': path to background image
                - 'product_1': path to first product image
                - 'product_2': path to second product image
                - 'subtitle_1': text for first subtitle
                - 'subtitle_2': text for second subtitle
                - 'header': header text
                - 'header_font_size': (optional) custom font size
                - 'header_color': (optional) custom color tuple
                - 'subtitle_font_size': (optional) custom font size
                - 'subtitle_color': (optional) custom color tuple
            output_path: Path where to save the generated poster
        """
        # Create blank canvas
        canvas = Image.new('RGBA', (self.width_px, self.height_px), (255, 255, 255, 255))
        
        # Track product image heights for subtitle positioning
        product_heights = {}
        
        # Process each element in template
        for element in self.template['elements']:
            elem_type = element['type']
            elem_id = element['id']
            
            # Convert normalized coordinates to pixels
            x_px = int(element['x'] * self.width_px)
            y_px = int(element['y'] * self.height_px) if isinstance(element['y'], (int, float)) else None
            width_px = int(element['width'] * self.width_px) if element.get('width') else None
            height_px = int(element['height'] * self.height_px) if element.get('height') else None
            
            if elem_type == 'image':
                image_path = user_inputs.get(elem_id)
                if image_path:
                    mode = element.get('mode', 'contain')
                    keep_aspect = element.get('keepAspectRatio', True)
                    
                    img = self._load_image(image_path, width_px, height_px, mode, keep_aspect)
                    canvas.paste(img, (x_px, y_px), img)
                    
                    # Store actual image height for subtitle positioning
                    if 'product' in elem_id:
                        product_heights[elem_id] = {'y': y_px, 'height': img.height}
            
            elif elem_type == 'text':
                text_content = user_inputs.get(elem_id, '')
                if text_content:
                    # Determine font type and get custom sizes/colors if provided
                    font_type = 'header' if elem_id == 'header' else 'subtitle'
                    custom_size = user_inputs.get(f'{elem_id}_font_size') or user_inputs.get(f'{font_type}_font_size')
                    custom_color = user_inputs.get(f'{elem_id}_color') or user_inputs.get(f'{font_type}_color') or self.default_fonts[font_type]['color']
                    
                    font = self._get_font(font_type, custom_size)
                    
                    # Handle "after_image" positioning
                    if element['y'] == 'after_image':
                        # Find corresponding product image
                        product_num = elem_id.split('_')[1]
                        product_key = f'product_{product_num}'
                        
                        if product_key in product_heights:
                            margin_px = int(element.get('margin', 0) * self.height_px)
                            y_px = product_heights[product_key]['y'] + product_heights[product_key]['height'] + margin_px
                    
                    # Draw text
                    draw = ImageDraw.Draw(canvas)
                    align = element.get('align', 'center')
                    multiline = element.get('multiLine', False)
                    
                    self._draw_text(draw, text_content, x_px, y_px, width_px, 
                                  font, custom_color, align, multiline)
        
        # Convert to RGB for PNG output
        canvas = canvas.convert('RGB')
        
        # Save with high quality
        canvas.save(output_path, 'PNG', dpi=(self.dpi, self.dpi))
        print(f"Poster generated successfully: {output_path}")
        print(f"Dimensions: {self.width_px} x {self.height_px} pixels ({self.dpi} DPI)")


def main():
    """
    Main function to demonstrate usage.
    """
    # User inputs dictionary
    user_inputs = {
        'background_top': 'image.png',
        'product_1': 'product_1.jpg',
        'product_2': 'product_2.jpg',
        'subtitle_1': 'Herbal Tea',
        'subtitle_2': 'Instant Noodles',
        'header': 'Christmas Sale',
        
        # Optional: Override default font settings
        # 'header_font_size': 100,
        # 'header_color': (0, 0, 0),
        # 'subtitle_font_size': 45,
        # 'subtitle_color': (60, 60, 60),
    }
    
    # Generate poster
    generator = PosterGenerator('template.json', dpi=300)
    generator.generate_poster(user_inputs, 'output_poster.png')


if __name__ == '__main__':
    main()