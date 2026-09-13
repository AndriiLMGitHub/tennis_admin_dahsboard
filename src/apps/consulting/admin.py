from django.contrib import admin
from django.contrib.auth import get_user_model
from django.template.defaultfilters import filesizeformat
from django.utils.safestring import mark_safe

from apps.consulting.models import Request, Media, Service, RequestStatusHistory, Report, PendingUpload, \
    NutritionIntake, PsychologyIntake
from django.utils.translation import gettext_lazy as _

from apps.consulting.services import assign_coach_to_request, log_status_change

User = get_user_model()

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'specialty', 'service_type', 'is_active', 'created_at')
    list_filter = ('specialty', 'is_active', 'service_type')
    search_fields = ('name', 'code')

    # 🌟 Якщо ти використовуєш prepopulated_fields, поле 'code' ОБОВ'ЯЗКОВО
    # має бути присутнім у формі (тобто НЕ заблокованим повністю через fields/exclude).
    # prepopulated_fields = {'code': ('name',)}

    readonly_fields = ('created_at',)  # Поле 'code' НЕ повинно бути в readonly тут, щоб працював JS!

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'code', 'is_active')
        }),
        (_('Categorization'), {
            'fields': ('specialty', 'service_type'),
            'description': _('Ensure the Service Type strictly matches the chosen Specialty Domain.')
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Робимо поле 'code' доступним лише для читання ТІЛЬКИ ПРИ РЕДАГУВАННІ існуючого запису.
        При створенні нового воно відкрите, щоб prepopulated_fields міг у нього писати.
        """
        if obj:
            return ('code', 'created_at')
        return ('created_at',)


class MediaInline(admin.TabularInline):
    model = Media
    extra = 0
    fields = ('media_type', 'file', 'url')
    readonly_fields = ()
    classes = ('collapse',)
    verbose_name = _("Media Attachment")
    verbose_name_plural = _("Media Attachments")


class RequestStatusHistoryInline(admin.TabularInline):
    model = RequestStatusHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'changed_at')
    fields = ('old_status', 'new_status', 'changed_by', 'changed_at')
    can_delete = False

    classes = ('collapse',)

    def has_add_permission(self, request, obj=None):
        return False


# ==========================================
# 1. NUTRITION INLINE (Колапс)
# ==========================================
class NutritionIntakeInline(admin.StackedInline):
    model = NutritionIntake
    can_delete = False
    extra = 0
    max_num = 1

    verbose_name = _("Nutrition Medical Card")
    verbose_name_plural = _("Nutrition Medical Cards")

    autocomplete_fields = ['student']
    readonly_fields = ('created_at', 'get_file_size_display')

    classes = ('collapse',)

    fieldsets = (
        (_('General Information'), {
            'fields': ('student', 'full_name'),
            'classes': ('collapse',),
        }),
        (_('Consultation Scheduling'), {
            'fields': ('appointment_date',),
            'description': _('Specify the exact date and time for the consultation.'),
            'classes': ('collapse',),
        }),
        (_('Anthropometry & Contacts'), {
            'fields': (
                ('age',),
                ('weight', 'weight_unit'),
                ('height', 'height_unit'),
                ('handedness', 'language'),
                ('whatsapp_number',),
            ),
            'classes': ('collapse',),
        }),
        (_('Clinical Anamnesis'), {
            'fields': (
                'complaints', 'chronic_diseases', 'medications_and_vitamins',
                'operations', 'traumas', 'allergies'
            ),
            'classes': ('collapse',),
        }),
        (_('Medical Documents'), {
            'fields': ('attachments', 'get_file_size_display',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description=_("Verified Size (R2)"))
    def get_file_size_display(self, obj):
        size = obj.safe_file_size
        if size:
            return filesizeformat(size)
        if obj.attachments and obj.attachments.name:
            return mark_safe('<span style="color: #ffa726;">⚠️ File missing in R2</span>')
        return "—"


# ==========================================
# 2. PSYCHOLOGY INLINE (Колапс)
# ==========================================
class PsychologyIntakeInline(admin.StackedInline):
    model = PsychologyIntake
    can_delete = False
    extra = 0
    max_num = 1

    verbose_name = _("Psychology Context")
    verbose_name_plural = _("Psychology Contexts")

    autocomplete_fields = ['student']
    readonly_fields = ('created_at',)

    classes = ('collapse',)

    fieldsets = (
        (_('Consultation Scheduling & Contacts'), {
            'fields': ('appointment_date', 'whatsapp_number'),
            'description': _('Scheduled time and mandatory contact number for the online session.'),
            'classes': ('collapse',),
        }),
        (_('Clinical Context'), {
            'fields': ('primary_concern', 'psychiatric_medications'),
            'classes': ('collapse',),
        }),
        (_('Important Flags'), {
            'fields': ('previous_therapy', 'crisis_state'),
            'classes': ('collapse',),
            'description': _('Pay special attention if the client is in a crisis state.'),
        }),
    )


# ==========================================
# 3. OPTIMIZED MODEL ADMIN
# ==========================================
@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_select_related = ('user', 'service', 'assigned_specialist')

    list_display = ('specialty_needed', 'id', 'user', 'service', 'status', 'assigned_specialist', 'created_at',
                    'is_viewed')
    list_filter = ('status', 'specialty_needed', 'created_at', 'service', "is_viewed")
    search_fields = ('user__email', 'user__first_name', 'assigned_specialist__email', 'comment')
    readonly_fields = ('created_at', 'updated_at')

    autocomplete_fields = ['assigned_specialist']

    actions = ['mark_as_in_progress', 'mark_as_completed']

    # 🌟 Динамічні блоки поля (Client Info, Management, Tennis Comment як колапс, Timestamps)
    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (_('Client Info'), {
                'fields': ('user', 'service', 'specialty_needed')
            }),
            (_('Management'), {
                'fields': (
                    'status',
                    'is_viewed',
                    'assigned_specialist',
                )
            }),
        ]

        # Якщо це теніс, додаємо поле коментаря як окремий згорнутий блок (колапс)
        if obj and obj.specialty_needed == 'TENNIS':
            fieldsets.append(
                (_('Tennis Client Comment'), {
                    'fields': ('comment',),
                    'classes': ('collapse',),
                })
            )
        elif not obj:
            fieldsets.append(
                (_('Tennis Client Comment'), {
                    'fields': ('comment',),
                    'classes': ('collapse',),
                })
            )

        fieldsets.append(
            (_('Timestamps'), {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            })
        )
        return fieldsets

    # 🌟 Динамічне підключення інлайнів залежно від спеціальності
    def get_inlines(self, request, obj=None):
        inlines = [RequestStatusHistoryInline]

        if obj:
            if obj.specialty_needed == 'PSYCHOLOGY':
                inlines.append(PsychologyIntakeInline)
            elif obj.specialty_needed == 'NUTRITION':
                inlines.append(NutritionIntakeInline)
            elif obj.specialty_needed == 'TENNIS':
                inlines.append(MediaInline)  # Медіа для тенісу як інлайн

        return inlines

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "assigned_specialist":
            kwargs["queryset"] = User.objects.filter(
                role__in=['Coach', 'Nutrition', 'Psychology']
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if change:
            if 'status' in form.changed_data:
                log_status_change(
                    request_obj=obj,
                    old_status=form.initial.get('status'),
                    new_status=obj.status,
                    changed_by_user=request.user
                )

            if 'assigned_specialist' in form.changed_data and obj.assigned_specialist:
                current_domain = request.build_absolute_uri('/').rstrip('/')
                assign_coach_to_request(
                    request_obj=obj,
                    new_coach=obj.assigned_specialist,
                    assigned_by_user=request.user,
                    base_url=current_domain
                )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'user',
            'service',
            'assigned_specialist',
            'nutrition_intake',
            'psychology_intake'
        ).prefetch_related('media', 'status_history')

    @admin.action(description=_("Mark selected requests as 'In Progress'"))
    def mark_as_in_progress(self, request, queryset):
        updated = 0
        for request_obj in queryset:
            if request_obj.change_status(Request.Status.IN_PROGRESS, request.user):
                updated += 1
        self.message_user(request, f"{updated} requests marked as In Progress.")

    @admin.action(description=_("Mark selected requests as 'Completed'"))
    def mark_as_completed(self, request, queryset):
        updated = 0
        for request_obj in queryset:
            if request_obj.change_status(Request.Status.COMPLETED, request.user):
                updated += 1
        self.message_user(request, f"{updated} requests marked as Completed.")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'request', 'created_by', 'created_at')
    list_filter = ('created_at', 'created_by')
    search_fields = ('request__user__email', 'request__user__first_name', 'request__user__last_name')
    readonly_fields = ('created_at',)

    # Архітектура самої форми редагування (групування полів)
    fieldsets = (
        (_('System Information'), {
            'fields': ('request', 'created_by', 'created_at')
        }),
        (_('General Materials'), {
            'fields': ('text', 'pdf', 'external_link'),
            'description': _('Attach standard files or write unstructured comments here.')
        }),
        (_('Overall Assessment'), {
            'fields': ('overall_assessment',)
        }),
        (_('Key Strengths'), {
            'fields': ('strength_1', 'strength_2', 'strength_3')
        }),
        # Використовуємо 'classes': ('collapse',), щоб ці блоки можна було згортати, економлячи місце
        (_('Priority 1'), {
            'classes': ('collapse',),
            'fields': ('priority_1_issue', 'priority_1_why', 'priority_1_drill')
        }),
        (_('Priority 2'), {
            'classes': ('collapse',),
            'fields': ('priority_2_issue', 'priority_2_why', 'priority_2_drill')
        }),
        (_('Priority 3'), {
            'classes': ('collapse',),
            'fields': ('priority_3_issue', 'priority_3_why', 'priority_3_drill')
        }),
        (_('Action Plan'), {
            'fields': ('action_plan',)
        }),
    )


@admin.register(PendingUpload)
class PendingUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_key', 'created_at')
    list_filter = ('created_at',)


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    pass