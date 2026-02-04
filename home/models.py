from django.db import models

class GarbageBin(models.Model):
    location = models.CharField(max_length=100)
    fill_level = models.IntegerField()
    last_collected = models.DateTimeField()
    overflow_risk = models.BooleanField(default=False)

    def __str__(self):
        return self.location
