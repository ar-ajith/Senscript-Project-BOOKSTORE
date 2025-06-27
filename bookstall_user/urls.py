from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import*

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/user/', UserRegisterView.as_view(), name='user_register'),
    path('register/seller/', SellerRegisterView.as_view(), name='seller_register'),
    path('login/', UserLoginView.as_view(), name='user_login'),
    path('decode/',DecodeTokenView.as_view(),name='decode'),
    path('dashboard/',DashboardPageView.as_view(),name="dashboard"),
]
