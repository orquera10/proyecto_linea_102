from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class RegisterViewTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'usuario',
                'email': 'usuario@example.com',
                'password1': 'ClaveSegura123',
                'password2': 'ClaveSegura123',
            },
        )

        self.assertRedirects(response, reverse('home'))
        self.assertTrue(User.objects.filter(username='usuario').exists())

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(
            username='existente',
            email='usuario@example.com',
            password='ClaveSegura123',
        )

        response = self.client.post(
            reverse('register'),
            {
                'username': 'nuevo',
                'email': 'usuario@example.com',
                'password1': 'ClaveSegura123',
                'password2': 'ClaveSegura123',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe un usuario con este email.')
        self.assertFalse(User.objects.filter(username='nuevo').exists())

# Create your tests here.
