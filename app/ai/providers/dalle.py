"""DALL-E image generator using OpenAI SDK."""
import httpx
from typing import Optional
import base64
import io
import random
from PIL import Image

from app.ai.image_generator import ImageGenerator, ImageGenerationError
from app.config import get_settings

settings = get_settings()


class DallEGenerator(ImageGenerator):
    """DALL-E image generator using OpenAI API."""
    
    def __init__(self):
        self.api_key = settings.DALLE_API_KEY or settings.LLM_API_KEY
        self.model = settings.DALLE_MODEL
        self.size = settings.DALLE_SIZE
        self.quality = settings.DALLE_QUALITY
    
    async def generate(
        self,
        positive_prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 3508,  # A3 portrait width at 300 DPI
        height: int = 4961,  # A3 portrait height at 300 DPI
        **kwargs
    ) -> bytes:
        """Generate image using DALL-E with random system prompt and upscale to requested dimensions."""
        url = "https://api.openai.com/v1/images/generations"

        # Randomly select one of the system prompts
        system_prompt = random.choice(settings.DALLE_SYSTEM_PROMPTS)

        # Prepend system prompt to user's theme description
        full_prompt = f"{system_prompt}\n\nTheme/Keywords: {positive_prompt}"

        # Log which system prompt was selected (for debugging)
        prompt_index = settings.DALLE_SYSTEM_PROMPTS.index(system_prompt) + 1
        print(f"🎨 Selected DALL-E System Prompt #{prompt_index}")
        print(f"📝 User theme: {positive_prompt}")

        # DALL-E 3 only supports specific sizes, use closest preset
        if width > height:
            dalle_size = "1792x1024"  # Landscape
        else:
            dalle_size = "1024x1792"  # Portrait (for A3)

        print(f"Generating DALL-E image at {dalle_size}, will upscale to {width}x{height}")

        # Request base64 response instead of URL to avoid Azure blob auth issues
        payload = {
            "model": self.model,
            "prompt": full_prompt,  # Use combined prompt
            "size": dalle_size,
            "quality": self.quality,
            "n": 1,
            "response_format": "b64_json"  # Get base64 directly instead of URL
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                print(f"Calling DALL-E API with prompt: {positive_prompt[:100]}...")

                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()

                # Get base64 image data
                b64_json = data["data"][0]["b64_json"]

                print(f"DALL-E returned base64 image data")

                # Decode base64 to bytes
                image_bytes = base64.b64decode(b64_json)

                # Load image and upscale to requested size
                img = Image.open(io.BytesIO(image_bytes))
                print(f"Original DALL-E image: {img.size[0]}x{img.size[1]}")

                # Upscale to A3 dimensions
                img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
                print(f"Upscaled to: {img_resized.size[0]}x{img_resized.size[1]}")

                # Convert back to PNG bytes
                buffer = io.BytesIO()
                img_resized.save(buffer, format="PNG")
                upscaled_bytes = buffer.getvalue()

                print(f"Image upscaled successfully! Size: {len(upscaled_bytes)} bytes")
                return upscaled_bytes
        
        except httpx.HTTPStatusError as e:
            error_msg = f"DALL-E API error: {e.response.status_code}"
            try:
                error_detail = e.response.json()
                if "error" in error_detail:
                    error_msg += f" - {error_detail['error'].get('message', '')}"
            except:
                error_msg += f" - {e.response.text}"
            
            raise ImageGenerationError(error_msg)
        
        except Exception as e:
            raise ImageGenerationError(f"DALL-E generation failed: {str(e)}")