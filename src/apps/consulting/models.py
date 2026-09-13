from botocore.exceptions import ClientError
from django.conf import settings
from django.core.exceptions import ValidationError, SuspiciousFileOperation
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.consulting.enums import Specialty
from apps.consulting.managers import RequestManager
from apps.consulting.validators import validate_media_file

User = get_user_model()


# Create request
class Service(models.Model):
    class ServiceType(models.TextChoices):
        # --- TENNIS ---
        SHORT = "short", _("Video Analysis Short")
        LONG = "long", _("Video Analysis Long")

        # --- NUTRITION ---
        NUTRITION_INTRO = "nutr_intro", _("Introductory Session")
        NUTRITION_BASIC = "nutr_basic", _("Basic Support")
        NUTRITION_IN_DEPTH = "nutr_in_depth", _("In-Depth Coaching & Support")

        # --- PSYCHOLOGY  ---
        PSYCHOLOGY_DISCOVER = "psych_discover", _("Discover")
        PSYCHOLOGY_DEVELOP = "psych_develop", _("Develop")
        PSYCHOLOGY_TRANSFORM = "psych_transform", _("Transform")

    name = models.CharField(max_length=255, verbose_name=_("Service Name"))
    code = models.CharField(max_length=50, unique=True, db_index=True)

    # 🌟 ДОДАНО: Пряма прив'язка до домену для нормальної фільтрації
    specialty = models.CharField(
        max_length=20,
        choices=Specialty.choices,
        default=Specialty.TENNIS,
        verbose_name=_("Specialty Domain")
    )

    service_type = models.CharField(max_length=50, choices=ServiceType.choices)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._build_unique_code()
        super().save(*args, **kwargs)

    def _build_unique_code(self):
        max_length = self._meta.get_field("code").max_length
        base_code = slugify(self.name) or "service"
        base_code = base_code[:max_length]

        code = base_code
        counter = 1
        queryset = type(self).objects.all()
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        while queryset.filter(code=code).exists():
            suffix = f"-{counter}"
            code = f"{base_code[:max_length - len(suffix)]}{suffix}"
            counter += 1

        return code

    def __str__(self):
        return f"{self.name} ({self.get_specialty_display()})"


# User створює Request.
class Request(models.Model):
    class Status(models.TextChoices):
        NEW = "new", _("New")
        ASSIGNED = "assigned", _("Assigned")
        IN_PROGRESS = "in_progress", _("In Progress")
        COMPLETED = "completed", _("Completed")
        REJECTED = "rejected", _("Rejected")

    STATUS_CHOICES = Status.choices

    objects = RequestManager()

    id: int
    specialty_needed = models.CharField(
        max_length=20,
        choices=list(Specialty.choices),
        default=Specialty.TENNIS,
        help_text=_("The type of specialist required for this request.")
    )

    assigned_specialist = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_requests",
        limit_choices_to={"role__in": ["Coach", "Nutrition", "Psychology"]},
        help_text=_("The specific coach assigned to this request. Empty until accepted.")
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="requests")
    service = models.ForeignKey(Service, on_delete=models.PROTECT)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=Status.NEW, db_index=True)
    comment = models.TextField(blank=True, verbose_name=_("Client Comment"))
    deadline = models.DateTimeField(null=True, blank=True)

    is_viewed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def status_color_class(self):
        colors = {
            self.Status.NEW: 'info',
            self.Status.ASSIGNED: 'primary',
            self.Status.IN_PROGRESS: 'warning',
            self.Status.COMPLETED: 'success',
            self.Status.REJECTED: 'danger',
        }
        return colors.get(self.status, 'secondary')

    @property
    def progress_percentage(self):
        """Повертає відсоток виконання заявки у вигляді цілого числа"""
        progress_map = {
            self.Status.NEW: 25,
            self.Status.ASSIGNED: 50,
            self.Status.IN_PROGRESS: 75,
            self.Status.COMPLETED: 100,
            self.Status.REJECTED: 100,
        }
        return progress_map.get(self.status, 0)

    def clean(self):
        super().clean()
        if self.status not in self.Status.values:
            raise ValidationError({"status": _("Invalid request status.")})

    @transaction.atomic
    def change_status(self, new_status, user):
        if self.status == new_status:
            return False

        if new_status not in self.Status.values:
            raise ValidationError({"status": _("Invalid request status.")})

        old_status = self.status
        self.status = new_status

        self.save(update_fields=['status', 'updated_at'])

        RequestStatusHistory.objects.create(
            request=self,
            old_status=old_status,
            new_status=new_status,
            changed_by=user
        )
        return True

    @property
    def all_files(self):
        """
        Уніфікований архітектурний метод.
        Збирає файли як з моделі Media (Tennis), так і з NutritionIntake (Nutrition).
        """
        file_list = []

        # 1. Збираємо медіафайли тенісу (якщо є)
        # noinspection PyUnresolvedReferences
        for media in self.media.all():
            if media.media_type in ("video", "file"):
                file_list.append({
                    "url": media.get_absolute_media_url,
                    "name": media.file.name.split("/")[-1] if media.file else "Attached File",
                    "icon": "ki-video" if media.media_type == "video" else "ki-file"
                })
            elif media.media_type == "link":
                file_list.append({
                    "url": media.url,
                    "name": "YouTube Link",
                    "icon": "ki-youtube"
                })

        # 2. Збираємо файли анкет Нутриціолога (через OneToOne зв'язок)
        # hasattr перевіряє, чи взагалі існує заповнена анкета для цього запиту
        if hasattr(self, 'nutrition_intake') and self.nutrition_intake:
            intake = self.nutrition_intake
            if intake.attachments:
                file_list.append({
                    "url": intake.attachments.url,
                    "name": intake.attachments.name.split("/")[-1],
                    "icon": "ki-file"  # або будь-яка інша іконка документів
                })

        return file_list

    class Meta:
        verbose_name = _("Request")
        verbose_name_plural = _("Requests")

    def __str__(self):
        return f"Request #{self.id} - {self.user.email} [{self.get_status_display()}]"


class Media(models.Model):
    class MediaType(models.TextChoices):
        VIDEO = "video", _("Video")
        FILE = "file", _("File")
        LINK = "link", _("Link")

    MEDIA_TYPES = MediaType.choices

    request = models.ForeignKey('Request', on_delete=models.CASCADE, related_name="media")
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES)

    file = models.FileField(upload_to="requests/tennis/%Y/%m/%d/", null=True, blank=True)
    url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    file_size_bytes = models.PositiveBigIntegerField(
        verbose_name=_("File size in bytes"),
        null=True,
        blank=True,
        help_text=_("Stored locally to prevent N+1 API calls to cloud storage.")
    )

    class Meta:
        verbose_name = _("Media")
        verbose_name_plural = _("Medias")

    def clean(self):
        super().clean()
        if self.media_type in [self.MediaType.VIDEO, self.MediaType.FILE] and not self.file:
            raise ValidationError(_("File must be uploaded for video/file media types."))
        if self.media_type in [self.MediaType.VIDEO, self.MediaType.FILE] and self.url:
            raise ValidationError(_("URL must be empty for uploaded media files."))
        if self.media_type == self.MediaType.LINK and not self.url:
            raise ValidationError(_("URL must be provided for link media type."))
        if self.media_type == self.MediaType.LINK and self.file:
            raise ValidationError(_("File must be empty for link media type."))
        if self.media_type == self.MediaType.LINK and self.url:
            if "youtube.com" not in self.url and "youtu.be" not in self.url:
                raise ValidationError(_("Only YouTube links are allowed."))
        if self.media_type in [self.MediaType.VIDEO, self.MediaType.FILE]:
            validate_media_file(self.media_type, self.file)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_file_available(self):
        if not self.file:
            return False
        try:
            return self.file.storage.exists(str(self.file.name))
        except (SuspiciousFileOperation, ClientError, OSError):
            # Логуйте помилку, не просто ковтайте її
            return False

    @property
    def get_absolute_media_url(self):
        if self.media_type == self.MediaType.LINK:
            return self.url
        if self.file:
            return self.file.url
        return "#"

    @property
    def safe_size(self):
        """
        Повертає розмір файлу або None, якщо файл відсутній у сховищі.
        """
        try:
            if self.file and self.file.name:
                return self.file.size
            return None
        except (AttributeError, OSError, Exception):
            return None

    @property
    def public_url(self):
        return self.get_absolute_media_url


class Report(models.Model):
    id: int
    # --- 1. BASIC LINKS AND METADATA ---
    request = models.OneToOneField(
        'Request',
        on_delete=models.CASCADE,
        related_name="report"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_reports",
        limit_choices_to={"role": "Coach"}
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # --- 2. GENERAL MATERIALS (Your saved fields) ---
    text = models.TextField(
        blank=True,
        verbose_name=_("Additional Comments / General Text"),
        help_text=_("Use this for any general feedback that doesn't fit the structured analysis.")
    )
    pdf = models.FileField(
        upload_to="reports/coach/%Y/%m/",
        null=True,
        blank=True,
        verbose_name=_("Attached PDF")
    )
    external_link = models.URLField(
        blank=True,
        verbose_name=_("External Link")
    )

    # --- 3. STRUCTURED ANALYSIS (According to the DOCX questionnaire) ---

    # Overall score
    overall_assessment = models.TextField(
        blank=True,
        verbose_name=_("Overall Assessment")
    )

    # Key strengths
    strength_1 = models.CharField(max_length=255, blank=True, verbose_name=_("Key Strength 1"))
    strength_2 = models.CharField(max_length=255, blank=True, verbose_name=_("Key Strength 2"))
    strength_3 = models.CharField(max_length=255, blank=True, verbose_name=_("Key Strength 3"))

    # ----- Top 3 priorities for improvement -----
    # Priority 3
    priority_1_issue = models.CharField(max_length=255, blank=True, verbose_name=_("Priority 1 Issue"))
    priority_1_why = models.TextField(blank=True, verbose_name=_("Why it matters (1)"))
    priority_1_drill = models.TextField(blank=True, verbose_name=_("Recommended drill (1)"))

    # Priority 2
    priority_2_issue = models.CharField(max_length=255, blank=True, verbose_name=_("Priority 2 Issue"))
    priority_2_why = models.TextField(blank=True, verbose_name=_("Why it matters (2)"))
    priority_2_drill = models.TextField(blank=True, verbose_name=_("Recommended drill (2)"))

    # Priority 3
    priority_3_issue = models.CharField(max_length=255, blank=True, verbose_name=_("Priority 3 Issue"))
    priority_3_why = models.TextField(blank=True, verbose_name=_("Why it matters (3)"))
    priority_3_drill = models.TextField(blank=True, verbose_name=_("Recommended drill (3)"))

    # Action plan
    action_plan = models.TextField(
        blank=True,
        verbose_name=_("2–4 Week Action Plan")
    )

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ['-created_at']

    def __str__(self):
        return f"Report for Req #{self.request.id}"


class RequestStatusHistory(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="status_changes")
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Індексація для швидкого пошуку історії конкретної заявки
        indexes = [
            models.Index(fields=['request', '-changed_at']),
        ]
        verbose_name = _("Request Status History")
        verbose_name_plural = _("Request Status Histories")

    def __str__(self):
        return f"Req #{self.request.id}: {self.old_status} -> {self.new_status}"


class NutritionIntake(models.Model):
    id: int
    WEIGHT_UNIT_CHOICES = (
        ('kg', 'kg'),
        ('lbs', 'lbs'),
    )
    HEIGHT_UNIT_CHOICES = (
        ('cm', 'cm'),
        ('in', 'in'),
    )
    HANDEDNESS_CHOICES = (
        ('Right', _('Right-handed')),
        ('Left', _('Left-handed')),
        ('Ambidextrous', _('Ambidextrous')),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='nutrition_intakes',
        verbose_name=_("Student")
    )
    request = models.OneToOneField(
        'consulting.Request',
        on_delete=models.CASCADE,
        related_name='nutrition_intake',
        verbose_name=_("Associated Request"),
        null=True, blank=True
    )

    full_name = models.CharField(_("Full Name"), max_length=255)
    age = models.PositiveIntegerField(_("Age at the time of appeal"))

    weight = models.DecimalField(_("Weight"), max_digits=5, decimal_places=2)
    weight_unit = models.CharField(_("Weight Unit"), max_length=5, choices=WEIGHT_UNIT_CHOICES, default='kg')

    height = models.PositiveIntegerField(_("Height"))
    height_unit = models.CharField(_("Height Unit"), max_length=5, choices=HEIGHT_UNIT_CHOICES, default='cm')

    handedness = models.CharField(_("Handedness"), max_length=15, choices=HANDEDNESS_CHOICES, default='Right')
    language = models.CharField(_("Preferred Language"), max_length=100)
    whatsapp_number = models.CharField(_("WhatsApp Contact Number"), max_length=30)

    complaints = models.TextField(_("Complaints at the time of Appeal"))
    chronic_diseases = models.TextField(_("Chronic Diseases"), blank=True, null=True)
    medications_and_vitamins = models.TextField(_("Constant intake of medication, vitamins, sport nutrition"),
                                                blank=True, null=True)
    operations = models.TextField(_("Operations"), blank=True, null=True)
    traumas = models.TextField(_("Traumas"), blank=True, null=True)
    allergies = models.TextField(_("Allergies"), blank=True, null=True)

    attachments = models.FileField(
        _("Analyses and/or diagnostic papers"),
        upload_to="requests/nutrition/%Y/%m/%d/",
        blank=True, null=True,
    )

    file_size_bytes = models.PositiveBigIntegerField(
        verbose_name=_("File size in bytes"),
        null=True,
        blank=True,
        help_text=_("Stored locally to prevent N+1 API calls to cloud storage.")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    appointment_date = models.DateTimeField(
        _("Appointment Date & Time"),
        blank=True,
        null=True,
        help_text=_("Scheduled date and time for the consultation.")
    )

    class Meta:
        verbose_name = _("Nutrition Intake")
        verbose_name_plural = _("Nutrition Intakes")
        ordering = ['-created_at']

    def __str__(self):
        return f"Intake {self.id} - {self.full_name} ({self.created_at.date()})"

    @property
    def safe_file_size(self):
        """
        Безпечно повертає розмір файлу.
        Захищає від FileNotFoundError, якщо файлу немає на диску або в R2.
        """
        try:
            if self.attachments and self.attachments.name:
                return self.attachments.size
        except (AttributeError, OSError, Exception):
            return None
        return None

    @property
    def public_url(self):
        return self.attachments.url if self.attachments else "#"

    def clean(self):
        super().clean()
        if self.request_id and self.student_id and self.request.user_id != self.student_id:
            raise ValidationError({"student": _("Student must match the associated request owner.")})
        if self.attachments:
            validate_media_file("file", self.attachments)


class PsychologyIntake(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='psychology_intakes',
        verbose_name=_("Client")
    )
    request = models.OneToOneField(
        'consulting.Request',
        on_delete=models.CASCADE,
        related_name='psychology_intake',
        verbose_name=_("Associated Request"),
        null=True, blank=True
    )

    # --- Main data ---
    appointment_date = models.DateTimeField(
        _("Appointment Date & Time"),
        help_text=_("Scheduled date and time for the psychology consultation.")
    )
    whatsapp_number = models.CharField(
        _("Contact Number (WhatsApp/Telegram)"),
        max_length=30,
        help_text=_("Crucial for online therapy sessions."),
    )

    # --- Context ---
    primary_concern = models.TextField(
        _("Primary Concern / Reason for seeking help"),
        help_text=_("Describe what bothers the client right now."),
        blank=True, null=True,
    )
    previous_therapy = models.BooleanField(
        _("Previous Therapy Experience"),
        default=False
    )
    psychiatric_medications = models.TextField(
        _("Current Psychiatric Medications"),
        blank=True, null=True,
        help_text=_("Antidepressants, anxiolytics, etc. (if any).")
    )
    crisis_state = models.BooleanField(
        _("Is the client in a crisis state?"),
        default=False,
        help_text=_("Flag for urgent attention (e.g. severe depression, panic attacks).")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Psychology Intake")
        verbose_name_plural = _("Psychology Intakes")
        ordering = ['-created_at']

    def __str__(self):
        return f"Psychology Intake {self.id} - {self.student.email} ({self.created_at.date()})"

    def clean(self):
        super().clean()
        if self.request_id and self.student_id and self.request.user_id != self.student_id:
            raise ValidationError({"student": _("Client must match the associated request owner.")})


# Utils models
class PendingUpload(models.Model):
    """
    Журнал відстеження файлів, які завантажуються в Cloudflare R2,
    але ще не прив'язані до реальних заявок.
    """
    file_key = models.CharField(max_length=500, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Pending Upload")
        verbose_name_plural = _("Pending Uploads")

    def __str__(self):
        return self.file_key
