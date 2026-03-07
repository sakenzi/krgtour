from django import forms
from .models import Booking
from django.utils import timezone


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['tour_date', 'num_people', 'contact_name', 'contact_phone', 'contact_email', 'special_requests']
        widgets = {
            'tour_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'min': timezone.now().date().isoformat(),
            }),
            'num_people': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 50}),
            'contact_name': forms.TextInput(attrs={'class': 'form-input'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+7 (777) 000-00-00'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-input'}),
            'special_requests': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Дополнительные пожелания...'}),
        }

    def clean_tour_date(self):
        date = self.cleaned_data['tour_date']
        if date < timezone.now().date():
            raise forms.ValidationError('Дата не может быть в прошлом.')
        return date