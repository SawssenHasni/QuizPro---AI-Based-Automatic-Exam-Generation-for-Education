from app.extensions import mongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

class User:
    def __init__(self, username, email, password, role='user', registration_type='free', status='active'):
        self.username = username
        self.email = email
        self.password = generate_password_hash(password)
        self.role = role
        self.registration_type = registration_type
        self.status = 'pending' if registration_type == 'pro' else status
        self.payment_status = 'pending' if registration_type == 'pro' else 'completed'
        self.questions_generated = 0
        self.exams_generated = 0
        self.created_at = datetime.utcnow()
        self.last_login = datetime.utcnow()

    def save(self):
        user_data = {
            'username': self.username,
            'email': self.email,
            'password': self.password,
            'role': self.role,
            'registration_type': self.registration_type,
            'status': self.status,
            'payment_status': self.payment_status,
            'questions_generated': 0,
            'exams_generated': 0,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S'),
            'last_activity': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'last_activity_type': 'registration'
        }
        mongo.db.users.insert_one(user_data)

    @staticmethod
    def get_by_username(username):
        return mongo.db.users.find_one({"username": username})

    @staticmethod
    def get_by_email(email):
        return mongo.db.users.find_one({'email': email})

    @staticmethod
    def verify_password(user, password):
        if not user:
            return False
        return check_password_hash(user['password'], password)

    @staticmethod
    def get_all_users():
        """Récupère tous les utilisateurs avec des informations formatées"""
        users = list(mongo.db.users.find())
        for user in users:
            # Ajouter des valeurs par défaut pour les champs manquants
            user['created_at'] = user.get('created_at', 'N/A')
            user['last_login'] = user.get('last_login', 'Never')
            user['status'] = user.get('status', 'inactive')
            user['role'] = user.get('role', 'user')
            user['questions_generated'] = user.get('questions_generated', 0)
            user['exams_generated'] = user.get('exams_generated', 0)
        return users

    @staticmethod
    def update_user(username, update_data):
        """Met à jour les informations d'un utilisateur"""
        mongo.db.users.update_one(
            {'username': username},
            {'$set': update_data}
        )

    @staticmethod
    def delete_user(username):
        """Supprime un utilisateur"""
        mongo.db.users.delete_one({'username': username})

    @staticmethod
    def count_users():
        return mongo.db.users.count_documents({})

    @staticmethod
    def count_active_users():
        return mongo.db.users.count_documents({'status': 'active'})

    @staticmethod
    def get_recent_users(limit=5):
        return list(mongo.db.users.find().sort('_id', -1).limit(limit))

    @classmethod
    def search_users(cls, search_term):
        """
        Recherche des utilisateurs par nom d'utilisateur ou email
        """
        # Utiliser une expression régulière pour faire une recherche insensible à la casse
        query = {
            "$or": [
                {"username": {"$regex": search_term, "$options": "i"}},
                {"email": {"$regex": search_term, "$options": "i"}}
            ]
        }
        users = mongo.db.users.find(query)
        return list(users)

    @staticmethod
    def increment_questions_count(username, count=1):
        """Incrémente le nombre de questions générées"""
        try:
            current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            
            # Mettre à jour le compteur et la dernière activité
            result = mongo.db.users.update_one(
                {'username': username},
                {
                    '$inc': {'questions_generated': count},
                    '$set': {
                        'last_activity': current_time,
                        'last_activity_type': 'question_generation'
                    }
                }
            )
            
            if result.modified_count == 0:
                print(f"Warning: No document updated for user {username}")
                
            # Ajouter l'entrée dans l'historique des questions
            mongo.db.questions_history.insert_one({
                'username': username,
                'count': count,
                'created_at': current_time,
                'type': 'generated'
            })
            
            return True
        except Exception as e:
            print(f"Error incrementing questions count: {str(e)}")
            return False

    @staticmethod
    def increment_exams_count(username):
        """Incrémente le nombre d'examens générés"""
        try:
            current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            
            # Mettre à jour le compteur et la dernière activité
            result = mongo.db.users.update_one(
                {'username': username},
                {
                    '$inc': {'exams_generated': 1},
                    '$set': {
                        'last_activity': current_time,
                        'last_activity_type': 'exam_generation'
                    }
                }
            )
            
            if result.modified_count == 0:
                print(f"Warning: No document updated for user {username}")
                
            # Ajouter l'entrée dans l'historique des examens
            mongo.db.exams_history.insert_one({
                'username': username,
                'created_at': current_time
            })
            
            return True
        except Exception as e:
            print(f"Error incrementing exams count: {str(e)}")
            return False

    @staticmethod
    def get_user_stats(username):
        """Récupère les statistiques détaillées d'un utilisateur"""
        user = mongo.db.users.find_one({'username': username})
        current_time = datetime.utcnow()
        today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Statistiques de base
        stats = {
            'questions_generated': user.get('questions_generated', 0),
            'exams_generated': user.get('exams_generated', 0),
            'last_activity': user.get('last_activity', 'Never'),
        }
        
        # Questions aujourd'hui
        stats['questions_today'] = mongo.db.questions.count_documents({
            'created_by': username,
            'created_at': {
                '$gte': today_start.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
        # Questions cette semaine
        week_start = today_start - timedelta(days=today_start.weekday())
        stats['questions_week'] = mongo.db.questions.count_documents({
            'created_by': username,
            'created_at': {
                '$gte': week_start.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
        # Questions ce mois
        month_start = today_start.replace(day=1)
        stats['questions_month'] = mongo.db.questions.count_documents({
            'created_by': username,
            'created_at': {
                '$gte': month_start.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
        return stats

    @staticmethod
    def initialize_user_stats():
        """Initialise les statistiques pour tous les utilisateurs qui n'en ont pas"""
        mongo.db.users.update_many(
            {
                '$or': [
                    {'questions_generated': {'$exists': False}},
                    {'exams_generated': {'$exists': False}}
                ]
            },
            {
                '$set': {
                    'questions_generated': 0,
                    'exams_generated': 0
                }
            }
        )

    @staticmethod
    def update_last_login(username):
        """Met à jour la date de dernière connexion"""
        mongo.db.users.update_one(
            {'username': username},
            {'$set': {'last_login': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}}
        )

    @staticmethod
    def search_users(query):
        """Recherche des utilisateurs par nom ou email"""
        try:
            regex_query = {'$regex': query, '$options': 'i'}
            users = list(mongo.db.users.find({
                '$or': [
                    {'username': regex_query},
                    {'email': regex_query}
                ]
            }))
            
            # Ajouter des valeurs par défaut pour les champs manquants
            for user in users:
                user['created_at'] = user.get('created_at', 'N/A')
                user['last_login'] = user.get('last_login', 'Never')
                user['status'] = user.get('status', 'inactive')
                user['role'] = user.get('role', 'user')
                user['questions_generated'] = user.get('questions_generated', 0)
                user['exams_generated'] = user.get('exams_generated', 0)
                
                # Supprimer le mot de passe de la réponse
                if 'password' in user:
                    del user['password']
            
            return users
        except Exception as e:
            print(f"Error in search_users: {str(e)}")
            return []

    @staticmethod
    def get_user_activity(username):
        """Récupère l'activité récente d'un utilisateur"""
        user = mongo.db.users.find_one({'username': username})
        return {
            'last_login': user.get('last_login'),
            'questions_generated': user.get('questions_generated', 0),
            'exams_generated': user.get('exams_generated', 0)
        }

    @staticmethod
    def initialize_user_fields():
        """Initialise les champs manquants pour les utilisateurs existants"""
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        default_preferences = {
            'email_notifications': False,
            'theme': 'light'
        }
        
        mongo.db.users.update_many(
            {'preferences': {'$exists': False}},
            {
                '$set': {
                    'preferences': default_preferences,
                    'created_at': current_time,
                    'status': 'active',
                    'questions_generated': 0,
                    'exams_generated': 0
                }
            }
        )

    @staticmethod
    def count_total_exams():
        """Compte le nombre total d'examens générés par tous les utilisateurs"""
        pipeline = [
            {
                '$group': {
                    '_id': None,
                    'total_exams': {'$sum': '$exams_generated'}
                }
            }
        ]
        result = list(mongo.db.users.aggregate(pipeline))
        return result[0]['total_exams'] if result else 0

    @staticmethod
    def count_total_questions():
        """Compte le nombre total de questions générées par tous les utilisateurs"""
        pipeline = [
            {
                '$group': {
                    '_id': None,
                    'total_questions': {'$sum': '$questions_generated'}
                }
            }
        ]
        result = list(mongo.db.users.aggregate(pipeline))
        return result[0]['total_questions'] if result else 0

    @staticmethod
    def get_user_stats_summary():
        """Récupère un résumé des statistiques des utilisateurs"""
        try:
            # Calculer les totaux depuis les collections d'historique
            total_questions = mongo.db.questions_history.count_documents({})
            total_exams = mongo.db.exams_history.count_documents({})
            
            # Autres statistiques
            total_users = mongo.db.users.count_documents({})
            active_users = mongo.db.users.count_documents({'status': 'active'})
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'total_questions': total_questions,
                'total_exams': total_exams
            }
        except Exception as e:
            print(f"Error getting stats summary: {str(e)}")
            return {
                'total_users': 0,
                'active_users': 0,
                'total_questions': 0,
                'total_exams': 0
            }

    @staticmethod
    def get_by_stripe_customer_id(customer_id):
        return mongo.db.users.find_one({"stripe_customer_id": customer_id})

    @staticmethod
    def get_subscription_status(username):
        user = User.get_by_username(username)
        return user.get('subscription', 'free') if user else 'free'

    @staticmethod
    def has_active_subscription(username):
        user = User.get_by_username(username)
        return user.get('subscription') in ['pro', 'enterprise'] if user else False

    @staticmethod
    def complete_registration(username, subscription_data):
        """Complète l'inscription avec les données d'abonnement"""
        update_data = {
            'subscription': subscription_data.get('plan'),
            'stripe_customer_id': subscription_data.get('customer_id'),
            'stripe_subscription_id': subscription_data.get('subscription_id'),
            'registration_type': 'completed',
            'pending_subscription_session': None
        }
        User.update_user(username, update_data)

    @staticmethod
    def update_profile(username, update_data):
        """Met à jour le profil de l'utilisateur"""
        # Récupérer l'utilisateur actuel
        user = mongo.db.users.find_one({'username': username})
        
        # Initialiser les préférences si elles n'existent pas
        if 'preferences' not in user:
            user['preferences'] = {}
        
        # Mettre à jour les préférences
        if 'preferences' in update_data:
            user['preferences'].update(update_data['preferences'])
            update_data['preferences'] = user['preferences']
        
        # Mettre à jour les autres champs
        mongo.db.users.update_one(
            {'username': username},
            {'$set': update_data}
        )

    @staticmethod
    def add_activity(username, activity_type, details):
        """Ajoute une activité à l'historique de l'utilisateur"""
        activity = {
            'type': activity_type,
            'details': details,
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        mongo.db.users.update_one(
            {'username': username},
            {'$push': {'activities': activity}}
        )

    @staticmethod
    def get_activities(username, limit=10):
        """Récupère l'historique des activités de l'utilisateur"""
        user = mongo.db.users.find_one(
            {'username': username},
            {'activities': {'$slice': -limit}}
        )
        return user.get('activities', []) if user else []

    @staticmethod
    def add_favorite(username, question_data):
        """Ajoute une question aux favoris"""
        favorite = {
            'question': question_data,
            'added_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        mongo.db.users.update_one(
            {'username': username},
            {'$push': {'favorites': favorite}}
        )

    @staticmethod
    def remove_favorite(username, question_id):
        """Supprime une question des favoris"""
        mongo.db.users.update_one(
            {'username': username},
            {'$pull': {'favorites': {'question.id': question_id}}}
        )

    @staticmethod
    def get_favorites(username):
        """Récupère les questions favorites de l'utilisateur"""
        user = mongo.db.users.find_one({'username': username})
        return user.get('favorites', []) if user else []

    @staticmethod
    def add_notification(username, message, type='info'):
        """Ajoute une notification pour l'utilisateur"""
        notification = {
            'message': message,
            'type': type,
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'read': False
        }
        
        mongo.db.users.update_one(
            {'username': username},
            {'$push': {'notifications': notification}}
        )

    @staticmethod
    def get_notifications(username, unread_only=False):
        """Récupère les notifications de l'utilisateur"""
        query = {'username': username}
        if unread_only:
            query['notifications.read'] = False
            
        user = mongo.db.users.find_one(query)
        return user.get('notifications', []) if user else []

    @staticmethod
    def mark_notification_read(username, notification_id):
        """Marque une notification comme lue"""
        mongo.db.users.update_one(
            {
                'username': username,
                'notifications._id': notification_id
            },
            {'$set': {'notifications.$.read': True}}
        )

    @staticmethod
    def get_questions_count_today(username):
        today = datetime.utcnow().date()
        return mongo.db.questions.count_documents({
            'created_by': username,
            'created_at': {'$gte': today.strftime('%Y-%m-%d')}
        })

    @staticmethod
    def get_questions_count_week(username):
        week_ago = datetime.utcnow() - timedelta(days=7)
        return mongo.db.questions.count_documents({
            'created_by': username,
            'created_at': {'$gte': week_ago.strftime('%Y-%m-%d')}
        })

    @staticmethod
    def get_questions_count_month(username):
        month_ago = datetime.utcnow() - timedelta(days=30)
        return mongo.db.questions.count_documents({
            'created_by': username,
            'created_at': {'$gte': month_ago.strftime('%Y-%m-%d')}
        })

    @staticmethod
    def get_achievements(username):
        return mongo.db.users.find_one(
            {'username': username},
            {'achievements': 1}
        ).get('achievements', [])

    @staticmethod
    def export_user_data(username):
        user = mongo.db.users.find_one({'username': username})
        if user:
            # Supprimer les informations sensibles
            del user['password']
            return user
        return None

    @staticmethod
    def update_activity(username, activity_type):
        """Met à jour l'activité de l'utilisateur"""
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # Utiliser $set au lieu de $inc pour la date
        mongo.db.users.update_one(
            {'username': username},
            {
                '$set': {
                    'last_activity': current_time,
                    'last_activity_type': activity_type
                },
                '$inc': {
                    f'activity_count.{activity_type}': 1  # Incrémenter le compteur d'activité
                }
            }
        )

    @staticmethod
    def repair_counters(username):
        """Répare les compteurs d'un utilisateur en les recalculant depuis l'historique"""
        try:
            # Calculer le total des questions depuis l'historique
            questions_count = mongo.db.questions_history.count_documents({'username': username})
            
            # Calculer le total des examens depuis l'historique
            exams_count = mongo.db.exams_history.count_documents({'username': username})
            
            # Mettre à jour les compteurs
            mongo.db.users.update_one(
                {'username': username},
                {
                    '$set': {
                        'questions_generated': questions_count,
                        'exams_generated': exams_count
                    }
                }
            )
            
            return True
        except Exception as e:
            print(f"Error repairing counters for user {username}: {str(e)}")
            return False

    @staticmethod
    def update_user_status(username, new_status):
        """Met à jour spécifiquement le statut d'un utilisateur"""
        try:
            result = mongo.db.users.update_one(
                {'username': username},
                {
                    '$set': {
                        'status': new_status,
                        'last_modified': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                    }
                }
            )
            
            if result.modified_count == 0:
                print(f"No document was updated for username: {username}")
                return False
            
            return True
        except Exception as e:
            print(f"Error updating user status: {str(e)}")
            return False

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password, method='pbkdf2:sha256')
    
    @staticmethod
    def verify_password(user, password):
        return check_password_hash(user['password'], password)