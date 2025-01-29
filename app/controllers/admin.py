from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify, send_file, make_response
from app.models.user import User
from functools import wraps
from datetime import datetime
import csv
from io import StringIO

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        
        user = User.get_by_username(session['username'])
        if not user or user.get('role') != 'admin':
            flash('Admin access required')
            return redirect(url_for('quiz.dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    search_term = request.args.get('search', '').strip()
    
    # Récupérer toutes les statistiques en une seule requête
    stats = User.get_user_stats_summary()
    
    if search_term:
        users = User.search_users(search_term)
    else:
        users = User.get_all_users()
        
    return render_template('admin_dashboard.html',
                         users=users,
                         search_term=search_term,
                         total_users=stats['total_users'],
                         active_users=stats['active_users'],
                         total_exams=stats['total_exams'],
                         total_questions=stats['total_questions'])

@admin_bp.route('/create_admin')
def create_admin():
    # Vérifier si l'admin existe déjà
    admin = User.get_by_username('admin')
    if not admin:
        # Créer l'admin avec le rôle 'admin'
        admin_user = User(
            username='admin',
            email='admin@quizpro.com',
            password='admin123',
            role='admin'
        )
        admin_user.save()
        flash('Admin account created successfully')
    return redirect(url_for('auth.login'))

@admin_bp.route('/delete_user/<username>', methods=['POST'])
@admin_required
def delete_user(username):
    try:
        # Empêcher la suppression du compte admin
        if username == 'admin':
            return jsonify({
                'success': False, 
                'message': 'Cannot delete admin account'
            }), 400
        
        # Vérifier si l'utilisateur existe
        user = User.get_by_username(username)
        if not user:
            return jsonify({
                'success': False, 
                'message': 'User not found'
            }), 404
        
        # Supprimer l'utilisateur
        User.delete_user(username)
        
        # Ajouter un message flash pour l'interface utilisateur
        flash(f'User {username} has been deleted successfully', 'success')
        
        return jsonify({
            'success': True,
            'message': f'User {username} has been deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting user: {str(e)}")  # Pour le débogage
        return jsonify({
            'success': False,
            'message': f'Error deleting user: {str(e)}'
        }), 500

@admin_bp.route('/stats')
@admin_required
def stats():
    # Récupérer les statistiques complètes avec les tendances
    stats_data = User.get_user_stats_summary()
    
    # Récupérer les utilisateurs récents
    recent_users = User.get_recent_users(limit=5)
    
    # Ajouter les utilisateurs récents aux statistiques
    stats_data['recent_users'] = recent_users
    
    # S'assurer que toutes les clés nécessaires existent
    default_stats = {
        'total_users': 0,
        'total_questions': 0,
        'total_exams': 0,
        'active_users': 0,
        'user_growth': 0,
        'questions_growth': 0,
        'exams_growth': 0,
        'active_growth': 0,
        'recent_users': []
    }
    
    # Fusionner les statistiques par défaut avec les données réelles
    stats_data = {**default_stats, **stats_data}
    
    return render_template('admin/stats.html', stats=stats_data)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        # Handle updating system settings
        flash('Settings updated successfully')
        return redirect(url_for('admin.settings'))
    
    return render_template('admin/settings.html')

@admin_bp.route('/toggle_user_status/<username>', methods=['POST'])
@admin_required
def toggle_user_status(username):
    try:
        # Empêcher la désactivation du compte admin
        if username == 'admin':
            return jsonify({
                'success': False,
                'message': 'Cannot modify admin account status'
            }), 400
        
        # Vérifier si l'utilisateur existe
        user = User.get_by_username(username)
        if not user:
            print(f"User not found: {username}")  # Debug log
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Basculer le statut
        current_status = user.get('status', 'inactive')
        new_status = 'inactive' if current_status == 'active' else 'active'
        
        # Mettre à jour le statut
        success = User.update_user_status(username, new_status)
        
        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to update user status'
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'User status changed to {new_status}',
            'new_status': new_status
        })
        
    except Exception as e:
        print(f"Error toggling user status: {str(e)}")  # Pour le débogage
        return jsonify({
            'success': False,
            'message': f'Error toggling user status: {str(e)}'
        }), 500

@admin_bp.route('/user/<username>')
@admin_required
def user_details(username):
    """Affiche les détails d'un utilisateur spécifique"""
    user = User.get_by_username(username)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/user_details.html', user=user)

@admin_bp.route('/update_user_role/<username>', methods=['POST'])
@admin_required
def update_user_role(username):
    """Met à jour le rôle d'un utilisateur"""
    if username == 'admin':
        return {'success': False, 'message': 'Cannot modify admin role'}, 400
    
    new_role = request.json.get('role')
    if new_role not in ['user', 'admin']:
        return {'success': False, 'message': 'Invalid role'}, 400
    
    User.update_user(username, {'role': new_role})
    return {
        'success': True,
        'message': f'User role updated to {new_role}',
        'new_role': new_role
    }

@admin_bp.route('/search_users')
@admin_required
def search_users():
    """Recherche des utilisateurs"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'users': []})
    
    try:
        users = User.search_users(query)
        # Formater les dates pour la réponse JSON
        formatted_users = []
        for user in users:
            user_dict = {
                'username': user.get('username'),
                'email': user.get('email'),
                'role': user.get('role', 'user'),
                'status': user.get('status', 'inactive'),
                'created_at': user.get('created_at'),
                'last_login': user.get('last_login'),
                'questions_generated': user.get('questions_generated', 0),
                'exams_generated': user.get('exams_generated', 0)
            }
            formatted_users.append(user_dict)
        
        return jsonify({'users': formatted_users})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/export_users')
@admin_required
def export_users():
    """Exporte les données des utilisateurs en CSV"""
    try:
        users = User.get_all_users()
        
        # Créer un buffer pour le CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Écrire l'en-tête
        writer.writerow([
            'Username',
            'Email',
            'Role',
            'Status',
            'Created At',
            'Last Login',
            'Questions Generated',
            'Exams Generated'
        ])
        
        # Écrire les données des utilisateurs
        for user in users:
            writer.writerow([
                user.get('username', ''),
                user.get('email', ''),
                user.get('role', 'user'),
                user.get('status', 'inactive'),
                user.get('created_at', 'N/A'),
                user.get('last_login', 'Never'),
                str(user.get('questions_generated', 0)),
                str(user.get('exams_generated', 0))
            ])
        
        # Créer la réponse
        output.seek(0)
        filename = f'users_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        return response
        
    except Exception as e:
        print(f"Export error: {str(e)}")  # Pour le débogage
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/check_user_stats/<username>')
@admin_required
def check_user_stats(username):
    user = User.get_by_username(username)
    if user:
        stats = {
            'username': username,
            'questions_generated': user.get('questions_generated', 0),
            'exams_generated': user.get('exams_generated', 0),
            'last_activity': user.get('last_activity', 'Never'),
            'last_activity_type': user.get('last_activity_type', 'None')
        }
        return jsonify(stats)
    return jsonify({'error': 'User not found'}), 404

@admin_bp.route('/repair_counters/<username>')
@admin_required
def repair_user_counters(username):
    """Route pour réparer les compteurs d'un utilisateur"""
    success = User.repair_counters(username)
    if success:
        flash(f'Counters repaired for user {username}', 'success')
    else:
        flash(f'Error repairing counters for user {username}', 'error')
    return redirect(url_for('admin.user_details', username=username))