from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from wtforms.fields import SelectField

class FlashcardSetForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Create Flashcard Set')
class FlashcardForm(FlaskForm):
    question = StringField('Question', validators=[DataRequired()])
    answer = StringField('Answer', validators=[DataRequired()])
    submit = SubmitField('Add Flashcard')

class AddToSetForm(FlaskForm):
    flashcard_id = SelectField('Flashcard', coerce=int)
    submit = SubmitField('Add Flashcard')
class VirtualTutorForm(FlaskForm):
    subject = StringField('Subject', validators=[DataRequired()])
    user_input = StringField('User Input', validators=[DataRequired()])
    submit = SubmitField('Submit')

class SearchSetsForm(FlaskForm):
    search_query = StringField('Search Query', validators=[DataRequired()])
    submit = SubmitField('Search')
class BlogPostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Post')

class CommentForm(FlaskForm):
    content = TextAreaField('Leave a comment', validators=[DataRequired()])
    submit = SubmitField('Post Comment')

class CreateStudyPodForm(FlaskForm):
    name = StringField('Pod Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Create Pod')

class CreateStudyPodPostForm(FlaskForm):
    title = StringField('Post Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Post')

class CreateStudyPodCommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Comment')

class FlashcardGeneratorForm(FlaskForm):
    topic = StringField('Topic', validators=[DataRequired()])
    user_prompt = StringField('Prompt', validators=[DataRequired()])
    submit = SubmitField('Generate Flashcards')