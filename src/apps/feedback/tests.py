from typing import Any, cast
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import FeedbackForm
from .models import Feedback, FAQItem, FAQCategory

User: Any = get_user_model()

class ContactUsViewTest(TestCase):
    url = reverse('contact_us')
    expected_name = 'Test User'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpassword123',
            first_name='Test',
            last_name='User',
            role='Student',
        )

    def test_contact_us_requires_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_contact_us_get_prefills_data(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)
        form = response.context['form']

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(form, FeedbackForm)
        self.assertEqual(form.initial['email'], self.user.email)
        self.assertEqual(form.initial['name'], self.expected_name)

    def assert_feedback_created(self, data, mock_send_notification):
        response = self.client.post(self.url, data)

        self.assertRedirects(response, self.url)
        self.assertEqual(Feedback.objects.count(), 1)

        feedback = cast(Feedback, Feedback.objects.get())
        self.assertEqual(feedback.subject, data['subject'])
        self.assertEqual(feedback.message, data['message'])
        self.assertEqual(feedback.email, self.user.email)
        self.assertEqual(feedback.name, self.expected_name)
        self.assertEqual(feedback.user, self.user)
        mock_send_notification.assert_called_once_with(feedback)

    @patch('apps.feedback.views.send_feedback_notification')
    def test_contact_us_post_valid_data_and_security(self, mock_send_notification):
        self.client.force_login(self.user)

        data = {
            'name': 'Alex',
            'email': 'alex@example.com',
            'subject': 'Malicious or Alternate Subject',
            'message': 'This is a test message to verify security restrictions.',
        }

        self.assert_feedback_created(data, mock_send_notification)

    @patch('apps.feedback.views.send_feedback_notification')
    def test_contact_us_post_valid_data(self, mock_send_notification):
        self.client.force_login(self.user)

        data = {
            'name': 'Alternate Name',
            'email': 'alternate@example.com',
            'subject': 'Need Help',
            'message': 'This is a test message.',
        }

        self.assert_feedback_created(data, mock_send_notification)


class FAQListViewTests(TestCase):
    """
    Тести для дашборду FAQ (Питання та Відповіді).
    """
    url = reverse('faq_list')  # Якщо назва урлу в urls.py відрізняється, підстав свою

    @classmethod
    def setUpTestData(cls):
        # Створюємо користувача для проходження захисту @login_required
        cls.user = User.objects.create_user(
            email='faqstudent@example.com',
            password='testpassword123',
            first_name='FAQ',
            last_name='Student',
            role='Student',
        )

        # 1. Створюємо ВАЛІДНІ дані (активна категорія + опубліковане питання)
        cls.active_category = FAQCategory.objects.create(
            title="General Questions",
            slug="general-questions",
            sort_order=1,
            is_active=True
        )
        cls.published_item = FAQItem.objects.create(
            category=cls.active_category,
            question="How to book a court?",
            answer="Use the online dashboard calendar.",
            sort_order=1,
            is_published=True
        )

        # 2. Створюємо НЕВАЛІДНІ дані (для тестування залізобетонної фільтрації контенту)
        cls.inactive_category = FAQCategory.objects.create(
            title="Hidden Category",
            slug="hidden-category",
            sort_order=2,
            is_active=False
        )
        cls.unpublished_item = FAQItem.objects.create(
            category=cls.active_category,
            question="Draft Question?",
            answer="This is a draft and should not be displayed.",
            sort_order=2,
            is_published=False
        )

    def test_faq_page_requires_login(self):
        """Перевірка, що анонімного користувача не пустить декоратор @login_required."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_faq_page_success_for_authenticated_user(self):
        """Авторизований користувач успішно отримує сторінку FAQ з правильним шаблоном."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, 'feedback/faq_page.html')

    def test_faq_page_filters_and_prefetches_data_correctly(self):
        """
        Перевірка, що в'юха віддає тільки активні категорії та опубліковані питання
        через наш оптимізований атрибут `published_items`.
        """
        self.client.force_login(self.user)

        response = self.client.get(self.url)
        categories_in_context = response.context['categories']

        # Перевірка фільтрації категорій на рівні БД
        self.assertEqual(categories_in_context.count(), 1)
        self.assertEqual(categories_in_context[0], self.active_category)
        self.assertNotIn(self.inactive_category, categories_in_context)

        # Перевірка наявності та фільтрації префетч-атрибуту
        first_category = categories_in_context[0]
        self.assertTrue(hasattr(first_category, 'published_items'))

        published_items = first_category.published_items
        self.assertEqual(len(published_items), 1)
        self.assertEqual(published_items[0], self.published_item)
        self.assertNotIn(self.unpublished_item, published_items)

    def test_faq_page_renders_correct_html_content(self):
        """Перевірка, що тільки дозволений контент фізично рендериться в HTML коді."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        # Перевіряємо наявність валідного контенту
        self.assertContains(response, self.active_category.title)
        self.assertContains(response, self.published_item.question)
        self.assertContains(response, self.published_item.answer)

        # Перевіряємо відсутність прихованого контенту
        self.assertNotContains(response, self.inactive_category.title)
        self.assertNotContains(response, self.unpublished_item.question)
