from django.urls import path
from .views import (
    PetListCreateView, PetDetailView,
    ServiceRequestListCreateView, ServiceRequestDetailView, RegisterView,
    GuideAvailableRequestsList, GuideAssignedRequestsList,
    AcceptRequestView, CreateMilestoneView, CurrentUserView,
    CreateServiceRatingView, PendingFeedbackList,
    GuidePublicProfileView, UserHistoryRequestsView
)

urlpatterns = [
    path('pets/', PetListCreateView.as_view(), name='pets'),
    path('pets/<int:pk>/', PetDetailView.as_view(), name='pet-detail'),
    path('requests/', ServiceRequestListCreateView.as_view(), name='requests'),
    path('requests/<int:pk>/', ServiceRequestDetailView.as_view(), name='request-detail'),
    path('register/', RegisterView.as_view(), name='register'),
    path('guide/available-requests/', GuideAvailableRequestsList.as_view(), name='guide-available'),
    path('guide/assigned-requests/', GuideAssignedRequestsList.as_view(), name='guide-assigned'),
    path('requests/<int:pk>/accept/', AcceptRequestView.as_view(), name='request-accept'),
    path('requests/<int:pk>/milestones/', CreateMilestoneView.as_view(), name='request-milestones'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('requests/<int:pk>/rating/', CreateServiceRatingView.as_view(), name='request-rating'),
    path('requests/pending-feedback/', PendingFeedbackList.as_view(), name='pending-feedback'),
    path('guides/<int:guide_id>/profile/', GuidePublicProfileView.as_view(), name='guide-profile'),
    path('history/requests/', UserHistoryRequestsView.as_view(), name='user-history-requests'),
]
