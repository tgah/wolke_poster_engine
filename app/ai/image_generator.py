"""Abstraction layer for image generation."""
from abc import ABC, abstractmethod
from typing import Optional
import asyncio

from app.config import get_settings

settings = get_settings()


class ImageGenerationError(Exception):
    """Error during image generation."""
    pass


class ImageGenerator(ABC):
    """Abstract base for image generators."""
    
    @abstractmethod
    async def generate(
        self,
        positive_prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        **kwargs
    ) -> bytes:
        """
        Generate image and return bytes.
        """
        pass


def get_image_generator() -> ImageGenerator:
    """
    Factory function to get configured image generator.
    
    Returns:
        ImageGenerator instance based on IMAGE_GEN_PROVIDER setting
    """
    if settings.IMAGE_GEN_PROVIDER == "stable_diffusion":
        from app.ai.providers.stable_diffusion import StableDiffusionGenerator
        return StableDiffusionGenerator()
    elif settings.IMAGE_GEN_PROVIDER == "dalle":
        from app.ai.providers.dalle import DallEGenerator
        return DallEGenerator()
    else:
        raise ValueError(
            f"Unknown image generation provider: {settings.IMAGE_GEN_PROVIDER}. "
            f"Expected 'stable_diffusion' or 'dalle'"
        )