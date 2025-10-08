from django.db import models

from globalapp.models import Common
from ckeditor.fields import RichTextField
from django.utils.text import slugify
from solo.models import SingletonModel
# Create your models here.
class Button(Common):
    title = models.CharField(max_length=200)
    link = models.URLField()
    def __str__(self):
        return self.title
class BannerItem(Common):
    title = models.TextField(max_length=250,blank=True, null=True)
    image = models.ImageField(upload_to='banner_images/')
    mobile_image = models.ImageField(upload_to='banner_images/',blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    descriptions = RichTextField(blank=True, null=True)
    order = models.PositiveIntegerField()
    button = models.ManyToManyField(Button)

    def __str__(self):
        return f"Item {self.title}"
class Banner(Common):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    items = models.ManyToManyField('BannerItem', related_name='banners')

    def __str__(self):
        return self.title
    
class BannerLMS(Common):
    title = models.CharField(max_length=200)
    description = RichTextField()
    image = models.ImageField()

    def __str__(self):
        return self.title

class CounterItem(Common):
    title = models.CharField(max_length=100)
    number = models.IntegerField()
    icon = models.FileField(upload_to='icons/', blank=True, null=True)

    def __str__(self):
        return self.title
class Counter(SingletonModel):
    counter_item = models.ManyToManyField(CounterItem)

class FacilitiesItem(Common):
    icon = models.ImageField(upload_to="icons/")
    title = models.CharField(max_length=100)
    description = RichTextField(default=None)

    def __str__(self):
        return self.title
class Facilities(SingletonModel):
    facilities_item = models.ManyToManyField(FacilitiesItem)

class SpecialCta(SingletonModel):
    icon = models.ImageField(upload_to="icons/",default=None,null=True,blank=True)
    title = models.CharField(max_length=100,default=None,null=True,blank=True)
    description = RichTextField(default="none",null=True,blank=True)
    button_text = models.CharField(max_length=100,default=None,null=True,blank=True)
    button_url = models.URLField(default=None,null=True,blank=True)
    # def __str__(self):
    #     return self.title
class Page(Common):
    DRAFT = 'DRAFT'
    PUBLISHED = 'PUBLISHED'
    
    PUB_STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PUBLISHED, 'Published'),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = RichTextField()
    content = RichTextField()
    pub_status = models.CharField(max_length=10, choices=PUB_STATUS_CHOICES, default=DRAFT)
    image = models.ImageField(upload_to='images/')
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class FAQ(Common):
    question = models.CharField(max_length=100)
    icon = models.ImageField(null=True,blank=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    answer = RichTextField()

    def __str__(self):
        return self.question

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.question)
        super().save(*args, **kwargs)

class Testimonial(Common):
    author = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    content = RichTextField()
    rating = models.IntegerField()

    def __str__(self):
        return f"Testimonial by {self.author}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.author)
        super().save(*args, **kwargs)

class Blog(Common):
    DRAFT = 'DRAFT'
    PUBLISHED = 'PUBLISHED'
    
    PUB_STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PUBLISHED, 'Published'),
    ]

    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    content = RichTextField()
    pub_status = models.CharField(max_length=10, choices=PUB_STATUS_CHOICES, default=DRAFT)
    image = models.ImageField(upload_to='blog_images/')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

# class FrontMenu(Common):
#     TYPE_CHOICES = (
#     ('PAGE', 'PAGE'),
#     ('LINK', 'LINK'),
#         )
#     name = models.CharField(max_length=100)
#     content = models.TextField()
#     status = models.CharField(
#         max_length=1,
#         choices=TYPE_CHOICES,
#         default='PAGE',
#     )

