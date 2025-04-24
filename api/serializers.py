from rest_framework import serializers
from .models import CustomUser, ChildDevice, AppUsageLog

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'password', 'is_parent', 'is_child']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            is_parent=validated_data.get('is_parent', False),
            is_child=validated_data.get('is_child', False)
        )
        return user

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildDevice
        fields = ['device_id', 'parent']

class AppUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUsageLog
        fields = ['app_name', 'start_time', 'end_time']