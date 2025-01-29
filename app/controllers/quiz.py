from flask import Blueprint, render_template, request, session, redirect, url_for, send_file, current_app, make_response, flash, jsonify
from werkzeug.utils import secure_filename
from app.services.quiz_service import QuizService
from functools import wraps
import os
from app.models.user import User
from app.utils.file_handler import allowed_file, secure_save_file

quiz_bp = Blueprint('quiz', __name__)

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

@quiz_bp.route('/')
def question_selection():
    return render_template('question_selection.html')

@quiz_bp.route('/dashboard')
@login_required
def dashboard():
    user = User.get_by_username(session['username'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
        
    stats = {
        'questions_generated': user.get('questions_generated', 0),
        'exams_generated': user.get('exams_generated', 0)
    }
    
    return render_template('dashboard.html', 
                         username=session['username'],
                         stats=stats)

@quiz_bp.route('/admin/users')
@admin_required
def admin_users():
    users = User.get_all_users()
    return render_template('admin/users.html', users=users)

@quiz_bp.route('/project1', methods=['GET', 'POST'])
@login_required
def project1():
    if request.method == 'POST':
        paragraph = request.form.get('paragraph', '')
        num_questions = int(request.form.get('num_questions', 1))
        
        questions = QuizService.generate_questions(paragraph, num_questions)
        
        # Incrémenter le compteur de questions
        User.increment_questions_count(session['username'], num_questions)
        
        # Ajouter l'activité
        User.add_activity(
            session['username'], 
            'question', 
            f'Generated {num_questions} questions'
        )
        
        return render_template('project1.html', 
                             questions=questions, 
                             paragraph=paragraph,
                             num_questions=num_questions)
            
    return render_template('project1.html')

@quiz_bp.route('/project2', methods=['GET', 'POST'])
@login_required
def project2():
    if request.method == 'POST':
        try:
            # Créer le dossier PDF_FOLDER s'il n'existe pas
            os.makedirs(current_app.config['PDF_FOLDER'], exist_ok=True)
            
            if 'pdf_file' not in request.files:
                flash('No file part', 'error')
                return redirect(request.url)
                
            file = request.files['pdf_file']
            if file.filename == '':
                flash('No selected file', 'error')
                return redirect(request.url)
            
            # Check file size
            file_content = file.read()
            file.seek(0)  # Reset file pointer after reading
            
            if len(file_content) > current_app.config['FILE_SIZE_LIMIT']:
                flash('File size exceeds 1MB limit', 'error')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                # Sauvegarder le fichier de manière sécurisée
                filename = secure_save_file(file, current_app.config['PDF_FOLDER'])
                if not filename:
                    flash('Error saving file', 'error')
                    return redirect(request.url)
                
                # Générer l'examen
                num_questions = int(request.form.get('num_questions', 5))
                difficulty = request.form.get('difficulty', 'medium')
                question_type = request.form.get('question_type', 'mcq')
                
                file_path = os.path.join(current_app.config['PDF_FOLDER'], filename)
                questions, pdf_path = QuizService.generate_quiz(
                    file_path,
                    num_questions,
                    difficulty,
                    question_type
                )
                
                # Stocker le chemin du PDF généré dans la session
                session['generated_pdf'] = pdf_path
                
                return render_template('project2.html', 
                                     pdf_generated=True,
                                     pdf_url=url_for('quiz.view_pdf'),
                                     download_url=url_for('quiz.download_pdf'))
            else:
                flash('Invalid file type', 'error')
            
            return redirect(request.url)
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            return redirect(request.url)
            
    return render_template('project2.html')

@quiz_bp.route('/download_pdf')
@login_required
def download_pdf():
    pdf_path = session.get('generated_pdf')
    if pdf_path and os.path.exists(pdf_path):
        try:
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name="generated_questions.pdf",
                mimetype='application/pdf'
            )
        except Exception as e:
            current_app.logger.error(f"Error downloading PDF: {str(e)}")
            flash('Error downloading PDF', 'error')
    else:
        flash('PDF not found or has expired', 'error')
    return redirect(url_for('quiz.project2'))

@quiz_bp.route('/view_pdf')
@login_required
def view_pdf():
    pdf_path = session.get('generated_pdf')
    if pdf_path and os.path.exists(pdf_path):
        return send_file(
            pdf_path,
            mimetype='application/pdf'
        )
    flash('PDF not found or has expired', 'error')
    return redirect(url_for('quiz.project2'))

@quiz_bp.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    try:
        content = request.form.get('content')
        num_questions = int(request.form.get('num_questions', 5))
        difficulty = request.form.get('difficulty', 'medium')
        
        # Gérer le fichier uploadé si présent
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                # Sauvegarder et traiter le fichier
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                # Extraire le contenu du fichier selon son type
                content = extract_file_content(filepath)
        
        if not content:
            flash('Please provide content for quiz generation', 'error')
            return redirect(url_for('quiz.project1'))
            
        # Générer les questions (à implémenter selon votre logique)
        questions = generate_questions(content, num_questions, difficulty)
        
        User.add_activity(
            session['username'], 
            'question', 
            f'Generated {num_questions} questions about {content}'
        )
        
        return render_template('project1.html', questions=questions)
        
    except Exception as e:
        flash(f'Error generating quiz: {str(e)}', 'error')
        return redirect(url_for('quiz.project1'))

@quiz_bp.route('/generate_question', methods=['POST'])
@login_required
def generate_question():
    try:
        # Votre logique de génération de question existante...
        
        # Après avoir généré la question avec succès :
        User.increment_questions_count(session['username'])
        
        return jsonify({'success': True, 'question': question})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@quiz_bp.route('/generate_exam', methods=['POST'])
@login_required
def generate_exam():
    try:
        # Récupérer les paramètres de la requête
        file = request.files.get('pdf_file')
        num_questions = int(request.form.get('num_questions', 5))
        difficulty = request.form.get('difficulty', 'medium')
        question_type = request.form.get('question_type', 'multiple_choice')
        
        # Traiter le fichier si présent
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Générer l'examen à partir du fichier
            generated_exam = QuizService.generate_quiz(
                file_path,
                question_type,
                num_questions,
                difficulty
            )
        else:
            # Générer l'examen à partir d'autres paramètres
            content = request.form.get('content', '')
            generated_exam = QuizService.generate_quiz_from_content(
                content,
                question_type,
                num_questions,
                difficulty
            )
        
        # Incrémenter le compteur d'examens
        User.increment_exams_count(session['username'])
        
        # Ajouter l'activité
        User.add_activity(
            session['username'],
            'exam',
            f'Generated exam with {num_questions} questions'
        )
        
        return jsonify({
            'success': True,
            'exam': generated_exam,
            'message': 'Exam generated successfully'
        })
        
    except Exception as e:
        print(f"Error generating exam: {str(e)}")  # Pour le débogage
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quiz_bp.route('/generate_questions', methods=['POST'])
@login_required
def generate_questions():
    try:
        # Récupérer les paramètres
        content = request.form.get('content', '')
        num_questions = int(request.form.get('num_questions', 5))
        difficulty = request.form.get('difficulty', 'medium')
        question_type = request.form.get('question_type', 'multiple_choice')
        
        # Générer les questions
        generated_questions = QuizService.generate_questions(
            content,
            num_questions,
            difficulty,
            question_type
        )
        
        # Incrémenter le compteur de questions
        User.increment_questions_count(session['username'], len(generated_questions))
        
        # Ajouter l'activité
        User.add_activity(
            session['username'],
            'question',
            f'Generated {len(generated_questions)} questions'
        )
        
        return jsonify({
            'success': True,
            'questions': generated_questions,
            'message': 'Questions generated successfully'
        })
        
    except Exception as e:
        print(f"Error generating questions: {str(e)}")  # Pour le débogage
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quiz_bp.route('/upload_pdf', methods=['POST'])
@login_required
def upload_pdf():
    try:
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_save_file(file, current_app.config['PDF_FOLDER'])
            if filename:
                # Enregistrement en base de données
                user = User.get_by_username(session['username'])
                User.add_document(user['_id'], filename)
                flash('File uploaded successfully', 'success')
            else:
                flash('Error saving file', 'error')
        else:
            flash('Invalid file type', 'error')
            
        return redirect(url_for('quiz.dashboard'))
        
    except Exception as e:
        flash(f'Upload failed: {str(e)}', 'error')
        return redirect(url_for('quiz.dashboard'))