import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

model_id = "runwayml/stable-diffusion-v1-5"

pipe = StableDiffusionPipeline.from_pretrained(
    model_id,
    torch_dtype=torch.float32,
    safety_checker=None
)

pipe.scheduler = DPMSolverMultistepScheduler.from_config(
    pipe.scheduler.config
)

pipe = pipe.to("mps")

prompt = "Create a background poster with light colors for a Christmas sale with festive decorations, snowflakes, and holiday colors, high resolution"

image = pipe(
    prompt,
    num_inference_steps=20,
    guidance_scale=7.5
).images[0]

image.save("output.png")
print("✅ Image saved")
