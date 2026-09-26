import math
from pydantic import BaseModel, ConfigDict, Field, model_validator

Vec3 = tuple[float, float, float]

class ViewSpec(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    origin: Vec3
    right: Vec3
    down: Vec3
    aspect: float = Field(ge=.35, le=4)

    @model_validator(mode='after')
    def camera_is_valid(self):
        norm = lambda a: math.sqrt(sum(v * v for v in a))
        dot = lambda a, b: sum(x * y for x, y in zip(a, b))
        o, r, d = norm(self.origin), norm(self.right), norm(self.down)
        if abs(o - 1) > .01 or not (.01 < r < 8 and .01 < d < 8):
            raise ValueError('Invalid camera basis. Zoom to a normal street view.')
        if abs(dot(self.origin, self.right)) / r > .03 or abs(dot(self.origin, self.down)) / d > .03 or abs(dot(self.right, self.down)) / (r * d) > .03:
            raise ValueError('Camera basis must be orthogonal.')
        if abs(r / d / self.aspect - 1) > .08:
            raise ValueError('Camera aspect does not match the viewport.')
        return self

class PanoramaAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    image_id: str = Field(pattern=r'^\d{1,30}$')

class AnalysisRequest(PanoramaAnalysisRequest):
    view: ViewSpec
