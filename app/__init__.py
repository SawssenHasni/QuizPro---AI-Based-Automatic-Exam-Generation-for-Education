from flask import Flask, send_from_directory
from app.config import Config
from dotenv import load_dotenv
import os
from app.extensions import mongo
from datetime import datetime
from app.controllers.user import user_bp
from flask import session

# Load environment variables from .env file
load_dotenv()

def create_app(config_class=Config):
    # Set custom template and static folder paths
    app = Flask(__name__, 
                template_folder='views/templates',
                static_folder='views/static')
    
    # Load configuration
    app.config.from_object(config_class)
    
    # Ensure secret key is set
    if not app.secret_key:
        app.secret_key = 'votre-cle-secrete-par-defaut'
    
    # Initialize extensions
    mongo.init_app(app)
    
    # Create upload folders
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['AVATARS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PDF_FOLDER'], exist_ok=True)
    os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)
    
    # Register custom template filters
    @app.template_filter('format_datetime')
    def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
        if value is None or value == 'N/A':
            return 'N/A'
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return value
        try:
            return value.strftime(format)
        except:
            return 'Invalid date'
    
    # Global context processor for notifications
    @app.context_processor
    def inject_notifications():
        if 'username' in session:
            from app.models.user import User
            user = User.get_by_username(session['username'])
            if user:  # Vérifier si l'utilisateur existe
                notifications = User.get_notifications(session['username'], unread_only=True)
                theme = user.get('preferences', {}).get('theme', 'light')
                return {
                    'unread_notifications_count': len(notifications),
                    'current_theme': theme
                }
        # Retourner les valeurs par défaut si l'utilisateur n'existe pas ou n'est pas connecté
        return {
            'unread_notifications_count': 0,
            'current_theme': 'light'
        }
    
    # Register blueprints
    from app.controllers.auth import auth_bp
    from app.controllers.admin import admin_bp
    from app.controllers.quiz import quiz_bp
    from app.controllers.main import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)
    
    # Import User model after mongo initialization
    from app.models.user import User
    
    with app.app_context():
        # Initialiser les statistiques et les champs manquants
        User.initialize_user_stats()
        User.initialize_user_fields()
    
    # Ajouter cette route pour servir les fichiers uploads
    @app.route('/uploads/<path:filename>')
    def uploads(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    return app