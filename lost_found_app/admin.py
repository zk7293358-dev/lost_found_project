from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, LostItem, FoundItem, Claim, Notification, AIClassificationLog

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type', 'phone_number', 'tower_number', 'room_number', 'date_joined')
    list_filter = ('user_type', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('DHUAM Information', {
            'fields': ('user_type', 'phone_number', 'tower_number', 'room_number')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('DHUAM Information', {
            'fields': ('user_type', 'phone_number', 'tower_number', 'room_number')
        }),
    )

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    list_per_page = 20

@admin.register(LostItem)
class LostItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'ai_suggested_category', 'ai_confidence', 'status', 'lost_location', 'lost_date', 'created_at')
    list_filter = ('status', 'category', 'lost_date', 'created_at')
    search_fields = ('title', 'description', 'lost_location', 'ai_suggested_category')
    readonly_fields = ('created_at', 'updated_at', 'ai_suggested_category', 'ai_confidence', 'ai_top_predictions')
    list_per_page = 20
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'description', 'category')
        }),
        ('AI Classification', {
            'fields': ('ai_suggested_category', 'ai_confidence', 'ai_top_predictions'),
            'classes': ('collapse',)
        }),
        ('Location & Time', {
            'fields': ('lost_location', 'lost_date', 'lost_time')
        }),
        ('Item Details', {
            'fields': ('brand', 'color', 'item_image')
        }),
        ('Status', {
            'fields': ('status', 'is_verified')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(FoundItem)
class FoundItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'ai_suggested_category', 'ai_confidence', 'status', 'found_location', 'found_date', 'created_at')
    list_filter = ('status', 'category', 'found_date', 'created_at')
    search_fields = ('title', 'description', 'found_location', 'ai_suggested_category')
    readonly_fields = ('created_at', 'updated_at', 'ai_suggested_category', 'ai_confidence', 'ai_top_predictions')
    list_per_page = 20
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'description', 'category')
        }),
        ('AI Classification', {
            'fields': ('ai_suggested_category', 'ai_confidence', 'ai_top_predictions'),
            'classes': ('collapse',)
        }),
        ('Finding Details', {
            'fields': ('found_location', 'found_date', 'found_time', 'storage_location')
        }),
        ('Item Details', {
            'fields': ('brand', 'color', 'item_image')
        }),
        ('Status', {
            'fields': ('status', 'is_verified')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('user', 'found_item', 'status', 'created_at', 'resolved_at')
    list_filter = ('status', 'created_at', 'resolved_at')
    search_fields = ('user__username', 'found_item__title', 'claim_description')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20
    
    fieldsets = (
        ('Claim Information', {
            'fields': ('user', 'found_item', 'claim_description', 'proof_of_ownership')
        }),
        ('Supporting Evidence', {
            'fields': ('supporting_images',)
        }),
        ('Status & Review', {
            'fields': ('status', 'admin_notes', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at',)
    list_per_page = 20

@admin.register(AIClassificationLog)
class AIClassificationLogAdmin(admin.ModelAdmin):
    list_display = ('predicted_category', 'confidence_score', 'model_version', 'processing_time', 'created_at')
    list_filter = ('model_version', 'created_at')
    search_fields = ('predicted_category', 'image_path')
    readonly_fields = ('created_at',)
    list_per_page = 20
    
    fieldsets = (
        ('Classification Results', {
            'fields': ('predicted_category', 'confidence_score', 'top_predictions')
        }),
        ('Technical Details', {
            'fields': ('image_path', 'model_version', 'processing_time')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )