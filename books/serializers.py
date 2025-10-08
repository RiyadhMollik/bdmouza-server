
# serializers.py
from rest_framework import serializers
from .models import Book, Author, Dummy

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = '__all__'

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'
class DummySerializer(serializers.ModelSerializer):
    class Meta:
        model = Dummy
        fields = '__all__'
