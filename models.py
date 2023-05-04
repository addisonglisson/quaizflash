from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(250), nullable=False)
    flashcards = db.relationship('Flashcard', backref='user', lazy=True)
    flashcard_sets = db.relationship('FlashcardSet', backref='author', lazy=True)
    



    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flashcard_set_id = db.Column(db.Integer, db.ForeignKey('flashcard_set.id', name='fk_flashcard_set_id'), nullable=True)  # Added ForeignKey with name

    def __repr__(self):
        return f"Flashcard('{self.question}', '{self.answer}')"


class FlashcardSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flashcards = db.relationship('Flashcard', backref='flashcard_set', lazy=True)  # Added relationship
    correct_count = db.Column(db.Integer, default=0)  # Add this line
    incorrect_count = db.Column(db.Integer, default=0)  # Add this line
    flashcards = db.relationship('Flashcard', backref='flashcard_set', lazy=True)
    public = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"FlashcardSet('{self.title}', '{self.description}')"

class Deck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cards = db.relationship('Card', backref='deck', lazy=True)

    def __repr__(self):
        return f"<Deck {self.name}>"


class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    front = db.Column(db.String(200), nullable=False)
    back = db.Column(db.String(200), nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey('deck.id'), nullable=False)

    def __repr__(self):
        return f"<Card {self.front}>"
    
class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)  # Nullable since a session can be ongoing
    flashcard_set_id = db.Column(db.Integer, db.ForeignKey('flashcard_set.id'), nullable=False)
    flashcard_set = db.relationship('FlashcardSet', backref='study_sessions', lazy=True)
    def __repr__(self):
        return f"<StudySession {self.id}>"
class FlashcardInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    study_session_id = db.Column(db.Integer, db.ForeignKey('study_session.id'), nullable=False)
    flashcard_id = db.Column(db.Integer, db.ForeignKey('flashcard.id'), nullable=False)
    correct = db.Column(db.Boolean, nullable=False)
    time_spent = db.Column(db.Integer, nullable=False)  # Time spent on the flashcard in seconds
    
    def __repr__(self):
        return f"<FlashcardInteraction {self.id}>"
