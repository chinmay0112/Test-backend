from import_export import resources
from .models import Question

class QuestionResource(resources.ModelResource):
    # We need to map the 'section' column in Excel (which contains a name like 'Math')
    # to the actual Section ID in the database.
  

    class Meta:
        model = Question
        # List the fields you want to import
        fields = ('id', 'section', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option', 'explanation')
        # Which field is the unique ID? (usually 'id')
        import_id_fields = ('id',)
        # If Excel has extra columns, ignore them
        skip_unchanged = True
        report_skipped = False

