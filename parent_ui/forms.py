# parent_ui/forms.py
from django import forms
from api.models import ChildDevice, ScreenTimeRule, BlockedApp

class DeviceForm(forms.ModelForm):
    class Meta:
        model = ChildDevice
        fields = ['device_id', 'nickname']
        widgets = {
            'device_id': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

class ScreenTimeRuleForm(forms.ModelForm):
    class Meta:
        model = ScreenTimeRule
        fields = ['daily_limit_minutes', 'bedtime_start', 'bedtime_end']
        widgets = {
            'bedtime_start': forms.TimeInput(attrs={'type': 'time'}),
            'bedtime_end': forms.TimeInput(attrs={'type': 'time'}),
        }

class BlockAppForm(forms.ModelForm):
    class Meta:
        model = BlockedApp
        fields = ['app_name']


from django import forms
from api.models import BlockedApp

class BlockAppForm(forms.ModelForm):
    class Meta:
        model = BlockedApp
        fields = ['app_name', 'package_name']
        widgets = {
            'app_name': forms.TextInput(attrs={'class': 'form-control'}),
            'package_name': forms.TextInput(attrs={'class': 'form-control'}),
        }