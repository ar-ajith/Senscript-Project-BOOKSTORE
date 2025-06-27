from django.contrib.auth import authenticate,login,logout
from .serializers import SellerSerializer
from .models import CustomUser,Book,Category,Pincode,RejectedBook,Userprofile,Coupon,BookOrder,Rating,Author,Publication
from django.shortcuts import render,redirect,get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from decimal import Decimal
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.views.generic import UpdateView,ListView,TemplateView,DetailView,CreateView
from django.urls import reverse_lazy,reverse
from .utils import EmailThread
from django.db.models import Q
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.db.models import Sum,Count
from django.db.models.functions import TruncMonth
import calendar




token_generator = PasswordResetTokenGenerator()



class LoginView(APIView):
    def get(self, request):
        return render(request, "login.html")

    def post(self, request):
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            if user.is_superuser:
                messages.success(request, f"Welcome {user.first_name}, login successful")
                return redirect("admindashboard")
            elif user.role == "seller":
                messages.success(request, f"Welcome {user.first_name}, login successful")
                return redirect("admindashboard")
            else:
                return redirect("/")
        else:
            return render(request, "login.html", {"error": "Invalid email or password."})
        

        
@method_decorator(login_required, name='dispatch')
class MemberProfileView(TemplateView):
    template_name="profile.html"
    def get(self,request,*args, **kwargs):
        user=request.user
        profile,created=Userprofile.objects.get_or_create(user=user)
        context={
            "user":user,
            "profile":profile,
        }
        return render(request,self.template_name,context)

@method_decorator(login_required, name='dispatch')
class ChangePasswordView(View):
    def get(self, request):
        return render(request, 'change_password.html')

    def post(self, request):        
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(current_password):
            messages.error(request, 'Incorrect current password.')
            return redirect('change_password')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('change_password')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user) 
        

        EmailThread(
            subject='Password Changed Successfully',
            message='Hello, your password was changed successfully.',
            recipient_list=[request.user.email]
        ).start()

        messages.success(request, 'Your password has been changed successfully.')
        return redirect('profile')


@method_decorator(login_required, name='dispatch')
class EditProfileView(View):
    def get(self, request):
        user=request.user
        profile,created=Userprofile.objects.get_or_create(user=user)
        context={
            "user":user,
            "profile":profile
        }
        return render(request, 'edit_profile.html', context)

    def post(self, request):
        user = request.user
        profile,created=Userprofile.objects.get_or_create(user=user)

        if request.method == "POST":
            if 'remove_image' in request.POST:
                profile.profile_image.delete(save=False)
                profile.profile_image = None
                profile.save()
                messages.success(request, "Profile image removed successfully.")
                return redirect('edit_profile') 

        
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        address = request.POST.get('address')

        if "profile_image" in request.FILES:
            profile.profile_image = request.FILES["profile_image"]
           

        gender=request.POST.get('gender')
        country=request.POST.get('country')
        phone_number=request.POST.get('phone_number')

        
        if email and email != user.email:
            if CustomUser.objects.filter(email=email).exclude(pk=user.pk).exists():
                messages.error(request, 'This email is already in use by another account.')
                return render(request, 'edit_profile.html', {'user': user})
        if phone_number:
            if not phone_number.isdigit():
                messages.error(request, "Phone number must contain only digits.")
                return redirect("edit_profile")
            if len(phone_number) < 10 or len(phone_number) > 15:
                messages.error(request, "Phone number must be between 10 and 15 digits.")
                return redirect("edit_profile")
            if Userprofile.objects.exclude(id=user.id).filter(phone_number=phone_number).exists():
                messages.error(request, "This phone number is already in use.")
                return redirect("edit_profile")
            
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        profile.address = address
        profile.gender=gender
        profile.country=country
        profile.phone_number=phone_number
        user.save()
        profile.save()

        
        EmailThread(
                subject='Profile Updated Successfully',
                message=f'Hello {user.first_name}, your profile has been updated successfully.',
                recipient_list=[user.email]
            ).start()

        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    

class AdminDashboardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        total_members = CustomUser.objects.filter(is_superuser=False, is_staff=False).count()
        total_books = Book.objects.count()
        total_sellers = CustomUser.objects.filter(role='seller').count()
        sellers = CustomUser.objects.filter(role='seller')
        seller_list = SellerSerializer(sellers, many=True).data
        total_orders = BookOrder.objects.count()
        total_amount = BookOrder.objects.aggregate(total=Sum('total_price'))['total'] or 0


        monthly_sales = (
            BookOrder.objects
            .filter(is_paid=True)
            .annotate(month=TruncMonth('order_date'))
            .values('month')
            .annotate(total=Sum('total_price'))
            .order_by('month')
        )

        monthly_orders = (
            BookOrder.objects
            .annotate(month=TruncMonth('order_date'))
            .values('month')
            .annotate(order_count=Count('id'))
            .order_by('month')
        )

        revenue_dict = {entry['month'].month: entry['total'] for entry in monthly_sales}
        orders_dict = {entry['month'].month: entry['order_count'] for entry in monthly_orders}

        month_labels = [calendar.month_name[i] for i in range(1, 13)]
        chart_data_revenue = [revenue_dict.get(i, 0) for i in range(1, 13)]
        chart_data_orders = [orders_dict.get(i, 0) for i in range(1, 13)]

        def round_up(value, base):
            return base * ((value + base - 1) // base) if value > 0 else base

        max_revenue = max(chart_data_revenue) if chart_data_revenue else 0
        max_orders = max(chart_data_orders) if chart_data_orders else 0

        max_revenue_y = round_up(max_revenue, 500)
        max_orders_y = round_up(max_orders, 1)

        context = {
            "total_members": total_members,
            "total_books": total_books,
            "total_sellers": total_sellers,
            "sellers": seller_list,
            "total_orders": total_orders,
            "total_amount": total_amount,
            "chart_labels": month_labels,
            "chart_data_revenue": chart_data_revenue,
            "chart_data_orders": chart_data_orders,
            "max_revenue_y": max_revenue_y,
            "max_orders_y": max_orders_y,
        }
        return render(request, "dashboard.html", context)


    

class SellerListView(View): 
    def get(self, request):
        sellers = CustomUser.objects.filter(role='seller')
        serializer = SellerSerializer(sellers, many=True)
        return render(request, 'sellers_list.html', {'sellers': serializer.data})
    

@method_decorator(staff_member_required, name='dispatch')
class SellerManageView(View):
    def get(self, request, seller_id):
        seller = get_object_or_404(CustomUser, id=seller_id)
        books = Book.objects.filter(seller=seller)

        try:
            profile = seller.userprofile
        except Userprofile.DoesNotExist:
            profile = None

        context = {
            'seller': seller,
            'books': books,
            'profile': profile,
        }

        return render(request, 'seller_manage.html', context)

    

class UserListView(ListView):
    model = CustomUser
    template_name = 'user_list.html'  
    context_object_name = 'users'
    paginate_by = 10 

    def get_queryset(self):
        return CustomUser.objects.filter(role='user').order_by('-created_at')   
    

class CategoryManageView(View):
    def get(self, request):
        categories = Category.objects.all().order_by('type', 'name')
        return render(request, 'category_manage.html', {'categories': categories})

    def post(self, request):
        name = request.POST.get('name')
        category_type = request.POST.get('type')

        if name and category_type:
            Category.objects.get_or_create(name=name, type=category_type)

        return redirect('create_categories')


class CategoryBooksCombinedView(View):
    def get(self, request):
        books = Book.objects.filter(
        Q(status='approved') | Q(seller__is_staff=True) | Q(seller__is_superuser=True)
        ).distinct()

        main_category = request.GET.get('main_category')
        genre = request.GET.get('genre')
        language = request.GET.get('language')
        binding = request.GET.get('binding')
        max_price=request.GET.get('price')

        if main_category:
            books = books.filter(main_category__id=main_category)
        if genre:
            books = books.filter(genre__id=genre)
        if language:
            books = books.filter(language__id=language)
        if binding:
            books = books.filter(binding__id=binding)

        if max_price:
            try:
                price_value = float(max_price)
                books = books.filter(price__lte=price_value)
            except ValueError:
                pass     


        context = {
            'books': books,
            'main_categories': Category.objects.filter(type='main'),
            'genre_categories': Category.objects.filter(type='genre'),
            'language_categories': Category.objects.filter(type='language'),
            'binding_categories': Category.objects.filter(type='binding'),
        }

        return render(request, 'category_combined.html', context)


class BookUploadView(View):
    def get(self, request):
        if request.user.role in ['seller'] or request.user.is_staff or request.user.is_superuser:
            return render(request, 'book_upload.html', self._get_context())
        raise PermissionDenied("Only sellers or admins can upload books.")

    def post(self, request):
        title = request.POST.get('title')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        quantity=request.POST.get('quantity')

        try:
            price = float(request.POST.get('price', 0))
        except (ValueError, TypeError):
            messages.error(request, "Price must be a valid number.")
            return self._render_with_error(request)

        try:
            discount_percent = float(request.POST.get('discount_percent', 0))
        except (ValueError, TypeError):
            discount_percent = 0 

        main_category = self._get_or_create_category(request, 'main_category', 'main')
        genre = self._get_or_create_category(request, 'genre', 'genre')
        language = self._get_or_create_category(request, 'language', 'language')
        binding = self._get_or_create_category(request, 'binding', 'binding')
        author=self._get_or_create_author(request)
        publication=self._get_or_create_publication(request)

        if not all([title, author,publication,description, price, main_category]):
            messages.error(request, "All required fields must be filled.")
            return self._render_with_error(request)

        status = 'approved' if request.user.is_staff or request.user.is_superuser else 'pending'

        book = Book.objects.create(
            title=title,
            author=author,
            publication=publication,
            description=description,
            price=price,
            discount_percent=discount_percent,
            image=image,
            main_category=main_category,
            genre=genre,
            language=language,
            binding=binding,
            seller=request.user,
            status=status,
            quantity=quantity,
        )
        
        pincodes_ids = request.POST.getlist('pincode')
        if pincodes_ids:
            book.pincodes.set(pincodes_ids)
        
        book.save()

        messages.success(request, "Book uploaded successfully.")
        return redirect('book_list')

    def _get_or_create_category(self, request, field_name, category_type):
        selected_id = request.POST.get(field_name)
        if selected_id == 'other':
            custom_name = request.POST.get(f"{field_name}_name")
            if custom_name:
                return Category.objects.get_or_create(name=custom_name, type=category_type)[0]
            return None
        return Category.objects.filter(id=selected_id).first()
    
    def _get_or_create_author(self,request):
        selected_id=request.POST.get('author')
        if selected_id=='other':
            name=request.POST.get('new_author')
            if name:
                return Author.objects.get_or_create(name=name)[0]
            return None
        return Author.objects.filter(id=selected_id).first()
    
    def _get_or_create_publication(self,request):
        selected_id=request.POST.get('publications')
        if selected_id=='other':
            name=request.POST.get('new_publication')
            if  name:
                return Publication.objects.get_or_create(name=name)[0]
            return None
        return Publication.objects.filter(id=selected_id).first()

    def _get_context(self):
        return {
            'main_categories': Category.objects.filter(type='main'),
            'genre_categories': Category.objects.filter(type='genre'),
            'language_categories': Category.objects.filter(type='language'),
            'binding_categories': Category.objects.filter(type='binding'),
            'authors':Author.objects.all(),
            'publications':Publication.objects.all(),
            'pincodes': Pincode.objects.all(),
        }

    def _render_with_error(self, request):
        context = self._get_context()
        return render(request, 'book_upload.html', context)


class BookListView(ListView):
    model = Book
    template_name = 'book_list.html'
    context_object_name = 'books'

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Book.objects.all()
        else:
            return Book.objects.filter(seller=user)    


class UpdateBookView(UpdateView):
    model = Book
    fields = ['title', 'author', 'description','quantity', 'price', 'discounted_price', 'main_category', 'genre', 'language', 'binding', 'image']
    template_name = 'book_update.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pincodes'] = Pincode.objects.all()
        context['selected_pincodes'] = self.object.pincodes.values_list('id', flat=True)
        return context

    def form_valid(self, form):
        book = form.save(commit=False)
        user = self.request.user

        if book.price and book.discounted_price and book.price > 0:
            discount = ((book.price - book.discounted_price) / book.price) * 100
            book.discount_percent = round(discount)
        else:
            book.discount_percent = 0

        if user.role == 'admin':
            pass
        elif book.seller == user:
            book.status = 'pending'
        else:
            return redirect('no_permission')

        book.trending = 'trending' in self.request.POST
        book.save()

        selected_pincodes = self.request.POST.getlist('pincodes')
        book.pincodes.set(selected_pincodes)

        messages.success(self.request, "Book updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('book_list')

    def dispatch(self, request, *args, **kwargs):
        book = self.get_object()
        user = request.user

        if user.role == 'admin' or user.is_staff or book.seller == user:
            return super().dispatch(request, *args, **kwargs)
        else:
            return redirect('no_permission')

        

class PincodeManageView(View):
    def get(self, request):
        pincodes = Pincode.objects.all()
        return render(request, 'pincode_manage.html', {'pincodes': pincodes})

    def post(self, request):
        code = request.POST.get('code')
        try:
            code = int(code)
            Pincode.objects.get_or_create(code=code)
            messages.success(request, f"Pincode {code} added successfully.")
        except ValueError:
            messages.error(request, "Please enter a valid pincode.")
        return redirect('pincode_manage')
    


class AssignBookToPincodeView(View):
    template_name = 'assign_book_pincode.html'

    def get(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        pincodes = Pincode.objects.all()
        return render(request, self.template_name, {'book': book, 'pincodes': pincodes})

    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        selected_pincode_ids = request.POST.getlist('pincodes')  
        book.pincode.set(selected_pincode_ids)
        return redirect('assign_book_list')
    

class BooksByPincodeView(View):
    def get(self, request, pincode_id):
        pincode = get_object_or_404(Pincode, id=pincode_id)

        books = Book.objects.filter(
            pincodes__id=pincode_id, 
            status='approved'  
        ).select_related('main_category', 'genre', 'language', 'binding', 'seller')

        context = {
            'pincode': pincode,
            'books': books
        }
        return render(request, 'books_by_pincode.html', context)
    

class AuthorView(View):
    template_name='author.html'

    def get(self,request):
        authors=Author.objects.all()
        return  render(request,self.template_name,{'authors':authors})
    
    def post(self,request):
         name=request.POST.get('name')
         author_image=request.FILES.get('author_image')

         if name:
             author=Author(name=name)
             if author_image:
                 author.author_image=author_image
             author.save()   

         return redirect('author')     

class PublicationView(View):
    template_name='publication.html'    

    def get(self,request):
        publication=Publication.objects.all()
        return render(request,self.template_name,{'publication':publication})
    
    def post(self,request):
        name=request.POST.get('name')
        logo=request.FILES.get('logo')

        if name:
            publication=Publication(name=name)
            if logo:
                publication.logo=logo
            publication.save()

        return redirect('Publication')     
    

@method_decorator(staff_member_required, name='dispatch')
class AdminBookApprovalView(View):
    def get(self, request):
        books = Book.objects.all() 
        return render(request, 'admin_book_list.html', {'books': books})



@method_decorator(staff_member_required, name='dispatch')
class BookStatusUpdateView(View):
    def get(self, request, pk):
            book = get_object_or_404(Book, pk=pk)
            all_pincodes = Pincode.objects.all()  
            pincodes = book.pincodes.all()  
            return render(request, 'book_approval.html', {'book': book, 'all_pincodes': all_pincodes, 'pincodes': pincodes})

    def post(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        action = request.POST.get('action')
        reason = request.POST.get('rejection_reason', '').strip()
        price = request.POST.get('price')
        discount_percent = request.POST.get('discount_percent')

        if price:
            book.price = price

        if discount_percent:
            try:
                discount_percent = int(discount_percent)
                book.discount_percent = discount_percent
                discount_amount = Decimal(book.price) * Decimal(discount_percent) / 100
                book.discounted_price = Decimal(book.price) - discount_amount
            except:
                book.discount_percent = None
                book.discounted_price = None

        book.trending = 'trending' in request.POST        

        if action == 'approve':
            book.status = 'approved'
            book.rejection_reason = ''

            pincode_ids = request.POST.getlist('pincode')
            if pincode_ids:
                book.pincodes.set(pincode_ids)  
            book.save()

            EmailThread(
                subject='Your book has been approved!',
                message=f'Congratulations, your book "{book.title}" has been approved by the admin.',
                recipient_list=[book.seller.email]
            ).start()

            messages.success(request, f'Book "{book.title}" approved successfully.')

        elif action == 'reject':
            if not reason:
                messages.error(request, "Rejection reason is required.")
                return render(request, 'book_approval.html', {'book': book, 'pincodes': book.pincode.all()})

            RejectedBook.objects.create(
                title=book.title,
                author=book.author,
                description=book.description,
                price=book.price,
                image=book.image,  
                seller=book.seller,
                rejection_reason=reason
            )

            EmailThread(
                subject='Your book has been rejected',
                message=f'Sorry, your book "{book.title}" has been rejected.\nReason: {reason}',
                recipient_list=[book.seller.email]
            ).start()

            book.delete()

            messages.success(request, f'Book "{book.title}" rejected, saved to history, and email sent to seller.')

        return redirect('book_list')

@method_decorator(login_required, name='dispatch')
class SellerBooksStatusView(View):
    def get(self, request):
        approved_books = Book.objects.filter(seller=request.user, status='approved')
        pending_books = Book.objects.filter(seller=request.user, status='pending')
        rejected_books = RejectedBook.objects.filter(seller=request.user)

        context = {
            'approved_books': approved_books,
            'pending_books': pending_books,
            'rejected_books': rejected_books,
        }
        return render(request, 'seller_book_status.html', context)
    


class CouponListView(ListView):
    model = Coupon
    template_name = 'coupon_list.html'
    context_object_name = 'coupons'

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(code__icontains=search_query) |
                Q(discount__icontains=search_query) |
                Q(upto_amount__icontains=search_query)
            )
        return queryset


class CouponCreateView(View):
    template_name = 'coupon_create.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        code = request.POST.get('code')
        discount = request.POST.get('discount')
        coupon_type = request.POST.get('type')
        upto_amount_checkbox = request.POST.get('upto_amount_checkbox')
        upto_amount = request.POST.get('upto_amount')

        if not code or not discount or not coupon_type:
            messages.error(request, "All fields are required.")
            return render(request, self.template_name)

        if Coupon.objects.filter(code=code).exists():
            messages.error(request, "Coupon code already exists.")
            return render(request, self.template_name)

        try:
            discount = float(discount)
            if upto_amount_checkbox: 
                upto_amount = float(upto_amount)
            else:
                upto_amount = 0 
        except ValueError:
            messages.error(request, "Discount and Amount must be valid numbers.")
            return render(request, self.template_name)
        
        if coupon_type == "Upto" and not upto_amount_checkbox:
            messages.error(request, "Please check the 'Enable Upto Amount' checkbox.")
            return render(request, self.template_name)

        Coupon.objects.create(
            code=code,
            discount=discount,
            upto_amount=upto_amount,
            type=coupon_type
        )

        messages.success(request, "Coupon created successfully.")
        return redirect('coupon_list') 
    
class CouponUpdateView(View):
    template_name = 'coupon_update.html'

    def get(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        return render(request, self.template_name, {'coupon': coupon})

    def post(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)

        code = request.POST.get('code')
        discount = request.POST.get('discount')
        coupon_type = request.POST.get('type')
        upto_amount_checkbox = request.POST.get('upto_amount_checkbox')  
        upto_amount = request.POST.get('upto_amount')

        if not code or not discount or not coupon_type:
            messages.error(request, "All fields are required.")
            return render(request, self.template_name, {'coupon': coupon})

        try:
            discount = float(discount)
            if upto_amount_checkbox:  
                upto_amount = float(upto_amount)
            else:
                upto_amount = 0  
        except ValueError:
            messages.error(request, "Discount and Amount must be valid numbers.")
            return render(request, self.template_name, {'coupon': coupon})

        if coupon_type == "Upto" and not upto_amount_checkbox:
            messages.error(request, "Please check the 'Enable Upto Amount' checkbox.")
            return render(request, self.template_name, {'coupon': coupon})

        coupon.code = code
        coupon.discount = discount
        coupon.type = coupon_type
        coupon.upto_amount = upto_amount if upto_amount_checkbox else 0
        coupon.save()

        messages.success(request, "Coupon updated successfully.")
        return redirect('coupon_list')


class CouponDeleteView(View):
    def post(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        coupon.delete()
        return redirect('coupon_list')
    


class BookOrderListView(ListView):
    model = BookOrder
    template_name = 'book_order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        return BookOrder.objects.all().order_by('-order_date')


class BookOrderDetailView(DetailView):
    model = BookOrder
    template_name = 'book_order_detail.html'
    context_object_name = 'order'
    slug_field = 'order_id'
    slug_url_kwarg = 'order_id'  

    def get_queryset(self):
        return BookOrder.objects.all()


class OrderReportView(ListView):
    model=BookOrder 
    template_name="order_report.html"
    context_object_name="orders"

    def get_queryset(self):
        return BookOrder.objects.select_related('user','profile','shipping_address').prefetch_related('books')      
    

class PendingOrdersListView(ListView):
    model=BookOrder
    template_name="pending_orders.html"
    context_object_name='pending_orders'

    def get_queryset(self):
        return BookOrder.objects.filter(status='pending')
    
class PendingOrderDetailView(DetailView):
    model=BookOrder
    template_name='Pending_order_details.html' 
    context_object_name='order'


class ConfirmOrderView(View):
    def post(self,request,pk):
        order=get_object_or_404(BookOrder,pk=pk)
        action=request.POST.get('action')

        if action=='confirm':
            order.status='completed'
            messages.success(request,f"Order {order.order_id} confirmed.")
        elif action=='reject':
            order.status='cancelled'  
            messages.warning(request,f"Order {order.order_id} rejected.") 
        order.save()
        return redirect('pending_orders')    



class RatingListView(ListView):
    model = Rating
    template_name = 'rating.html'
    context_object_name = 'ratings'

    def get_queryset(self):
        return Rating.objects.select_related('book', 'user').order_by('-created_at')

    

class ForgotPasswordView(View):
    def get(self, request):
        return render(request, 'forgot_password.html')

    def post(self, request):
        email = request.POST.get('email')
        user = CustomUser.objects.filter(email=email).first()

        if user and (user.is_superuser or user.role == "seller"):
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)

            reset_link = request.build_absolute_uri(
                reverse('reset_password', kwargs={'uidb64': uid, 'token': token})
            )
            subject = "Reset Your Password"

            html_message = f"""
            <html>
            <body>
                <p>Hello {user.first_name},</p>
                <p>You requested a password reset. Click the button below to reset your password:</p>
                <p>
                    <a href="{reset_link}" 
                       style="background-color: #4CAF50; color: white; padding: 10px 20px;
                              text-decoration: none; display: inline-block; font-size: 16px;
                              border-radius: 5px;">
                        Reset Password
                    </a>
                </p>
                <p>This link will expire in 10 minutes.</p>
                <p>If you did not request this, please ignore this email.</p>
                <p>Best regards,<br>Book Stall Team</p>
            </body>
            </html>
            """

            EmailThread(subject, html_message, [user.email]).start()
            return redirect('password_reset_done')
        else:
            return render(request, 'forgot_password.html', {'error': 'Email not found or not allowed.'})   


class PasswordResetDoneView(View):
    def get(self, request):
        return render(request, 'password_reset_done.html')
        

class ResetPasswordView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)

            if token_generator.check_token(user, token):
                return render(request, 'reset_password.html', {
                    'validlink': True,
                    'uidb64': uidb64,
                    'token': token
                })
            else:
                return render(request, 'reset_password.html', {'validlink': False})

        except (CustomUser.DoesNotExist, ValueError, TypeError, OverflowError):
            return render(request, 'reset_password.html', {'validlink': False})

    def post(self, request, uidb64, token):
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)

            if token_generator.check_token(user, token):
                if password == confirm_password:
                    user.set_password(password)
                    user.save()
                    messages.success(request, "Your password has been reset successfully. You can now log in.")
                    return redirect('login')  
                else:
                    return render(request, 'reset_password.html', {
                        'validlink': True,
                        'uidb64': uidb64,
                        'token': token,
                        'error': 'Passwords do not match.'
                    })
            else:
                return render(request, 'reset_password.html', {'validlink': False})

        except (CustomUser.DoesNotExist, ValueError, TypeError, OverflowError):
            return render(request, 'reset_password.html', {'validlink': False})
        



class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login') 






