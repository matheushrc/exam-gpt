import os
import re


def load_images_from_folder(img_folder):
    """
    Load all image files from a folder and return them as a list of bytes.

    Args:
        img_folder (str): Path to the folder containing image files

    Returns:
        list: List of image bytes
    """
    img_files: list[str] = os.listdir(img_folder)
    img_files = [
        f"{img_folder}/{file}"
        for file in img_files
        if file.endswith((".png", ".jpg", ".jpeg"))
    ]

    # Sort the files naturally so page numbers are in correct order
    def natural_sort_key(s: str):
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", s)
        ]

    img_files.sort(key=natural_sort_key)

    # Load all images into a list
    images: list[bytes] = []
    for img in img_files:
        with open(img, "rb") as f:
            page_bytes = f.read()
            images.append(page_bytes)

    return images
