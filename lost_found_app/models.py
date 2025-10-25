from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
import uuid
from datetime import date
######################################################################################################################################################
######################################################################################################################################################
class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('resident', 'DHUAM Resident'),
        ('admin', 'Administrator'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='resident')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    tower_number = models.CharField(max_length=10, blank=True, null=True)
    room_number = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        Automatically assign permission levels based on user type.
        """
        if self.user_type == 'admin':
            # Give full admin rights
            self.is_active = True
            self.is_staff = True
            self.is_superuser = True
        else:
            # Limited access for residents
            self.is_active = True
            self.is_staff = False
            self.is_superuser = False

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} - {self.get_user_type_display()}"
######################################################################################################################################################
######################################################################################################################################################
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
######################################################################################################################################################
######################################################################################################################################################
class LostItem(models.Model):
    STATUS_CHOICES = (
        ('lost', 'Lost'),
        ('found', 'Found'),
        ('claimed', 'Claimed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lost_items')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    # AI Classification Fields
    ai_suggested_category = models.CharField(max_length=200, blank=True)
    ai_confidence = models.FloatField(null=True, blank=True)
    ai_top_predictions = models.JSONField(default=dict, blank=True)  # Store all top predictions
    
    # Location details
    lost_location = models.CharField(max_length=200)
    lost_date = models.DateField(default=date.today)
    lost_time = models.TimeField(blank=True, null=True)
    
    # Item details
    brand = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=50, blank=True)
    
    # Image handling
    item_image = models.ImageField(
        upload_to='lost_items/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='lost')
    is_verified = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # Auto-classify image if it's being added/updated and AI fields are empty
        if self.item_image and (not self.ai_suggested_category or not self.ai_top_predictions):
            from .ai_service import PyTorchAIClassificationService
            try:
                ai_service = PyTorchAIClassificationService()
                result = ai_service.classify_image(self.item_image.path)
                
                if result:
                    self.ai_suggested_category = result.get('suggested_category', '')
                    self.ai_confidence = result.get('confidence', 0.0)
                    self.ai_top_predictions = result.get('top_predictions', {})
            except Exception as e:
                print(f"AI classification failed: {e}")
        
        super().save(*args, **kwargs)
######################################################################################################################################################
######################################################################################################################################################
class FoundItem(models.Model):
    STATUS_CHOICES = (
        ('found', 'Found'),
        ('returned', 'Returned'),
        ('disposed', 'Disposed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='found_items')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    # AI Classification Fields
    ai_suggested_category = models.CharField(max_length=200, blank=True)
    ai_confidence = models.FloatField(null=True, blank=True)
    ai_top_predictions = models.JSONField(default=dict, blank=True)
    
    # Finding details
    found_location = models.CharField(max_length=200)
    found_date = models.DateField(default=date.today)
    found_time = models.TimeField(blank=True, null=True)
    
    # Item details
    brand = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=50, blank=True)
    
    # Image handling
    item_image = models.ImageField(
        upload_to='found_items/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    
    # Storage location
    storage_location = models.CharField(max_length=200, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='found')
    is_verified = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # Auto-classify image if it's being added/updated and AI fields are empty
        if self.item_image and (not self.ai_suggested_category or not self.ai_top_predictions):
            from .ai_service import PyTorchAIClassificationService
            try:
                ai_service = PyTorchAIClassificationService()
                result = ai_service.classify_image(self.item_image.path)
                
                if result:
                    self.ai_suggested_category = result.get('suggested_category', '')
                    self.ai_confidence = result.get('confidence', 0.0)
                    self.ai_top_predictions = result.get('top_predictions', {})
            except Exception as e:
                print(f"AI classification failed: {e}")
        
        super().save(*args, **kwargs)
######################################################################################################################################################
######################################################################################################################################################
class Claim(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('returned', 'Item Returned'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claims')
    found_item = models.ForeignKey(FoundItem, on_delete=models.CASCADE, related_name='claims')
    
    # Claim details
    claim_description = models.TextField()
    proof_of_ownership = models.TextField(blank=True)
    supporting_images = models.ImageField(
        upload_to='claim_support/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'found_item']
    
    def __str__(self):
        return f"Claim by {self.user.username} for {self.found_item.title}"
######################################################################################################################################################
######################################################################################################################################################
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('claim_update', 'Claim Status Update'),
        ('match_found', 'Potential Match Found'),
        ('item_found', 'Your Lost Item Found'),
        ('system', 'System Notification'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related item (optional)
    lost_item = models.ForeignKey(LostItem, on_delete=models.CASCADE, null=True, blank=True)
    found_item = models.ForeignKey(FoundItem, on_delete=models.CASCADE, null=True, blank=True)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, null=True, blank=True)
    
    # Read status
    is_read = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} - {self.user.username}"
######################################################################################################################################################
######################################################################################################################################################
class AIClassificationLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image_path = models.CharField(max_length=500)
    predicted_category = models.CharField(max_length=200)
    confidence_score = models.FloatField()
    top_predictions = models.JSONField(default=dict)
    model_version = models.CharField(max_length=50, default='resnet101')
    processing_time = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI Classification - {self.predicted_category} ({self.confidence_score:.2f})"