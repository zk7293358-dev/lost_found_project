from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
import time
from django.shortcuts import render
from django.contrib import messages
from django.db.models import Count
import logging
from .serializers import *
from .ai_service import pytorch_ai_service
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import generics, permissions, status
######################################################################################################################################################
from .models import (
    User, 
    Category,
    LostItem,
    FoundItem, 
    Claim, 
    Notification
)
##########################################################################################################################################################
from .serializers import ( 
    RegisterSerializer, 
    LoginSerializer,
    UserProfileSerializer, 
    UpdatePasswordSerializer
)
############################################################################
from rest_framework.permissions import AllowAny
logger = logging.getLogger(__name__)
###########################################################################################################################################################
#############################################################################################################################################################
###########################################################################################################################################################
# Custom permission for Owner or Admin
###########################################################################################################################################################
class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Allow admin users to access everything
        if request.user.user_type == 'admin':
            return True
        # Allow owners to access their own data
        return obj == request.user
###########################################################################################################################################################
# User ViewSet (Admin can view all users, others only their profile)
###########################################################################################################################################################
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin':
            return User.objects.all()
        return User.objects.filter(id=user.id)
###########################################################################################################################################################
# Register API
###########################################################################################################################################################
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    Register a new user (Resident or Admin)
    """
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()

        # Generate tokens on registration for immediate login
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'User registered successfully.',
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
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
###########################################################################################################################################################
# Login API
###########################################################################################################################################################
@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """
    Login with email & password.
    Returns JWT tokens and redirects based on role.
    """
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
##########################################################################################################################################################
#########################################################################################################################################################
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Profile API for viewing and updating user details.
    - Residents: can only access their own profile.
    - Admins: can access any user's profile by ID.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user

        # If admin, can view specific user via ?user_id param
        user_id = self.request.query_params.get('user_id')
        if user.is_superuser and user_id:
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Otherwise, return own profile
        return user
##########################################################################################################################################################
#########################################################################################################################################################
class UpdatePasswordView(generics.UpdateAPIView):
    """
    API endpoint for authenticated users to change password.
    """
    serializer_class = UpdatePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)
###########################################################################################################################################################
#############################################################################################################################################################
class CategoryViewSet(viewsets.ModelViewSet):  # changed here ✅
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
###########################################################################################################################################################
#############################################################################################################################################################
class LostItemViewSet(viewsets.ModelViewSet):
    serializer_class = LostItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin':
            return LostItem.objects.all()
        return LostItem.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        category = request.query_params.get('category', '')
        
        queryset = self.get_queryset().filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(lost_location__icontains=query)
        )
        
        if category:
            queryset = queryset.filter(category__name__iexact=category)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def classify_image(self, request, pk=None):
        """Re-classify image using AI"""
        lost_item = self.get_object()
        
        if not lost_item.item_image:
            return Response({'error': 'No image available for classification'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = pytorch_ai_service.classify_image(lost_item.item_image.path)
            
            # Update the lost item with new AI data
            if result and 'error' not in result:
                lost_item.ai_suggested_category = result.get('suggested_category', '')
                lost_item.ai_confidence = result.get('confidence', 0.0)
                lost_item.ai_top_predictions = result.get('top_predictions', {})
                lost_item.save()
                
                serializer = self.get_serializer(lost_item)
                return Response({
                    'message': 'Image classified successfully',
                    'ai_results': result,
                    'item': serializer.data
                })
            else:
                return Response({'error': result.get('error', 'Classification failed')}, 
                              status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Image classification failed: {str(e)}")
            return Response({'error': 'Classification failed'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
###########################################################################################################################################################
#############################################################################################################################################################
class FoundItemViewSet(viewsets.ModelViewSet):
    serializer_class = FoundItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin':
            return FoundItem.objects.all()
        return FoundItem.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        category = request.query_params.get('category', '')
        
        queryset = self.get_queryset().filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(found_location__icontains=query)
        )
        
        if category:
            queryset = queryset.filter(category__name__iexact=category)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def potential_matches(self, request, pk=None):
        found_item = self.get_object()
        # Simple matching logic based on category and keywords
        lost_items = LostItem.objects.filter(
            category=found_item.category,
            status='lost'
        ).exclude(user=found_item.user)
        
        serializer = LostItemSerializer(lost_items, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def classify_image(self, request, pk=None):
        """Re-classify image using AI"""
        found_item = self.get_object()
        
        if not found_item.item_image:
            return Response({'error': 'No image available for classification'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = pytorch_ai_service.classify_image(found_item.item_image.path)
            
            # Update the found item with new AI data
            if result and 'error' not in result:
                found_item.ai_suggested_category = result.get('suggested_category', '')
                found_item.ai_confidence = result.get('confidence', 0.0)
                found_item.ai_top_predictions = result.get('top_predictions', {})
                found_item.save()
                
                serializer = self.get_serializer(found_item)
                return Response({
                    'message': 'Image classified successfully',
                    'ai_results': result,
                    'item': serializer.data
                })
            else:
                return Response({'error': result.get('error', 'Classification failed')}, 
                              status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Image classification failed: {str(e)}")
            return Response({'error': 'Classification failed'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
###########################################################################################################################################################
#############################################################################################################################################################
class ClaimViewSet(viewsets.ModelViewSet):
    serializer_class = ClaimSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin':
            return Claim.objects.all()
        return Claim.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve_claim(self, request, pk=None):
        claim = self.get_object()
        claim.status = 'approved'
        claim.admin_notes = request.data.get('admin_notes', '')
        claim.resolved_at = timezone.now()
        claim.save()
        
        # Update the found item status
        found_item = claim.found_item
        found_item.status = 'returned'
        found_item.save()
        
        # Create notification
        Notification.objects.create(
            user=claim.user,
            notification_type='claim_update',
            title='Claim Approved',
            message=f'Your claim for "{found_item.title}" has been approved.',
            claim=claim,
            found_item=found_item
        )
        
        return Response({'status': 'claim approved'})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject_claim(self, request, pk=None):
        claim = self.get_object()
        claim.status = 'rejected'
        claim.admin_notes = request.data.get('admin_notes', '')
        claim.resolved_at = timezone.now()
        claim.save()
        
        Notification.objects.create(
            user=claim.user,
            notification_type='claim_update',
            title='Claim Rejected',
            message=f'Your claim for "{claim.found_item.title}" has been rejected.',
            claim=claim,
            found_item=claim.found_item
        )
        return Response({'status': 'claim rejected'})
###########################################################################################################################################################
#############################################################################################################################################################
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'all notifications marked as read'})
###########################################################################################################################################################
#############################################################################################################################################################
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def classify_image(request):
    """Standalone image classification endpoint"""
    serializer = AIClassificationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        image_file = serializer.validated_data['image']
        item_type = serializer.validated_data['item_type']
        
        result = pytorch_ai_service.real_time_classify(image_file)
        
        if 'error' in result:
            return Response(
                {'error': result['error']}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        response_serializer = AIClassificationResponseSerializer(result)
        return Response(response_serializer.data)
    
    except Exception as e:
        logger.error(f"AI classification error: {str(e)}")
        return Response(
            {'error': 'Image classification failed'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
###########################################################################################################################################################
#############################################################################################################################################################
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def real_time_classify(request):
    """Real-time classification endpoint (similar to Streamlit app)"""
    serializer = RealTimeClassificationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        image_file = serializer.validated_data['image']
        result = pytorch_ai_service.real_time_classify(image_file)
        
        if 'error' in result:
            return Response(
                {'error': result['error']}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Format response similar to Streamlit output
        response_data = {
            'predictions': result['top_predictions']['predictions'],
            'processing_time': result['processing_time'],
            'model_version': result['model_version']
        }
        
        response_serializer = RealTimeClassificationResponseSerializer(response_data)
        return Response(response_serializer.data)
    
    except Exception as e:
        logger.error(f"Real-time classification error: {str(e)}")
        return Response(
            {'error': 'Real-time classification failed'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
###########################################################################################################################################################
#############################################################################################################################################################
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def ai_service_status(request):
    """Check AI service status"""
    status_info = {
        'model_loaded': pytorch_ai_service.model_loaded,
        'model_version': pytorch_ai_service.model_version,
        'classes_loaded': len(pytorch_ai_service.classes) > 0,
        'service_ready': pytorch_ai_service.model_loaded and len(pytorch_ai_service.classes) > 0
    }
    return Response(status_info)
###########################################################################################################################################################
#############################################################################################################################################################
def home(request):
    """
    View function for the home page of the Lost and Found Application.
    Fetches counts for the dashboard and handles any success messages.
    """

    
    # Example of adding a success message if an item was successfully added
    # You can uncomment and use this in other views (e.g., after adding a lost item)
    # messages.success(request, 'Item reported successfully!')

    context = {
        
    }
    
    # Render the HTML template index.html with the data in the context variable
    return render(request, 'home.html', context=context)