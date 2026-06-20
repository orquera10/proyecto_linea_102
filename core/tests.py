from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import NoReverseMatch, reverse


class AuthNavigationTests(TestCase):
    def test_register_route_is_removed(self):
        with self.assertRaises(NoReverseMatch):
            reverse('register')

    def test_login_page_does_not_offer_public_registration(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Registrarse')
        self.assertNotContains(response, 'Registrate')

    def test_login_redirects_to_stats(self):
        get_user_model().objects.create_user(
            username='operador',
            password='ClaveSegura123',
        )

        response = self.client.post(
            reverse('login'),
            {'username': 'operador', 'password': 'ClaveSegura123'},
        )

        self.assertRedirects(response, reverse('llamadas:stats'))

    def test_home_redirects_authenticated_users_to_stats(self):
        user = get_user_model().objects.create_user(
            username='operador',
            password='ClaveSegura123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('llamadas:stats'))

    def test_navbar_shows_brand_and_user_menu(self):
        user = get_user_model().objects.create_user(
            username='operador',
            password='ClaveSegura123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('llamadas:stats'))

        self.assertContains(response, 'Panel de llamadas')
        self.assertContains(response, 'user-menu')
        self.assertContains(response, 'Cerrar sesion')

    def test_staff_profile_link_goes_to_admin(self):
        user = get_user_model().objects.create_user(
            username='admin',
            password='ClaveSegura123',
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('llamadas:stats'))

        self.assertContains(response, f'href="{reverse("admin:index")}"')
