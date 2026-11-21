import uuid

import django
from django.db import models

django.setup()


class Author(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)


class BlogPost(models.Model):
    published_at = models.DateTimeField()
    title = models.CharField(max_length=128)
    content = models.TextField()

    authors = models.ManyToManyField(Author, related_name="blogposts")


class Comment(models.Model):
    content = models.TextField()

    author = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name="comments"
    )
    blogpost = models.ForeignKey(
        BlogPost, on_delete=models.CASCADE, related_name="comments"
    )


class Ticket(models.Model):
    """
    Has nullable fields, which the other models do not.
    """

    number = models.IntegerField()
    title = models.CharField(max_length=128, null=True)
    assignee = models.ForeignKey(
        Author, null=True, on_delete=models.SET_NULL, related_name="tickets"
    )

    class Meta:
        ordering = ["-number"]
