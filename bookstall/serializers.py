from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser,Book

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'address', 'password']
        extra_kwargs = {'password': {'write_only': True}} 

    def validate_email(self, value):
        """Check if the email is already registered."""
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def create(self, validated_data):
        """Automatically assigns role based on request data and hashes password."""
        request = self.context.get('request')  
        role = request.data.get('role', 'user') if request else 'user'  
        validated_data['role'] = role  
        validated_data['password'] = make_password(validated_data['password'])  
        user = CustomUser.objects.create(**validated_data)  
        return user
    
class LoginUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True) 

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'
        read_only_fields = ['seller', 'status', 'rejection_reason']

    def validate(self, data):
        user = self.context['request'].user
        title = data.get('title')

        if Book.objects.filter(title=title, seller=user).exists():
            raise serializers.ValidationError("You already uploaded a book with this name.")
        return data 
    

class SellerSerializer(serializers.ModelSerializer):
    approved_books=serializers.SerializerMethodField()
    pending_books=serializers.SerializerMethodField()
    manage=serializers.SerializerMethodField()
     
    class Meta:
        model=CustomUser
        fields=['id','email','first_name','last_name','pending_books','approved_books','manage'] 
    def get_approved_books(self,obj):
        return Book.objects.filter(seller=obj,status='approved').count()
    def get_pending_books(self,obj):
        return Book.objects.filter(seller=obj,status='pending').count() 
    def get_manage(self,obj):
        return f"/seller/{obj.id}/" 
    
class SellerDetailSerializer(serializers.ModelSerializer):
        books=BookSerializer(many=True,source='book_set')

        class Meta:
            model= CustomUser
            fields=[]
       


