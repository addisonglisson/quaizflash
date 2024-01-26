import os
import openai
import requests
import xmltodict
import re
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from models import db, User, Flashcard
from models import User, Flashcard, FlashcardSet, FlashcardInteraction, StudySession, BlogPost, Comment, study_pod_members, StudyPodComment, StudyPod, StudyPodPost
from forms import FlashcardSetForm, FlashcardForm, AddToSetForm, VirtualTutorForm, SearchSetsForm, BlogPostForm, CommentForm, CreateStudyPodCommentForm, CreateStudyPodForm, CreateStudyPodPostForm, FlashcardGeneratorForm
from functools import wraps
from youtube_transcript_api import YouTubeTranscriptApi
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask import abort
from datetime import datetime
from random import shuffle
from sqlalchemy.sql.expression import func
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
from lxml.etree import Element, SubElement, tostring
from urllib.parse import urljoin
from flaskext.markdown import Markdown

app = Flask(__name__)

Markdown(app)

app.config["MAIL_SERVER"] = "smtp.office365.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = "info@quaizflash.com"
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SECURITY_PASSWORD_SALT"] = os.environ.get("SECURITY_PASSWORD_SALT")
##app.config["SERVER_NAME"] = "quaizflash.herokuapp.com"

mail=Mail(app)
def generate_token(email):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    return serializer.dumps(email, salt=app.config["SECURITY_PASSWORD_SALT"])

def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    try:
        email = serializer.loads(token, salt=app.config["SECURITY_PASSWORD_SALT"], max_age=expiration)
    except:
        return False
    return email

def save_flashcards_to_set(flashcard_data, set_id):
    for flashcard_info in flashcard_data:
        flashcard = Flashcard(question=flashcard_info['question'], answer=flashcard_info['answer'], user_id=current_user.id, flashcard_set_id=set_id)
        db.session.add(flashcard)
    db.session.commit()

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        user = User.query.filter_by(email=email).first()
        if user:
            token = generate_token(user.email)
            reset_url = url_for("reset_password", token=token, _external=True)
            send_email(user.email, "Password Reset Request", "email/reset_password", reset_url=reset_url)
            flash("An email has been sent with instructions to reset your password.", "success")
            return redirect(url_for("login"))
        else:
            flash("Invalid email address.", "danger")
    return render_template("forgot_password.html",search_form=SearchSetsForm())

def send_email(to, subject, template, **kwargs):
    msg = Message(subject, recipients=[to], sender=app.config["MAIL_DEFAULT_SENDER"])
    msg.body = render_template(f"{template}.txt", **kwargs)
    msg.html = render_template(f"{template}.html", **kwargs)
    mail.send(msg)


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    email = confirm_token(token)
    if not email:
        flash("The password reset link is invalid or has expired.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        user.set_password(password)
        db.session.commit()
        flash("Your password has been updated.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token, search_form=SearchSetsForm())

openai.api_key = os.environ.get('OPENAI_API_KEY')  # Replace 'OPENAI_API_KEY' with your actual API key variable name
def get_chatgpt_response(user_message, context=None):
    prompt = f"{context}\nUser: {user_message}\nChatGPT:"
    response = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.5,
    )
    message = response.choices[0].text.strip()
    return message

# Initialize the LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
# User loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///your_database_file.db') # Replace with your desired database URI
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
#app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL','sqlite:///your_database_file.db' ) # Replace with your desired database URI
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
    is_logged_in = 'user_id' in session
    print("Session data:", session)
    if current_user.is_authenticated:
        return render_template("index.html", search_form=SearchSetsForm())
  


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

    return render_template("register.html", search_form=SearchSetsForm())

@app.route("/login", methods=["GET", "POST"])
def login():
   if request.method == "POST":
       email = request.form.get("email")
       password = request.form.get("password")

       user = User.query.filter_by(email=email).first()
       if user and check_password_hash(user.password_hash, password):
           login_user(user)  # Use Flask-Login's login_user() function
           session["logged_in"] = True
           flash("Logged in successfully!")
           return redirect(url_for("index"))
       else:
           flash("Invalid email or password. Please try again")

   return render_template("login.html", search_form=SearchSetsForm())



@app.route("/logout")
def logout():
    logout_user()  # Use Flask-Login's logout_user() function
    session.pop("logged_in", None)
    flash("Logged out successfully!")
    return redirect(url_for("login"))


@app.route('/profile')
@login_required
def profile():
    flashcards = Flashcard.query.filter_by(user_id=current_user.id).all()
    flashcard_sets = FlashcardSet.query.filter_by(user_id=current_user.id).all()
    study_pods = current_user.study_pods  
    total_flashcards = len(flashcards)
    total_sets = len(flashcard_sets)
    total_pods = len(study_pods)
    
    # Fetch recent activities (implement according to your app's logic)


    return render_template('profile.html', title='Profile', 
                           flashcards=flashcards,
                           flashcard_sets=flashcard_sets, 
                           study_pods=study_pods,
                           total_flashcards=total_flashcards,
                           total_sets=total_sets,
                           total_pods=total_pods,
                           search_form=SearchSetsForm())
 
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
        engine="gpt-3.5-turbo-instruct",
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

    return render_template('edit_flashcard.html', title='Edit Flashcard', flashcard=flashcard, search_form=SearchSetsForm())

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
    return render_template("create_flashcard_set.html", title="New Flashcard Set", form=form, legend="New Flashcard Set", search_form=SearchSetsForm())
@app.route("/flashcard_set/<int:set_id>")
@login_required
def flashcard_set(set_id):
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    if flashcard_set.user_id != current_user.id:
        abort(403)

    flashcards = Flashcard.query.filter_by(flashcard_set_id=set_id).all()
    return render_template("flashcard_set.html", title=flashcard_set.title, flashcards=flashcards, flashcard_set=flashcard_set, search_form=SearchSetsForm())

@app.route("/flashcard_set/<int:set_id>/add_to_set", methods=["GET", "POST"])
@login_required
def add_to_set(set_id):
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    if flashcard_set.user_id != current_user.id:
        abort(403)

    form = AddToSetForm()
    
    form.flashcard.choices = [(flashcard.id, flashcard.question) for flashcard in Flashcard.query.filter(
        (Flashcard.flashcard_set_id == None) | (Flashcard.flashcard_set_id == set_id),
        Flashcard.user_id == current_user.id
    ).all()]


    if form.validate_on_submit():
        flashcard = Flashcard.query.get(form.flashcard_id.data)
        print(set_id)
        flashcard.flashcard_set_id = set_id
        db.session.commit()

        flash("Flashcard added to set!", "success")
        return redirect(url_for("flashcard_set", set_id=set_id))

    return render_template("add_to_set.html", title="Add Flashcard to Set", form=form, flashcard_set=flashcard_set, search_form=SearchSetsForm())
@app.route('/flashcard/<int:flashcard_id>/select_set', methods=['GET', 'POST'])
@login_required
def select_set(flashcard_id):
    flashcard = Flashcard.query.get_or_404(flashcard_id)
    sets = FlashcardSet.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        set_id = request.form['set_id']
        flashcard.flashcard_set_id = set_id
        db.session.commit()
        return redirect(url_for('profile'))

    return render_template('select_set.html', title='Select Set', flashcard=flashcard, sets=sets, search_form=SearchSetsForm())


@app.route("/new_flashcard", methods=["GET", "POST"])
@app.route("/flashcard_set/<int:set_id>/new_flashcard", methods=["GET", "POST"])
@login_required
def new_flashcard(set_id=None):
    if set_id:
        flashcard_set = FlashcardSet.query.get_or_404(set_id)
        if flashcard_set.user_id != current_user.id:
            abort(403)

    form = FlashcardForm()
    if form.validate_on_submit():
        if set_id:
            flashcard = Flashcard(question=form.question.data, answer=form.answer.data, user_id=current_user.id, flashcard_set_id=set_id)
        else:
            flashcard = Flashcard(question=form.question.data, answer=form.answer.data, user_id=current_user.id)
        db.session.add(flashcard)
        db.session.commit()
        flash("Your flashcard has been added!", "success")
        return redirect(url_for("profile"))
    return render_template("new_flashcard.html", title="New Flashcard", form=form, legend="New Flashcard", search_form=SearchSetsForm())

@app.route('/quiz/<int:set_id>/<quiz_mode>')
def quiz(set_id, quiz_mode):
    # You'll need to fetch the flashcard set and its cards from the database here
    flashcard_set = FlashcardSet.query.get(set_id)
    flashcards = Flashcard.query.filter_by(flashcard_set_id=set_id).all()

    if quiz_mode == "multiple_choice":
        return redirect(url_for('quiz_set_multiple_choice', set_id=set_id))  # Redirect to the multiple choice quiz route
    elif quiz_mode == "matching":
        return redirect(url_for('quiz_set_matching', set_id=set_id))  # Redirect to the matching quiz route



    return render_template('quiz.html', title='Quiz', flashcard_set=flashcard_set, flashcards=flashcards, quiz_mode=quiz_mode, search_form=SearchSetsForm())

@app.route('/quiz-settings/<int:set_id>', methods=['GET', 'POST'])
def quiz_settings(set_id):
    if request.method == 'POST':
        quiz_mode = request.form.get('quiz_mode')
        return redirect(url_for('quiz', set_id=set_id, quiz_mode=quiz_mode))

    flashcard_set = FlashcardSet.query.get(set_id)
    return render_template('quiz_settings.html', title='Quiz Settings', flashcard_set=flashcard_set, search_form=SearchSetsForm())
@app.route('/submit_interaction', methods=['POST'])
def submit_interaction():
    data = request.get_json()  # Add this line to get JSON data from the request
    user_id = current_user.id
    set_id = data.get('set_id')
    flashcard_id = data.get('flashcard_id')
    correct = data.get('correct')
    time_spent = int(data.get('time_spent'))
    quiz_finished = data.get('quiz_finished', False)

    study_session = StudySession.query.filter_by(user_id=user_id, flashcard_set_id=set_id, end_time=None).first()

    if not study_session:
        study_session = StudySession(user_id=user_id, start_time=datetime.utcnow(), flashcard_set_id=set_id)
        db.session.add(study_session)
        db.session.commit()


    # Create a new FlashcardInteraction instance and save it to the database
    interaction = FlashcardInteraction(study_session_id=study_session.id, flashcard_id=flashcard_id, correct=correct, time_spent=time_spent)
    db.session.add(interaction)

    if quiz_finished:
        study_session.end_time = datetime.utcnow()

    db.session.commit()

    return {'status': 'success'}

@app.route('/api/update-flashcard', methods=['POST'])
def update_flashcard():
    data = request.json
    flashcard_id = data['flashcard_id']
    correct = data['correct']

    flashcard = Flashcard.query.get(flashcard_id)

    if correct:
        flashcard.correct_count += 1
    else:
        flashcard.incorrect_count += 1

    db.session.commit()

    return jsonify({'message': 'Flashcard updated successfully'})

@app.route('/progress')
@login_required
def progress():
    user_id = current_user.id
    study_sessions = StudySession.query.filter_by(user_id=user_id).all()
    
    # Create a dictionary to store insights for each flashcard set
    progress_data = {}
    for session in study_sessions:
        if session.flashcard_set_id not in progress_data:
            progress_data[session.flashcard_set_id] = {
                'set_title': session.flashcard_set.title,
                'total_sessions': 0,
                'total_time_spent': 0,
                'total_correct': 0,
                'total_incorrect': 0
            }
        progress_data[session.flashcard_set_id]['total_sessions'] += 1

        interactions = FlashcardInteraction.query.filter_by(study_session_id=session.id).all()
        for interaction in interactions:
            progress_data[session.flashcard_set_id]['total_time_spent'] += interaction.time_spent
            if interaction.correct:
                progress_data[session.flashcard_set_id]['total_correct'] += 1
            else:
                progress_data[session.flashcard_set_id]['total_incorrect'] += 1

    return render_template('progress.html', title='Progress', progress_data=progress_data, search_form=SearchSetsForm())

@app.route('/virtual_tutor', methods=['GET', 'POST'])
@login_required
def virtual_tutor():
    form = VirtualTutorForm()
    conversation_history = session.get('conversation_history', [])

    if form.validate_on_submit():
        subject = form.subject.data
        user_input = form.user_input.data
        conversation_history.append({'role': 'user', 'content': user_input})

        history_text = "\n".join([entry['content'] for entry in conversation_history[-10:]])
        prompt = f"ChatGPT, you are an expert {subject} tutor. Please provide accurate, helpful, and easy-to-understand answers to any questions related to {subject}. When possible, include step-by-step explanations or examples to help the user better understand your answers.\n\n{history_text}\n{user_input}"
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.6,
        )

        gpt_response = response.choices[0].text.strip()
        conversation_history.append({'role': 'tutor', 'content': gpt_response})
        session['conversation_history'] = conversation_history

    conversation_history = conversation_history[::-1]
    return render_template('virtual_tutor.html', title='Virtual Tutor', form=form, conversation_history=conversation_history, search_form=SearchSetsForm())
@app.route('/search_sets', methods=['GET', 'POST'])
def search_sets():
    form = SearchSetsForm()
    flashcard_results = []
    studypod_results = []

    if form.validate_on_submit():
        search_query = form.search_query.data

        # Search for public flashcard sets
        flashcard_results = FlashcardSet.query.filter(
            FlashcardSet.public == True,
            FlashcardSet.title.ilike(f"%{search_query}%")
        ).all()

        # Search for StudyPods
        studypod_results = StudyPod.query.filter(
            StudyPod.name.ilike(f"%{search_query}%")
        ).all()
#    search_results = []

 #   if form.validate_on_submit():
 #       search_query = form.search_query.data

        # Perform a search for public flashcard sets containing the search query
#        search_results = FlashcardSet.query.filter(FlashcardSet.public == True, FlashcardSet.title.ilike(f"%{search_query}%")).all()

        for result in flashcard_results:
            first_flashcard = Flashcard.query.filter_by(flashcard_set_id=result.id).first()
            result.first_flashcard_id = first_flashcard.id if first_flashcard else None

    return render_template('search_sets.html', title='Search Public Sets', form=form, flashcard_results=flashcard_results,studypod_results=studypod_results, search_form=SearchSetsForm())

@app.route('/quiz_searched_set/<int:set_id>/<quiz_mode>')
@login_required
def quiz_searched_set(set_id, quiz_mode):
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    flashcards = Flashcard.query.filter_by(flashcard_set_id=set_id).all()

    return render_template('quiz.html', title='Quiz Searched Set', flashcard_set=flashcard_set, flashcards=flashcards, quiz_mode=quiz_mode, search_form=SearchSetsForm())

@app.route('/view_searched_set/<int:set_id>')
def view_searched_set(set_id):
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    flashcards = Flashcard.query.filter_by(flashcard_set_id=set_id).all()
    return render_template('view_searched_set.html', title='View Searched Set', flashcard_set=flashcard_set, flashcards=flashcards, search_form=SearchSetsForm())

@app.route("/my_flashcards", methods=["GET"])
@login_required
def my_flashcards():
    user_id = session["user_id"]
    flashcards = Flashcard.query.filter_by(user_id=user_id).all()
    sets = FlashcardSet.query.filter_by(user_id=user_id).all()

    return render_template("my_flashcards.html", flashcards=flashcards,sets=sets)

@app.route('/quiz-set-multiple-choice/<int:set_id>')
def quiz_set_multiple_choice(set_id):
    flashcard_set = FlashcardSet.query.get(set_id)
    flashcards = Flashcard.query.filter_by(flashcard_set_id=set_id).all()

    mc_flashcards = []

    for flashcard in flashcards:
        mc_options = [flashcard.answer]
        wrong_options = Flashcard.query.filter(
            Flashcard.flashcard_set_id == set_id, 
            Flashcard.id != flashcard.id
        ).order_by(func.random()).limit(3).all()


        mc_options.extend([wrong_option.answer for wrong_option in wrong_options])
        shuffle(mc_options)

        mc_flashcards.append({
            'question': flashcard.question,
            'answer': flashcard.answer,
            'options': mc_options
        })

    return render_template('quiz_set_multiple_choice.html', title='Multiple Choice Quiz', flashcard_set=flashcard_set, mc_flashcards=mc_flashcards, search_form=SearchSetsForm())
@app.route("/home", methods=["GET"])
def home():
    return render_template("home.html", search_form=SearchSetsForm())
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)

@app.route('/sitemap.xml')
def sitemap():
    # Define the base url and create the root sitemap element
    base_url = 'https://www.quaizflash.com'
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    # List of static routes you want to add
    static_routes = ['login', 'home', 'register', 'blog']  

    # Add static routes to sitemap
    for route in static_routes:
        url = SubElement(root, "url")
        SubElement(url, "loc").text = urljoin(base_url, url_for(route))
        SubElement(url, "changefreq").text = "monthly"
        SubElement(url, "priority").text = "1.0"

    # Add public flashcard sets to sitemap
    public_sets = FlashcardSet.query.filter_by(public=True).all()
    for set in public_sets:
        url = SubElement(root, "url")
        SubElement(url, "loc").text = urljoin(base_url, url_for('view_searched_set', set_id=set.id))
        SubElement(url, "changefreq").text = "weekly"
        SubElement(url, "priority").text = "0.5"
    # Add blog posts to sitemap
    # Add blog posts to sitemap
    blog_posts = BlogPost.query.all()
    for post in blog_posts:
        url = SubElement(root, "url")
        SubElement(url, "loc").text = urljoin(base_url, url_for('post', post_id=post.id))
        SubElement(url, "changefreq").text = "weekly"
        SubElement(url, "priority").text = "0.5"
    return Response(tostring(root, pretty_print=True), content_type='application/xml')
@app.route('/quiz-set-matching/<int:set_id>')
def quiz_set_matching(set_id):
    flashcard_set = FlashcardSet.query.get(set_id)
    flashcards = Flashcard.query.filter_by(flashcard_set_id=set_id).all()
    cards = []
    for flashcard in flashcards:
        cards.append({
            'type': 'question',
            'content': flashcard.question,
            'pair_id': flashcard.id
        })
        cards.append({
            'type': 'answer',
            'content': flashcard.answer,
            'pair_id': flashcard.id
        })

    shuffle(cards)

    return render_template('quiz_matching.html', title='Matching Quiz', flashcard_set=flashcard_set, cards=cards, search_form=SearchSetsForm())
@app.route('/public_sets', methods=['GET'])
def public_sets():
    page = request.args.get('page', 1, type=int)
    flashcard_sets = FlashcardSet.query.filter_by(public=True).paginate(page=page, per_page=10)
    return render_template('public_sets.html', title='Public Flashcard Sets', flashcard_sets=flashcard_sets, search_form=SearchSetsForm())

@app.route('/blog')
def blog():
    posts = BlogPost.query.order_by(BlogPost.date_posted.desc()).all()
    return render_template('blog.html', posts=posts, search_form=SearchSetsForm())

@app.route('/post/<int:post_id>')
def post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.date_posted.desc()).all()
    comment_form = CommentForm()
    return render_template('post.html', post=post, comments=comments, comment_form=comment_form, search_form=SearchSetsForm())

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = BlogPostForm()
    if form.validate_on_submit():
        post = BlogPost(title=form.title.data, content=form.content.data, user_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('blog'))
    return render_template('create_post.html', form=form, search_form=SearchSetsForm())
@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def post_comment(post_id):
    post = BlogPost.query.get_or_404(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, user_id=current_user.id, post_id=post.id)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been posted!', 'success')
    return redirect(url_for('post', post_id=post_id))

@app.route('/create_pod', methods=['GET', 'POST'])
@login_required
def create_pod():
    form = CreateStudyPodForm()
    if form.validate_on_submit():
        new_pod = StudyPod(name=form.name.data, description=form.description.data)
        new_pod.members.append(current_user)
        db.session.add(new_pod)
        db.session.commit()
        flash('Study Pod created successfully!', 'success')
        return redirect(url_for('view_pod', pod_id=new_pod.id))
    return render_template('create_pod.html', form=form,search_form=SearchSetsForm())

@app.route('/pod/<int:pod_id>')
def view_pod(pod_id):
    pod = StudyPod.query.get_or_404(pod_id)
    return render_template('view_pod.html', pod=pod,search_form=SearchSetsForm())

@app.route('/pod/<int:pod_id>/post', methods=['GET', 'POST'])
@login_required
def create_pod_post(pod_id):
    form = CreateStudyPodPostForm()
    pod = StudyPod.query.get_or_404(pod_id)
    if form.validate_on_submit():
        post = StudyPodPost(title=form.title.data, content=form.content.data, study_pod=pod, user_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash('Post added successfully!', 'success')
        return redirect(url_for('view_pod', pod_id=pod_id))
    else:
        print(form.errors)  
    return render_template('create_pod_post.html', form=form, pod=pod, search_form=SearchSetsForm())

@app.route('/pod_post/<int:post_id>/comment', methods=['GET', 'POST'])
@login_required
def create_pod_comment(post_id):
    form = CreateStudyPodCommentForm()
    post = StudyPodPost.query.get_or_404(post_id)
    post_user = User.query.get_or_404(post.user_id)
    if form.validate_on_submit():
        comment = StudyPodComment(content=form.content.data, user_id=current_user.id, study_pod_post_id=post.id)
        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
        return redirect(url_for('view_pod', pod_id=post.study_pod_id))

    return render_template('create_pod_comment.html', form=form, post=post , post_user=post_user,search_form=SearchSetsForm())   

@app.route('/join_pod/<int:pod_id>', methods=['POST'])
@login_required
def join_pod(pod_id):
    pod = StudyPod.query.get_or_404(pod_id)
    if current_user not in pod.members:
        pod.members.append(current_user)
        db.session.commit()
        flash('You have joined the pod!', 'success')
    else:
        flash('You are already a member of this pod.', 'info')
    return redirect(url_for('view_pod', pod_id=pod_id))

@app.route("/leave_pod/<int:pod_id>", methods=["POST"])
@login_required
def leave_pod(pod_id):
    pod = StudyPod.query.get_or_404(pod_id)
    if current_user in pod.members:
        pod.members.remove(current_user)
        db.session.commit()
        flash('You have left the pod.', 'success')
    else:
        flash('You are not a member of this pod.', 'warning')
    return redirect(url_for('profile'))

@app.route('/generate_multiple_flashcards', methods=['GET', 'POST'])
@login_required
def generate_flashcards():
    form = FlashcardGeneratorForm()
    set_form = FlashcardSetForm()
    # Retrieve generated flashcards from the session (for displaying after generation)
    generated_flashcards = session.get('generated_flashcards', [])

    if form.validate_on_submit():
        topic = form.topic.data
        user_prompt = form.user_prompt.data

        # Adjust the prompt for multiple flashcards
        prompt = f"Create a list of flashcards about {topic}. Start each flashcard with 'Q:' for question and 'A:' for answer. Each flashcard should be concise.\n\n{user_prompt}"

        # Call OpenAI's API with the modified prompt
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=700,
            n=1,
            stop=None,
            temperature=0.5,
        )

        # Parse the response to create flashcards
        flashcard_pairs = parse_flashcards(response.choices[0].text.strip())
        # Store the parsed flashcards in the session
        session['generated_flashcards'] = [{"question": q, "answer": a} for q, a in flashcard_pairs]

        flash('Flashcards generated successfully! Review and save them.', 'success')
        # Redirect to the same route to display generated flashcards
        return redirect(url_for('generate_flashcards'))

    if request.method == 'POST':
        # Check if the 'Create Set' button was clicked
        if 'create_set' in request.form:
            if set_form.validate():
                new_set = FlashcardSet(title=set_form.title.data, description=set_form.description.data, user_id=current_user.id)
                db.session.add(new_set)
                db.session.commit()
                flash("New flashcard set created!", "success")
                # Assign generated flashcards to the new set
                save_flashcards_to_set(session.get('generated_flashcards', []), new_set.id)
                session.pop('generated_flashcards', None)  # Clear session
                return redirect(url_for("flashcard_set", set_id=new_set.id))
    

    return render_template('generate_flashcards.html', title='Generate Multiple Flashcards', form=form, set_form=set_form, flashcards=generated_flashcards, search_form=SearchSetsForm())

def parse_flashcards(response_text):
    flashcard_pairs = []
    for line in response_text.split('\n'):
        if line.startswith("Q:"):
            question = line[2:].strip()
        elif line.startswith("A:"):
            answer = line[2:].strip()
            flashcard_pairs.append((question, answer))
    return flashcard_pairs


@app.route('/save_generated_flashcards', methods=['POST'])
@login_required
def save_generated_flashcards():
    generated_flashcards = session.pop('generated_flashcards', [])
    if generated_flashcards:
        for flashcard in generated_flashcards:
            new_flashcard = Flashcard(question=flashcard['question'], answer=flashcard['answer'], user_id=current_user.id)
            db.session.add(new_flashcard)
        db.session.commit()
        flash('Flashcards saved to your profile!', 'success')
    else:
        flash('No flashcards to save.', 'info')

    return redirect(url_for('profile'))

@app.route('/edit_generated_flashcards', methods=['GET', 'POST'])
@login_required
def edit_generated_flashcards():
    generated_flashcards = session.get('generated_flashcards', [])

    if request.method == 'POST':
        # Process the edited flashcards
        edited_flashcards = []
        for i in range(len(generated_flashcards)):
            question = request.form.get(f'question-{i}')
            answer = request.form.get(f'answer-{i}')
            edited_flashcards.append({'question': question, 'answer': answer})
        
        # Update the session with edited flashcards
        session['generated_flashcards'] = edited_flashcards
        flash('Flashcards updated!', 'success')

        # Redirect back to the generate flashcards page to review edited flashcards
        return redirect(url_for('generate_flashcards'))

    return render_template('edit_generated_flashcards.html', flashcards=generated_flashcards, search_form=SearchSetsForm())
