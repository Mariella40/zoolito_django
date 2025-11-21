from rest_framework import generics, permissions, status
from .models import Pet, ServiceRequest
from .serializers import PetSerializer, ServiceRequestSerializer
from rest_framework.response import Response
from .serializers import RegisterSerializer, get_tokens_for_user
from rest_framework.views import APIView
from .models import ServiceRequest, ServiceRequestMilestone, Profile, MILESTONE_CHOICES, ServiceRating
from .serializers import ServiceRequestSerializer, ServiceRequestMilestoneSerializer, UserSerializer, GuidePublicProfileSerializer, ServiceRatingSerializer
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count
from django.contrib.auth.models import User



class PetListCreateView(generics.ListCreateAPIView):
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)


class PetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # aseguramos que solo el owner acceda/elimine su mascota
        return Pet.objects.filter(owner=self.request.user)


class ServiceRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ServiceRequest.objects.filter(user=self.request.user)


class ServiceRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ServiceRequest.objects.filter(user=self.request.user)

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = []  # AllowAny implicitly; si quieres explícito: [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        data = {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "tokens": tokens
        }
        return Response(data, status=status.HTTP_201_CREATED)
    
class IsGuide(permissions.BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, 'profile') and request.user.profile.role == 'guide'

class GuideAvailableRequestsList(APIView):
    permission_classes = [permissions.IsAuthenticated, IsGuide]
    """
    Listado de solicitudes activas que no están asignadas (o podrías listar asignadas al guía)
    """
    def get(self, request):
        qs = ServiceRequest.objects.filter(assigned_guide__isnull=True).order_by('created_at')
        serializer = ServiceRequestSerializer(qs, many=True)
        return Response(serializer.data)

class GuideAssignedRequestsList(APIView):
    permission_classes = [permissions.IsAuthenticated, IsGuide]
    def get(self, request):
        qs = ServiceRequest.objects.filter(assigned_guide=request.user).order_by('-created_at')
        serializer = ServiceRequestSerializer(qs, many=True)
        return Response(serializer.data)

class AcceptRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsGuide]

    def post(self, request, pk):
        sr = get_object_or_404(ServiceRequest, pk=pk)
        if sr.assigned_guide is not None:
            return Response({"detail":"Ya asignada"}, status=status.HTTP_400_BAD_REQUEST)
        sr.assigned_guide = request.user
        sr.save()
        return Response({"detail":"Asignada", "request_id": sr.id})

class CreateMilestoneView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsGuide]

    def post(self, request, pk):
        sr = get_object_or_404(ServiceRequest, pk=pk)
        if sr.assigned_guide != request.user:
            return Response({"detail":"No autorizado. Sólo el guía asignado puede registrar hitos."}, status=status.HTTP_403_FORBIDDEN)

        milestone = request.data.get('milestone')
        valid_milestones = [m[0] for m in MILESTONE_CHOICES]
        if milestone not in valid_milestones:
            return Response({"detail":"Hito inválido."}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar secuencia: permitir solo si el anterior hito ya existe (a excepción del primero)
        order = valid_milestones
        idx = order.index(milestone)
        if idx > 0:
            prev = order[idx-1]
            if not sr.milestones.filter(milestone=prev).exists():
                return Response({"detail":f"Debe registrar primero el hito previo: {prev}"}, status=status.HTTP_400_BAD_REQUEST)

        # Evitar duplicados
        if sr.milestones.filter(milestone=milestone).exists():
            return Response({"detail":"Hito ya registrado"}, status=status.HTTP_400_BAD_REQUEST)

        m = ServiceRequestMilestone.objects.create(request=sr, milestone=milestone, recorded_by=request.user)
        serializer = ServiceRequestMilestoneSerializer(m)
        # opcional: cambiar estado en ServiceRequest (ej. confirmed o similar) si milestone == delivered
        if milestone == 'delivered':
            sr.confirmed = True
            sr.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return getattr(obj, 'user_id', None) == request.user.id

def _is_delivered(sr: ServiceRequest) -> bool:
    if sr.confirmed:
        return True
    return sr.milestones.filter(milestone='delivered').exists()

class CreateServiceRatingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        sr = get_object_or_404(ServiceRequest, pk=pk)
        if sr.user_id != request.user.id:
            return Response({"detail": "No autorizado"}, status=403)
        if not _is_delivered(sr):
            return Response({"detail": "La solicitud aún no está finalizada"}, status=400)
        if hasattr(sr, 'rating'):
            return Response({"detail": "Esta solicitud ya está calificada"}, status=400)
        if not sr.assigned_guide_id:
            return Response({"detail": "La solicitud no tiene guía asignado"}, status=400)

        stars = int(request.data.get('stars', 0))
        comment = request.data.get('comment', '')
        if stars < 1 or stars > 5:
            return Response({"detail":"stars debe estar entre 1 y 5"}, status=400)

        rating = ServiceRating.objects.create(
            request=sr,
            user=request.user,
            guide=sr.assigned_guide,
            stars=stars,
            comment=comment
        )
        return Response(ServiceRatingSerializer(rating).data, status=201)

class PendingFeedbackList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = ServiceRequest.objects.filter(user=request.user)\
            .filter(assigned_guide__isnull=False)\
            .filter(confirmed=True) \
            .filter(rating__isnull=True)

        # Si usas “delivered” en milestones, puedes ampliar:
        # qs = ServiceRequest.objects.filter(user=request.user, assigned_guide__isnull=False).filter(
        #    Q(confirmed=True) | Q(milestones__milestone='delivered')
        # ).distinct().filter(rating__isnull=True)

        serializer = ServiceRequestSerializer(qs, many=True)
        return Response(serializer.data)
    
class GuidePublicProfileView(APIView):
    permission_classes = [permissions.AllowAny]  # o IsAuthenticated si prefieres

    def get(self, request, guide_id):
        guide = get_object_or_404(User, pk=guide_id)
        agg = ServiceRating.objects.filter(guide=guide).aggregate(
            rating_avg=Avg('stars'),
            rating_count=Count('id')
        )
        data = {
            "guide_id": guide.id,
            "username": guide.username,
            "full_name": f"{guide.first_name} {guide.last_name}".strip(),
            "rating_avg": agg['rating_avg'] or 0.0,
            "rating_count": agg['rating_count'] or 0,
        }
        return Response(GuidePublicProfileSerializer(data).data)
    
class UserHistoryRequestsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = ServiceRequest.objects.filter(user=request.user).order_by('-created_at')
        serializer = ServiceRequestSerializer(qs, many=True)
        return Response(serializer.data)