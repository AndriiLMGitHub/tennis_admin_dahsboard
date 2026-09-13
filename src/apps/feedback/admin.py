from adminsortable2.admin import SortableAdminMixin, SortableInlineAdminMixin
from django.contrib import admin
from django.db import models
from django.db.models import Count
from django.forms import Textarea

from apps.feedback.models import Feedback, FAQItem, FAQCategory
from django.utils.translation import gettext_lazy as _


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'user', 'email', 'created_at')
    list_display_links = ('id', 'subject')

    search_fields = ('name', 'email', 'subject', 'message', 'user__email', 'user__first_name', 'user__last_name')

    list_filter = ('created_at',)
    date_hierarchy = 'created_at'

    readonly_fields = ('user', 'name', 'email', 'subject', 'message', 'created_at', 'updated_at')

    fieldsets = (
        (_('Sender Information'), {
            'fields': ('user', 'name', 'email'),
            'classes': ('collapse',),  # Можна згорнути блок за замовчуванням
        }),
        (_('Message Content'), {
            'fields': ('subject', 'message'),
        }),
        (_('System Metadata'), {
            'fields': ('created_at', 'updated_at'),
        }),
    )


    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True


class FAQItemInline(SortableInlineAdminMixin, admin.TabularInline):
    model = FAQItem
    extra = 1
    fields = ('is_published', 'question', 'answer')

    formfield_overrides = {
        models.TextField: {
            'widget': Textarea(attrs={
                'rows': 2,
                'style': 'width: 90%; min-width: 300px; resize: vertical;'
            })
        },
    }


@admin.register(FAQCategory)
class FAQCategoryAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'slug', 'is_active', 'get_items_count']
    list_display_links = ['title']
    list_editable = ['is_active']

    prepopulated_fields = {'slug': ('title',)}
    search_fields = ['title']
    inlines = [FAQItemInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(_items_count=Count('items'))
        return queryset.order_by('sort_order')

    def get_items_count(self, obj):
        return obj._items_count

    get_items_count.short_description = _("Questions Count")
    get_items_count.admin_order_field = '_items_count'


@admin.register(FAQItem)
class FAQItemAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ['get_short_question', 'category', 'is_published', 'updated_at']
    list_filter = ['category', 'is_published', 'created_at']
    list_editable = ['is_published']
    search_fields = ['question', 'answer']

    autocomplete_fields = ['category']

    def get_short_question(self, obj):
        return obj.question[:70] + "..." if len(obj.question) > 70 else obj.question

    get_short_question.short_description = _("Question")