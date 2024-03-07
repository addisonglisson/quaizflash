from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, IntegerField, FormField, FieldList, Form, HiddenField
from wtforms.validators import DataRequired, Optional, URL
from wtforms.fields import SelectField
from flask_wtf.file import FileField, FileAllowed

class FlashcardSetForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Create Flashcard Set')
class FlashcardForm(FlaskForm):
    question = StringField('Question', validators=[DataRequired()])
    answer = StringField('Answer', validators=[DataRequired()])
    submit = SubmitField('Save Flashcards')

class CreateMultipleFlashcardForm(FlaskForm):
    flashcards = FieldList(FormField(FlashcardForm), min_entries=1)
    submit = SubmitField('Submit')

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
    image = FileField('Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    submit = SubmitField('Post')

class CreateStudyPodCommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Comment')

class FlashcardGeneratorForm(FlaskForm):
    topic = StringField('Topic', validators=[DataRequired()])
    num_flashcards = IntegerField('Number of Flashcards', validators=[DataRequired()])
    question = StringField('Question', validators=[Optional()])
    article_text = TextAreaField('Article Text', validators=[Optional()])
    url = StringField('URL', validators=[Optional(), URL(message='Invalid URL')])
    submit = SubmitField('Generate Flashcards')

class AdvancedTutorForm(FlaskForm):
    flashcard_set = SelectField('Choose a Flashcard Set', coerce=int)
    user_input = StringField('Ask a question or say "quiz me" on a chosen set', validators=[DataRequired()])
    mode = HiddenField(default='learn')
    submit = SubmitField('Submit')