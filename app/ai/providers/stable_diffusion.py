"""Stable Diffusion 1.5 local generator with M1 Mac support."""
import torch
from diffusers import StableDiffusionPipeline
from PIL import Image
import io
import asyncio
from typing import Optional

from app.ai.image_generator import ImageGenerator, ImageGenerationError
from app.config import get_settings

settings = get_settings()


class StableDiffusionGenerator(ImageGenerator):
    """Local Stable Diffusion generator with M1/MPS support."""
    
    def __init__(self):
        self.model_path = settings.SD_MODEL_PATH
        self.device = settings.SD_DEVICE
        self.num_steps = settings.SD_NUM_INFERENCE_STEPS
        self.guidance_scale = settings.SD_GUIDANCE_SCALE
        self.pipeline = None
    
    def _get_device_and_dtype(self):
        """Determine device and dtype based on configuration and availability."""
        device = self.device.lower()
        
        if device == "cuda" and torch.cuda.is_available():
            return "cuda", torch.float16
        elif device == "mps" and torch.backends.mps.is_available():
            # M1 Mac - use MPS (Metal Performance Shaders)
            return "mps", torch.float32  # MPS works better with float32
        else:
            # Fallback to CPU
            return "cpu", torch.float32
    
    def _load_pipeline(self):
        """Lazy load pipeline to save memory."""
        if self.pipeline is None:
            device, dtype = self._get_device_and_dtype()
            
            print(f"Loading Stable Diffusion on device: {device} with dtype: {dtype}")
            
            self.pipeline = StableDiffusionPipeline.from_pretrained(
                self.model_path,
                torch_dtype=dtype,
                safety_checker=None,  # Disable for speed
                requires_safety_checker=False
            )
            
            self.pipeline = self.pipeline.to(device)
            
            # Optimizations
            if device == "cuda":
                self.pipeline.enable_attention_slicing()
                # Optional: enable xformers for faster inference
                # self.pipeline.enable_xformers_memory_efficient_attention()
            elif device == "mps":
                # M1 optimizations
                self.pipeline.enable_attention_slicing()
    
    async def generate(
        self,
        positive_prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        **kwargs
    ) -> bytes:
        """Generate image using Stable Diffusion."""
        try:
            self._load_pipeline()
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            image = await loop.run_in_executor(
                None,
                self._generate_sync,
                positive_prompt,
                negative_prompt,
                width,
                height
            )
            
            # Convert to bytes
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            return buffer.getvalue()
        
        except Exception as e:
            raise ImageGenerationError(f"SD generation failed: {str(e)}")
    
    def _generate_sync(
        self,
        positive_prompt: str,
        negative_prompt: Optional[str],
        width: int,
        height: int
    ) -> Image.Image:
        """Synchronous generation."""
        print(f"Generating image with prompt: {positive_prompt[:100]}...")
        
        # For M1 Macs, we might need to adjust dimensions to multiples of 8
        width = (width // 8) * 8
        height = (height // 8) * 8
        
        result = self.pipeline(
            prompt=positive_prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=self.num_steps,
            guidance_scale=self.guidance_scale,
            width=width,
            height=height
        )
        
        print("Image generation completed!")
        return result.images[0]