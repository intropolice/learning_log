from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

User = get_user_model()


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class AuthenticationTests(TestCase):
    password = 'Testing-Log-2026-Unique!'

    def test_register_logs_in(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'student', 'password1': self.password, 'password2': self.password})
        self.assertRedirects(response, reverse('learning_logs:index'))
        user = User.objects.get(username='student')
        self.assertTrue(user.check_password(self.password))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)

    def test_weak_or_mismatched_passwords_rejected(self):
        for p1, p2 in [('123', '123'), (self.password, 'another-password')]:
            response = self.client.post(reverse('users:register'), {
                'username': 'student', 'password1': p1, 'password2': p2})
            self.assertTrue(response.context['form'].errors)
        self.assertFalse(User.objects.exists())

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username='student')
        response = self.client.post(reverse('users:register'), {
            'username': 'student', 'password1': self.password, 'password2': self.password})
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_login_next_and_post_logout(self):
        User.objects.create_user(username='student', password=self.password)
        response = self.client.post(reverse('users:login'), {
            'username': 'student', 'password': self.password, 'next': reverse('learning_logs:topics')})
        self.assertRedirects(response, reverse('learning_logs:topics'))
        response = self.client.post(reverse('users:logout'))
        self.assertContains(response, 'Вы вышли из аккаунта')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_external_next_not_allowed(self):
        User.objects.create_user(username='student', password=self.password)
        response = self.client.post(reverse('users:login'), {
            'username': 'student', 'password': self.password, 'next': 'https://example.org/'})
        self.assertRedirects(response, reverse('learning_logs:index'))

    def test_wrong_password_shows_error(self):
        User.objects.create_user(username='student', password=self.password)
        response = self.client.post(reverse('users:login'), {'username': 'student', 'password': 'wrong'})
        self.assertTrue(response.context['form'].errors)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_auth_forms_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        for name in ['register', 'login']:
            self.assertEqual(client.post(reverse('users:' + name), {}).status_code, 403)

    def test_login_get_renders_form(self):
        response = self.client.get(reverse('users:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, reverse('users:register'))

    def test_login_get_preserves_next(self):
        response = self.client.get(reverse('users:login'), {'next': reverse('learning_logs:topics')})
        self.assertContains(response, 'name="next" value="/topics/"')

    def test_login_with_real_csrf_cookie(self):
        user = User.objects.create_user(username='student', password=self.password)
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('users:login'))
        token = client.cookies['csrftoken'].value
        response = client.post(reverse('users:login'), {
            'username': 'student', 'password': self.password,
            'csrfmiddlewaretoken': token, 'next': reverse('learning_logs:topics'),
        })
        self.assertRedirects(response, reverse('learning_logs:topics'))
        self.assertEqual(int(client.session['_auth_user_id']), user.id)
