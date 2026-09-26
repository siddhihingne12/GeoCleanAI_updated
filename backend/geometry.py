import io
import base64
import numpy as np
from PIL import Image
from backend.schemas import ViewSpec

def rays_to_basic(rays: np.ndarray) -> np.ndarray:
    normalized = rays / np.linalg.norm(rays, axis=-1, keepdims=True)
    u = (np.arctan2(normalized[..., 0], normalized[..., 2]) / (2 * np.pi) + .5) % 1
    v = .5 - np.arcsin(np.clip(normalized[..., 1], -1, 1)) / np.pi
    return np.stack((u, v), axis=-1)

def point_to_basic(x: float, y: float, view: ViewSpec) -> list[float]:
    ray = np.array(view.origin) + (2 * x - 1) * np.array(view.right) + (2 * y - 1) * np.array(view.down)
    return rays_to_basic(ray).tolist()

def perspective(image: Image.Image, view: ViewSpec, longest_side: int = 640) -> Image.Image:
    width = longest_side if view.aspect >= 1 else round(longest_side * view.aspect)
    height = round(longest_side / view.aspect) if view.aspect >= 1 else longest_side
    x, y = np.meshgrid((np.arange(width) + .5) / width, (np.arange(height) + .5) / height)
    rays = np.array(view.origin) + (2 * x[..., None] - 1) * np.array(view.right) + (2 * y[..., None] - 1) * np.array(view.down)
    uv = rays_to_basic(rays)
    source = np.asarray(image.convert('RGB'))
    # Bilinear sampling wraps horizontally at the panorama seam, clamps at poles.
    sx, sy = uv[..., 0] * image.width - .5, np.clip(uv[..., 1] * image.height - .5, 0, image.height - 1)
    x0, y0 = np.floor(sx).astype(int), np.floor(sy).astype(int)
    dx, dy = (sx - x0)[..., None], (sy - y0)[..., None]
    top = source[y0, x0 % image.width] * (1 - dx) + source[y0, (x0 + 1) % image.width] * dx
    bottom = source[np.minimum(y0 + 1, image.height - 1), x0 % image.width] * (1 - dx) + source[np.minimum(y0 + 1, image.height - 1), (x0 + 1) % image.width] * dx
    return Image.fromarray(np.rint(top * (1 - dy) + bottom * dy).astype('uint8'))

def letterbox(image: Image.Image, size: int = 640):
    scale = min(size / image.width, size / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.BILINEAR)
    left, top = (size - resized.width) // 2, (size - resized.height) // 2
    canvas = Image.new('RGB', (size, size), (114, 114, 114))
    canvas.paste(resized, (left, top))
    tensor = np.asarray(canvas, dtype=np.float32).transpose(2, 0, 1)[None] / 255.
    return tensor, scale, left, top

def preview_data_url(image: Image.Image, longest_side: int = 640) -> str:
    # Views rendered larger for tiled detection are still sent at the usual preview size.
    if max(image.size) > longest_side:
        scale = longest_side / max(image.size)
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.BILINEAR)
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=78)
    return 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')
