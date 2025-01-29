from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.models.user import User
from functools import wraps
import re

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        user = User.get_by_username(session['username'])
        if not user or user.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/create_admin', methods=['GET'])
def create_admin():
    # Vérifier si l'admin existe déjà
    admin = User.get_by_username('admin')
    if not admin:
        # Créer l'admin avec le rôle 'admin'
        admin_user = User(
            username='admin',
            email='admin@quizpro.com',
            password='admin123',
            role='admin'  # Spécifier explicitement le rôle admin
        )
        admin_user.save()
        flash('Admin account created successfully', 'success')
    else:
        flash('Admin account already exists', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.get_by_username(username)
        
        if user and User.verify_password(user, password):
            if user.get('status') == 'inactive':
                flash('Your account has been deactivated. Please contact an administrator.', 'error')
                return redirect(url_for('auth.login'))
            
            User.update_last_login(username)
            session['username'] = username
            User.add_activity(username, 'login', 'User logged in successfully')
            
            if user.get('role') == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('quiz.dashboard'))
            
        flash('Invalid username or password', 'error')
        return redirect(url_for('auth.login'))
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            email = request.form['email']

            # Validation des données
            validation_errors = validate_registration_data(username, email, password)
            if validation_errors:
                for error in validation_errors:
                    flash(error, 'error')
                return redirect(url_for('auth.register'))

            # Vérification si l'utilisateur existe déjà
            if User.get_by_username(username):
                flash('Username already exists', 'error')
                return redirect(url_for('auth.register'))

            # Création de l'utilisateur avec mot de passe haché
            new_user = User(
                username=username,
                password=password,
                email=email
            )
            new_user.save()
            
            # Connecter l'utilisateur directement
            session['username'] = username
            
            flash('Registration successful!', 'success')
            return redirect(url_for('auth.welcome'))
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
            return redirect(url_for('auth.register'))
            
    # GET request - afficher le formulaire
    return render_template('register.html')

@auth_bp.route('/register/pro', methods=['GET', 'POST'])
def register_pro():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            
            # Vérifications
            if User.get_by_username(username):
                return jsonify({'success': False, 'error': 'Username already exists'})
                
            if User.get_by_email(email):
                return jsonify({'success': False, 'error': 'Email already registered'})
            
            # Create user
            user = User(
                username=username, 
                email=email, 
                password=password
            )
            user.save()
            
            # Connecter l'utilisateur directement
            session['username'] = username
            
            return jsonify({
                'success': True,
                'redirect_url': url_for('auth.welcome')
            })
            
        except Exception as e:
            current_app.logger.error(f"Error during registration: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'An error occurred during registration'
            })
        
    return render_template('register_pro.html')

@auth_bp.route('/welcome')
@login_required
def welcome():
    username = session.get('username')
    if not username:
        return redirect(url_for('auth.login'))
    return render_template('auth/welcome.html', username=username)

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

def validate_registration_data(username, email, password):
    errors = []
    
    # Validation de l'email
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        errors.append("Invalid email address")
    
    # Validation du mot de passe
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not re.search("[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search("[0-9]", password):
        errors.append("Password must contain at least one number")
    
    return errors