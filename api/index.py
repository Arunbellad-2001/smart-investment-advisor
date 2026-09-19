import os
import sys

# Add root folder to system path so Python can find app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the existing Flask app from app.py at root
from app import app

