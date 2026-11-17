"""Публичные учебные реквизиты, только для локальной демонстрации."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from learning_logs.models import Entry, Topic

DEMO_USERNAME = 'demo'
DEMO_PASSWORD = 'LearningLog2026!'
DEMO_DATA = [
    ('Python и Django', [
        'Django разделяет код на модели, представления и шаблоны.\n\nМодель описывает данные, представление обрабатывает запрос, шаблон формирует HTML.',
        'Формы проверяют введённые данные.\n\nПопробуйте отредактировать эту запись или добавить свою. Чужие темы недоступны обычным пользователям.',
    ]),
    ('Английский язык', [
        'Слова на сегодня:\nlearn — учиться\npractice — практиковаться\nprogress — прогресс\n\nПридумайте по одному предложению с каждым словом.',
        'Present Simple подходит для привычек и регулярных действий.\n\nI learn English every day.\nShe reads books in the evening.',
    ]),
    ('Книги и идеи', [
        'Идея для обучения: после каждой главы записывать три главные мысли и один вопрос.\n\nТакая заметка помогает вернуться к прочитанному.',
        'План на неделю:\n1. Прочитать одну главу.\n2. Написать короткий конспект.\n3. Применить одну идею на практике.\n\nЭто демонстрационные данные — их можно свободно менять.',
    ]),
]


class Command(BaseCommand):
    help = 'Создать локальный demo-аккаунт и примеры, не изменяя существующие данные.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Демо-аккаунт с общедоступным паролем разрешён только при DJANGO_DEBUG=True. Не используйте его на публичном сервере.')
        User = get_user_model()
        user = User.objects.filter(username=DEMO_USERNAME).first()
        if user is not None:
            if user.is_staff or user.is_superuser or not user.is_active or not user.check_password(DEMO_PASSWORD):
                raise CommandError('Имя demo уже занято другим или изменённым аккаунтом. Его пароль, права и записи НЕ изменены. Создайте свой аккаунт через регистрацию.')
            self.stdout.write('Демо-аккаунт уже существует. Темы, записи и их изменения сохранены без повторного заполнения.')
        else:
            user = User.objects.create_user(username=DEMO_USERNAME, password=DEMO_PASSWORD,
                                            first_name='Демо', last_name='Пользователь')
            for title, texts in DEMO_DATA:
                topic = Topic.objects.create(owner=user, text=title)
                for text in texts:
                    Entry.objects.create(topic=topic, text=text)
            self.stdout.write(self.style.SUCCESS('Создан демо-профиль: 3 темы и 6 записей. Административных прав нет.'))
        self.stdout.write('Логин: %s | Пароль: %s' % (DEMO_USERNAME, DEMO_PASSWORD))
        self.stdout.write('Только учебные данные. Не храните личные сведения и не публикуйте этот аккаунт.')
