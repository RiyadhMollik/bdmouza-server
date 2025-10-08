from django.shortcuts import render

# Create your views here.
# views.py
from rest_framework import viewsets

from globalapp.views import BaseViews
from .models import Book, Author, Dummy
from .serializers import BookSerializer, AuthorSerializer, DummySerializer

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(BaseViews):
    model_name = Book
    methods = ["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    queryset = Book.objects.all()
    serializer_class = BookSerializer

class DummyViewSet(BaseViews):
    model_name = Dummy
    methods = ["list", "retrieve", "create", "update", "partial_update", "destroy", "soft_delete", "change_status", "restore_soft_deleted"]
    # queryset = Book.objects.all()
    serializer_class = DummySerializer