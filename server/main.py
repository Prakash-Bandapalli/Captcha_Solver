import torch
import onnx
import onnxruntime as rt
from torchvision import transforms as T
from PIL import Image
import io
import os

# We assume tokenizer_base.py is in the same directory
try:
    from tokenizer_base import Tokenizer
except ImportError:
    print("Error: tokenizer_base.py not found.")
    raise

# --- Configuration ---
# Get the absolute path to the directory containing this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define the model file path relative to this file
model_file = os.path.join(BASE_DIR, "captcha.onnx")

img_size = (32, 128)
charset = r"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
tokenizer_base = Tokenizer(charset)

# --- Global variables for the loaded model ---
# We will initialize these in the initialize_model function
ort_session = None
transform = None

# --- Helper Functions (from original) ---

def get_transform(img_size):
    transforms = []
    transforms.extend(
        [
            T.Resize(img_size, T.InterpolationMode.BICUBIC),
            T.ToTensor(),
            T.Normalize(0.5, 0.5),
        ]
    )
    return T.Compose(transforms)

def to_numpy(tensor):
    return (
        tensor.detach().cpu().numpy() if tensor.requires_grad else tensor.cpu().numpy()
    )

# --- Main Functions for API ---

def initialize_model(model_path):
    """
    Loads the ONNX model and transform into global variables.
    Called by the API server on startup.
    """
    global ort_session, transform
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")

    transform = get_transform(img_size)
    
    # Onnx model loading
    onnx_model = onnx.load(model_path)
    onnx.checker.check_model(onnx_model)
    # Use 'CPUExecutionProvider' for broad compatibility
    ort_session = rt.InferenceSession(model_path, providers=['CPUExecutionProvider']) 
    
    print("Model and transform initialized successfully.")

def get_text_from_image_object(img_obj: Image.Image):
    """
    Takes a PIL Image object and returns the predicted text.
    This is the core logic.
    """
    global ort_session, transform

    if ort_session is None or transform is None:
        raise Exception("Model is not initialized. Call initialize_model() first.")

    # Preprocess. Model expects a batch of images with shape: (B, C, H, W)
    x = transform(img_obj.convert("RGB")).unsqueeze(0)

    # compute ONNX Runtime output prediction
    ort_inputs = {ort_session.get_inputs()[0].name: to_numpy(x)}
    logits = ort_session.run(None, ort_inputs)[0]
    
    probs = torch.tensor(logits).softmax(-1)
    # We only need the predicted text (preds)
    preds, _ = tokenizer_base.decode(probs) 
    print(f"Decoded predictions: {preds[0]}")
    return preds[0] # Return the first (and only) prediction

def get_text_from_image_bytes(image_bytes: bytes):
    """
    Takes image bytes (from an API upload) and returns the predicted text.
    This is the function api.py will import.
    """
    # Open image from bytes
    img_obj = Image.open(io.BytesIO(image_bytes))
    
    # Call the core logic function
    return get_text_from_image_object(img_obj)

# --- Original function (kept for testing) ---
def get_text_from_path(img_path):
    """Takes an image file path and returns the predicted text."""
    img_obj = Image.open(img_path)
    return get_text_from_image_object(img_obj)


# --- Test block ---
if __name__ == "__main__":
    # This code runs ONLY if you execute 'python main.py' directly
    # It's for testing this script
    print("Running main.py as a script for testing...")
    
    try:
        # 1. Initialize model
        initialize_model(model_file)
        
        # 2. Find a test image
        # Place an image named 'test_captcha.png' in the same folder to test
        test_image_path = os.path.join(BASE_DIR, "test_captcha.png") 
        
        if os.path.exists(test_image_path):
            predicted_text = get_text_from_path(test_image_path)
            print(f"Predicted text for '{test_image_path}': {predicted_text}")
        else:
            print(f"Test image '{test_image_path}' not found. Skipping test.")
            
    except Exception as e:
        print(f"Error during testing: {e}")