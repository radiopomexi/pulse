from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, Role, TrainerProfile

@receiver(post_save, sender=CustomUser)
def ensure_trainer_profile(sender, instance: CustomUser, created, **kwargs):
    if instance.role != Role.TRAINER:
        return
    TrainerProfile.objects.get_or_create(user=instance)
