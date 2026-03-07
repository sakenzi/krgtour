from django import forms
from .models import Review, Route, RoutePoint


class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, i) for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={'class': 'star-radio'}),
        label='Оценка'
    )

    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment', 'visit_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Заголовок отзыва (необязательно)'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'Поделитесь своими впечатлениями...'
            }),
            'visit_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
        }


class RouteSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'search-input',
            'placeholder': 'Поиск маршрутов...',
        })
    )
    difficulty = forms.ChoiceField(
        choices=[('', 'Любой')] + Route.DIFFICULTY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    min_distance = forms.FloatField(required=False, min_value=0)
    max_distance = forms.FloatField(required=False, min_value=0)
    max_price = forms.FloatField(required=False, min_value=0)


class RouteAdminForm(forms.ModelForm):
    """Form for admin route creation/editing."""

    class Meta:
        model = Route
        fields = [
            'title', 'description', 'short_description', 'cover_image',
            'category', 'difficulty', 'distance_km', 'duration_hours',
            'price', 'max_group_size', 'min_age', 'status', 'is_featured',
            'start_lat', 'start_lng', 'end_lat', 'end_lng',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 6}),
            'short_description': forms.TextInput(attrs={'class': 'form-input'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-file', 'accept': 'image/*'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'distance_km': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1'}),
            'duration_hours': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5'}),
            'price': forms.NumberInput(attrs={'class': 'form-input', 'step': '100'}),
            'max_group_size': forms.NumberInput(attrs={'class': 'form-input'}),
            'min_age': forms.NumberInput(attrs={'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_lat': forms.HiddenInput(),
            'start_lng': forms.HiddenInput(),
            'end_lat': forms.HiddenInput(),
            'end_lng': forms.HiddenInput(),
        }