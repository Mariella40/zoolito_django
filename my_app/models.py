from django.db import models
from django.contrib.auth.models import User

ROLE_CHOICES = [
    ('user', 'Usuario'),
    ('guide', 'Guía'),
]

MILESTONE_CHOICES = [
    ('arrival_origin', 'Llegada al Origen'),
    ('pet_on_board', 'Mascota a Bordo'),
    ('delivered', 'Entrega Exitosa en Destino'),
]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Pet(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='pets',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=50, blank=True)
    breed = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ServiceRequest(models.Model):
    SERVICE_CHOICES = [
        ('traslado', 'Traslado'),
        ('paseo', 'Paseo'),
        ('veterinaria', 'Veterinaria'),
    ]

    SCHEDULE_TYPE = [
        ('immediate', 'Inmediato'),
        ('scheduled', 'Programado'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='service_requests',
        null=True,
        blank=True
    )

    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPE)
    scheduled_datetime = models.DateTimeField(blank=True, null=True)

    origin_text = models.CharField(max_length=300)
    origin_lat = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    origin_lng = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)

    dest_text = models.CharField(max_length=300)
    dest_lat = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    dest_lng = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)

    pet = models.ForeignKey(Pet, on_delete=models.SET_NULL, null=True, blank=True)
    quick_pet_name = models.CharField(max_length=100, blank=True)
    quick_pet_species = models.CharField(max_length=50, blank=True)
    quick_pet_notes = models.TextField(blank=True)

    observations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed = models.BooleanField(default=False)
    assigned_guide = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_requests')

    def __str__(self):
        return f"{self.user.username} - {self.get_service_type_display()} - {self.origin_text} -> {self.dest_text}"

class ServiceRequestMilestone(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='milestones')
    milestone = models.CharField(max_length=50, choices=MILESTONE_CHOICES)
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('request', 'milestone')  # cada hito registrado una vez
        ordering = ['recorded_at']

    def __str__(self):
        return f"{self.request.id} - {self.get_milestone_display()} @ {self.recorded_at}"
    
class ServiceRating(models.Model):
    request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name='rating')  # 1 rating por solicitud
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_ratings')           # quien califica (dueño)
    guide = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_ratings')       # a quién califican (guía)
    stars = models.PositiveSmallIntegerField()  # 1..5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # un usuario no puede calificar dos veces la misma request
        constraints = [
            models.CheckConstraint(check=models.Q(stars__gte=1, stars__lte=5), name='stars_between_1_and_5'),
        ]

    def __str__(self):
        return f"Rating {self.stars} for req {self.request_id} by {self.user_id}"