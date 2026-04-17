from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Введите ваше имя пользователя'
    }), label='Имя пользователя')

    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Введите ваш пароль'
    }), label='Пароль')


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Придумайте пароль', 'id': 'password'}),
    )
    confirm_password = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Повторите пароль', 'id': 'confirmPassword'})
    )
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Придумайте логин', 'id': 'login'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Введите ваш email', 'id': 'email'}),
        }

        def clean_password(self):
            password = self.cleaned_data.get('password')
            user = User(username=self.cleaned_data.get('username'), email=self.cleaned_data.get('email'))
            validate_password(password, user)
            return password

        def clean(self):
            cleaned_data = super().clean()
            password = cleaned_data.get('password')
            confirm = cleaned_data.get('confirm_password')
            if password and confirm and password != confirm:
                self.add_error('confirm_password', "Пароли не совпадают")
            return cleaned_data