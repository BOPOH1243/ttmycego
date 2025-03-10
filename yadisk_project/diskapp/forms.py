# diskapp/forms.py
from django import forms

class PublicKeyForm(forms.Form):
    public_key = forms.CharField(
        label="Публичная ссылка (public_key)",
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите публичную ссылку'})
    )
