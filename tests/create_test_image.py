from PIL import Image

def create_test_image():
    """Creates a test image with a gradient."""
    image = Image.new("RGB", (32, 32))
    for x in range(32):
        for y in range(32):
            image.putpixel((x, y), (x * 8, y * 8, 0))
    image.save("tests/test_image.png")

if __name__ == "__main__":
    create_test_image()
