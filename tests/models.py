
from django.db import models


class Parent(models.Model):
    parent_field = models.CharField(max_length=100)


class Child(Parent):
    child_field = models.CharField(max_length=100)


class Proxy(Parent):
    class Meta:
        proxy = True


class Related(models.Model):
    parent = models.ForeignKey(Parent)
    related_field = models.CharField(max_length=100)


class OtherRelated(models.Model):
    related = models.ForeignKey(Related)
