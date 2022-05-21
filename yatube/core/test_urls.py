from django.test import TestCase


class ViewTestClass(TestCase):
    def test_error_page(self):
        """Тестрирование ответа на запрос к несуществующей странице"""
        response = self.client.get('/nonexist-page/')
        self.assertTemplateUsed(response, 'core/404.html')
        self.assertEqual(response.status_code, 404)
