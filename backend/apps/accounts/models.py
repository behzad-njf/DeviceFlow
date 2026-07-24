import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .email_utils import normalize_email_identity
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    locale = models.CharField(max_length=10, default="en")
    theme = models.CharField(max_length=10, default="system")
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email

    def clean(self):
        super().clean()
        if self.email:
            self.email = normalize_email_identity(self.email)

    def save(self, *args, **kwargs):
        if self.email:
            self.email = normalize_email_identity(self.email)
        super().save(*args, **kwargs)
