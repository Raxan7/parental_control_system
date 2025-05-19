# parent_ui/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
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