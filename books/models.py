from django.db import models

# Create your models here.
# models.py
from django.utils.text import slugify
from globalapp.models import Common

class Author(models.Model):
    name = models.CharField(max_length=100)
    biography = models.TextField()

    def __str__(self):
        return self.name

class Book(Common):
    title = models.CharField(max_length=200)
    # author = models.ForeignKey(Author, on_delete=models.CASCADE,blank=True,null=True)
    publication_date = models.DateField()
    isbn = models.CharField(max_length=13)
    image = models.ImageField(upload_to="images/",null=True,blank=True)

    def __str__(self):
        return self.title
    
class Dummy(models.Model):
    route = models.CharField(max_length=20,default=None)
    content = models.TextField(default=None)
    slug = models.SlugField(max_length=20, unique=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            # Generate a slug from the route field
            self.slug = slugify(self.route[:20])  # Use the first 50 characters of the route
        super(Dummy, self).save(*args, **kwargs)
