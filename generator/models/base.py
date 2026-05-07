import uuid
from django.db import models


class BaseModel(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class TrackableModel(BaseModel):
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class VersionedModel(TrackableModel):
    changed_at   = models.DateTimeField(null=True, blank=True)
    changed_by   = models.CharField(max_length=100, blank=True)
    changed_from = models.JSONField(null=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if self.pk:
            try:
                old = self.__class__.objects.get(pk=self.pk)
                self.changed_at   = timezone.now()
                self.changed_from = {
                    f.name: str(getattr(old, f.name))
                    for f in old._meta.fields
                    if f.name not in ("changed_from", "changed_at")
                }
            except self.__class__.DoesNotExist:
                pass
        super().save(*args, **kwargs)
