from django import forms
from .models import *

class CategoryForm(forms.Form):

    class Meta:
        model = QuestionAnswer
        fields = ['category']

class CreateModersForm(forms.ModelForm):

    name = forms.CharField(disabled=True)
    login_tg = forms.CharField(disabled=True)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), disabled=True)
    categories = forms.ModelMultipleChoiceField(queryset=Category.objects.all(), disabled=True)

    class Meta:
        model = RequestToAddModerators
        fields = ['name', 'login_tg', 'department', 'categories', 'comment', 'it_rejection']

class DeleteModersForm(forms.ModelForm):

    user_edit_delete = forms.ModelChoiceField(queryset=User.objects.all(), disabled=True)

    class Meta:
        model = RequestToAddModerators
        fields = ['user_edit_delete', 'comment', 'it_rejection']

class EditModersFormAction(forms.ModelForm):

    user_edit_delete = forms.ModelChoiceField(queryset=User.objects.all(), disabled=True)
    name = forms.CharField(disabled=True)
    login_tg = forms.CharField(disabled=True)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), disabled=True)
    categories = forms.ModelMultipleChoiceField(queryset=Category.objects.all(), disabled=True)

    class Meta:
        model = RequestToAddModerators
        fields = ['user_edit_delete', 'name', 'login_tg', 'department', 'categories', 'comment', 'it_rejection']

class FeedbackUpdateForm(forms.ModelForm):

    feedback = forms.CharField(disabled=True, widget=forms.Textarea)
    type_feedback = forms.ChoiceField(choices=FeedbackFromUsers.CHOISE_TYPE_FEEDBACK, disabled=True)

    class Meta:
        model = FeedbackFromUsers
        fields = ['feedback', 'status', 'comment', 'type_feedback']

class FeedbackAddForm(forms.ModelForm):

    class Meta:
        model = FeedbackFromUsers
        fields = ['feedback', 'type_feedback']