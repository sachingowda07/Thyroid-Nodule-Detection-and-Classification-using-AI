import os
import hashlib
from PIL import Image

DATASET_DIR = r"E:\25_final_yearproject\thyroid_nodules\data\train"  # CHANGE PATH

def hash_image(image_path):
    with Image.open(image_path) as img:
        img = img.resize((64, 64)).convert("L")
        return hashlib.md5(img.tobytes()).hexdigest()

def remove_duplicates(folder):
    hashes = {}
    removed = 0

    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                path = os.path.join(root, file)

                try:
                    img_hash = hash_image(path)
                except:
                    continue

                if img_hash in hashes:
                    print("Duplicate Removed:", path)
                    os.remove(path)
                    removed += 1
                else:
                    hashes[img_hash] = path

    print("\nDone! Total duplicates removed:", removed)


if __name__ == "__main__":
    remove_duplicates(DATASET_DIR)
