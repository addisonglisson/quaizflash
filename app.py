import os
import openai
import requests
import xmltodict
import re
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from models import db, User, Flashcard
from models import User, Flashcard, FlashcardSet
from forms import FlashcardSetForm
from functools import wraps
from youtube_transcript_api import YouTubeTranscriptApi
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask import abort


app = Flask(__name__)
app.config["SECRET_KEY"] = "5a4379b0d0a662d6d1f14b3f6b1e6d92"
openai.api_key = os.environ.get('OPENAI_API_KEY')  # Replace 'OPENAI_API_KEY' with your actual API key variable name
# Initialize the LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
# User loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database_file.db'  # Replace with your desired database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Create tables
@app.before_first_request
def create_tables():
   db.create_all()

def fetch_url_content(url):
   try:
       response = requests.get(url)
       response.raise_for_status()
       soup = BeautifulSoup(response.text, "html.parser")

       paragraphs = soup.find_all("p")
       content = " ".join([p.get_text() for p in paragraphs])
       return content
   except Exception as e:
       print(f"Error fetching content from URL: {e}")
       return ""
   
def extract_video_id(url):
    video_id_regex = r"(?<=v=)[^&#]+"
    match = re.search(video_id_regex, url)
    if match:
        return match.group()
    return None

def fetch_youtube_captions(video_url):
    video_id = extract_video_id(video_url)  # Change this line
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
    captions = [entry['text'] for entry in transcript]
    return captions

@app.route("/", methods=["GET"])
@login_required
def index():
    return render_template("index.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        # Check if the user with the same username already exists
        user = User.query.filter_by(username=username).first()
        if user:
            flash("Username already exists. Please choose a different one.")
            return redirect(url_for("register"))

        # Check if the user with the same email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash("Email already exists. Please use a different email address.")
            return redirect(url_for("register"))

        # Create a new user and add to the database
        new_user = User(username=username, email=email, password_hash=generate_password_hash(password, method="sha256"))
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
   if request.method == "POST":
       email = request.form.get("email")
       password = request.form.get("password")

       user = User.query.filter_by(email=email).first()
       if user and check_password_hash(user.password_hash, password):
           login_user(user)  # Use Flask-Login's login_user() function
           flash("Logged in successfully!")
           return redirect(url_for("index"))
       else:
           flash("Invalid email or password. Please try again")

   return render_template("login.html")



@app.route("/logout")
def logout():
    logout_user()  # Use Flask-Login's logout_user() function
    flash("Logged out successfully!")
    return redirect(url_for("login"))


@app.route('/profile')
@login_required
def profile():
    flashcards = Flashcard.query.filter_by(user_id=current_user.id).all()
    flashcard_sets = FlashcardSet.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', title='Profile', flashcards=flashcards,flashcard_sets=flashcard_sets)

@app.route("/ask", methods=["POST"])
@login_required
def ask():
    data = request.json
    url = request.json.get("url")
    question = data["question"]
    article_text = data.get("article_text", "")
    captions_text = request.json.get("captions_text")

    if url:
        video_id = extract_video_id(url)
        if video_id:
            captions = fetch_youtube_captions(url)
            if captions:
                article = "\n".join(captions)

            else:
                article = ""
        else:
            article = fetch_url_content(url)
    elif article_text:
        article = article_text
    elif captions_text:
        article = captions_text
    else:
        article = ""

    if not article:
        prompt = f"Question: {question}\nAnswer:"
    else:
        prompt = f"{article}\n\nQuestion: {question}\nAnswer:"
    print(f"Prompt: {prompt}")

    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.5,
    )
   
    answer = response.choices[0].text.strip()
    flashcard = Flashcard(question=question, answer=answer, user_id=current_user.id)
    db.session.add(flashcard)
    db.session.commit()

    return jsonify({"answer": answer})
@app.route("/captions", methods=["POST"])
@login_required
def captions():
    data = request.json
    video_url = data.get("video_url")

    if not video_url:
        return jsonify({"error": "No video URL provided"}), 400
    print(f"Received video URL: {video_url}")
    video_id = extract_video_id(video_url)


    print(f"Extracted video ID: {video_id}")

    if not video_id:
        return jsonify({"error": "Invalid video URL"}), 400

    try:
        # Fetch captions
        captions = fetch_youtube_captions(video_url)
        print(f"Fetched captions: {captions}")
       

        if not captions:
            return jsonify({"error": "No captions found for the video"}), 404

        return jsonify(captions)
    except Exception as e:
        return jsonify({"error": str(e)})
@app.route("/create_flashcard", methods=["POST"])
@login_required
def create_flashcard():
    question = request.form.get("question")
    answer = request.form.get("answer")
    user_id = current_user.id

    flashcard = Flashcard(question=question, answer=answer, user_id=current_user.id)
    db.session.add(flashcard)
    db.session.commit()

    flash('Flashcard created successfully!')
    return redirect(url_for('index'))

@app.route('/edit_flashcard/<int:flashcard_id>', methods=['GET', 'POST'])
@login_required
def edit_flashcard(flashcard_id):
    flashcard = Flashcard.query.get_or_404(flashcard_id)
    if flashcard.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        flashcard.question = request.form['question']
        flashcard.answer = request.form['answer']
        db.session.commit()
        flash('Flashcard updated!', 'success')
        return redirect(url_for('profile'))

    return render_template('edit_flashcard.html', title='Edit Flashcard', flashcard=flashcard)

@app.route('/delete_flashcard/<int:flashcard_id>', methods=['POST'])
@login_required
def delete_flashcard(flashcard_id):
    flashcard = Flashcard.query.get_or_404(flashcard_id)
    if flashcard.user_id != current_user.id:
        abort(403)

    db.session.delete(flashcard)
    db.session.commit()
    flash('Flashcard deleted!', 'success')
    return redirect(url_for('profile'))

@app.route("/create_flashcard_set/new", methods=["GET", "POST"])
@login_required
def create_flashcard_set():
    form = FlashcardSetForm()
    if form.validate_on_submit():
        flashcard_set = FlashcardSet(title=form.title.data, description=form.description.data, user_id=current_user.id)
        db.session.add(flashcard_set)
        db.session.commit()
        flash("Your flashcard set has been created!", "success")
        return redirect(url_for("index"))
    return render_template("create_flashcard_set.html", title="New Flashcard Set", form=form, legend="New Flashcard Set")

@app.route("/my_flashcards", methods=["GET"])
@login_required
def my_flashcards():
    user_id = session["user_id"]
    flashcards = Flashcard.query.filter_by(user_id=user_id).all()

    return render_template("my_flashcards.html", flashcards=flashcards)

if __name__ == "__main__":
    app.run(debug=True)