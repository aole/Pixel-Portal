import pytest

from portal.ai.image_generator import ImageGenerator


@pytest.fixture()
def generator() -> ImageGenerator:
    return ImageGenerator()


def test_sd15_scales_up_to_minimum(generator: ImageGenerator) -> None:
    size = generator.calculate_generation_size("SD1.5", (300, 200))
    assert size == (768, 512)
    assert size[0] % 8 == 0 and size[1] % 8 == 0


def test_sd15_snaps_near_square(generator: ImageGenerator) -> None:
    size = generator.calculate_generation_size("SD1.5", (1001, 1000))
    assert size == (1000, 1000)


def test_sd15_respects_soft_max(generator: ImageGenerator) -> None:
    size = generator.calculate_generation_size("SD1.5", (2048, 1024))
    assert size == (1024, 512)


def test_sdxl_honours_minimum(generator: ImageGenerator) -> None:
    size = generator.calculate_generation_size("SDXL", (512, 512))
    assert size == (768, 768)


def test_sdxl_expands_for_wide_aspect(generator: ImageGenerator) -> None:
    size = generator.calculate_generation_size("SDXL", (1400, 600))
    assert size == (1792, 768)


def test_invalid_size_falls_back(generator: ImageGenerator) -> None:
    size = generator.calculate_generation_size("SD1.5", None)
    assert size == (512, 512)
