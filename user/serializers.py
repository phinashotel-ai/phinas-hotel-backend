from rest_framework import serializers
from .models import CustomUser, ContactMessage
import re


PASSWORD_RULE_TEXT = "Password must be at least 8 characters and include uppercase, lowercase, and a special character."


def validate_password_strength(value):
    if len(value) < 8:
        raise serializers.ValidationError(PASSWORD_RULE_TEXT)
    if not re.search(r"[A-Z]", value):
        raise serializers.ValidationError(PASSWORD_RULE_TEXT)
    if not re.search(r"[a-z]", value):
        raise serializers.ValidationError(PASSWORD_RULE_TEXT)
    if not re.search(r"[^A-Za-z0-9]", value):
        raise serializers.ValidationError(PASSWORD_RULE_TEXT)
    return value

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = [
            "id", "first_name", "middle_name", "last_name", "username",
            "contact", "address", "gender", "email", "password", "confirm_password"
        ]

    def validate_contact(self, value):
        if not re.match(r'^\+?1?\d{9,15}$', value):
            raise serializers.ValidationError("Invalid phone number format.")
        return value

    def validate_password(self, value):
        return validate_password_strength(value)

    def validate(self, data):
        if CustomUser.objects.filter(username=data["username"]).exists():
            raise serializers.ValidationError({"username": "This username is already taken."})
        if CustomUser.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError({"email": "This email is already in use."})
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match!"})
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password") 
        user = CustomUser.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class UserProfileSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ["id", "first_name", "middle_name", "last_name", "username", "contact", "address", "gender", "email", "role"]
        read_only_fields = fields

    def get_role(self, obj):
        return obj.role

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["first_name", "middle_name", "last_name", "contact", "address", "gender"]


class AdminUserManageSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = CustomUser
        fields = [
            "id", "first_name", "middle_name", "last_name", "username",
            "contact", "address", "gender", "email", "role", "password",
        ]

    def validate_contact(self, value):
        if not re.match(r"^\+?1?\d{9,15}$", value):
            raise serializers.ValidationError("Invalid phone number format.")
        return value

    def validate_password(self, value):
        return validate_password_strength(value)

    def validate(self, data):
        instance = getattr(self, "instance", None)
        username = data.get("username")
        email = data.get("email")
        contact = data.get("contact")

        if username:
            qs = CustomUser.objects.filter(username=username)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"username": "This username is already taken."})

        if email:
            qs = CustomUser.objects.filter(email=email)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"email": "This email is already in use."})

        if contact:
            qs = CustomUser.objects.filter(contact=contact)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"contact": "This contact is already in use."})

        return data

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "Password is required."})
        return CustomUser.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class PasswordResetSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        validate_password_strength(data["new_password"])
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match!"})
        return data


class ContactMessageSerializer(serializers.ModelSerializer):
    replied_by_name = serializers.CharField(source="replied_by.username", read_only=True)

    class Meta:
        model = ContactMessage
        fields = [
            "id", "name", "email", "phone", "subject", "message", "status",
            "reply", "replied_at", "replied_by", "replied_by_name", "created_at",
        ]
        read_only_fields = ["replied_at", "replied_by", "replied_by_name", "created_at"]
