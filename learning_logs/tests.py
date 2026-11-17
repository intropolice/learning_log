from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Entry, Topic

User = get_user_model()


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class TopicAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner')
        self.other = User.objects.create_user(username='other')
        self.topic = Topic.objects.create(text='Django', owner=self.owner)
        self.topic_url = reverse('learning_logs:topic', args=[self.topic.id])
        self.entry = Entry.objects.create(topic=self.topic, text='Первый конспект')

    def test_guest_is_sent_to_login(self):
        response = self.client.get(self.topic_url)
        self.assertRedirects(response, reverse('users:login') + '?next=' + self.topic_url)

    def test_owner_can_open_topic(self):
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.topic_url), self.topic.text)

    def test_other_user_cannot_open_topic(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.topic_url).status_code, 404)

    def test_get_does_not_log_user_out(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('users:logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_homepage_is_public(self):
        self.assertContains(self.client.get(reverse('learning_logs:index')), 'Learning Log')

    def test_all_private_routes_redirect_guest(self):
        urls = [reverse('learning_logs:topics'), self.topic_url,
                reverse('learning_logs:new_topic'),
                reverse('learning_logs:new_entry', args=[self.topic.id]),
                reverse('learning_logs:edit_entry', args=[self.entry.id])]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)
                self.assertEqual(self.client.post(url, {'text': 'Чужое изменение'}).status_code, 302)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.text, 'Первый конспект')

    def test_topics_only_contain_owners_topics(self):
        other_topic = Topic.objects.create(text='Чужая приватная тема', owner=self.other)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('learning_logs:topics'))
        self.assertContains(response, self.topic.text)
        self.assertNotContains(response, other_topic.text)

    def test_other_user_cannot_add_or_edit_entry(self):
        self.client.force_login(self.other)
        for url in [reverse('learning_logs:new_entry', args=[self.topic.id]),
                    reverse('learning_logs:edit_entry', args=[self.entry.id])]:
            for method in ['get', 'post']:
                with self.subTest(url=url, method=method):
                    response = getattr(self.client, method)(url, {'text': 'Взлом'})
                    self.assertEqual(response.status_code, 404)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.text, 'Первый конспект')
        self.assertEqual(Entry.objects.count(), 1)

    def test_missing_objects_return_404(self):
        self.client.force_login(self.owner)
        for name in ['topic', 'new_entry', 'edit_entry']:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse('learning_logs:' + name, args=[999999])).status_code, 404)

    def test_entries_are_newest_first(self):
        newer = Entry.objects.create(topic=self.topic, text='Новейшая запись')
        Entry.objects.filter(pk=self.entry.pk).update(date_added=timezone.now() - timedelta(days=1))
        self.client.force_login(self.owner)
        response = self.client.get(self.topic_url)
        self.assertEqual(list(response.context['entries']), [newer, self.entry])

    def test_topics_are_oldest_first(self):
        newer = Topic.objects.create(owner=self.owner, text='Вторая тема')
        Topic.objects.filter(pk=self.topic.pk).update(date_added=timezone.now() - timedelta(days=1))
        self.client.force_login(self.owner)
        response = self.client.get(reverse('learning_logs:topics'))
        self.assertEqual(list(response.context['topics']), [self.topic, newer])

    def test_owner_can_open_edit_and_create_forms(self):
        self.client.force_login(self.owner)
        for name, args in [('new_topic', []), ('new_entry', [self.topic.id]), ('edit_entry', [self.entry.id])]:
            self.assertEqual(self.client.get(reverse('learning_logs:' + name, args=args)).status_code, 200)

    def test_new_topic_uses_logged_in_owner(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('learning_logs:new_topic'), {'text': 'Python', 'owner': self.other.id})
        self.assertRedirects(response, reverse('learning_logs:topics'))
        self.assertEqual(Topic.objects.get(text='Python').owner, self.owner)

    def test_invalid_topics_not_saved(self):
        self.client.force_login(self.owner)
        for text in ['', '   ', 'x' * 201]:
            response = self.client.post(reverse('learning_logs:new_topic'), {'text': text})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.assertEqual(Topic.objects.count(), 1)

    def test_new_entry_assigned_to_url_topic(self):
        self.client.force_login(self.owner)
        foreign = Topic.objects.create(text='Чужая', owner=self.other)
        response = self.client.post(reverse('learning_logs:new_entry', args=[self.topic.id]),
                                    {'text': 'Новая заметка', 'topic': foreign.id})
        self.assertRedirects(response, self.topic_url)
        self.assertEqual(Entry.objects.get(text='Новая заметка').topic, self.topic)

    def test_blank_entry_not_saved(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('learning_logs:new_entry', args=[self.topic.id]), {'text': '   '})
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(Entry.objects.count(), 1)

    def test_edit_changes_text_not_date_or_topic(self):
        self.client.force_login(self.owner)
        initial_date = self.entry.date_added
        foreign = Topic.objects.create(text='Чужая', owner=self.other)
        response = self.client.post(reverse('learning_logs:edit_entry', args=[self.entry.id]),
                                    {'text': 'Исправленный конспект', 'topic': foreign.id})
        self.assertRedirects(response, self.topic_url)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.text, 'Исправленный конспект')
        self.assertEqual(self.entry.date_added, initial_date)
        self.assertEqual(self.entry.topic, self.topic)

    def test_invalid_edit_does_not_erase_text(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('learning_logs:edit_entry', args=[self.entry.id]), {'text': ''})
        self.assertTrue(response.context['form'].errors)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.text, 'Первый конспект')

    def test_html_is_escaped_and_linebreaks_preserved(self):
        self.entry.text = '<script>alert(1)</script>\nВторая строка'
        self.entry.save()
        self.client.force_login(self.owner)
        response = self.client.get(self.topic_url)
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertContains(response, '<br>')

    def test_csrf_required_for_mutations_and_logout(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for url in [reverse('learning_logs:new_topic'), reverse('users:logout'),
                    reverse('learning_logs:new_entry', args=[self.topic.id]),
                    reverse('learning_logs:edit_entry', args=[self.entry.id])]:
            self.assertEqual(client.post(url, {'text': 'No CSRF'}).status_code, 403)

    def test_empty_states(self):
        self.client.force_login(self.other)
        self.assertContains(self.client.get(reverse('learning_logs:topics')), 'Тем пока нет')
        topic = Topic.objects.create(text='Пустая', owner=self.other)
        self.assertContains(self.client.get(reverse('learning_logs:topic', args=[topic.id])), 'Первая запись')

    def test_model_strings_and_cascade(self):
        self.assertEqual(str(self.topic), 'Django')
        self.entry.text = 'x' * 60
        self.assertEqual(str(self.entry), 'x' * 50 + '...')
        self.topic.delete()
        self.assertFalse(Entry.objects.filter(pk=self.entry.pk).exists())

    def test_user_delete_cascades_topics(self):
        self.owner.delete()
        self.assertFalse(Topic.objects.exists())
        self.assertFalse(Entry.objects.exists())


@override_settings(DEBUG=True)
class DemoProfileTests(TestCase):
    def seed(self):
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_demo', stdout=StringIO())

    def test_demo_created_with_examples_and_can_login(self):
        self.seed()
        user = User.objects.get(username='demo')
        self.assertTrue(self.client.login(username='demo', password='LearningLog2026!'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(Topic.objects.filter(owner=user).count(), 3)
        self.assertEqual(Entry.objects.filter(topic__owner=user).count(), 6)

    def test_repeated_seed_preserves_edits_and_does_not_duplicate(self):
        self.seed()
        topic = Topic.objects.first()
        topic.text = 'Изменённая тема'
        topic.save()
        entry = Entry.objects.first()
        entry.text = 'Мой конспект'
        entry.save()
        self.seed()
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Topic.objects.count(), 3)
        self.assertEqual(Entry.objects.count(), 6)
        topic.refresh_from_db()
        entry.refresh_from_db()
        self.assertEqual(topic.text, 'Изменённая тема')
        self.assertEqual(entry.text, 'Мой конспект')

    def test_existing_other_account_not_overwritten(self):
        from django.core.management.base import CommandError
        user = User.objects.create_user(username='demo', password='Other-Password!')
        with self.assertRaises(CommandError):
            self.seed()
        user.refresh_from_db()
        self.assertTrue(user.check_password('Other-Password!'))
        self.assertEqual(Topic.objects.count(), 0)

    def test_admin_account_not_reused(self):
        from django.core.management.base import CommandError
        user = User.objects.create_superuser(username='demo', password='LearningLog2026!')
        with self.assertRaises(CommandError):
            self.seed()
        user.refresh_from_db()
        self.assertTrue(user.is_superuser)
        self.assertEqual(Topic.objects.count(), 0)

    def test_inactive_account_not_reactivated(self):
        from django.core.management.base import CommandError
        user = User.objects.create_user(username='demo', password='LearningLog2026!', is_active=False)
        with self.assertRaises(CommandError):
            self.seed()
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    @override_settings(DEBUG=False)
    def test_production_seed_refused(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self.seed()
        self.assertFalse(User.objects.filter(username='demo').exists())
