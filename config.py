import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

config = {
    'HOST': os.getenv('HOST', '127.0.0.1'),
    'PORT': int(os.getenv('PORT', 5000)),
    'DEBUG': os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes'),
    'SECRET_KEY': os.getenv('SECRET_KEY', 'your-secret-key-here'),
    'FLASK_ENV': os.getenv('FLASK_ENV', 'development'),
    'MONGODB_URI': os.getenv('MONGODB_URI', 'mongodb://localhost:27017/roadmap_db'),
    'JWT_ACCESS_TOKEN_EXPIRES': int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)),  # 1 hour in seconds
    'JWT_REFRESH_TOKEN_EXPIRES': int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 604800))  # 7 days in seconds
}

# Development configuration
class DevelopmentConfig:
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 5000

# Production configuration
class ProductionConfig:
    DEBUG = False
    HOST = '0.0.0.0'
    PORT = int(os.getenv('PORT', 8080))

# Get configuration based on environment
def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig()
    return DevelopmentConfig()