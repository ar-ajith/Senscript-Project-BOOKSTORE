from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import logout
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from bookstall.models import CustomUser
from .serializers import SellerRegisterSerializer,UserRegisterSerializer,UserLoginSerializer

from django.shortcuts import render,redirect
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from django.views.generic import TemplateView
from django.http import JsonResponse



# User Registration View
class UserRegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['role'] = 'user'  


        try:
            validate_email(data.get("email", ""))
            if CustomUser.objects.filter(email=data["email"]).exists():
                return Response({"email": "Email is already registered."}, status=status.HTTP_400_BAD_REQUEST)

            if data.get("password") != data.get("password2"):
                return Response({"password": "Passwords didn't match."}, status=status.HTTP_400_BAD_REQUEST)

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            return Response({
                "status": "User Registered Successfully!",
            }, status=status.HTTP_201_CREATED)

        except DjangoValidationError:
            return Response({"email": "Enter a valid email address."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"password": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Something went wrong: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
# Seller Registration View
class SellerRegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = SellerRegisterSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['role'] = 'seller' 


        try:
            validate_email(data.get("email", ""))
            if CustomUser.objects.filter(email=data["email"]).exists():
                return Response({"email": "Email is already registered."}, status=status.HTTP_400_BAD_REQUEST)

            if data.get("password") != data.get("password2"):
                return Response({"password": "Passwords didn't match."}, status=status.HTTP_400_BAD_REQUEST)

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            return Response({
                "status": "Seller Registered Successfully!",
            }, status=status.HTTP_201_CREATED)

        except DjangoValidationError:
            return Response({"email": "Enter a valid email address."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"password": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Something went wrong: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# User Login View
class UserLoginView(APIView):
    def get(self, request):
        return render(request, "apitokenexmp.html")

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            token = serializer.get_token(user)
            return Response({
                "status": "Login Successful!",
                "token": token,
                "role":user.role, 
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DecodeTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        first_name=getattr(user,'first_name',None)
        role = getattr(user, 'role', None)
        email = getattr(user, 'email', None)

        if role:
            return Response({
                "role": role,
                "email": email,
                "first_name":first_name
            })
        return Response({"error": "Unknown role"}, status=403)
    
class DashboardPageView(TemplateView):
    template_name = "apidashboard.html"


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return JsonResponse({"message": "Logged out successfully"})