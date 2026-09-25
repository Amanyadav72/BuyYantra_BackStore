from django.shortcuts import render, redirect
from .models import Product, SellerProfile, Category
from .forms import ProductForm, RegisterForm, SellerProfileForm
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

class ProductListView(ListView):
    model = Product
    template_name = "products/home.html"
    context_object_name = "products"
    paginate_by = 6

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.order_by("name")
        return context

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            qs = Product.objects.published().prefetch_related("categories")
        elif user.is_superuser:
            qs = Product.objects.all().select_related("owner").prefetch_related("categories")
        elif user.has_perm("products.add_product"):
            qs = Product.objects.by_owner(user).select_related("owner").prefetch_related("categories")
        else:
            qs = Product.objects.published().select_related("owner").prefetch_related("categories")

        search_query = self.request.GET.get("q")
        category_filter = self.request.GET.get("category")
        ordering = self.request.GET.get("ordering")

        if search_query:
            qs = qs.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(categories__name__icontains=search_query)
            ).distinct()

        if category_filter:
            qs = qs.filter(categories__name=category_filter)

        if ordering in ["price", "-price", "-created_at"]:
            qs = qs.order_by(ordering)

        return qs
    

class ProductDetailView(DetailView):
    model = Product
    template_name = "products/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        public = Product.objects.published()
        if self.request.user.is_authenticated:
            public = public | Product.objects.by_owner(self.request.user)
        return public.select_related("owner").prefetch_related("categories")


class SellerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict store-management pages to staff users."""

    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff


class MyProductListView(SellerRequiredMixin, ListView):
    model = Product
    template_name = "products/my_products.html"
    context_object_name = "products"
    paginate_by = 6

    def get_queryset(self):
        return Product.objects.by_owner(self.request.user).prefetch_related("categories")


class ProductCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "products/product_Form.html"
    success_url = reverse_lazy("product_form")
    permission_required = "products.add_product"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Product(owner=self.request.user)
        return kwargs

    def form_valid(self, form):
        try:
            form.instance.full_clean()
        except ValidationError as exc:
            for field, errors in exc.message_dict.items():
                for error in errors:
                    form.add_error(field, error)
            return self.form_invalid(form)

        response = super().form_valid(form)
        messages.success(self.request, "Product created successfully.")
        return response


class OwnerProductMixin(SellerRequiredMixin):
    def get_queryset(self):
        return Product.objects.by_owner(self.request.user)


class ProductUpdateView(OwnerProductMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "products/product_Form.html"
    success_url = reverse_lazy("my_products")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Product updated succesfully.")
        return response


class ProductDeleteView(OwnerProductMixin, DeleteView):
    model = Product
    template_name = "products/product_confirm_delete.html"
    success_url = reverse_lazy("my_products")
    
    
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("home")
    
    else:
        form = RegisterForm()

    return render(request, "products/register.html", {"form" : form})

def user_login(request):
    next_url = request.POST.get("next") or request.GET.get("next")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

            return redirect("home")
    else:
        form = AuthenticationForm()

    return render(request, "products/login.html", {"form": form, "next": next_url})

@login_required
@require_POST
def user_logout(request):
    logout(request)
    return redirect("home")

@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect("home")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "products/change_password.html", {"form":form})


@login_required
def seller_profile(request):
    if not request.user.is_staff:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    profile, _ = SellerProfile.objects.get_or_create(user=request.user)
    return render(request, "products/profile.html", {"profile": profile})


@login_required
def seller_profile_edit(request):
    if not request.user.is_staff:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    profile, _ = SellerProfile.objects.get_or_create(user=request.user)
    form = SellerProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated Succesfully.")
        return redirect("seller_profile")
    return render(request, "products/profile_form.html", {"form": form})
