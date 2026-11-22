from django.db import models

class Kos(models.Model):
    nama = models.CharField(max_length=100)
    jarak_km = models.FloatField()
    harga = models.IntegerField()
    ac = models.CharField(max_length=10)
    rating = models.FloatField()

    def __str__(self):
        return self.nama
