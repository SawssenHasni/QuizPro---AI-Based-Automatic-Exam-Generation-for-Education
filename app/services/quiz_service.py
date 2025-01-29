from Pipeline.project_1 import generate_questions as p1_generate_questions, model, tokenizer, device
from Pipeline.project_2 import MCQ, TrueFalse, OpenEnded, FillInTheBlanks, llm
from flask import current_app, session
from app.models.user import User
import os
from datetime import datetime

class QuizService:
    @staticmethod
    def get_quiz_generator(quiz_type, num_questions, difficulty):
        # Normaliser le type de quiz
        quiz_type = quiz_type.lower()
        
        generator_map = {
            'mcq': MCQ,
            'truefalse': TrueFalse,
            'openended': OpenEnded,
            'fillintheblank': FillInTheBlanks,
            'fillintheblanks': FillInTheBlanks  # Alias commun
        }
        
        generator_class = generator_map.get(quiz_type)
        if not generator_class:
            raise ValueError(f"Type de quiz invalide: {quiz_type}. Types valides: {', '.join(generator_map.keys())}")
            
        return generator_class(llm=llm, number_of_questions=num_questions, difficulty=difficulty)

    @staticmethod
    def generate_questions(paragraph, num_questions):
        return p1_generate_questions(model, tokenizer, device, paragraph, num_questions)

    @staticmethod
    def generate_quiz(file_path, num_questions, difficulty, quiz_type):
        try:
            current_app.logger.info(f"Starting quiz generation with params: type={quiz_type}, questions={num_questions}, difficulty={difficulty}")
            
            # Créer une instance du générateur de quiz approprié
            quiz_generator = QuizService.get_quiz_generator(quiz_type, num_questions, difficulty)
            current_app.logger.info(f"Quiz generator created: {type(quiz_generator).__name__}")
            
            # Générer les questions
            current_app.logger.info(f"Generating questions from file: {file_path}")
            questions = quiz_generator.generate_qa(file_path=file_path)
            
            # Vérifier si des questions ont été générées
            if not questions:
                current_app.logger.error("No questions were generated")
                raise ValueError("Aucune question n'a pu être générée")
            
            current_app.logger.info(f"Successfully generated {len(questions)} questions")
            
            # Sauvegarder en PDF avec timestamp dans le dossier uploads/pdfs
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f'quiz_{timestamp}.pdf'
            
            # Utiliser le chemin complet pour le PDF
            output_pdf = os.path.join(current_app.config['PDF_FOLDER'], pdf_filename)
            
            # S'assurer que le dossier existe
            os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
            
            current_app.logger.info(f"Saving questions to PDF: {output_pdf}")
            pdf_path = quiz_generator.save_questions_as_pdf(questions, output_pdf)
            
            if not pdf_path or not os.path.exists(pdf_path):
                current_app.logger.error("PDF file was not created")
                raise ValueError("Le fichier PDF n'a pas pu être créé")
            
            current_app.logger.info("Quiz generation completed successfully")
            return questions, pdf_path
            
        except Exception as e:
            current_app.logger.error(f"Error in generate_quiz: {str(e)}")
            current_app.logger.exception("Full traceback:")
            raise