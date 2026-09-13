from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .forms import FeedbackForm
from .models import FAQCategory, FAQItem
from .services import send_feedback_notification
from apps.consulting.decorators import allowed_roles_only


CONTACT_TEMPLATE = 'feedback/contact_us.html'
FAQ_TEMPLATE = 'feedback/faq_page.html'
CONTACT_REDIRECT_URL = 'contact_us'
CONTACT_ALLOWED_ROLES = ['Student', 'Coach', 'Nutrition', 'Psychology']


def _get_user_contact_data(user):
    if not user.is_authenticated:
        return {}

    return {
        'name': user.get_full_name() or user.username,
        'email': user.email,
    }


def _attach_authenticated_user_data(feedback_instance, user):
    if not user.is_authenticated:
        return

    contact_data = _get_user_contact_data(user)
    feedback_instance.user = user
    feedback_instance.name = contact_data['name']
    feedback_instance.email = contact_data['email']


@allowed_roles_only(allowed_roles=CONTACT_ALLOWED_ROLES)
def contact_us_view(request):
    if request.method == "POST":
        form = FeedbackForm(request.POST)

        if form.is_valid():
            feedback_instance = form.save(commit=False)
            _attach_authenticated_user_data(feedback_instance, request.user)
            feedback_instance.save()

            send_feedback_notification(feedback_instance)

            messages.success(request, _("Your message has been successfully sent!"))
            return redirect(CONTACT_REDIRECT_URL)
        else:
            messages.error(request, _("Please correct the errors below."))
    else:
        form = FeedbackForm(initial=_get_user_contact_data(request.user))

    return render(request, CONTACT_TEMPLATE, {'form': form})


@login_required
def faq_list_view(request):
    categories = FAQCategory.objects.filter(is_active=True).prefetch_related(
        models.Prefetch(
            'items',
            queryset=FAQItem.objects.filter(is_published=True),
            to_attr='published_items'
        )
    )
    return render(request, FAQ_TEMPLATE, {'categories': categories})
