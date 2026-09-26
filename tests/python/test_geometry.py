import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError
from backend.geometry import perspective, point_to_basic, letterbox
from backend.schemas import ViewSpec

def view(origin=(0, 0, 1), right=(1, 0, 0), down=(0, -1, 0), aspect=1):
    return ViewSpec(origin=origin, right=right, down=down, aspect=aspect)

def test_center_and_cardinal_directions():
    assert point_to_basic(.5, .5, view()) == pytest.approx([.5, .5])
    assert point_to_basic(1, .5, view()) == pytest.approx([.625, .5])
    assert point_to_basic(.5, 0, view()) == pytest.approx([.5, .25])

def test_seam_wraps_without_flipping():
    backward = view(origin=(0, 0, -1), right=(-1, 0, 0))
    assert point_to_basic(.49, .5, backward)[0] > .99
    assert point_to_basic(.51, .5, backward)[0] < .01

def test_crop_reads_correct_pixels_and_wraps_seam():
    array = np.zeros((180, 360, 3), dtype='uint8')
    array[:, 150:210, 0] = 255
    array[:, :30, 1] = 255
    array[:, -30:, 1] = 255
    image = Image.fromarray(array)
    front = np.asarray(perspective(image, view(), 41))
    assert front[20, 20].tolist() == [255, 0, 0]
    back = np.asarray(perspective(image, view(origin=(0, 0, -1), right=(-1, 0, 0)), 41))
    assert back[20, 20].tolist() == [0, 255, 0]
    assert back[20, 19, 1] == back[20, 21, 1] == 255

def test_viewport_aspect_and_letterbox_roundtrip():
    crop = perspective(Image.new('RGB', (1024, 512)), view(right=(2, 0, 0), aspect=2))
    assert crop.size == (640, 320)
    tensor, scale, left, top = letterbox(crop)
    assert tensor.shape == (1, 3, 640, 640)
    assert (scale, left, top) == (1, 0, 160)
    assert tensor[0, 0, 0, 0] == pytest.approx(114/255)

@pytest.mark.parametrize('change', [{'origin': (0, 0, 0)}, {'right': (0, 0, 1)}, {'down': (1, 0, 0)}, {'aspect': float('nan')}, {'right': (99, 0, 0)}])
def test_invalid_camera_rejected(change):
    with pytest.raises(ValidationError):
        ViewSpec(**{**view().model_dump(), **change})
