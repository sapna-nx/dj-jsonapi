
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


# forward/reverse relationship testing models
class Author(models.Model):
    name = models.CharField(max_length=100)


class Cover(models.Model):
    text = models.CharField(max_length=100)


class Tag(models.Model):
    text = models.CharField(max_length=100)


class Book(models.Model):
    author = models.ForeignKey(Author)
    cover = models.OneToOneField(Cover)
    tags = models.ManyToManyField(Tag)
    title = models.CharField(max_length=100)
