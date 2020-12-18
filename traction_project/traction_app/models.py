from django.db import models


class Item(models.Model):
    name = models.TextField()
    hash = models.TextField()

    @classmethod
    def create(cls, name, hash):
        item = cls(name=name, hash=hash)

        item.save()

    def __str__(self):
        return self.name
