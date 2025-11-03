from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from testprep.utils import generate_random_uuid


class HashModelMixin(models.Model):
    hash = models.CharField(max_length=36, unique=True)

    class Meta:
        abstract = True


class ActiveModelMixin(models.Model):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


@receiver(pre_save)
def handle_models_with_hash_pre_save(sender, instance=None, **kwargs):
    if not issubclass(sender, HashModelMixin):
        return

    if not instance.id:
        instance.hash = generate_random_uuid()
