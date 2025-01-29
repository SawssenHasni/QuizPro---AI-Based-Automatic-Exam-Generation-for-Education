from langchain.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.chains import LLMChain
from langchain_groq import ChatGroq
import re
import random
from abc import ABC, abstractmethod
import locale
from fpdf import FPDF
import os

# Définir l'encodage local pour UTF-8
locale.getpreferredencoding = lambda: "UTF-8"


llm = ChatGroq(
    temperature=0.7,
    model_name="mixtral-8x7b-32768",
    max_tokens=4000, 
    api_key= "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")



class QuizGenerator(ABC):
    DEFAULT_CHUNK_SIZE = 4000 
    DEFAULT_CHUNK_OVERLAP = 200
    
    def __init__(self, llm, number_of_questions, difficulty):
        self.llm = llm
        self.number_of_questions = number_of_questions
        self.difficulty = difficulty
        self.chunk_size = self.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = self.DEFAULT_CHUNK_OVERLAP
        
    @abstractmethod
    def generate_template(self):
        pass
    
    @abstractmethod
    def generate_template_and_format(self):
        pass
    
    def file_processing(self, loader):
        try:
            data = loader.load()
            text = ''
            for page in data:
                text += page.page_content
            chunks = self.text_splitter(data=text)
            return chunks
        except Exception as e:
            print(f"Erreur lors du traitement du fichier: {e}")
            return []
    
    def text_splitter(self, data):
        try:
            if len(data) < self.chunk_size:
                return [data]
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                add_start_index=True
            )
            all_splits = text_splitter.split_text(data)
            return all_splits
        except Exception as e:
            print(f"Erreur lors du découpage du texte: {e}")
            return []

    def parse_json_like(self, text):
        try:
            object_pattern = r'\{.*?\}'
            pair_pattern = r'"(.*?)":\s*"(.*?)"'
            objects = re.findall(object_pattern, text, re.DOTALL)
            dict_list = []
            for obj in objects:
                pairs = re.findall(pair_pattern, obj)
                d = {key: value for key, value in pairs}
                dict_list.append(d)
            return dict_list
        except Exception as e:
            print(f"Erreur lors de l'analyse du texte: {e}")
            return []

    def create_llm_chain(self):
        template, format_instructions = self.generate_template_and_format()
        prompt = PromptTemplate(
            input_variables=["text"],
            template=template,
            partial_variables={"format_instructions": format_instructions},)
        return LLMChain(llm=self.llm, prompt=prompt)

    def generate_qa(self, file_path=None, text=None):
        if file_path and text:
            print("Entrez un fichier ou des données texte. Pas les deux.")
            return
        elif file_path:
            try:
                if file_path.endswith(".txt"):
                    loader = TextLoader(file_path)
                elif file_path.endswith(".pdf"):
                    loader = PyPDFLoader(file_path)
                else:
                    print("Format de fichier non pris en charge.")
                    return
                chunks = self.file_processing(loader=loader)
            except Exception as e:
                print(f"Erreur lors du chargement du fichier: {e}")
                return
        elif text:
            chunks = self.text_splitter(text)
        else:
            print("Veuillez fournir un chemin de fichier ou des données texte.")
            return

        if not chunks:
            print("Le document est vide ou n'a pas pu être traité.")
            return

        print(f"Traitement du document...")
        llm_chain = self.create_llm_chain()
        all_questions = []

        for i, chunk in enumerate(chunks):
            try:
                print(f"Génération de questions pour le morceau {i+1}/{len(chunks)}")
                quiz = llm_chain.invoke({'text': chunk})
                result = self.parse_json_like(quiz['text'])
                all_questions.extend(result)
            except Exception as e:
                print(f"Erreur lors de la génération des questions pour le morceau {i+1}: {e}")
                continue

        unique_questions = []
        seen_questions = set()
        for item in all_questions:
            if item.get('question') and 'answer' in item and item['question'] not in seen_questions and len(unique_questions) < self.number_of_questions:
                seen_questions.add(item['question'])
                unique_questions.append(item)

        if unique_questions:
            random.shuffle(unique_questions)
            self.format_and_display_questions(unique_questions)
            self.save_questions_as_pdf(unique_questions)
            return unique_questions
        else:
            print("Aucune question n'a pu être générée.")
            return []
        

class MCQ(QuizGenerator):
    def __init__(self, llm, number_of_questions, difficulty):
        super().__init__(llm, number_of_questions, difficulty)

    def generate_template(self):
        template = f"""<s>[INST]  Vous êtes un expert en création de questions à choix multiples basées UNIQUEMENT sur le texte fourni.
        
        IMPORTANT: Ne générez PAS de questions basées sur des connaissances générales. Utilisez UNIQUEMENT du texte .
        
        Votre objectif est de familiariser les utilisateurs avec le contenu du texte à travers des questions à choix multiples bien conçues.
        
        IMPORTANT: Pour chaque question, donnez la réponse correcte et n'utilisez pas de phrases incomplètes comme contexte.
        
        IMPORTANT: Ne répétez pas la même question. Ne reformulez/mélangez pas la même question plusieurs fois.
        
        Assurez-vous d'inclure la question et la solution dans un seul message et ne les séparez pas.
        
        Veillez à ne perdre aucune information importante.
        
        Définissez la difficulté des questions à {self.difficulty} (facile, moyen, ou difficile). Assurez-vous que toutes les questions sont réglées sur la difficulté spécifiée.
        
        Le texte d'entrée donné est :
        
        ------------
        {{text}}
        ------------
        
        IMPORTANT: Créez exactement {self.number_of_questions} questions et donnez la réponse correcte.
        
        IMPORTANT: Pour chaque question, donnez quatre options avec l'une d'entre elles étant la réponse correcte et les autres options étant incorrectes 
        (par exemple, a) Incorrect, b) Incorrect, c) Incorrect, d) Correct, réponse: d) Correct).
        
        Assurez-vous de suivre le même format {{format_instructions}} pour toutes les questions.
        
        Réfléchissez clairement et suivez les instructions marquées IMPORTANT avec la plus grande attention.
        [/INST]</s>"""
        return template

    def generate_template_and_format(self):
        template = self.generate_template()
        response_schema = [
            ResponseSchema(name="question", description="Question à choix multiples"),
            ResponseSchema(name="a)", description="Option 1"),
            ResponseSchema(name="b)", description="Option 2"),
            ResponseSchema(name="c)", description="Option 3"),
            ResponseSchema(name="d)", description="Option 4"),
            ResponseSchema(name="answer", description="Réponse correcte (format: 'd) réponse')")
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schema)
        format_instructions = output_parser.get_format_instructions()
        return template, format_instructions

    def format_and_display_questions(self, questions):
        print("\n=== Questions QCM générées ===\n")
        for i, q in enumerate(questions, 1):
            print(f"{i}. {q['question']}")
            for option in ['a)', 'b)', 'c)', 'd)']:
                if option in q:
                    print(f"   {option} {q[option]}")
            print(f"   Réponse : {q['answer']}\n")
    
    def sanitize_text(self, text):
        """Remplace les caractères spéciaux par leurs équivalents ASCII"""
        replacements = {
            'β': 'beta',
            'α': 'alpha',
            'γ': 'gamma',
            'δ': 'delta',
            'μ': 'mu',
            'π': 'pi',
            'σ': 'sigma',
            'τ': 'tau',
            'ω': 'omega',
            '°': 'deg',
            '±': '+/-',
            '×': 'x',
            '÷': '/',
            '≈': '~',
            '≠': '!=',
            '≤': '<=',
            '≥': '>=',
            '∞': 'inf',
            '∑': 'sum',
            '∏': 'prod',
            '∫': 'int',
            '∂': 'd',
            '√': 'sqrt',
            '∴': 'therefore',
            '∵': 'because',
            '∼': '~',
            '≅': '~=',
            '≡': '===',
            '≪': '<<',
            '≫': '>>'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def save_questions_as_pdf(self, questions, filename="qcm_questions.pdf"):
        try:
            # Utiliser le chemin complet dans le dossier generated
            output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'generated', filename)
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            
            # Encoder le titre
            pdf.cell(190, 10, "Questions à Choix Multiples", ln=True, align='C')
            pdf.ln(10)

            # Questions et options
            for i, q in enumerate(questions, 1):
                pdf.set_font("Helvetica", '', 12)
                
                # Nettoyer et encoder la question
                question_text = self.sanitize_text(f"{i}. {q['question']}")
                pdf.multi_cell(0, 10, question_text)
                
                # Nettoyer et encoder les options
                for option in ['a)', 'b)', 'c)', 'd)']:
                    if option in q:
                        option_text = self.sanitize_text(f"   {option} {q[option]}")
                        pdf.multi_cell(0, 10, option_text)
                
                # Nettoyer et encoder la réponse
                answer_text = self.sanitize_text(f"   Réponse : {q['answer']}")
                pdf.multi_cell(0, 10, answer_text)
                pdf.ln(5)

            # Sauvegarder dans le chemin complet
            pdf.output(output_path)
            print(f"\nQuestions sauvegardées dans {output_path}")
            return output_path

        except Exception as e:
            print(f"Erreur lors de la sauvegarde du PDF: {str(e)}")
            return None

    def save_questions_as_txt(self, questions, filename="qcm_questions.txt"):
        """Sauvegarde les questions dans un fichier texte avec encodage UTF-8"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=== Questions à Choix Multiples ===\n\n")
                for i, q in enumerate(questions, 1):
                    f.write(f"{i}. {q['question']}\n")
                    for option in ['a)', 'b)', 'c)', 'd)']:
                        if option in q:
                            f.write(f"   {option} {q[option]}\n")
                    f.write(f"   Réponse : {q['answer']}\n\n")
            print(f"\nQuestions sauvegardées dans {filename}")
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du fichier texte: {str(e)}")


class TrueFalse(QuizGenerator):
    def __init__(self, llm, number_of_questions, difficulty):
        super().__init__(llm, number_of_questions, difficulty)

    def generate_template(self):
        template = f"""<s>[INST]Vous êtes un expert en création de questions Vrai/Faux basées UNIQUEMENT sur le texte fourniet, et vous devez générer les questions dans la même langue que le texte d'entrée..
        
        IMPORTANT: Ne générez PAS de questions basées sur des connaissances générales. Utilisez UNIQUEMENT les informations présentes dans le texte donné.
        
        Votre objectif est de familiariser les utilisateurs avec le contenu du texte à travers des questions Vrai/Faux bien conçues.
        
        IMPORTANT: Pour chaque question, donnez la réponse correcte et n'utilisez pas de phrases incomplètes comme contexte.
        
        IMPORTANT: Ne répétez pas la même question. Ne reformulez/mélangez pas la même question plusieurs fois.
        
        Assurez-vous d'inclure la question et la solution dans un seul message et ne les séparez pas.
        
        Veillez à ne perdre aucune information importante.
        
     
        Le texte d'entrée donné est :
        
        ------------
        {{text}}
        ------------
        IMPORTANT:  Définissez la difficulté des questions à {self.difficulty} (facile, moyen, ou difficile). Assurez-vous que toutes les questions sont réglées sur la difficulté spécifiée.
        
        IMPORTANT: Créez exactement {self.number_of_questions} questions et donnez la réponse correcte.
        IMPORTANT: Pour chaque question, la réponse correcte doit être binaire, c'est-à-dire soit Vrai soit Faux uniquement.
        Assurez-vous de suivre le même format {{format_instructions}} pour toutes les questions.
        Réfléchissez clairement et suivez les instructions marquées IMPORTANT avec la plus grande attention.
        [/INST]</s>"""
        return template

    def generate_template_and_format(self):
        template = self.generate_template()
        response_schema = [
            ResponseSchema(name="question", description="Question vrai/faux"),
            ResponseSchema(name="answer", description="Réponse correcte (format: 'Vrai' ou 'Faux')")
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schema)
        format_instructions = output_parser.get_format_instructions()
        return template, format_instructions

    def format_and_display_questions(self, questions):
        print("\n=== Questions Vrai/Faux générées ===\n")
        for i, q in enumerate(questions, 1):
            print(f"{i}. {q['question']}")
            print(f"   a) Vrai\n   b) Faux")
            print(f"   Réponse correcte : {'a) Vrai' if q['answer'] == 'Vrai' else 'b) Faux'}\n")

    def sanitize_text(self, text):
        """Remplace les caractères spéciaux par leurs équivalents ASCII"""
        replacements = {
            'β': 'beta',
            'α': 'alpha',
            'γ': 'gamma',
            'δ': 'delta',
            'μ': 'mu',
            'π': 'pi',
            'σ': 'sigma',
            'τ': 'tau',
            'ω': 'omega',
            '°': 'deg',
            '±': '+/-',
            '×': 'x',
            '÷': '/',
            '≈': '~',
            '≠': '!=',
            '≤': '<=',
            '≥': '>=',
            '∞': 'inf',
            '∑': 'sum',
            '∏': 'prod',
            '∫': 'int',
            '∂': 'd',
            '√': 'sqrt',
            '∴': 'therefore',
            '∵': 'because',
            '∼': '~',
            '≅': '~=',
            '≡': '===',
            '≪': '<<',
            '≫': '>>'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def save_questions_as_pdf(self, questions, filename="true_false_questions.pdf"):
        """Sauvegarde les questions en PDF avec gestion des caractères spéciaux"""
        try:
            # Utiliser le chemin complet dans le dossier generated
            output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'generated', filename)
            
            pdf = FPDF()
            pdf.add_page()
            
            # Titre
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(190, 10, "Questions Vrai/Faux", ln=True, align='C')
            pdf.ln(10)

            # Questions et réponses
            for i, q in enumerate(questions, 1):
                pdf.set_font("Helvetica", '', 12)
                
                # Nettoyer et encoder la question
                question_text = self.sanitize_text(f"{i}. {q['question']}")
                pdf.multi_cell(0, 10, question_text)
                
                # Options
                pdf.multi_cell(0, 10, "   a) Vrai")
                pdf.multi_cell(0, 10, "   b) Faux")
                
                # Réponse
                answer_text = "   Réponse correcte : " + ('a) Vrai' if q['answer'] == 'Vrai' else 'b) Faux')
                pdf.multi_cell(0, 10, answer_text)
                pdf.ln(5)

            # Sauvegarder dans le chemin complet
            pdf.output(output_path)
            print(f"\nQuestions sauvegardées dans {output_path}")
            return output_path

        except Exception as e:
            print(f"Erreur lors de la sauvegarde du PDF: {str(e)}")
            return None



class OpenEnded(QuizGenerator):
    """Inherits QuizGenerator class and creates Open-Ended questions"""
    
    def __init__(self, llm, number_of_questions, difficulty):
        super().__init__(llm, number_of_questions, difficulty)

    def generate_template(self):
        template = f"""<s>[INST]Vous êtes un expert en création de questions ouvertes basées UNIQUEMENT sur le texte fourni.
        
        IMPORTANT: Ne générez PAS de questions basées sur des connaissances générales. Utilisez UNIQUEMENT les informations présentes dans le texte donné.
        
        Votre objectif est de familiariser les utilisateurs avec le contenu du texte à travers des questions ouvertes bien conçues.
        
        IMPORTANT: Pour chaque question, fournissez une réponse détaillée et n'utilisez pas de phrases incomplètes comme contexte.
        
        IMPORTANT: Ne répétez pas la même question. Ne reformulez/mélangez pas la même question plusieurs fois.
        
        Assurez-vous d'inclure la question et la solution dans un seul message et ne les séparez pas.
        
        Veillez à ne perdre aucune information importante.
        
        Définissez la difficulté des questions à {self.difficulty}. Assurez-vous que toutes les questions sont réglées sur la difficulté spécifiée.
        Le texte d'entrée donné est :
        
        ------------ 
        {{text}} 
        ------------ 
        IMPORTANT: Créez exactement {self.number_of_questions} questions et donnez la réponse détaillée.
        
        IMPORTANT: Générez des questions qui nécessitent une réponse d'au moins une demi-douzaine de mots, avec une réponse claire et descriptive.
        
        Assurez-vous de suivre le même format {{format_instructions}} pour toutes les questions.
        
        Réfléchissez clairement et suivez les instructions marquées IMPORTANT avec la plus grande attention.
        [/INST]</s>"""
        return template

    def generate_template_and_format(self):
        template = self.generate_template()
        response_schema = [
            ResponseSchema(name="question", description="Une question ouverte générée à partir du snippet de texte d'entrée."),
            ResponseSchema(name="answer", description="Réponse détaillée à la question ouverte.")
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schema)
        format_instructions = output_parser.get_format_instructions()
        return template, format_instructions

    def format_and_display_questions(self, questions):
        print("\n=== Questions ouvertes générées ===\n")
        for i, q in enumerate(questions, 1):
            print(f"Question {i}:")
            print(f"   {q['question']}")
            print(f"\n   Réponse :")
            print(f"   {q['answer']}\n")

    def sanitize_text(self, text):
        """Remplace les caractères spéciaux par leurs équivalents ASCII"""
        replacements = {
            'β': 'beta',
            'α': 'alpha',
            'γ': 'gamma',
            'δ': 'delta',
            'μ': 'mu',
            'π': 'pi',
            'σ': 'sigma',
            'τ': 'tau',
            'ω': 'omega',
            '°': 'deg',
            '±': '+/-',
            '×': 'x',
            '÷': '/',
            '≈': '~',
            '≠': '!=',
            '≤': '<=',
            '≥': '>=',
            '∞': 'inf',
            '∑': 'sum',
            '∏': 'prod',
            '∫': 'int',
            '∂': 'd',
            '√': 'sqrt',
            '∴': 'therefore',
            '∵': 'because',
            '∼': '~',
            '≅': '~=',
            '≡': '===',
            '≪': '<<',
            '≫': '>>'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def save_questions_as_pdf(self, questions, filename="open_ended_questions.pdf"):
        """Sauvegarde les questions en PDF avec gestion des caractères spéciaux"""
        try:
            # Utiliser le chemin complet dans le dossier generated
            output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'generated', filename)
            
            pdf = FPDF()
            pdf.add_page()
            
            # Titre
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(190, 10, "Questions ouvertes", ln=True, align='C')
            pdf.ln(10)

            # Questions et réponses
            for i, q in enumerate(questions, 1):
                pdf.set_font("Helvetica", '', 12)
                
                # Nettoyer et encoder la question
                question_text = self.sanitize_text(f"{i}. {q['question']}")
                pdf.multi_cell(0, 10, question_text)
                
                # Nettoyer et encoder la réponse
                answer_text = self.sanitize_text(f"   Réponse : {q['answer']}")
                pdf.multi_cell(0, 10, answer_text)
                pdf.ln(5)

            # Sauvegarder dans le chemin complet
            pdf.output(output_path)
            print(f"\nQuestions sauvegardées dans {output_path}")
            return output_path

        except Exception as e:
            print(f"Erreur lors de la sauvegarde du PDF: {str(e)}")
            return None



class FillInTheBlanks(QuizGenerator):
    """
    Hérite de la classe QuizGenerator et crée des questions à compléter
    """
    def __init__(self, llm, number_of_questions, difficulty):
        super().__init__(llm, number_of_questions, difficulty)

    def generate_template(self):
        template = f"""<s>[INST] Vous êtes un expert en création de questions de type "Remplissez les blancs" basées UNIQUEMENT sur le texte fourni.

                  IMPORTANT : Ne générez PAS de questions basées sur des connaissances générales. Utilisez UNIQUEMENT les informations présentes dans le texte donné.

                  Votre objectif est de familiariser les utilisateurs avec le contenu du texte à travers des questions "Remplissez les blancs" bien conçues.

                  IMPORTANT : Pour chaque question, laissez un espace vide à remplir et donnez la réponse correcte à la fin de la question. N'utilisez pas de phrases incomplètes comme contexte.

                  IMPORTANT : Ne répétez pas la même question. Ne reformulez/mélangez pas la même question plusieurs fois.

                  Assurez-vous d'inclure la question et la solution dans un seul message et ne les séparez pas.

                  Veillez à ne perdre aucune information importante.

                  Définissez la difficulté des questions à {self.difficulty} (facile, moyen, ou difficile). Assurez-vous que toutes les questions sont réglées sur la difficulté spécifiée.

                  Le texte d'entrée donné est :

                    ------------ 
                      {{text}} 
                    ------------

                   IMPORTANT : Créez exactement {self.number_of_questions} questions de type "Remplissez les blancs" et donnez la réponse correcte pour chaque espace vide.

                   Exemple de format :
                   "Le ________ est responsable de la transmission des impulsions nerveuses. Réponse : neurone"

                  Assurez-vous de suivre le même format {{format_instructions}} pour toutes les questions.

                  Réfléchissez clairement et suivez les instructions marquées IMPORTANT avec la plus grande attention.
        [/INST]</s>"""
        return template

    def generate_template_and_format(self):
        template = self.generate_template()
        response_schema = [
            ResponseSchema(name="question", 
                         description="Une question à compléter avec le mot clé représenté par un espace vide, générée à partir du texte d'entrée."),
            ResponseSchema(name="answer", 
                         description="Réponse correcte pour la question. Fournir la réponse avec les espaces remplis.")
        ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schema)
        format_instructions = output_parser.get_format_instructions()
        return template, format_instructions

    def format_and_display_questions(self, questions):
        print("=== Questions générées ===\n")
        seen_questions = set()
        for i, q in enumerate(questions, 1):
            question = q['question'].strip()
            answer = q['answer'].strip()
            
            if question and question not in seen_questions:
                seen_questions.add(question)
                
                # Remplacer le mot ou phrase clé par des underscores
                formatted_question = question.replace(answer, '_____')
                
                print(f"Question {i}:")
                print(f"   {formatted_question}")
                print(f"\n   Réponse :")
                print(f"   {answer}\n")
            else:
                print(f"Question déjà affichée ou vide (question {i}): {question}")

    def sanitize_text(self, text):
        """Remplace les caractères spéciaux par leurs équivalents ASCII"""
        replacements = {
            'β': 'beta',
            'α': 'alpha',
            'γ': 'gamma',
            'δ': 'delta',
            'μ': 'mu',
            'π': 'pi',
            'σ': 'sigma',
            'τ': 'tau',
            'ω': 'omega',
            '°': 'deg',
            '±': '+/-',
            '×': 'x',
            '÷': '/',
            '≈': '~',
            '≠': '!=',
            '≤': '<=',
            '≥': '>=',
            '∞': 'inf',
            '∑': 'sum',
            '∏': 'prod',
            '∫': 'int',
            '∂': 'd',
            '√': 'sqrt',
            '∴': 'therefore',
            '∵': 'because',
            '∼': '~',
            '≅': '~=',
            '≡': '===',
            '≪': '<<',
            '≫': '>>',
            'œ':'oe',
            '’': "'" 
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    
    def save_questions_as_pdf(self, questions, filename="fill_in_the_blanks_questions.pdf"):
        """Sauvegarde les questions en PDF avec gestion des caractères spéciaux"""
        try:
            # Utiliser le chemin complet dans le dossier generated
            output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'generated', filename)
            
            pdf = FPDF()
            pdf.add_page()
            
            # Titre
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(190, 10, "Questions Remplir les blancs ", ln=True, align='C')
            pdf.ln(10)

            # Questions et réponses
            for i, q in enumerate(questions, 1):
                pdf.set_font("Helvetica", '', 12)
                
                # Nettoyer et encoder la question
                question_text = self.sanitize_text(f"{i}. {q['question']}")
                pdf.multi_cell(0, 10, question_text)
                
                # Nettoyer et encoder la réponse
                answer_text = self.sanitize_text(f"   Réponse : {q['answer']}")
                pdf.multi_cell(0, 10, answer_text)
                pdf.ln(5)

            # Sauvegarder dans le chemin complet
            pdf.output(output_path)
            print(f"\nQuestions sauvegardées dans {output_path}")
            return output_path

        except Exception as e:
            print(f"Erreur lors de la sauvegarde du PDF: {str(e)}")
            return None
