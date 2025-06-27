from django.db import models
from django.contrib.auth.models import BaseUserManager,AbstractBaseUser,PermissionsMixin
from django.conf import settings
from django.urls import reverse
from decimal import Decimal
from django.utils import timezone


# Create your models here.

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("role", "user")
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        return self.create_user(email, password, **extra_fields)

    
class CustomUser(AbstractBaseUser,PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'admin'),
        ('user', 'user'),
        ('seller', 'seller'),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name']

    def __str__(self):
        return f"{self.first_name} ({self.email})"
    
    @property
    def manage_url(self):
        if self.role == 'seller':
            return reverse('seller_manage', kwargs={'pk': self.pk})
        return '#'
    

class Userprofile(models.Model):
    user=models.OneToOneField(CustomUser,on_delete=models.CASCADE)   
    country_choices=[
        ('India', 'India'),
        ('United States', 'United States'),
        ('United Kingdom', 'United Kingdom'),
        ('Australia', 'Australia'),
        ('Canada', 'Canada'),
    ]
    country=models.CharField(max_length=50,choices=country_choices,null=True,blank=True)
    gender=models.CharField(max_length=10,choices=[('Male','Male'),('Female','Female'),('Other','Other')],null=True,blank=True)
    phone_number=models.CharField(max_length=15)
    address = models.TextField(blank=True, null=True)
    profile_image=models.ImageField(upload_to='profile_images/',null=True,blank=True)

    def __str__(self):
        return f"Profile of {self.user.email}"
    


class Category(models.Model):
    CATEGORY_TYPE_CHOICES = [
        ('main', 'Main Category'),
        ('genre', 'Genre'),
        ('language', 'Language'),
        ('binding', 'Binding Type'),
    ]

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=CATEGORY_TYPE_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Pincode(models.Model):
    code=models.IntegerField(max_length=10,unique=True)

    def __str__(self):
        return str(self.code) 
    
class Author(models.Model):
    name=models.CharField(max_length=250)
    author_image=models.ImageField(upload_to='authors/',blank=True,null=True)

    def __str__(self):
        return self.name

class Publication(models.Model):
    name=models.CharField(max_length=250,blank=True,null=True)
    logo=models.ImageField(upload_to='publications/',blank=True,null=True)

    def __str__(self):
        return self.name  
    

class RejectedBook(models.Model):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author, on_delete=models.SET_NULL,null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='books/', blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.title
    

class Coupon(models.Model):
    TYPE_CHOICES = [
        ('Percentage', 'Percentage'),
        ('Upto', 'Upto')
    ]
    code=models.CharField(max_length=20,unique=True)
    discount=models.FloatField(help_text="Enter discount amount or percentage")
    upto_amount=models.DecimalField(max_digits=10,decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code





class Book(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author, on_delete=models.SET_NULL,null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.PositiveIntegerField(blank=True, null=True)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,default=0.0)
    trending = models.BooleanField(default=False) 
    publication=models.ForeignKey(Publication,on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField(default=1)

    image= models.ImageField(upload_to='books/', blank=True, null=True)

    main_category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='main_books'
    )
    genre = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='genre_books'
    )
    language = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='language_books'
    )
    binding = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='binding_books'
    )

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    message_to_seller = models.TextField(blank=True, null=True)
    pincodes=models.ManyToManyField(Pincode,related_name='books',blank=True)
    date_uploaded = models.DateTimeField(default=timezone.now)


    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.price and self.discount_percent:
            try:
                price = float(self.price)
                discount = float(self.discount_percent)
                self.discounted_price = price - (price * discount / 100)
            except ValueError:
                self.discounted_price = None  
        super().save(*args, **kwargs)

class ShippingAddress(models.Model):
    district_choices = [
    ("Thiruvananthapuram", "Thiruvananthapuram"),
    ("Kollam", "Kollam"),
    ("Pathanamthitta", "Pathanamthitta"),
    ("Alappuzha", "Alappuzha"),
    ("Kottayam", "Kottayam"),
    ("Idukki", "Idukki"),
    ("Ernakulam", "Ernakulam"),
    ("Thrissur", "Thrissur"),
    ("Palakkad", "Palakkad"),
    ("Malappuram", "Malappuram"),
    ("Kozhikode", "Kozhikode"),
    ("Wayanad", "Wayanad"),
    ("Kannur", "Kannur"),
    ("Kasaragod", "Kasaragod")
    ]
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='shipping_address')
    shipping_addresses=models.CharField(max_length=300)
    city=models.CharField(max_length=100)
    district=models.CharField(max_length=100,choices=district_choices,null=True,blank=True)
    shipping_pincodes=models.CharField(max_length=10)
    shipping_phone_number=models.CharField(max_length=15)
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.shipping_addresses}({self.shipping_pincodes})"


PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('upi', 'UPI'),
        ('bank_transfer', 'Bank Transfer'),
        ('cod','COD'),
    ]


class BookOrder(models.Model):
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('shipped', 'Shipped'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    profile=models.ForeignKey(Userprofile,on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(ShippingAddress, on_delete=models.SET_NULL, null=True, blank=True)
    order_id = models.CharField(max_length=20, unique=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES,default='code')
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    coupon_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal(0.00))
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    order_date = models.DateTimeField(default=timezone.now)
    books = models.ManyToManyField(Book)

    def __str__(self):
        return f"Order {self.order_id} {self.order_date}"

    def calculate_total(self):
        total = sum(book.price for book in self.books.all()) - self.coupon_amount
        return total


class Rating(models.Model):
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('book', 'user')
        
    def __str__(self):
        return f"{self.user.email} rated {self.book.title} ({self.rating} stars)"
    

class Cart(models.Model):
    user=models.OneToOneField(CustomUser,on_delete=models.CASCADE)
    created_at=models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart=models.ForeignKey(Cart,related_name='items',on_delete=models.CASCADE)
    book=models.ForeignKey('Book',on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField(default=1)

    class Meta:
        unique_together=('cart','book')   


class Wishlist(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='wishlist')
    book=models.ForeignKey('Book',on_delete=models.CASCADE)
    added_on=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together=('user','book')

    def __str__(self):
        return f"{self.user.email}-{self.book.title}"    

    

class BookstoreReview(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE)
    rating=models.IntegerField(choices=[(i,i) for i in range(1,6)])
    comment=models.TextField()
    created_at=models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.user.email}-{self.rating} Stars'



    