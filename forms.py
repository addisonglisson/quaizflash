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