from django.db import models
from django.contrib.auth.models import User
from traction_app.models import Item


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField()
    tracked_items = models.ManyToManyField(Item)

    display_name = models.TextField()
    membership_type = models.TextField()
    membership_id = models.TextField()

    def __str__(self):
        return f'{self.user.username} profile'
