# parent_ui/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import password_validation
from api.models import ChildDevice, ScreenTimeRule, BlockedApp, CustomUser

class DeviceForm(forms.ModelForm):
    class Meta:
        model = ChildDevice
        fields = ['device_id', 'nickname']
        widgets = {
            'device_id': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

# parent_ui/forms.py
class ScreenTimeRuleForm(forms.ModelForm):
    daily_limit_minutes = forms.IntegerField(
        min_value=1,
        max_value=1440,  # 24 hours in minutes
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    bedtime_start = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )
    
    bedtime_end = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )

    class Meta:
        model = ScreenTimeRule
        fields = ['daily_limit_minutes', 'bedtime_start', 'bedtime_end']
        

class BlockAppForm(forms.ModelForm):
    app_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter app name (e.g., WhatsApp)'
        })
    )
    
    package_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter package name (e.g., com.whatsapp)'
        })
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Reason for blocking (optional)',
            'rows': 3
        })
    )
    
    class Meta:
        model = BlockedApp
        fields = ['app_name', 'package_name', 'notes']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        app_name = cleaned_data.get('app_name')
        package_name = cleaned_data.get('package_name')
        
        # If both app name and package name are provided, validate they match
        if app_name and package_name and package_name.strip():
            from .templatetags.custom_filters import friendly_app_name
            
            # Get the expected app name from the package name
            expected_app_name = friendly_app_name(package_name, self.user)
            
            # Compare app names (case insensitive)
            if app_name.lower().strip() != expected_app_name.lower().strip():
                raise forms.ValidationError(
                    f"App name '{app_name}' does not match package name '{package_name}'. "
                    f"Expected app name: '{expected_app_name}'. "
                    f"Please ensure the app name and package name correspond to the same application."
                )
        
        return cleaned_data

class ParentRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class AccountSettingsForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password'
        }),
        help_text='Enter your current password to confirm the change.'
    )
    
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        help_text=password_validation.password_validators_help_text_html(),
    )
    
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        help_text='Enter the same password as before, for verification.'
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise forms.ValidationError('Your current password is incorrect.')
        return current_password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError('The two password fields didn\'t match.')
        
        password_validation.validate_password(password2, self.user)
        return password2

    def save(self):
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        self.user.save()
        return self.user