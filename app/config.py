import os
from datetime import timedelta

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'votre-cle-secrete-par-defaut'
    
    # MongoDB configuration
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/quizpro'
    
    # File upload configuration
    PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')
    AVATARS_FOLDER = os.path.join(UPLOAD_FOLDER, 'avatars')
    PDF_FOLDER = os.path.join(UPLOAD_FOLDER, 'pdfs')
    GENERATED_FOLDER = os.path.join(PROJECT_ROOT, 'generated')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    
    # File size limits (in bytes)
    FILE_SIZE_LIMIT = 1 * 1024 * 1024  # 1MB limit for all users
    
    # Créer les dossiers nécessaires au démarrage
    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['PDF_FOLDER'], exist_ok=True)
        os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)