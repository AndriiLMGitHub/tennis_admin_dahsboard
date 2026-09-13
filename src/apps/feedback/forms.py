from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Feedback


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['name', 'email', 'subject', 'message']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Your Name')}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Your Email')}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Subject')}),
            'message': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 6, 'placeholder': _('Type your message here...')}),
        }