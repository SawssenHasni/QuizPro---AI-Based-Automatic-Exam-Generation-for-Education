from flask import (
    Blueprint, 
    render_template, 
    request, 
    session, 
    redirect, 
    url_for, 
    jsonify, 
    flash,
    current_app
)
from app.models.user import User
from functools import wraps
import os
from werkzeug.utils import secure_filename
import time

user_bp = Blueprint('user', __name__, url_prefix='/user')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    try:
        user = User.get_by_username(session['username'])
        stats = User.get_user_stats(session['username'])
        
        if request.method == 'POST':
            update_data = {
                'email': request.form.get('email'),
                'display_name': request.form.get('display_name'),
                'preferences': {
                    'email_notifications': request.form.get('email_notifications') == 'on',
                    'theme': request.form.get('theme', 'light')
                }
            }
            
            User.update_profile(session['username'], update_data)
            flash('Profile updated successfully', 'success')
            return redirect(url_for('user.profile'))
            
        return render_template('user/profile.html', user=user, stats=stats)
    except Exception as e:
        current_app.logger.error(f"Error in profile route: {str(e)}")
        flash('An error occurred while loading profile', 'error')
        return redirect(url_for('quiz.dashboard'))

@user_bp.route('/activities')
@login_required
def activities():
    activities = User.get_activities(session['username'])
    return render_template('user/activities.html', activities=activities)

@user_bp.route('/favorites', methods=['GET', 'POST', 'DELETE'])
@login_required
def favorites():
    if request.method == 'POST':
        question_data = request.get_json()
        User.add_favorite(session['username'], question_data)
        return jsonify({'success': True})
        
    elif request.method == 'DELETE':
        question_id = request.args.get('id')
        User.remove_favorite(session['username'], question_id)
        return jsonify({'success': True})
        
    favorites = User.get_favorites(session['username'])
    return render_template('user/favorites.html', favorites=favorites)

@user_bp.route('/notifications')
@login_required
def notifications():
    notifications = User.get_notifications(session['username'])
    return render_template('user/notifications.html', notifications=notifications)

@user_bp.route('/notifications/mark-read/<notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    User.mark_notification_read(session['username'], notification_id)
    return jsonify({'success': True})

@user_bp.route('/update_theme', methods=['POST'])
@login_required
def update_theme():
    try:
        data = request.get_json()
        theme = data.get('theme', 'light')
        
        update_data = {
            'preferences': {
                'theme': theme
            }
        }
        
        User.update_profile(session['username'], update_data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400 

@user_bp.route('/update_avatar', methods=['POST'])
@login_required
def update_avatar():
    try:
        current_app.logger.info("Starting avatar upload process...")
        
        if 'avatar' not in request.files:
            current_app.logger.error("No avatar file in request")
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['avatar']
        if file.filename == '':
            current_app.logger.error("Empty filename")
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if file and allowed_file(file.filename):
            # Créer le dossier avatars s'il n'existe pas
            os.makedirs(current_app.config['AVATARS_FOLDER'], exist_ok=True)
            
            # Sécuriser le nom du fichier et ajouter un timestamp
            filename = secure_filename(f"{session['username']}_{int(time.time())}_{file.filename}")
            file_path = os.path.join(current_app.config['AVATARS_FOLDER'], filename)
            
            # Sauvegarder le fichier
            file.save(file_path)
            
            # Créer l'URL relative pour la base de données
            avatar_url = url_for('uploads', filename=f'avatars/{filename}')
            
            # Mettre à jour la base de données
            User.update_profile(session['username'], {'avatar_url': avatar_url})
            
            return jsonify({
                'success': True,
                'avatar_url': avatar_url
            })
        
        return jsonify({'success': False, 'error': 'File type not allowed'}), 400

    except Exception as e:
        current_app.logger.error(f"Error uploading avatar: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def allowed_file(filename):
    allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    current_app.logger.info(f"Checking file {filename} against allowed extensions: {allowed_extensions}")
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@user_bp.route('/update_stats', methods=['GET'])
@login_required
def get_user_stats():
    try:
        user = User.get_by_username(session['username'])
        stats = {
            'questions_today': User.get_questions_count_today(session['username']),
            'questions_week': User.get_questions_count_week(session['username']),
            'questions_month': User.get_questions_count_month(session['username']),
            'favorite_subjects': User.get_favorite_subjects(session['username']),
            'activity_streak': User.get_activity_streak(session['username']),
            'rank': User.get_user_rank(session['username']),
            'total_time': User.get_total_time_spent(session['username'])
        }
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@user_bp.route('/update_preferences', methods=['POST'])
@login_required
def update_preferences():
    try:
        data = request.get_json()
        preferences = {
            'theme': data.get('theme', 'light'),
            'email_notifications': data.get('email_notifications', False),
            'language': data.get('language', 'en'),
            'default_subject': data.get('default_subject'),
            'difficulty_level': data.get('difficulty_level', 'medium'),
            'questions_per_page': data.get('questions_per_page', 10),
            'auto_save': data.get('auto_save', True),
            'sound_effects': data.get('sound_effects', True)
        }
        
        User.update_profile(session['username'], {'preferences': preferences})
        return jsonify({'success': True, 'message': 'Preferences updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@user_bp.route('/update_profile_info', methods=['POST'])
@login_required
def update_profile_info():
    try:
        data = request.get_json()
        update_data = {
            'display_name': data.get('display_name'),
            'bio': data.get('bio'),
            'location': data.get('location'),
            'website': data.get('website'),
            'social_links': {
                'twitter': data.get('twitter'),
                'linkedin': data.get('linkedin'),
                'github': data.get('github')
            },
            'education': data.get('education'),
            'occupation': data.get('occupation'),
            'interests': data.get('interests', []),
            'skills': data.get('skills', [])
        }
        
        User.update_profile(session['username'], update_data)
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@user_bp.route('/achievements')
@login_required
def achievements():
    try:
        achievements = User.get_achievements(session['username'])
        return render_template('user/achievements.html', achievements=achievements)
    except Exception as e:
        flash('Error loading achievements', 'error')
        return redirect(url_for('user.profile'))

@user_bp.route('/progress')
@login_required
def progress():
    try:
        progress_data = {
            'daily_stats': User.get_daily_stats(session['username']),
            'weekly_stats': User.get_weekly_stats(session['username']),
            'monthly_stats': User.get_monthly_stats(session['username']),
            'subject_stats': User.get_subject_stats(session['username']),
            'improvement_rate': User.get_improvement_rate(session['username'])
        }
        return render_template('user/progress.html', progress=progress_data)
    except Exception as e:
        flash('Error loading progress data', 'error')
        return redirect(url_for('user.profile'))

@user_bp.route('/export_data')
@login_required
def export_user_data():
    try:
        user_data = User.export_user_data(session['username'])
        return jsonify(user_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    try:
        password = request.json.get('password')
        user = User.get_by_username(session['username'])
        
        if not User.verify_password(user, password):
            return jsonify({'success': False, 'error': 'Invalid password'}), 400
            
        User.delete_user(session['username'])
        session.clear()
        return jsonify({'success': True, 'message': 'Account deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@user_bp.route('/upgrade')
@login_required
def upgrade():
    return render_template('user/upgrade.html')