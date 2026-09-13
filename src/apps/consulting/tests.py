# ==========================================
# COACH TESTS
# ==========================================
import json
import time
from typing import Any, cast
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from unittest.mock import patch

from apps.consulting.models import Report, Service, Request, Media

User: Any = get_user_model()


class CoachViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.coach = User.objects.create_user(email='coach@test.com', password='password', role='Coach')
        self.student = User.objects.create_user(email='student@test.com', password='password', role='Student')
        self.service = Service.objects.create(name="Tennis Analysis")
        self.request_item = Request.objects.create(
            user=self.student,
            assigned_specialist=self.coach,
            service=self.service,
            status='Pending'
        )

    def test_list_coach_requests_security(self):
        """ПЕРЕВІРКА: Тренер бачить тільки свої заявки."""
        other_coach = User.objects.create_user(email='other@test.com', password='password', role='Coach')
        Request.objects.create(user=self.student, assigned_specialist=other_coach, service=self.service)

        self.client.force_login(self.coach)
        response = self.client.get(reverse('coach_list_requests'))

        self.assertEqual(response.status_code, 200)
        # Тренер має бачити лише 1 свою заявку, а не дві
        self.assertEqual(len(response.context['requests']), 1)

    def test_request_coach_detail_post_success(self):
        """ПЕРЕВІРКА: Успішне оновлення статусу та звіту (Атомарність)."""
        self.client.force_login(self.coach)

        url = reverse('coach_request_detail', kwargs={'request_id': self.request_item.id})

        data = {
            'status': 'Completed',
            'overall_assessment': 'Great performance',
            'text': 'Good job!'
        }

        response = self.client.post(url, data)
        self.assertRedirects(response, url)

        # Перевірка БД
        self.request_item.refresh_from_db()
        self.assertEqual(self.request_item.status, 'Completed')

        report = Report.objects.filter(request=self.request_item).first()
        self.assertIsNotNone(report)
        report = cast(Report, report)
        self.assertEqual(report.overall_assessment, 'Great performance')

    def test_request_coach_detail_pdf_upload(self):
        """ПЕРЕВІРКА: Завантаження PDF-файлу."""
        self.client.force_login(self.coach)
        url = reverse('coach_request_detail', kwargs={'request_id': self.request_item.id})

        pdf = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        data = {'pdf': pdf}

        self.client.post(url, data)

        report = Report.objects.get(request=self.request_item)
        self.assertTrue(report.pdf.name.endswith('.pdf'))

    def test_request_coach_detail_access_denied(self):
        """ПЕРЕВІРКА: Тренер не може редагувати заявку іншого тренера."""
        stranger_coach = User.objects.create_user(email='stranger@test.com', password='password', role='Coach')
        self.client.force_login(stranger_coach)

        url = reverse('coach_request_detail', kwargs={'request_id': self.request_item.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)  # get_object_or_404 має спрацювати


"""
Tests for dashboard/student request views.

Coverage strategy:
- Happy path (2xx, redirects, context shape)
- Auth boundary (anonymous + non-student roles)
- Edge cases (pagination overflow, malformed input, missing media)
- Security (object-level ownership, bulk delete IDOR)
- Side effects (Celery task enqueue, R2 file deletion)
- HTTP method enforcement
"""

# ---------------------------------------------------------------------------
# Helpers / Factories
# ---------------------------------------------------------------------------

def make_student(email="student@example.com", password="pass1234!") -> User:
    user = User.objects.create_user(email=email, password=password)
    user.role = "Student"
    user.save()
    return user


def make_coach(email="coach@example.com", password="pass1234!") -> User:
    user = User.objects.create_user(email=email, password=password)
    user.role = "Coach"
    user.coach_status = "approved"
    user.save()
    return user


def make_superuser(email="admin@example.com", password="pass1234!") -> User:
    return User.objects.create_superuser(email=email, password=password)


def make_service(name="Video Review", code="VR001", is_active=True) -> Service:
    return Service.objects.create(name=name, code=code, is_active=is_active)


def make_request(user: User, service: Service, **kwargs) -> Request:
    return Request.objects.create(user=user, service=service, **kwargs)


def make_media(request_obj: Request, media_type="link", url="https://example.com") -> Media:
    return Media.objects.create(
        request=request_obj,
        media_type=media_type,
        url=url,
    )


# ---------------------------------------------------------------------------
# 1. list_students_requests_view
# ---------------------------------------------------------------------------

class ListStudentsRequestsViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.student = make_student()
        self.service = make_service()
        self.url = reverse("student_list_requests")

    # --- auth ---

    def test_logged_in_as_wrong_role_returns_403(self):
        # Тепер цей тест PASS
        coach = make_coach()
        self.client.force_login(coach)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_non_student_role_forbidden(self):
        coach = make_coach()
        self.client.force_login(coach)
        response = self.client.get(self.url)
        # @student_required must return 403 or redirect; never 200
        self.assertIn(response.status_code, [302, 403])

    # --- happy path ---

    def test_student_sees_own_requests(self):
        self.client.force_login(self.student)
        make_request(self.student, self.service)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("requests", response.context)
        self.assertEqual(response.context["requests"].paginator.count, 1)

    def test_other_students_requests_not_visible(self):
        other = make_student(email="other@example.com")
        make_request(other, self.service)
        self.client.force_login(self.student)

        response = self.client.get(self.url)
        self.assertEqual(response.context["requests"].paginator.count, 0)

    # --- pagination ---

    def test_pagination_default_page_size_is_6(self):
        self.client.force_login(self.student)
        for _ in range(8):
            make_request(self.student, self.service)

        response = self.client.get(self.url)
        self.assertEqual(len(response.context["requests"].object_list), 6)

    def test_page_out_of_range_returns_last_page(self):
        self.client.force_login(self.student)
        for _ in range(8):
            make_request(self.student, self.service)

        response = self.client.get(self.url, {"page": 9999})
        self.assertEqual(response.status_code, 200)
        page_obj = response.context["requests"]
        self.assertEqual(page_obj.number, page_obj.paginator.num_pages)

    def test_non_integer_page_returns_first_page(self):
        self.client.force_login(self.student)
        for _ in range(8):
            make_request(self.student, self.service)

        response = self.client.get(self.url, {"page": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["requests"].number, 1)

    def test_ordering_is_newest_first(self):
        self.client.force_login(self.student)

        # Створюємо r1, чекаємо, створюємо r2
        r1 = make_request(self.student, self.service)
        time.sleep(0.05)  # Гарантуємо різницю в часі
        r2 = make_request(self.student, self.service)

        # GET запит
        response = self.client.get(self.url)

        # Отримуємо об'єкт сторінки
        page_obj = response.context["requests"]

        # Отримуємо ID об'єктів
        ids = [obj.id for obj in page_obj.object_list]

        # Лог для дебагу (якщо впаде, побачиш в консолі)
        print(f"DEBUG: IDs: {ids}, Expected: {[r2.id, r1.id]}")

        # Перевірка: перший ID має бути r2 (найновіший)
        self.assertEqual(ids[0], r2.id)
        self.assertEqual(ids[1], r1.id)

    # --- context shape ---

    def test_breadcrumbs_present_in_context(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertIn("breadcrumbs", response.context)
        self.assertEqual(len(response.context["breadcrumbs"]), 1)
        self.assertIsNone(response.context["breadcrumbs"][0]["url"])

    def test_correct_template_used(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "dashboard/student/requests/list.html")


# ---------------------------------------------------------------------------
# 2. create_request_view
# ---------------------------------------------------------------------------

class CreateRequestViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.student = make_student()
        self.service = make_service(is_active=True)
        self.url = reverse("student_create_request")
        self.client.force_login(self.student)

    # 🔥 ЄДИНИЙ SOURCE OF TRUTH
    def payload(self, **overrides):
        data = {
            "service": str(self.service.id),
            "comment": "Test comment",
            "specialty_needed": "TENNIS",
            "media_type": "file",
        }
        data.update(overrides)
        return data

    def post(self, data=None, file=None):
        payload = self.payload()
        if data:
            payload.update(data)

        files = {}
        if file:
            files["media_file"] = file

        return self.client.post(self.url, data=payload, files=files or None)

    # --- auth ---

    # --- GET renders form ---

    def test_get_returns_200_with_services(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("services", response.context)

        self.assertQuerySetEqual(
            response.context["services"],
            Service.objects.filter(is_active=True),
            ordered=False,
        )

    def test_inactive_services_excluded_from_context(self):
        make_service(name="Inactive", code="X999", is_active=False)

        response = self.client.get(self.url)

        codes = list(response.context["services"].values_list("code", flat=True))
        self.assertNotIn("X999", codes)

    # --- POST happy path ---

    def test_valid_post_creates_request_and_redirects(self):
        self.client.force_login(self.student)

        # 1. Формуємо словник з валідними даними
        data = {
            "service": self.service.id,
            "comment": "Test comment",
            "specialty_needed": "TENNIS",  # <--- ОСЬ ТУТ БУЛА ПОМИЛКА (було "BH")
            "media_type": "file",
            "media_file": SimpleUploadedFile("test.pdf", b"dummy_content", content_type="application/pdf")
        }

        # 2. Виконуємо запит без follow, щоб спіймати 302
        response = self.client.post(self.url, data=data, follow=False)

        # 3. АНАЛІТИКА ПРОВАЛУ
        if response.status_code == 200:
            form = response.context.get('form')
            if form and not form.is_valid():
                self.fail(f"ФОРМА НЕВАЛІДНА! Помилки: {form.errors}")

            messages_list = [m.message for m in response.context.get('messages', [])]
            if messages_list:
                self.fail(f"ПОМИЛКА В БЛОЦІ TRY/EXCEPT! Повідомлення: {messages_list}")

            self.fail("В'юха повернула 200, але форма валідна і повідомлень немає. Логічна помилка у view.")

        # 4. Якщо все ок, перевіряємо редирект
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("index"))

    @patch("infrastructure.email.tasks.send_email_task")
    def test_success_message_on_valid_post(self, mock_task):
        # 1. Формуємо повний і правильний словник даних
        file = SimpleUploadedFile("test.pdf", b"dummy", content_type="application/pdf")
        data = {
            "service": self.service.id,
            "comment": "Test comment",
            "specialty_needed": "TENNIS",
            "media_type": "file",
            "media_file": file
        }

        # 2. Використовуємо стандартний клієнт з follow=True, щоб перехопити messages після редиректу
        response = self.client.post(self.url, data=data, follow=True)

        # 3. Перевірка
        messages = list(get_messages(response.wsgi_request))
        texts = [m.message.lower() for m in messages]

        self.assertTrue(
            any("success" in t for t in texts),
            f"Очікувалося повідомлення про успіх, але отримано: {texts}"
        )

    @patch("infrastructure.email.tasks.send_email_task.delay")
    @patch("django.db.transaction.on_commit", side_effect=lambda fn: fn())
    def test_email_task_called(self, mock_on_commit, mock_delay):
        self.client.force_login(self.student)

        # СТВОРЮЄМО АДМІНА, ЩОБ ВІДПРАЦЮВАВ БЛОК `if admin_emails:`
        from django.contrib.auth import get_user_model
        get_user_model().objects.create_superuser(email='admin@example.com', password='password')

        # 1. Валідні дані
        file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        data = {
            "service": self.service.id,
            "comment": "Test email trigger",
            "specialty_needed": "TENNIS",
            "media_type": "file",
            "media_file": file
        }

        # 2. Виконуємо запит і ловимо відповідь
        response = self.client.post(self.url, data=data, follow=True)

        # 3. Дебаг: Чому не викликано?
        if response.status_code != 200:
            # Якщо 302 - все ок, але перевіримо таск
            pass

        # Перевірка: чи був взагалі код в'юхи успішним?
        # Якщо в БД не з'явився об'єкт Request, значить таск і не міг бути викликаний
        self.assertTrue(Request.objects.filter(user=self.student).exists(), "Request не був створений!")

        # 4. Перевірка виклику таску
        self.assertTrue(mock_delay.called, "Celery таск send_email_task.delay НЕ був викликаний!")

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("django.db.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("infrastructure.email.tasks.send_email_task.delay")
    def test_email_task_enqueued_via_on_commit(self, mock_delay, mock_on_commit):
        self.client.force_login(self.student)

        # 1. Створюємо адміна
        from django.contrib.auth import get_user_model
        get_user_model().objects.create_superuser(email='admin@example.com', password='pass')

        # 2. Формуємо дані
        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")

        valid_payload = {
            "service": self.service.id,
            "comment": "Task enqueue test",
            "specialty_needed": "TENNIS",
            "media_type": "file",
            "media_file": file
        }

        # 3. ВИМИКАЄМО follow, щоб зловити саме 302 статус
        response = self.client.post(self.url, data=valid_payload, follow=False)

        # 4. Аналітика провалу: тепер 200 означає виключно помилку форми
        if response.status_code == 200:
            form = response.context.get('form')
            self.fail(f"Запит не пройшов валідацію. Помилки форми: {form.errors if form else 'Невідома помилка'}")

        # 5. Перевіряємо, що в'юха віддала редирект (успішне створення)
        self.assertEqual(response.status_code, 302, f"Очікувався редирект, але отримано {response.status_code}")

        # 6. Фінальна перевірка таску
        self.assertTrue(mock_delay.called, "Task.delay не був викликаний. Код не дійшов до on_commit.")

    @patch("django.db.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("infrastructure.email.tasks.send_email_task.delay")  # Уточни шлях імпорту, якщо він інший
    def test_no_email_sent_when_no_superusers(self, mock_delay, mock_on_commit):
        self.client.force_login(self.student)

        # 1. Гарантуємо відсутність суперкористувачів у тестовій базі
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.filter(is_superuser=True).update(is_superuser=False)

        # 2. Формуємо валідний словник даних
        file = SimpleUploadedFile("test.pdf", b"dummy content", content_type="application/pdf")
        data = {
            "service": self.service.id,
            "comment": "Test without superusers",
            "specialty_needed": "TENNIS",
            "media_type": "file",
            "media_file": file
        }

        # 3. Виконуємо запит
        response = self.client.post(self.url, data=data, follow=False)

        # Аналітика на випадок провалу
        if response.status_code == 200:
            if 'form' in response.context and response.context['form'].errors:
                self.fail(f"Форма відхилила запит: {response.context['form'].errors}")

        # 4. Строга перевірка: таск НЕ повинен бути викликаний
        mock_delay.assert_not_called()

    # --- media: link ---

    @patch("infrastructure.email.tasks.send_email_task.delay")
    def test_link_media_created(self, mock_delay):
        self.post(data={
            "media_type": "link",
            "media_link": "https://youtube.com/watch?v=abc",
        })

        req = Request.objects.get(user=self.student)

        media = Media.objects.get(request=req)

        self.assertEqual(media.media_type, "link")
        self.assertEqual(media.url, "https://youtube.com/watch?v=abc")

    @patch("infrastructure.email.tasks.send_email_task")
    def test_link_without_url_raises_validation_error(self, mock_task):
        self.client.force_login(self.student)

        # 1. Дані, де media_type є "link", але media_link відсутній
        data = {
            "service": self.service.id,
            "comment": "Test link fail",
            "specialty_needed": "TENNIS",
            "media_type": "link",
            # "media_link" навмисно пропущено
        }

        # 2. Виконуємо прямий запит
        response = self.client.post(self.url, data=data, follow=True)

        # 3. Перевірка: запит не має бути створений
        self.assertEqual(Request.objects.count(), 0, "Запит був створений, хоча дані невалідні!")

        # 4. Перевірка повідомлень про помилку
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(
            any("Validation" in m or "Media" in m for m in messages),
            f"Очікувалося повідомлення про помилку, але отримано: {messages}"
        )

    # --- media: file ---

        # 2. Тест на валідність медіа
        def test_file_media_created(self):
            self.client.force_login(self.student)

            # ВАЖЛИВО: перевір, чи активний сервіс
            self.service.is_active = True
            self.service.save()

            upload = SimpleUploadedFile("clip.pdf", b"data", content_type="application/pdf")

            data = {
                "service": self.service.id,
                "comment": "Test",
                "specialty_needed": "TENNIS",
                "media_type": "file",
            }

            response = self.client.post(self.url, data=data, files={"media_file": upload}, follow=True)

            # ДЕБАГ: якщо 200, дістаємо помилки
            if response.status_code == 200 and 'form' in response.context:
                form = response.context['form']
                if form.errors:
                    self.fail(f"ФОРМА НЕ ВАЛІДНА: {form.errors.as_data()}")

            self.assertTrue(Request.objects.filter(user=self.student).exists())

    # --- invalid service code ---

    def test_invalid_service_returns_form_error(self):
        self.client.force_login(self.student)

        # 1. POST з неіснуючим ID сервісу (99999)
        response = self.client.post(self.url, {
            "service": 99999,
            "comment": "test",
            "specialty_needed": "TENNIS",
        })

        # 2. Перевіряємо статус 200 (в'юха відрендерила помилку)
        self.assertEqual(response.status_code, 200)

        # 3. Перевіряємо форму БЕЗ assertFormError (якщо він ламається)
        form = response.context.get("form")
        self.assertIsNotNone(form, "Форма не знайдена в контексті!")

        # Перевіряємо, що поле 'service' має помилку
        self.assertIn("service", form.errors, f"Помилки форми: {form.errors}")

    @patch("infrastructure.email.tasks.send_email_task")
    def test_media_failure_rolls_back_request(self, mock_task):
        self.client.force_login(self.student)

        # 1. Використовуємо ValidationError (як у Django), а не просто Exception
        # Це допоможе в'юсі коректно обробити помилку через except ValidationError
        with patch("apps.consulting.models.Media.full_clean", side_effect=ValidationError("broken")):
            data = {
                "service": self.service.id,
                "comment": "test",
                "specialty_needed": "TENNIS",
                "media_type": "link",
                "media_link": "https://x.com"
            }

            # Використовуємо client.post прямо, без хелпера post()
            self.client.post(self.url, data=data, follow=True)

        # 2. Перевірка - чи був здійснений Rollback?
        # Якщо транзакція atomic() спрацювала, Request має бути 0
        self.assertEqual(Request.objects.count(), 0, "Транзакція НЕ відкотилася!")

    # --- atomicity: media failure rolls back request ---

    @patch("infrastructure.email.tasks.send_email_task")
    def test_media_validation_failure_rolls_back_request(self, mock_task):
        self.client.force_login(self.student)

        # 1. Спеціально ламаємо валідацію медіа
        with patch("apps.consulting.models.Media.full_clean", side_effect=ValidationError("broken")):
            data = {
                "service": self.service.id,
                "comment": "test",
                "specialty_needed": "TENNIS",
                "media_type": "link",
                "media_link": "https://x.com"
            }

            # 2. Використовуємо прямий client.post
            response = self.client.post(self.url, data=data, follow=True)

        # 3. Перевірка: чи відбувся відкат транзакції?
        # Якщо транзакція працює, Request не має бути створено,
        # бо Media.full_clean() викликає ValidationError всередині atomic().
        self.assertEqual(Request.objects.count(), 0, "Транзакція не відкотилася: запит залишився в БД!")


# ---------------------------------------------------------------------------
# 3. student_request_detail_view
# ---------------------------------------------------------------------------

class StudentRequestDetailViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.student = make_student()
        self.service = make_service()
        self.request_obj = make_request(self.student, self.service)
        self.url = reverse("student_request_detail", kwargs={"request_id": self.request_obj.pk})



    def test_owner_sees_detail(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["request_item"], self.request_obj)

    def test_non_owner_gets_404(self):
        """Object-level security: other student must not access this request."""
        other = make_student(email="other@example.com")
        self.client.force_login(other)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_report_none_when_missing(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertIsNone(response.context["report"])

    def test_report_in_context_when_exists(self):
        report = Report.objects.create(request=self.request_obj, overall_assessment="Good.")
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.context["report"], report)


# ---------------------------------------------------------------------------
# 4. list_coaches_view
# ---------------------------------------------------------------------------

class ListCoachesViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.student = make_student()
        self.url = reverse("student_list_coaches")


    def test_only_approved_coaches_returned(self):
        approved = make_coach(email="approved@example.com")
        pending = make_coach(email="pending@example.com")
        pending.coach_status = "pending"
        pending.save()

        self.client.force_login(self.student)
        response = self.client.get(self.url)
        coaches = list(response.context["coaches"])
        self.assertIn(approved, coaches)
        self.assertNotIn(pending, coaches)

    def test_non_coach_role_excluded(self):
        """A student with role != 'Coach' must not appear in the list."""
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertNotIn(self.student, list(response.context["coaches"]))


# ---------------------------------------------------------------------------
# 5. file_delete_view
# ---------------------------------------------------------------------------

class FileDeleteViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.student = make_student()
        self.service = make_service()
        self.request_obj = make_request(self.student, self.service)
        self.media = make_media(self.request_obj)
        self.url = reverse("file_delete", kwargs={"pk": self.media.pk})

    def test_get_method_redirects_without_deleting(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("files_attach"))
        self.assertTrue(Media.objects.filter(pk=self.media.pk).exists())

    def test_post_deletes_media(self):
        self.client.force_login(self.student)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("files_attach"))
        self.assertFalse(Media.objects.filter(pk=self.media.pk).exists())

    def test_cannot_delete_another_users_media(self):
        """IDOR guard: other student must get 404, not delete the record."""
        other = make_student(email="other@example.com")
        self.client.force_login(other)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Media.objects.filter(pk=self.media.pk).exists())

    def test_file_storage_deletion_called(self):
        file_media = Media.objects.create(
            request=self.request_obj,
            media_type="file"
        )
        file_media.file.name = "uploads/test.mp4"
        file_media.save()

        url = reverse("file_delete", kwargs={"pk": file_media.pk})
        self.client.force_login(self.student)

        # ПАТЧИМО КЛАС, а не інстанс:
        from django.db.models.fields.files import FieldFile
        with patch.object(FieldFile, 'delete') as mock_delete:
            self.client.post(url)

            # Перевіряємо, чи був виклик
            self.assertTrue(mock_delete.called, "Метод delete не був викликаний")
            # Перевіряємо аргумент
            mock_delete.assert_called_with(save=False)

        self.assertFalse(Media.objects.filter(pk=file_media.pk).exists())


# ---------------------------------------------------------------------------
# 6. bulk_files_delete_view
# ---------------------------------------------------------------------------

class BulkFilesDeleteViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.student = make_student()
        self.service = make_service()
        self.request_obj = make_request(self.student, self.service)
        self.url = reverse("bulk_files_delete")

    def _post_ids(self, ids: list):
        return self.client.post(
            self.url,
            data=json.dumps({"ids": ids}),
            content_type="application/json",
        )


    def test_get_method_not_allowed(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_empty_ids_returns_400(self):
        self.client.force_login(self.student)
        response = self._post_ids([])
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "error")

    def test_deletes_own_media(self):
        m1 = make_media(self.request_obj)
        m2 = make_media(self.request_obj)
        self.client.force_login(self.student)

        response = self._post_ids([m1.pk, m2.pk])
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertFalse(Media.objects.filter(pk__in=[m1.pk, m2.pk]).exists())

    def test_cannot_delete_other_users_media(self):
        other = make_student(email="other@example.com")
        other_request = make_request(other, self.service)
        victim_media = make_media(other_request)

        self.client.force_login(self.student)
        response = self._post_ids([victim_media.pk])

        data = json.loads(response.content)
        # Виправлена перевірка:
        self.assertTrue(Media.objects.filter(pk=victim_media.pk).exists())
        self.assertIn("0", data["message"])  # Перевіряємо, що видалено 0 об'єктів

    def test_partial_ownership_only_own_deleted(self):
        """Mixed IDs: own media deleted, foreign media untouched."""
        own_media = make_media(self.request_obj)
        other = make_student(email="other2@example.com")
        other_request = make_request(other, self.service)
        foreign_media = make_media(other_request)

        self.client.force_login(self.student)
        self._post_ids([own_media.pk, foreign_media.pk])

        self.assertFalse(Media.objects.filter(pk=own_media.pk).exists())
        self.assertTrue(Media.objects.filter(pk=foreign_media.pk).exists())

    def test_invalid_json_returns_500(self):
        self.client.force_login(self.student)
        response = self.client.post(
            self.url,
            data="not-json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# 7. generate_report_docx_view
# ---------------------------------------------------------------------------

class GenerateReportDocxViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.student = make_student()
        # Створюємо тренера, бо звіт зазвичай має автора
        self.coach = make_coach(email="coach@test.com")
        self.service = make_service()
        self.request_obj = make_request(self.student, self.service)

        self.report = Report.objects.create(
            request=self.request_obj,
            created_by=self.coach,  # Прив'язуємо автора звіту
            overall_assessment="Excellent footwork.",
            strength_1="Serve speed",
            priority_1_issue="Backhand",
            priority_1_why="Loses points",
            priority_1_drill="Shadow drill",
            action_plan="Focus on backhand 3x/week.",
        )
        self.url = reverse("generate_report_docx", kwargs={"report_id": self.report.pk})


    def test_returns_docx_content_type(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def test_content_disposition_is_attachment(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(".docx", response["Content-Disposition"])

    def test_response_body_is_valid_docx(self):
        """
        A valid .docx is a ZIP archive. Verify the magic bytes instead of
        importing python-docx into tests — keeps the assertion fast and dependency-free.
        """
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        content = b"".join(response.streaming_content) if hasattr(response, "streaming_content") else response.content
        # ZIP magic bytes: PK\x03\x04
        self.assertEqual(content[:4], b"PK\x03\x04")

    def test_nonexistent_report_returns_404(self):
        self.client.force_login(self.student)
        url = reverse("generate_report_docx", kwargs={"report_id": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_filename_contains_student_identifier(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        disposition = response["Content-Disposition"]
        # Must contain either short name or student PK — not an empty segment
        self.assertRegex(disposition, r'filename="Tennis_Analysis_.+\.docx"')



class PsychologyDashboardAccessTests(TestCase):
    url = reverse('psychology')

    @classmethod
    def setUpTestData(cls):
        cls.psychologist = User.objects.create_user(
            email='psy@test.com', password='pwd', role='Psychology'
        )
        cls.student = User.objects.create_user(
            email='student@test.com', password='pwd', role='Student'
        )

    def test_psychologist_can_access_dashboard(self):
        """Користувач із роллю Psychology успішно заходить на свій дашборд."""
        self.client.force_login(self.psychologist)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/psychology/index.html")

    def test_student_is_forbidden_from_psychology_dashboard(self):
        """Студент отримує 403 при спробі зайти на дашборд психолога."""
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
