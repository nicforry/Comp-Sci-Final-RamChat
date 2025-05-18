from PIL import Image
import pytesseract
import os
from pdf2image import convert_from_path
from pytesseract import image_to_string

def extract_text_from_images(pdf_path):
    images = convert_from_path(pdf_path)
    text = ""
    for img in images:
        text += image_to_string(img)
    return text
import os

def extract_text_from_images(image_dir):
    text_chunks = []
    for filename in os.listdir(image_dir):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            path = os.path.join(image_dir, filename)
            img = Image.open(path)
            text = pytesseract.image_to_string(img)
            text_chunks.append({"source": filename, "text": text})
    return text_chunks
