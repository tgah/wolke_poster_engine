"""DALL-E image generator using OpenAI SDK."""
import httpx
from typing import Optional
import base64

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
        width: int = 1024,
        height: int = 1024,
        **kwargs
    ) -> bytes:
        """Generate image using DALL-E."""
        url = "https://api.openai.com/v1/images/generations"
        
        # Request base64 response instead of URL to avoid Azure blob auth issues
        payload = {
            "model": self.model,
            "prompt": positive_prompt,
            "size": self.size,
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
                
                print(f"Image decoded successfully! Size: {len(image_bytes)} bytes")
                return image_bytes
        
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