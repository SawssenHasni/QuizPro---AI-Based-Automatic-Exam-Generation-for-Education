import os

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'votre-cle-secrete-par-defaut'
    
    # MongoDB configuration
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/quizpro'
    
    # File upload configuration
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))  # Chemin vers app-flask1
    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')  # uploads sera à la racine
    AVATARS_FOLDER = os.path.join(UPLOAD_FOLDER, 'avatars')
    PDF_FOLDER = os.path.join(UPLOAD_FOLDER, 'pdfs')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    FILE_SIZE_LIMIT = 1 * 1024 * 1024  # 1MB limit for free users
    
    # Stripe configuration
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    # Assurez-vous que ces dossiers existent au démarrage
    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['PDF_FOLDER'], exist_ok=True)