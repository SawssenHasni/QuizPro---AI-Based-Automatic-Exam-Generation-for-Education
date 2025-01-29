import os
from werkzeug.utils import secure_filename
from flask import current_app
import uuid

def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def secure_save_file(file, destination):
    """
    Sauvegarde un fichier de manière sécurisée avec un nom unique
    
    Args:
        file: FileStorage object from Flask
        destination: Chemin du dossier de destination
        
    Returns:
        str: Nom du fichier sauvegardé ou None en cas d'erreur
    """
    try:
        if file and allowed_file(file.filename):
            # Générer un nom de fichier unique
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            
            # Créer le dossier de destination s'il n'existe pas
            os.makedirs(destination, exist_ok=True)
            
            # Sauvegarder le fichier
            file_path = os.path.join(destination, unique_filename)
            file.save(file_path)
            
            return unique_filename
    except Exception as e:
        current_app.logger.error(f"Error saving file: {str(e)}")
        return None 