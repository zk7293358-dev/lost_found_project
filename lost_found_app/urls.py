# lost_found_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserProfileView, UpdatePasswordView
from . import views

router = DefaultRouter()

# Register ViewSets with explicit basename since get_queryset() is used
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'lost-items', views.LostItemViewSet, basename='lostitem')
router.register(r'found-items', views.FoundItemViewSet, basename='founditem')
router.register(r'claims', views.ClaimViewSet, basename='claim')
router.register(r'notifications', views.NotificationViewSet, basename='notification')

urlpatterns = [
#####################################################################################################################################################
    path('api/', include(router.urls)),
    path('api/register/', views.register_user, name='register_user'),
    path('api/login/', views.login_user, name='login_user'),
#####################################################################################################################################################
    path('api/classify-image/', views.classify_image, name='classify_image'),
    path('api/real-time-classify/', views.real_time_classify, name='real_time_classify'),
    path('api/ai-service-status/', views.ai_service_status, name='ai_service_status'),
#####################################################################################################################################################
    path('api/profile/', UserProfileView.as_view(), name='user-profile'),
    path('profile/change-password/', UpdatePasswordView.as_view(), name='change-password'),
#####################################################################################################################################################


]
