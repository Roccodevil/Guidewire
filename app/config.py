import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "hackathon-dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("NEON_DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
