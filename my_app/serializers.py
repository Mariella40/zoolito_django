from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Pet, ServiceRequest, ServiceRequestMilestone, Profile, ServiceRating
from rest_framework_simplejwt.tokens import RefreshToken

class PetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = ['id', 'name', 'species', 'breed', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        user = self.context['request'].user
        return Pet.objects.create(owner=user, **validated_data)

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.species = validated_data.get('species', instance.species)
        instance.breed = validated_data.get('breed', instance.breed)
        instance.notes = validated_data.get('notes', instance.notes)
        instance.save()
        return instance

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=[('user','Usuario'),('guide','Guía')], default='user', write_only=True)

    class Meta:
        model = User
        fields = ('username','email','password','password2','first_name','last_name','role')

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden."})
        return data

    def create(self, validated_data):
        role = validated_data.pop('role', 'user')
        validated_data.pop('password2', None)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        # crear perfil y asignar rol
        # solución recomendada: crear o actualizar el profile si ya existe
        profile, created = Profile.objects.get_or_create(user=user, defaults={'role': role})
        if not created:
            # si ya existía, actualizamos el role en caso de que venga distinto
            profile.role = role
            profile.save()

        return user

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['role']

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']

class ServiceRequestMilestoneSerializer(serializers.ModelSerializer):
    recorded_by = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = ServiceRequestMilestone
        fields = ['id', 'milestone', 'recorded_at', 'recorded_by']
        read_only_fields = ['id', 'recorded_at', 'recorded_by']

class ServiceRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRating
        fields = ['id', 'stars', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']

class ServiceRequestSerializer(serializers.ModelSerializer):
    pet = serializers.PrimaryKeyRelatedField(queryset=Pet.objects.all(), required=False, allow_null=True)
    pet_detail = PetSerializer(source='pet', read_only=True)
    milestones = ServiceRequestMilestoneSerializer(many=True, read_only=True)
    rating = ServiceRatingSerializer(read_only=True)  # rating si existe

    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'service_type', 'schedule_type', 'scheduled_datetime',
            'origin_text', 'origin_lat', 'origin_lng',
            'dest_text', 'dest_lat', 'dest_lng',
            'pet', 'pet_detail',
            'quick_pet_name', 'quick_pet_species', 'quick_pet_notes',
            'observations', 'created_at', 'confirmed',
            'milestones', 'rating'
        ]
        read_only_fields = ['id', 'created_at', 'confirmed', 'milestones', 'rating']

    def validate(self, data):
        schedule_type = data.get('schedule_type', getattr(self.instance, 'schedule_type', None))
        scheduled_datetime = data.get('scheduled_datetime', getattr(self.instance, 'scheduled_datetime', None))
        if schedule_type == 'scheduled' and not scheduled_datetime:
            raise serializers.ValidationError("scheduled_datetime es requerido cuando schedule_type='scheduled'")
        if not data.get('origin_text') and not getattr(self.instance, 'origin_text', None):
            raise serializers.ValidationError("origin_text es requerido")
        if not data.get('dest_text') and not getattr(self.instance, 'dest_text', None):
            raise serializers.ValidationError("dest_text es requerido")
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        pet = validated_data.get('pet', None)
        if pet and pet.owner != user:
            raise serializers.ValidationError("Esta mascota no pertenece al usuario autenticado.")
        validated_data['user'] = user
        return ServiceRequest.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user = self.context['request'].user
        pet = validated_data.get('pet', instance.pet)
        if pet and pet.owner != user:
            raise serializers.ValidationError("La mascota seleccionada no pertenece al usuario autenticado.")
        for field in [
            'service_type','schedule_type','scheduled_datetime',
            'origin_text','origin_lat','origin_lng',
            'dest_text','dest_lat','dest_lng',
            'pet','quick_pet_name','quick_pet_species','quick_pet_notes',
            'observations'
        ]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        return instance

class GuidePublicProfileSerializer(serializers.Serializer):
    guide_id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    rating_avg = serializers.FloatField()
    rating_count = serializers.IntegerField()