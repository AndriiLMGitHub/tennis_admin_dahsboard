from typing import Any
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

User: Any = get_user_model()


class RoleSelectionViewTests(TestCase):
    """Тести для контролера вибору ролі (select_role)"""
    url = reverse('select_role')  # Перевір ім'я в urls.py

    @classmethod
    def setUpTestData(cls):
        # User без ролі
        cls.new_user = User.objects.create_user(
            email='newbie@test.com', password='password123', role=None
        )
        # Суперюзер
        cls.admin_user = User.objects.create_superuser(
            email='admin@test.com', password='password123'
        )
        # User, який вже має роль
        cls.student_user = User.objects.create_user(
            email='student@test.com', password='password123', role='Student'
        )

    def test_redirects_superuser_to_admin(self):
        """Superuser має бути негайно перенаправлений в адмінку."""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('admin:index'), fetch_redirect_response=False)

    def test_redirects_user_with_existing_role(self):
        """Якщо роль вже обрана, user має бути відправлений на головну."""
        self.client.force_login(self.student_user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('index'))

    def test_select_role_student_success(self):
        """Успішний вибір ролі Студента (без виклику Celery)."""
        self.client.force_login(self.new_user)
        response = self.client.post(self.url, {'role': 'Student'})

        self.new_user.refresh_from_db()
        self.assertEqual(self.new_user.role, 'Student')
        self.assertIsNone(self.new_user.coach_status)
        self.assertRedirects(response, reverse('index'))

    @patch('infrastructure.email.tasks.send_email_task.delay')
    def test_select_role_coach_success_triggers_celery(self, mock_send_email):
        """Успішний вибір ролі Coach має змінити статус та викликати Celery таску."""

        user = User.objects.create_user(
            email='futurecoach@test.com',
            password='pwd',
            role=None
        )
        self.client.force_login(user)

        response = self.client.post(self.url, {'role': 'Coach'})

        user.refresh_from_db()
        self.assertEqual(user.role, 'Coach')
        self.assertEqual(user.coach_status, 'pending')
        self.assertRedirects(response, reverse('index'))

        self.assertEqual(mock_send_email.call_count, 2)


class ProfileRouterViewTests(TestCase):
    """Тести для універсального роутера профілю (profile_router_view)"""
    url = reverse('profile_router')

    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(email='s@test.com', password='pwd', role='Student')
        cls.coach = User.objects.create_user(email='c@test.com', password='pwd', role='Coach')
        cls.unknown = User.objects.create_user(email='u@test.com', password='pwd', role='Alien')

    def test_router_redirects_student(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('student_profile'))

    def test_router_redirects_coach(self):
        self.client.force_login(self.coach)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('coach_profile'))

    def test_router_raises_404_for_unknown_role(self):
        """Якщо роль невідома, роутер має викинути Http404."""
        self.client.force_login(self.unknown)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)


class StudentProfileEditViewTests(TestCase):
    """Тести редагування профілю з фокусом на транзакції та файли"""
    url = reverse('student_profile_edit')

    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(
            email='edit@test.com', password='pwd', role='Student', first_name='Old'
        )

    def test_profile_edit_text_fields_success(self):
        """Перевірка успішного оновлення текстових полів."""
        self.client.force_login(self.student)
        data = {
            'first_name': 'NewName  ',  # Тестуємо .strip()
            'last_name': 'Smith',
            'country': 'UA'
        }
        response = self.client.post(self.url, data)

        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'NewName')  # Пробіли мають бути видалені
        self.assertEqual(self.student.country, 'UA')

        # Перевірка фреймворку повідомлень
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "You have successfully updated your profile.")
        self.assertRedirects(response, self.url)

    def test_profile_edit_avatar_upload(self):
        """Перевірка логіки завантаження файлу аватара."""
        self.client.force_login(self.student)

        # Створюємо фейковий файл у пам'яті
        avatar_mock = SimpleUploadedFile(
            name='test_avatar.jpg',
            content=b'file_content',
            content_type='image/jpeg'
        )

        response = self.client.post(self.url, {'avatar': avatar_mock})
        self.student.refresh_from_db()

        self.assertTrue(bool(self.student.avatar))
        self.assertRedirects(response, self.url)

    def test_profile_edit_avatar_remove(self):
        """Перевірка прапорця avatar_remove=1."""
        # Спочатку даємо юзеру файл
        self.student.avatar = SimpleUploadedFile('old.jpg', b'content')
        self.student.save()

        self.client.force_login(self.student)
        response = self.client.post(self.url, {'avatar_remove': '1'})

        self.student.refresh_from_db()
        # Поле має бути очищене
        self.assertFalse(bool(self.student.avatar))


class DeactivateAccountViewTests(TestCase):
    """Тестування критичного ендпоінту деактивації (deactivate_account_view)"""

    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(email='del@test.com', password='pwd', role='Student')

    def get_url(self, role='Student'):
        if role == 'Coach':
            return reverse('coach_deactivate_account')
        return reverse('student_deactivate_account')

    def test_deactivate_fails_without_checkbox(self):
        """Без checkbox confirm_deactivation акаунт НЕ деактивується."""
        self.client.force_login(self.student)
        response = self.client.post(self.get_url('Student'))

        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "You must check the box to confirm deactivation.")

    def test_deactivate_fails_on_role_mismatch(self):
        """Студент не може смикнути ендпоінт деактивації Coach."""
        self.client.force_login(self.student)
        # Студент намагається відправити POST на маршрут 'coach_deactivate_account'
        response = self.client.post(self.get_url('Coach'), {'confirm_deactivation': 'on'})

        self.assertEqual(response.status_code, 403)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

    def test_deactivate_success_soft_delete_and_logout(self):
        """Успішна деактивація: soft delete + знищення сесії."""
        self.client.force_login(self.student)
        self.assertIn('_auth_user_id', self.client.session)

        response = self.client.post(self.get_url('Student'), {'confirm_deactivation': 'on'})

        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)

        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertRedirects(response, reverse('account_login'), fetch_redirect_response=False)