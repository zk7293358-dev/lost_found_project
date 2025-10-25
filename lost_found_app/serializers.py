from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Category, LostItem, FoundItem, Claim, Notification, AIClassificationLog
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
########################################################################################################################################################
########################################################################################################################################################
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'password2',
            'first_name',
            'last_name',
            'user_type',
            'phone_number',
            'tower_number',
            'room_number',
        ]

    def validate(self, attrs):
        errors = {}

        # Required fields validation
        required_fields = ['username', 'email', 'password', 'password2','first_name','last_name','user_type','phone_number','tower_number','room_number']
        for field in required_fields:
            if not attrs.get(field):
                errors[field] = ['This field is required.']

        # Check if passwords match
        if attrs.get('password') and attrs.get('password2') and attrs['password'] != attrs['password2']:
            errors['password2'] = ['Passwords do not match.']

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')

        # Create user object
        user = User(**validated_data)
        user.set_password(password)

        # Apply permission logic explicitly here too (for extra safety)
        if user.user_type == 'admin':
            user.is_active = True
            user.is_staff = True
            user.is_superuser = True
        else:
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False

        user.save()
        return user
###########################################################################################################################################################
#############################################################################################################################################################
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        errors = {}

        # Validation for missing fields
        if not email:
            errors['email'] = ['This field is required.']
        if not password:
            errors['password'] = ['This field is required.']

        if errors:
            raise serializers.ValidationError(errors)

        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({'detail': 'Invalid email or password.'})

        # Authenticate user
        user = authenticate(username=user.username, password=password)
        if not user:
            raise serializers.ValidationError({'detail': 'Invalid email or password.'})

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        return {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            },
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'redirect_url': '/admin-dashboard/' if user.user_type == 'admin' else '/resident-dashboard/'
        }
###########################################################################################################################################################
#############################################################################################################################################################
class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for viewing and updating user profile."""
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'user_type',
            'phone_number',
            'tower_number',
            'room_number',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user_type', 'created_at', 'updated_at', 'username', 'email']
###########################################################################################################################################################
#############################################################################################################################################################
class UpdatePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password."""
    old_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password], style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    def validate(self, attrs):
        user = self.context['request'].user

        if not user.check_password(attrs.get('old_password')):
            raise serializers.ValidationError({"old_password": "Old password is incorrect."})

        if attrs.get('new_password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        return attrs
    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
###########################################################################################################################################################
#############################################################################################################################################################
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
###########################################################################################################################################################
#############################################################################################################################################################
class LostItemSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    ai_predictions_display = serializers.SerializerMethodField()
    
    class Meta:
        model = LostItem
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at', 'ai_suggested_category', 'ai_confidence', 'ai_top_predictions']
    
    def get_ai_predictions_display(self, obj):
        if obj.ai_top_predictions:
            return [f"{pred['category']}: {pred['confidence']:.2f}%" 
                   for pred in obj.ai_top_predictions.get('predictions', [])]
        return []
###########################################################################################################################################################
#############################################################################################################################################################
class FoundItemSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    claim_count = serializers.SerializerMethodField()
    ai_predictions_display = serializers.SerializerMethodField()
    
    class Meta:
        model = FoundItem
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at', 'ai_suggested_category', 'ai_confidence', 'ai_top_predictions']
    
    def get_claim_count(self, obj):
        return obj.claims.count()
    
    def get_ai_predictions_display(self, obj):
        if obj.ai_top_predictions:
            return [f"{pred['category']}: {pred['confidence']:.2f}%" 
                   for pred in obj.ai_top_predictions.get('predictions', [])]
        return []
###########################################################################################################################################################
#############################################################################################################################################################
class ClaimSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    found_item_details = FoundItemSerializer(source='found_item', read_only=True)
    
    class Meta:
        model = Claim
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']
###########################################################################################################################################################
#############################################################################################################################################################
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
###########################################################################################################################################################
#############################################################################################################################################################
class AIClassificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIClassificationLog
        fields = '__all__'
###########################################################################################################################################################
#############################################################################################################################################################
class AIClassificationRequestSerializer(serializers.Serializer):
    image = serializers.ImageField()
    item_type = serializers.ChoiceField(choices=[('lost', 'Lost'), ('found', 'Found')])
###########################################################################################################################################################
#############################################################################################################################################################
class AIClassificationResponseSerializer(serializers.Serializer):
    suggested_category = serializers.CharField()
    confidence = serializers.FloatField()
    top_predictions = serializers.ListField(child=serializers.DictField())
    processing_time = serializers.FloatField()
###########################################################################################################################################################
#############################################################################################################################################################
class RealTimeClassificationSerializer(serializers.Serializer):
    image = serializers.ImageField()
###########################################################################################################################################################
#############################################################################################################################################################
class RealTimeClassificationResponseSerializer(serializers.Serializer):
    predictions = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField())
    )
    processing_time = serializers.FloatField()
    model_version = serializers.CharField()