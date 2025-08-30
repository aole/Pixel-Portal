from PIL import Image

# Create a 1x1 red image
img = Image.new('RGB', (1, 1), color = 'red')
img.save('portal/tests/test_image.png')
