"""LLM-based prompt generation for image models."""
from typing import Dict, Optional
import httpx
from app.config import get_settings

settings = get_settings()


class PromptGenerationError(Exception):
    """Error during prompt generation."""
    pass


class LLMPromptBuilder:
    """Build Stable Diffusion prompts using an LLM."""
    
    SYSTEM_PROMPT = """You are an expert at creating prompts for Stable Diffusion 1.5 image generation.

Your task is to convert user theme descriptions into optimized prompts for generating promotional poster backgrounds for grocery stores.

Requirements:
- Output clean, commercial-grade backgrounds suitable for product overlays
- Leave ample clear space for text and product placement
- Avoid text, watermarks, logos, or cluttered elements
- Focus on atmosphere, color palette, and style
- High resolution, professional quality
- The style should be clean and appealing for retail/grocery context

The user will describe a theme (e.g., "Christmas, cozy, blue tones, minimal").

Respond with a JSON object containing:
{
  "positive_prompt": "detailed prompt for Stable Diffusion",
  "negative_prompt": "things to avoid",
  "style_notes": "brief description of intended aesthetic"
}

Make prompts specific and descriptive. Include:
- Main subject/theme
- Color palette
- Mood/atmosphere
- Art style (e.g., "soft gradient background", "minimal flat design")
- Lighting
- Quality markers (e.g., "professional, high resolution, clean")

Example output:
{
  "positive_prompt": "soft blue gradient background with subtle snowflakes, minimalist christmas theme, cozy warm lighting, clean commercial design, high resolution, professional photography, gentle bokeh effect, pastel winter colors, spacious composition",
  "negative_prompt": "text, words, letters, watermark, logo, signature, cluttered, busy, distorted, low quality, blurry, dark, chaotic, frames, borders",
  "style_notes": "Clean minimal winter aesthetic with soft blues and warm accents"
}"""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.base_url = settings.LLM_BASE_URL
        self.timeout = settings.LLM_TIMEOUT_SECONDS
    
    async def generate_prompt(self, theme_text: str) -> Dict[str, str]:
        """
        Generate SD prompt from theme description.
        Returns dict with positive_prompt, negative_prompt, style_notes.
        """
        try:
            if self.provider == "openai":
                return await self._generate_openai(theme_text)
            elif self.provider == "anthropic":
                return await self._generate_anthropic(theme_text)
            else:
                raise PromptGenerationError(f"Unknown LLM provider: {self.provider}")
        
        except Exception as e:
            raise PromptGenerationError(f"Failed to generate prompt: {str(e)}")
    
    async def _generate_openai(self, theme_text: str) -> Dict[str, str]:
        """Generate using OpenAI API."""
        url = self.base_url or "https://api.openai.com/v1/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Theme: {theme_text}"}
            ],
            "temperature": 0.7
            # "response_format": {"type": "json_object"}
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            import json
            result = json.loads(content)
            
            return {
                "positive_prompt": result.get("positive_prompt", ""),
                "negative_prompt": result.get("negative_prompt", ""),
                "style_notes": result.get("style_notes", "")
            }
    
    async def _generate_anthropic(self, theme_text: str) -> Dict[str, str]:
        """Generate using Anthropic API."""
        url = self.base_url or "https://api.anthropic.com/v1/messages"
        
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": f"{self.SYSTEM_PROMPT}\n\nTheme: {theme_text}"
                }
            ]
        }
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            content = data["content"][0]["text"]
            
            import json
            # Extract JSON from markdown if needed
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            return {
                "positive_prompt": result.get("positive_prompt", ""),
                "negative_prompt": result.get("negative_prompt", ""),
                "style_notes": result.get("style_notes", "")
            }
