from django import forms
from . models import Review

class ReviewRating(forms.ModelForm):
    class Meta:
        model=Review
        fields=['rating','review_text','ip_field']