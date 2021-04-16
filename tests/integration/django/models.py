import django
from django.db import models

django.setup()


class Author(models.Model):
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
