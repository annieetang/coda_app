import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
SOUNDSLICE_APP_ID = os.getenv("SOUNDSLICE_APP_ID")
SOUNDSLICE_PASSWORD = os.getenv("SOUNDSLICE_PASSWORD")

# File Upload Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "music")
ALLOWED_EXTENSIONS = {'xml', 'musicxml', 'mxl'}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS 