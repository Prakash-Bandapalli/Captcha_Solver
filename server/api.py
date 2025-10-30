import io
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from PIL import Image

# Import the specific function from your main.py
# This assumes main.py is in the same directory
try:
    # We need a function that takes image *bytes*
    # Let's ensure your main.py has 'get_text_from_image_bytes'
    from main import get_text_from_image_bytes, initialize_model, model_file
except ImportError:
    print("Error: Could not import from main.py.")
    print("Make sure main.py, tokenizer_base.py, and captcha.onnx are in the same directory.")
    exit(1)

# Create the FastAPI app instance
app = FastAPI(title="Captcha Solver API")

# --- IMPORTANT ---
# This enables CORS (Cross-Origin Resource Sharing)
# It allows your Chrome extension (on a different domain)
# to make requests to this server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (for development)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, etc.)
    allow_headers=["*"],  # Allows all headers
)

# This is a "startup" event.
# It ensures the model is loaded once when the server starts,
# not every time a request is made.
@app.on_event("startup")
def load_model():
    try:
        # This function is defined in your main.py
        # We just call it to get the model ready.
        initialize_model(model_file) 
        print(f"Model {model_file} loaded successfully on startup.")
    except Exception as e:
        print(f"Error loading model on startup: {e}")
        # You might want to exit if the model can't load
        # exit(1)


# Health check route
@app.get("/", summary="Health Check")
def read_root():
    """Check if the API server is running."""
    return {"status": "healthy", "message": "Captcha solver API is running."}


# This is your main API endpoint
@app.post("/solve_captcha", summary="Solve Captcha from Image")
async def solve_captcha(file: UploadFile = File(...)):
    """
    Receives a captcha image, solves it, and returns the predicted text.
    
    - **file**: The image file (e.g., PNG, JPEG) to be solved.
    """
    try:
        # 1. Read the image bytes from the uploaded file
        image_bytes = await file.read()
        
        # 2. Use your function from main.py to solve it
        predicted_text = get_text_from_image_bytes(image_bytes)
        print(predicted_text)
        
        # 3. Return the solution
        return {"text": predicted_text}
    
    except Exception as e:
        # Return an error if anything goes wrong
        return {"error": f"Error processing image: {str(e)}"}

if __name__ == "__main__":
    # This allows you to run the server by typing 'python api.py'
    # But the 'uvicorn' command is preferred for development.
    print("Starting server... (Use 'uvicorn api:app --reload' for development)")
    uvicorn.run("api:app", host="127.0.0.1", port=5000, reload=False)