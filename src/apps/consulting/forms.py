from datetime import datetime

from django import forms
from django.utils import timezone

from .models import Request, NutritionIntake, PsychologyIntake
from django.utils.translation import gettext_lazy as _


class CreateRequestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'service' in self.fields:
            self.fields['service'].empty_label = _("-- Choose Service --")
            self.fields['service'].label_from_instance = lambda obj: obj.name

    media_file = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control bg-transparent',
            'id': 'mediaFile'
        })
    )
    media_link = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control bg-transparent',
            'placeholder': _('e.g., https://youtube.com/watch?v=...'),
            'id': 'mediaLink'
        })
    )

    class Meta:
        model = Request
        fields = ('service', 'specialty_needed', 'comment')

        labels = {
            'service': _('Select service type'),
        }

        widgets = {
            'service': forms.Select(
                attrs={
                    'class': 'form-select bg-transparent',
                    'placeholder': _('Select a service...'),
                    'id': 'service'
                }
            ),
            'specialty_needed': forms.Select(
                attrs={
                    'class': 'form-select bg-transparent',
                    'id': 'specialty_needed'
                }
            ),
            'comment': forms.Textarea(
                attrs={
                    'class': 'form-control bg-transparent',
                    'rows': 4,
                    'placeholder': _('Describe your request or share any details and symptoms...')
                }
            ),
        }


class NutritionIntakeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Додаємо формат з пробілом, який генерує Flatpickr ("2026-08-26 12:00")
        datetime_formats = [
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%dT%H:%M:%S',
        ]
        self.fields['appointment_date'].input_formats = datetime_formats

    class Meta:
        model = NutritionIntake
        fields = (
            'full_name', 'age', 'weight', 'weight_unit', 'height', 'height_unit',
            'handedness', 'language', 'whatsapp_number',
            'appointment_date',
            'complaints', 'chronic_diseases', 'medications_and_vitamins',
            'operations', 'traumas', 'allergies', 'attachments'
        )
        widgets = {
            'full_name': forms.TextInput(
                attrs={'class': 'form-control bg-transparent', 'placeholder': _('e.g., John Doe')}),

            'age': forms.NumberInput(
                attrs={
                    'class': 'form-control bg-transparent',
                    'min': '0',
                    'placeholder': _('e.g., 30')
                }),

            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '0.0'}),
            'weight_unit': forms.Select(attrs={'class': 'form-select w-75px flex-grow-0'}),

            'height': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'height_unit': forms.Select(attrs={'class': 'form-select w-75px flex-grow-0'}),

            'handedness': forms.Select(
                attrs={
                    'class': 'form-select bg-transparent'
                }),

            'language': forms.TextInput(
                attrs={
                    'class': 'form-control bg-transparent',
                    'placeholder': _('e.g., English, Ukrainian')
                }),

            'whatsapp_number': forms.TextInput(
                attrs={
                    'class': 'form-control bg-transparent',
                    'placeholder': _('e.g., +380 50 123 4567')
                }),

            'appointment_date': forms.TextInput(
                attrs={
                    'class': 'form-control bg-transparent flatpickr-input',
                    'placeholder': _('Pick date & time'),
                    'readonly': 'readonly'
                }),

            'complaints': forms.Textarea(
                attrs={
                    'class': 'form-control bg-transparent',
                    'rows': 3,
                    'placeholder': _('Describe your main concerns (e.g., constant fatigue, bloating after meals, poor sleep...)')
                }),

            'chronic_diseases': forms.Textarea(
                attrs={
                    'class': 'form-control bg-transparent',
                    'rows': 3,
                    'placeholder': _('List any diagnosed chronic diseases, or write "None"')
                }),

            'medications_and_vitamins': forms.Textarea(
                attrs={
                    'class': 'form-control bg-transparent',
                    'rows': 3,
                    'placeholder': _('e.g., Vitamin D 2000 IU daily, Omega-3, or "None"')
                }),

            'operations': forms.Textarea(
                attrs={
                    'class': 'form-control bg-transparent',
                    'rows': 2,
                    'placeholder': _('List past surgeries with approximate years, or write "None"')
                }),

            'traumas': forms.Textarea(
                attrs={
                    'class': 'form-control bg-transparent',
                    'rows': 2,
                    'placeholder': _('List significant physical traumas, or write "None"')
                }),

            'allergies': forms.Textarea(
                attrs={
                    'class': 'form-control bg-transparent',
                    'rows': 2,
                    'placeholder': _('e.g., Peanuts, lactose, penicillin, or "None"')
                }),

            'attachments': forms.FileInput(
                attrs={
                    'class': 'form-control bg-transparent',
                    'accept': 'pdf, .doc, .docx, .xls, .xlsx, .txt, .jpg, .jpeg, .png'
                })
        }

    def clean(self):
        cleaned_data = super().clean()
        weight = cleaned_data.get('weight')
        weight_unit = cleaned_data.get('weight_unit')
        height = cleaned_data.get('height')
        height_unit = cleaned_data.get('height_unit')

        # Захист від аномальних значень із чітким зазначенням дозволеного діапазону
        if weight and weight_unit:
            if weight_unit == 'kg' and (weight < 20 or weight > 300):
                self.add_error('weight', _("Weight must be between 20 and 300 kg."))
            elif weight_unit == 'lbs' and (weight < 44 or weight > 660):
                self.add_error('weight', _("Weight must be between 44 and 660 lbs."))

        if height and height_unit:
            if height_unit == 'cm' and (height < 50 or height > 250):
                self.add_error('height', _("Height must be between 50 and 250 cm."))
            elif height_unit == 'in' and (height < 20 or height > 100):
                self.add_error('height', _("Height must be between 20 and 100 inches."))

        return cleaned_data

    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight and weight <= 0:
            raise forms.ValidationError(_("Weight must be a positive number."))
        return weight

    def clean_height(self):
        height = self.cleaned_data.get('height')
        if height and height <= 0:
            raise forms.ValidationError(_("Height must be a positive number."))
        return height

    def clean_appointment_date(self):
        appointment_date = self.cleaned_data.get('appointment_date')
        if appointment_date:
            now = timezone.now() if isinstance(appointment_date, datetime) else timezone.localdate()
            if appointment_date < now:
                raise forms.ValidationError(_("You cannot schedule an appointment in the past."))
        return appointment_date



class PsychologyIntakeForm(forms.ModelForm):
    class Meta:
        model = PsychologyIntake
        fields = [
            'appointment_date', 'whatsapp_number', 'primary_concern',
            'previous_therapy', 'psychiatric_medications', 'crisis_state'
        ]
        widgets = {
            'appointment_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'id': 'psychology_appointment_date'
            }),
            'whatsapp_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Crucial for online therapy sessions'
            }),
            'primary_concern': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe what bothers you right now...'
            }),
            'psychiatric_medications': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Antidepressants, anxiolytics, etc. (if any)'
            }),
            'previous_therapy': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'crisis_state': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
