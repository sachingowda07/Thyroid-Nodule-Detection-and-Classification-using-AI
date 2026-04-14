import torch
import torch.nn.functional as F
import timm
import cv2
import numpy as np
from torchvision import transforms
from PIL import Image
import os

# -------------------------------------------------
# CONFIGURATION (CHANGE PATHS IF NEEDED)
# -------------------------------------------------
MODEL_PATH = "models/efficientnet_best.pth"
IMAGE_PATH = "data/train/benign/000002.jpg"   # any image path
OUTPUT_DIR = "results/gradcam"

os.makedirs(OUTPUT_DIR, exist_ok=True)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -------------------------------------------------
# LOAD MODEL (SAME AS TRAINING)
# -------------------------------------------------
model = timm.create_model(
    "efficientnet_b0",
    pretrained=False,
    num_classes=4          # ✅ MUST MATCH YOUR TRAINED MODEL
)

model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.to(device)
model.eval()

# -------------------------------------------------
# IMAGE PREPROCESSING
# -------------------------------------------------
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

img = Image.open(IMAGE_PATH).convert("RGB")
input_tensor = transform(img).unsqueeze(0).to(device)

# -------------------------------------------------
# GRAD-CAM HOOKS
# -------------------------------------------------
features = []
gradients = []

def forward_hook(module, input, output):
    features.append(output)

def backward_hook(module, grad_input, grad_output):
    gradients.append(grad_output[0])

# LAST CONVOLUTION LAYER IN TIMM EFFICIENTNET
target_layer = model.conv_head
target_layer.register_forward_hook(forward_hook)
target_layer.register_backward_hook(backward_hook)

# -------------------------------------------------
# FORWARD + BACKWARD PASS
# -------------------------------------------------
output = model(input_tensor)
pred_class = output.argmax(dim=1)

model.zero_grad()
output[0, pred_class].backward()

# -------------------------------------------------
# GENERATE GRAD-CAM HEATMAP
# -------------------------------------------------
grads = gradients[0]          # gradients
fmap = features[0]            # feature maps

weights = grads.mean(dim=(2, 3), keepdim=True)
cam = (weights * fmap).sum(dim=1).squeeze()
cam = F.relu(cam)

cam -= cam.min()
cam /= cam.max()

cam = cam.cpu().detach().numpy()
cam = cv2.resize(cam, (224, 224))
heatmap = np.uint8(255 * cam)
heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

# -------------------------------------------------
# OVERLAY HEATMAP ON ORIGINAL IMAGE
# -------------------------------------------------
original = cv2.cvtColor(
    np.array(img.resize((224, 224))),
    cv2.COLOR_RGB2BGR
)

overlay = cv2.addWeighted(original, 0.6, heatmap, 0.4, 0)

# -------------------------------------------------
# SAVE OUTPUT
# -------------------------------------------------
output_path = os.path.join(OUTPUT_DIR, "gradcam_output.png")
cv2.imwrite(output_path, overlay)

print("✅ Grad-CAM generated successfully!")
print("📍 Saved at:", output_path)
