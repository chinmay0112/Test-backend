# core/forms.py
from django import forms

class AIQuestionForm(forms.Form):
    topic = forms.CharField(
        max_length=200, 
        required=True, 
        widget=forms.TextInput(attrs={'style': 'width: 300px;', 'placeholder': 'e.g., Indus Valley Civilization'})
    )
    num_questions = forms.IntegerField(
        min_value=1, 
        max_value=20, 
        initial=5,
        label="Number of Questions"
    )
    difficulty = forms.ChoiceField(
        choices=[
            ('Easy', 'Easy'), 
            ('Medium', 'Medium'), 
            ('Hard', 'Hard')
        ],
        initial='Medium'
    )