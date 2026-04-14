import torch
import torchvision.transforms as transforms
from PIL import Image
import timm
import numpy as np

MODEL_PATH = r"E:\25_final_yearproject\thyroid_nodules\models\efficientnet_best.pth"


def load_model():
    model = timm.create_model("tf_efficientnet_b0", pretrained=False, num_classes=4)
    model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
    model.eval()
    return model


def predict(image_path):
    model = load_model()

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor()
    ])

    # ---- Load image ----
    img = Image.open(image_path).convert("RGB")

    # ===== BLOCK NON-ULTRASOUND / COLOR PHOTOS =====
    # Ultrasound images are almost gray; normal photos have high color variation
    np_img = np.array(img)  # shape (H, W, 3)
    # difference between color channels
    diff_r_g = np_img[:, :, 0].astype("float32") - np_img[:, :, 1].astype("float32")
    diff_g_b = np_img[:, :, 1].astype("float32") - np_img[:, :, 2].astype("float32")
    color_variance = np.std(diff_r_g) + np.std(diff_g_b)

    # Threshold: if too colorful, treat as invalid image
    if color_variance > 35:      # you can change 35 -> 40 / 50 if needed
        return "Not a thyroid ultrasound image"

    # ---- Normal model prediction for valid-looking images ----
    img_tensor = transform(img).unsqueeze(0)

    with torch.no_grad():
        output = model(img_tensor)
        probabilities = torch.nn.functional.softmax(output, dim=1)[0]
        max_prob = torch.max(probabilities).item()
        predicted_class = torch.argmax(probabilities).item()

    # Extra safety: if model is not confident, also mark invalid
    if max_prob < 0.60:
        return "Not a thyroid ultrasound image"

    class_map = {
        0: "Benign",
        1: "Stage 1",
        2: "Stage 2",
        3: "Stage 3"
    }

    return class_map[predicted_class], round(max_prob * 100, 2)
