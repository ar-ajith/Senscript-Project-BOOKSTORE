from django.shortcuts import render,redirect
from bookstall.models import CustomUser,Book,Category,Cart,CartItem,Author,Wishlist,Coupon,Userprofile,BookOrder,PAYMENT_METHOD_CHOICES,Rating,BookstoreReview,ShippingAddress
from django.views.generic import View,ListView,TemplateView,DetailView
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth import authenticate,login,logout
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import F,Q,Avg,Count
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse,HttpResponseForbidden
from django.shortcuts import get_object_or_404
import json
from decimal import Decimal
from bookstall.utils import EmailThread
import uuid
from django.contrib.auth import update_session_auth_hash
from django.http import Http404






# Create your views here.

class UserRegistrationView(View):
    def get(self,request):
        return render(request,'mybookstall/registration.html')
    
    def post(self,request):
        email=request.POST.get('email')
        first_name=request.POST.get('first_name')
        last_name=request.POST.get('last_name')
        password=request.POST.get('password')
        password2=request.POST.get('password2')

        try:
            validate_email(email)
            if CustomUser.objects.filter(email=email).exists():
                return render(request,'mybookstall/registration.html',{"error":"Email already exists"})
            if password != password2:
                return render(request,'mybookstall/registration.html',{"error":"Password do not match"})
            user=CustomUser.objects.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role='user'
            )
            user.set_password(password)
            user.save()

            messages.success(request, "User registered successfully. Please log in.")
            return redirect(reverse("user_login"))
        except ValidationError:
            return render(request,'mybookstall/registration.html', {"error":"Invalid Email Address"})
        except Exception as e:
            return render(request,'mybookstall/registration.html',{"error":f"Error:{str(e)}"})
        
class SellerRegistrationView(View):
    def get(self,request):
        return render(request,'mybookstall/registration.html')
    
    def post(self,request):
        email=request.POST.get('email')
        first_name=request.POST.get('first_name')
        last_name=request.POST.get('last_name')
        password=request.POST.get('password')
        password2=request.POST.get('password2')

        try:
            validate_email(email)
            if CustomUser.objects.filter(email=email).exists():
                return render(request,'mybookstall/registration.html',{"error":"Email already exists"})
            if password != password2:
                return render(request,'mybookstall/registration.html',{"error":"Password do not match"})
            user=CustomUser.objects.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role='seller'
            )
            user.set_password(password)
            user.save()

            messages.success(request, "User registered successfully. Please log in.")
            return redirect(reverse("login"))
        except ValidationError:
            return render(request,'mybookstall/registration.html', {"error":"Invalid Email Address"})
        except Exception as e:
            return render(request,'mybookstall/registration.html',{"error":f"Error:{str(e)}"})        
        
class UserLoginView(View):
    def get(self,request):
        return render(request,'mybookstall/login.html')
    
    def post(self,request):
        email=request.POST.get("email")
        password=request.POST.get("password")

        user=authenticate(request,email=email,password=password)
        if user is not None:
            login(request,user)
            if user.role == "user":
                messages.success(request,f"Welcome {user.first_name},login Successful")
                return redirect("user_dashboard")
            else:
                return redirect("/")
        else:
            if not CustomUser.objects.filter(email=email).exists():
                error_msg = "Email not registered!"
            else:
                error_msg = "Invalid email or password!"

            return render(request, 'mybookstall/login.html', {"error": error_msg}) 
        
class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('user_login') 


class UserDashboardView(View):
    def get(self, request):
        bookstore_reviews=BookstoreReview.objects.select_related('user').order_by('-created_at')[:5]
        bookstore_avg_rating=BookstoreReview.objects.aggregate(avg=Avg('rating'))['avg'] or 0
        if request.user.is_authenticated:
            wishlist_books = Wishlist.objects.filter(user=request.user).values_list('book_id', flat=True)
            user_wishlist_book_ids = list(wishlist_books)
            user_ratings = Rating.objects.filter(user=request.user).select_related('book').order_by('-created_at')
        else:
            user_wishlist_book_ids = []
            user_ratings = Rating.objects.none()
        user_count=CustomUser.objects.filter(role='user').count() 
        book_count=Book.objects.filter(status='approved').count()


        recent_cutoff = timezone.now() - timedelta(days=7)

        trending_books = Book.objects.filter(trending=True, status='approved').annotate(
            average_rating=Avg('ratings__rating')
        )

        new_books = Book.objects.filter(date_uploaded__gte=recent_cutoff, status='approved').annotate(
            average_rating=Avg('ratings__rating')
        ).order_by('-date_uploaded')

        authors = Author.objects.all()

        high_discount_books_qs = Book.objects.filter(
            status='approved',
            discounted_price__lt=F('price'),
            discounted_price__isnull=False
        ).order_by('-discount_percent')

        high_discount_books = list(high_discount_books_qs)
        min_items = 4
        if len(high_discount_books) < min_items and len(high_discount_books) > 0:
            times = (min_items // len(high_discount_books)) + 1
            high_discount_books = (high_discount_books * times)[:min_items]

        high_discount_books = Book.objects.filter(id__in=[b.id for b in high_discount_books]).annotate(
            average_rating=Avg('ratings__rating')
        )

        categories_by_type = {}
        for category_type in ['main', 'genre', 'language', 'binding']:
            categories = Category.objects.filter(type=category_type)
            categories_with_books = []
            for cat in categories:
                books = Book.objects.filter(
                    Q(main_category=cat) |
                    Q(genre=cat) |
                    Q(language=cat) |
                    Q(binding=cat),
                    status='approved'
                ).distinct().annotate(
                    average_rating=Avg('ratings__rating')
                )
                categories_with_books.append({'category': cat, 'books': books})
            categories_by_type[category_type] = categories_with_books

        return render(request, 'mybookstall/dashboard.html', {
            'books': trending_books,
            'new_books': new_books,
            'high_discount_books': high_discount_books,
            'categories_by_type': categories_by_type,
            'authors': authors,
            'authors_count': authors.count(),
            'user_wishlist_book_ids': user_wishlist_book_ids,
            'user_ratings': user_ratings,
            'bookstore_reviews':bookstore_reviews,
            'bookstore_avg_rating':bookstore_avg_rating,
            'user_count':user_count,
            'book_count':book_count,

        })

class CartAddView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        book_id = request.POST.get('book_id')
        if not book_id:
            return JsonResponse({'success': False, 'message': 'Missing book ID'}, status=400)

        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Book not found'}, status=404)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, book=book)

        if not created:
            if cart_item.quantity >= book.quantity:
                return JsonResponse({'success':False,'message':'Cannot add more. Stock limit reached.'})
            cart_item.quantity += 1
            cart_item.save()
        else:
            if book.quantity <1:
                return JsonResponse({'success':False,'message':'Book out of stock.'})    
            cart_item.quantity=1
            cart_item.save()

        cart_count = CartItem.objects.filter(cart=cart).count()

        return JsonResponse({'success': True, 'cart_count': cart_count})
    

class CartRemoveView(View):
    def get(self, request, item_id):
        user = request.user
        CartItem.objects.filter(id=item_id, cart__user=user).delete()

        coupon_data = request.session.get("coupon")
        if coupon_data:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_data["code"])
            except Coupon.DoesNotExist:
                request.session.pop("coupon", None)
                return redirect('cartview')

            cart_items = user.cart.items.all()
            total = sum(Decimal(item.book.discounted_price) * item.quantity for item in cart_items)

            discount = Decimal('0.00')
            if coupon.type == "percentage":
                discount = (Decimal(coupon.discount) / Decimal(100)) * total
            elif coupon.type == "Upto":
                discount = Decimal(coupon.discount)
                if discount > coupon.upto_amount:
                    discount = coupon.upto_amount

            discounted_total = total - discount

            request.session["coupon"].update({
                "discount": float(discount),
                "discounted_total": float(discounted_total),
            })
            request.session.modified = True

        return redirect('cartview')
    

    

class CartUpdateView(LoginRequiredMixin, View):
    def post(self, request):
        data = json.loads(request.body)
        book_id = data.get('book_id')
        quantity = int(data.get('quantity', 1))

        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Book not found'}, status=404)

        if quantity > book.quantity:
            return JsonResponse({'success': False, 'message': f'Only {book.quantity} in stock.'})

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, _ = CartItem.objects.get_or_create(cart=cart, book=book)
        cart_item.quantity = quantity
        cart_item.save()

        item_total = cart_item.quantity * book.discounted_price
        cart_items = cart.items.all()
        cart_total = sum(item.quantity * item.book.discounted_price for item in cart_items)

        coupon_code = request.session.get('applied_coupon')
        discount_amount = 0
        final_total = cart_total

        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                discount_amount = (coupon.discount / 100) * cart_total
                final_total = cart_total - discount_amount
            except Coupon.DoesNotExist:
                del request.session['applied_coupon']

        return JsonResponse({
            'success': True,
            'item_total': round(item_total, 2),
            'cart_total': round(cart_total, 2),
            'discount_amount': round(discount_amount, 2),
            'final_total': round(final_total, 2),
            'coupon_applied': bool(coupon_code)
        })


class CartView(LoginRequiredMixin,TemplateView):
    template_name = 'mybookstall/cart.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return render(request, '404.html', status=404)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        cart_items = CartItem.objects.filter(cart__user=user)
        for item in cart_items:
            item.total_price = item.book.discounted_price * item.quantity

        total = sum(item.total_price for item in cart_items)

        self.recalc_coupon(self.request)

        coupon_data = self.request.session.get("coupon")
        discounted_total = coupon_data.get("discounted_total", total) if coupon_data else total
        shipping_addresses = ShippingAddress.objects.filter(user=user)

        
        for address in shipping_addresses:
            try:
                shipping_pin = int(address.shipping_pincodes)
            except ValueError:
                address.is_deliverable = False
                continue

            is_deliverable = any(
                item.book.pincodes.filter(code=shipping_pin).exists() for item in cart_items
            )
            address.is_deliverable = is_deliverable
 

        context.update({
            'cart_items': cart_items,
            'total': total,
            'discounted_total': discounted_total,
            'coupon': coupon_data,
            'shipping_addresses': shipping_addresses,
        })
        return context

    def recalc_coupon(self, request):
        """Recalculate and update coupon based on current cart total"""
        coupon_data = request.session.get("coupon")
        if not coupon_data:
            return

        try:
            coupon = Coupon.objects.get(code__iexact=coupon_data["code"], is_active=True)
        except Coupon.DoesNotExist:
            request.session.pop("coupon", None)
            return

        cart_items = CartItem.objects.filter(cart__user=request.user)
        total = sum(Decimal(item.book.discounted_price) * item.quantity for item in cart_items)

        discount = Decimal('0.00')

        if coupon.type == "Percentage":
            discount = (Decimal(coupon.discount) / Decimal(100)) * total

        elif coupon.type == "Upto":
            if total >= coupon.upto_amount:
                discount = (Decimal(coupon.discount) / Decimal(100)) * total
            else:
                request.session.pop("coupon", None)
                return

        discounted_total = total - discount

        request.session["coupon"] = {
            "code": coupon.code,
            "discount": float(discount),
            "discounted_total": float(discounted_total),
            "message": f"Coupon '{coupon.code}' applied successfully. You saved ₹{discount:.2f}."
        }
        request.session.modified = True

    def post(self, request, *args, **kwargs):
        user = request.user

        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                book_id = int(data.get('book_id'))
                quantity = int(data.get('quantity'))

                item = CartItem.objects.get(cart__user=user, book_id=book_id)
                max_stock = item.book.quantity

                if quantity > max_stock:
                    quantity = max_stock
                    message = f"Only {max_stock} units available."
                elif quantity < 1:
                    quantity = 1
                    message = "Quantity cannot be less than 1."
                else:
                    message = ""

                item.quantity = quantity
                item.save()

                self.recalc_coupon(request)

                cart_items = CartItem.objects.filter(cart__user=user)
                cart_total = sum(ci.book.discounted_price * ci.quantity for ci in cart_items)
                item_total = item.book.discounted_price * item.quantity

                coupon_data = request.session.get("coupon")
                discounted_total = coupon_data.get("discounted_total", cart_total) if coupon_data else cart_total

                return JsonResponse({
                    'success': True,
                    'item_total': float(item_total),
                    'cart_total': float(cart_total),
                    'discounted_total': float(discounted_total),
                    'coupon': coupon_data,
                    'message': message
                })

            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})

        cart_items = CartItem.objects.filter(cart__user=user)
        error_messages = []

        for item in cart_items:
            key = f'quantity_{item.book.id}'
            if key in request.POST:
                try:
                    qty = int(request.POST[key])
                except ValueError:
                    qty = item.quantity

                max_stock = item.book.quantity
                if qty > max_stock:
                    error_messages.append(f"Only {max_stock} units available for {item.book.title}")
                    qty = max_stock
                elif qty < 1:
                    qty = 1

                item.quantity = qty
                item.save()

        self.recalc_coupon(request)

        for error in error_messages:
            messages.error(request, error)

        return redirect('cartview')
    


class SaveShippingAddressView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            address_id = data.get('address_id')
            address = ShippingAddress.objects.get(id=address_id, user=request.user)
            request.session['selected_shipping_address'] = address_id
            request.session.modified = True
            return JsonResponse({'success': True})
        except ShippingAddress.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Address not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class ShopView(ListView):
    model=Book
    template_name="mybookstall/shop.html"
    context_object_name='books'

    def get_queryset(self):
        queryset = Book.objects.filter(status='approved')

        price = self.request.GET.get('price')
        genre = self.request.GET.get('genre')
        language = self.request.GET.get('language')
        category = self.request.GET.get('main_category')
        binding = self.request.GET.get('binding')
        author=self.request.GET.get('author')

        if price:
            try:
                queryset = queryset.filter(discounted_price__lte=float(price))
            except ValueError:
                pass

        if genre:
            queryset = queryset.filter(genre_id=genre)

        if language:
            queryset = queryset.filter(language_id=language)

        if category:
            queryset = queryset.filter(main_category_id=category)

        if binding:
            queryset = queryset.filter(binding_id=binding)

        if author:    
            queryset = queryset.filter(author_id=author)

        return queryset

    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            wishlist_books = Wishlist.objects.filter(user=self.request.user).values_list('book_id', flat=True)
            context['user_wishlist_book_ids'] = list(wishlist_books)
        else:
            context['user_wishlist_book_ids'] = []
        context['genres']=Category.objects.filter(type='genre')
        context['languages']=Category.objects.filter(type='language')
        context['categories']=Category.objects.filter(type='main')
        context['bindings']=Category.objects.filter(type='binding')
        context['authors']=Author.objects.all()

        return context
    
class BookDetailView(DetailView):
    model=Book
    template_name='mybookstall/book_detail.html'
    context_object_name='book'


class AuthorBooksView(ListView):
    model=Book
    template_name='mybookstall/author_book.html'
    context_object_name='books'

    def get_queryset(self):
        return Book.objects.filter(author_id=self.kwargs['author_id'])
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            wishlist_books = Wishlist.objects.filter(user=self.request.user).values_list('book_id', flat=True)
            context['user_wishlist_book_ids'] = list(wishlist_books)
        else:
            context['user_wishlist_book_ids'] = []
        context['author']=Author.objects.get(id=self.kwargs['author_id'])
        return context


class WishlistView(LoginRequiredMixin, View):
    
    
    def post(self, request, *args, **kwargs):
        book_id = request.POST.get('book_id')
        if not book_id:
            return JsonResponse({'success': False, 'message': 'Missing book ID'})

        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Book not found'})

        wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, book=book)
        if not created:
            wishlist_item.delete()
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
            return JsonResponse({'success': True, 'in_wishlist': False, 'wishlist_count': wishlist_count})
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
        return JsonResponse({'success': True, 'in_wishlist': True, 'wishlist_count': wishlist_count})



class WishlistShowView(LoginRequiredMixin, ListView):
    model = Wishlist
    template_name = 'mybookstall/wishlist.html'
    context_object_name = 'wishlist_items'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return render(request, '404.html', status=404)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related('book')


class WishlistRemoveView(LoginRequiredMixin,View):
    def post(self,request,pk):
        wishist_item=get_object_or_404(Wishlist,pk=pk,user=request.user)
        wishist_item.delete()
        messages.success(request,'Book removed form wishlist')
        return redirect('wishlist_view')



class ApplyCouponView(View):
    def post(self, request, *args, **kwargs):
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                coupon_code = data.get("coupon_code", "").strip()
            else:
                coupon_code = request.POST.get("coupon_code", "").strip()

            if not coupon_code:
                return JsonResponse({
                    "success": False,
                    "message": "Please enter a coupon code."
                })

            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code, is_active=True)
            except Coupon.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "message": "Invalid or inactive coupon code."
                })

            cart_items = CartItem.objects.filter(cart__user=request.user)
            if not cart_items.exists():
                return JsonResponse({
                    "success": False,
                    "message": "Your cart is empty."
                })

            total = sum(Decimal(item.book.discounted_price) * item.quantity for item in cart_items)
            discount = Decimal('0.00')

            if coupon.type == "Percentage":
                discount = (Decimal(coupon.discount) / Decimal(100)) * total
            elif coupon.type == "Upto":
                if total >= coupon.upto_amount:
                    discount = (Decimal(coupon.discount) / Decimal(100)) * total
                else:
                    return JsonResponse({
                        "success": False,
                        "message": f"Coupon '{coupon.code}' is only valid for orders above ₹{coupon.upto_amount}."
                    })

            discounted_total = total - discount

            request.session["coupon_code"] = coupon.code
            request.session["coupon_discount"] = str(round(discount, 2))  # 

            return JsonResponse({
                "success": True,
                "message": f"Coupon '{coupon.code}' applied successfully. You saved ₹{discount:.2f}!",
                "discounted_total": float(discounted_total),
                "discount": float(discount)
            })

        except json.JSONDecodeError:
            return JsonResponse({
                "success": False,
                "message": "Invalid JSON data."
            })


class RemoveCouponView(View):
    def post(self, request, *args, **kwargs):
        if "coupon" in request.session:
            request.session.pop("coupon")
        return JsonResponse({"success": True, "message": "Coupon removed."})



class UserProfileView(TemplateView):
    template_name='mybookstall/profile.html'
    
    def get(self, request, *args, **kwargs):
        user=request.user
        profile,created=Userprofile.objects.get_or_create(user=user)
        shipping_details=ShippingAddress.objects.filter(user=user)
        context={
            "user":user,
            "profile":profile,
            "shipping_details":shipping_details,
        }
        return self.render_to_response(context)
    


class UserEditProfileView(View):
    def get(self, request):
        user=request.user
        profile,created=Userprofile.objects.get_or_create(user=user)
        context={
            "user":user,
            "profile":profile
        }
        return render(request, 'mybookstall/user_edit_profile.html', context)

    def post(self, request):
        user = request.user
        profile,created=Userprofile.objects.get_or_create(user=user)

        if request.method == "POST":
            if 'remove_image' in request.POST:
                profile.profile_image.delete(save=False)
                profile.profile_image = None
                profile.save()
                messages.success(request, "Profile image removed successfully.")
                return redirect('UserEditProfile') 

        
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')

        if "profile_image" in request.FILES:
            profile.profile_image = request.FILES["profile_image"]
           

        gender=request.POST.get('gender')        
        if email and email != user.email:
            if CustomUser.objects.filter(email=email).exclude(pk=user.pk).exists():
                messages.error(request, 'This email is already in use by another account.')
                return render(request, 'mybookstall/user_edit_profile.html', {'user': user})            
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        profile.gender=gender
        user.save()
        profile.save()

        
        EmailThread(
                subject='Profile Updated Successfully',
                message=f'Hello {user.first_name}, your profile has been updated successfully.',
                recipient_list=[user.email]
            ).start()

        messages.success(request, 'Profile updated successfully!')
        return redirect('user_profile')    
            
            
class UserShippingEditView(View):
    def get(self, request):
        user=request.user
        profile,created=Userprofile.objects.get_or_create(user=user)
        context={
            "user":user,
            "profile":profile
        }
        return render(request, 'mybookstall/user_edit_address.html', context)

    def post(self, request):
        user = request.user
        profile,created=Userprofile.objects.get_or_create(user=user)
        address = request.POST.get('address')
        country=request.POST.get('country')
        phone_number=request.POST.get('phone_number')

        
        if phone_number:
            if not phone_number.isdigit():
                messages.error(request, "Phone number must contain only digits.")
                return redirect("UserEditAddress")
            if len(phone_number) < 10 or len(phone_number) > 15:
                messages.error(request, "Phone number must be between 10 and 15 digits.")
                return redirect("UserEditAddress")
            if Userprofile.objects.exclude(id=user.id).filter(phone_number=phone_number).exists():
                messages.error(request, "This phone number is already in use.")
                return redirect("UserEditAddress")
            
        profile.address = address
        profile.country=country
        profile.phone_number=phone_number
        profile.save()

        
        EmailThread(
                subject='Profile Updated Successfully',
                message=f'Hello {user.first_name}, your Address has been updated successfully.',
                recipient_list=[user.email]
            ).start()

        messages.success(request, 'Address updated successfully!')
        return redirect('user_profile')


class CheckoutView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'mybookstall/checkout.html', {
            'payment_methods': PAYMENT_METHOD_CHOICES
        })

    def post(self, request, *args, **kwargs): 
        user = request.user
        profile = Userprofile.objects.get(user=user)
        cart_items = CartItem.objects.filter(cart__user=user)

        if not cart_items.exists():
            return JsonResponse({'success': False, 'message': 'Your cart is empty'})

        total_price = sum(item.book.discounted_price * item.quantity for item in cart_items)

        coupon_code = request.session.get("coupon", {}).get("code")
        coupon_discount = Decimal(request.session.get("coupon", {}).get("discount", 0.00))

        final_price = total_price - coupon_discount

        payment_method = request.POST.get('payment_method', 'cod')
        valid_methods = [choice[0] for choice in PAYMENT_METHOD_CHOICES]
        if payment_method not in valid_methods:
            return JsonResponse({'success': False, 'message': 'Invalid payment method.'})

        address_id = request.session.get("selected_shipping_address")
        if not address_id:
            return JsonResponse({'success': False, 'message': 'No shipping address selected.'})

        try:
            shipping_address = ShippingAddress.objects.get(id=address_id, user=user)
        except ShippingAddress.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invalid shipping address selected.'})

        order = BookOrder.objects.create(
            user=user,
            profile=profile,
            order_id=str(uuid.uuid4()).replace('-', '')[:12],
            payment_method=payment_method,
            is_paid=True,
            total_price=final_price,
            coupon_code=coupon_code,
            coupon_amount=coupon_discount,
            shipping_address=shipping_address  
        )

        for item in cart_items:
            book = item.book
            if book.quantity < item.quantity:
                return JsonResponse({
                    'success': False,
                    'message': f"Only {book.quantity} unit(s) available for {book.title}."
                })

            book.quantity -= item.quantity
            book.save()
            order.books.add(book)

        cart_items.delete()
        request.session.pop("coupon", None)
        request.session.pop("selected_shipping_address", None)

        user_name = user.first_name or user.email

        EmailThread(
            subject=f"Order Confirmation - {order.order_id}",
            message=f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #2d89ef;">Order Confirmation</h2>
                <p>Dear <strong>{user_name}</strong>,</p>
                <p>Thank you for your order! Here are your order details:</p>
                <table style="border-collapse: collapse; margin-top: 10px;">
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Order ID:</td>
                        <td style="padding: 8px;">{order.order_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Total Amount:</td>
                        <td style="padding: 8px;">${order.total_price}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Payment Method:</td>
                        <td style="padding: 8px;">{order.payment_method.title()}</td>
                    </tr>
                </table>
                <p>We will notify you once your order is shipped.</p>
                <p>Best regards,<br><strong>MyBookstall Team</strong></p>
            </body>
            </html>
            """,
            recipient_list=[user.email],
        ).start()

        return JsonResponse({
            'success': True,
            'order_id': order.order_id,
            'redirect_url': reverse('rate_order_books', args=[order.id])
        })
    

class TrackOrderView(View):
    def get(self,request,*args, **kwargs):
        return render(request,'mybookstall/track_order.html')    
    
    def post(self, request):
        order_id = request.POST.get("order_id")
        try:
            order = BookOrder.objects.get(order_id=order_id)
            return render(request, "mybookstall/track_order.html", {"order": order})
        except BookOrder.DoesNotExist:
            return render(request, "mybookstall/track_order.html", {"error": "Order not found"})
     

class PastOrdersView(ListView):
    model=BookOrder
    template_name='mybookstall/past_orders.html'
    context_object_name='orders'

    def get_queryset(self):
        return BookOrder.objects.filter(user=self.request.user).order_by('-order_date')
    


class AboutView(View):
    def get(self,request):
        return render(request,'mybookstall/about.html')
    

class ServicesView(View):
    def get(self,request):
        return render(request,'mybookstall/services.html')
    

class BlogView(View):
    def get(self,request):
        return render(request,'mybookstall/blog.html')
    

class ContactView(TemplateView):
    template_name='mybookstall/contact.html'

    def post(self,request,*args, **kwargs):
        name=request.POST.get('name')
        email=request.POST.get('email')
        message=request.POST.get('message')

        if name and email and message:
            EmailThread(
                subject=f"Contact Inquiry from {name}",
                message=message,
                recipient_list=['ar.ajithrajan@gmail.com'],
            ).start()
            messages.success(request,'Thank you for contacting us!')
        else:
            messages.error(request,'Please fill in all fields.')    

        return redirect('contact')    
    
    

class UserChangePasswordView(View):
    def get(self,request):
        return render(request,'mybookstall/user_password_change.html')
    
    def post(self,request):
        current_password=request.POST.get('current_password')
        new_password=request.POST.get('new_password')
        confirm_password=request.POST.get('confirm_password')

        if not request.user.check_password(current_password):
            messages.error(request,'Incorrect current password')
            return redirect('user_change_password')
        if new_password != confirm_password:
            messages.error(request,'New password do not match.')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user) 

        EmailThread(
            subject='Password Changed Successfully',
            message='Hello, your password was changed successfully.',
            recipient_list=[request.user.email]
        ).start()

        messages.success(request, 'Your password has been changed successfully.')
        return redirect('user_profile')


class OrderRatingView(LoginRequiredMixin, TemplateView):
    template_name = 'mybookstall/rate_books.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_id = self.kwargs['order_id']
        order = get_object_or_404(BookOrder, id=order_id, user=self.request.user)
        context['order'] = order
        context['books'] = order.books.all()
        return context

class SubmitOrderRatingsView(LoginRequiredMixin, View):
    def post(self, request, order_id):
        order = get_object_or_404(BookOrder, id=order_id, user=request.user)
        for book in order.books.all():
            rating_val = request.POST.get(f'rating_{book.id}')
            review_text = request.POST.get(f'review_{book.id}', '')

            if rating_val:
                Rating.objects.update_or_create(
                    user=request.user,
                    book=book,
                    defaults={
                        'rating': int(rating_val),
                        'review': review_text
                    }
                )

        messages.success(request, "Thank you for rating your books!")
        return redirect('user_profile')


class RatingListView(LoginRequiredMixin,ListView):
    template_name='mybookstall/my_ratings.html'
    model=Rating
    context_object_name='ratings'

    def get_queryset(self):
        user_id=self.kwargs.get('user_id')
        return Rating.objects.filter(user__id=user_id)
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['first_name']=CustomUser.objects.get(id=self.kwargs['user_id']).first_name
        return context
    
    
class BookstoreReviewView(View):
    def post(self,request):
        if not request.user.is_authenticated:
            messages.error(request,"Login requierd to submit review.")
            return redirect('user_login')
        rating=int(request.POST.get('rating'))
        comment=request.POST.get('comment')

        BookstoreReview.objects.create(
            user=request.user,
            rating=rating,
            comment=comment,
        )
        messages.success(request,"Than You For Your Fedeback")
        return redirect('user_dashboard')
    
class ShippingAddressCreateView(View):
    def get(self,request):
        return render(request,'mybookstall/shipping_address.html')
    
    def post(self,request):
        ShippingAddress.objects.create(
            user=request.user,
            shipping_addresses=request.POST.get('shipping_addresses'),
            city=request.POST.get('city'),
            district=request.POST.get('district'),
            shipping_pincodes=request.POST.get('shipping_pincodes'),
            shipping_phone_number=request.POST.get('shipping_phone_number'),
        )
        return redirect('user_profile')


class ShippingAddressEditView(View):
    def get(self, request):
        address_id = request.GET.get('id')
        address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)

        districts = [
            "Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha", "Kottayam", 
            "Idukki", "Ernakulam", "Thrissur", "Palakkad", "Malappuram", 
            "Kozhikode", "Wayanad", "Kannur", "Kasaragod"
        ]

        return render(request, 'mybookstall/edit_shipping_address.html', {
            'address': address,
            'districts': districts,
        })

    def post(self, request):
        address_id = request.GET.get('id')
        address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)

        address.shipping_addresses = request.POST.get('shipping_addresses')
        address.city = request.POST.get('city')
        address.district = request.POST.get('district')
        address.shipping_pincodes = request.POST.get('shipping_pincodes')
        address.shipping_phone_number = request.POST.get('shipping_phone_number')
        address.save()

        return redirect('user_profile')


class DeleteShippingAddressView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        address = get_object_or_404(ShippingAddress, id=pk, user=request.user)
        address.delete()
        messages.success(request, "Shipping address deleted successfully.")
        return redirect('user_profile')