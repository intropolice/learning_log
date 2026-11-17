#!/usr/bin/env python3
"""Первый запуск и запуск локального сервера. Только для разработки."""
import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def run(command):
    subprocess.run([str(part) for part in command], cwd=ROOT, check=True)


def python312():
    """Находим Python 3.12 без зависимости от активированного окружения."""
    candidates = [[sys.executable]]
    for name in ('python3.12', 'python3', 'python'):
        path = shutil.which(name)
        if path:
            candidates.append([path])
    if os.name == 'nt' and shutil.which('py'):
        candidates.append(['py', '-3.12'])
    for command in candidates:
        try:
            result = subprocess.run(
                command + ['-c', 'import sys; print("%d.%d" % sys.version_info[:2])'],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip() == '3.12':
                return command
        except (OSError, subprocess.TimeoutExpired):
            continue
    raise RuntimeError('Python 3.12 не найден. Установите Python 3.12 и повторите запуск.')


def main():
    parser = argparse.ArgumentParser(description='Подготовка Learning Log и запуск локального Django-сервера')
    parser.add_argument('--port', type=int, default=8000, help='Локальный порт (по умолчанию 8000)')
    parser.add_argument('--setup-only', action='store_true', help='Только установить зависимости и подготовить базу')
    parser.add_argument('--skip-install', action='store_true', help='Пропустить pip, если зависимости уже установлены')
    parser.add_argument('--no-demo', action='store_true', help='Не создавать демонстрационный аккаунт')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Порт должен быть от 1 до 65535.')

    # Сначала проверяем порт, чтобы не открыть случайно другой локальный сервис.
    if not args.setup_only:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('127.0.0.1', args.port))
            except OSError as error:
                raise RuntimeError(
                    'Не удалось занять порт %s: %s. Возможно, сервер уже запущен. '
                    'Проверьте его терминал или выберите другой порт: python start.py --port 8001.'
                    % (args.port, error)
                ) from error

    env = ROOT / 'll_env'
    executable = env / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not executable.exists():
        print('Создаём локальное окружение ll_env на Python 3.12…', flush=True)
        run(python312() + ['-m', 'venv', str(env)])
    result = subprocess.run([str(executable), '-c', 'import sys; print("%d.%d" % sys.version_info[:2])'],
                            capture_output=True, text=True, check=True)
    if result.stdout.strip() != '3.12':
        raise RuntimeError('Окружение ll_env создано не на Python 3.12. Переименуйте его и повторите запуск.')
    if not args.skip_install:
        print('Проверяем и устанавливаем зависимости (первый запуск требует интернета)…', flush=True)
        # Установка строго в ll_env, даже если пользователь настроил pip install --user.
        install_env = dict(os.environ, PIP_USER='0')
        subprocess.run([str(executable), '-m', 'pip', 'install', '--disable-pip-version-check',
                        '-r', str(ROOT / 'requirements.txt')], cwd=ROOT, env=install_env, check=True)
    run([executable, ROOT / 'manage.py', 'migrate', '--noinput'])
    run([executable, ROOT / 'manage.py', 'check'])
    if not args.no_demo:
        demo_result = subprocess.run([str(executable), str(ROOT / 'manage.py'), 'seed_demo'], cwd=ROOT)
        if demo_result.returncode:
            print('Демо-профиль не создан: причина указана выше. Сервер можно использовать со своим аккаунтом.', flush=True)
    if args.setup_only:
        print('Подготовка завершена. Для запуска: python start.py', flush=True)
        return 0
    print('\nАдрес формы входа: http://127.0.0.1:%s/users/login/' % args.port, flush=True)
    print('Откройте адрес ПОСЛЕ строки «Starting development server».', flush=True)
    print('Не закрывайте этот терминал: он обслуживает сайт. Остановка — Ctrl+C.\n', flush=True)
    run([executable, ROOT / 'manage.py', 'runserver', '127.0.0.1:%s' % args.port])
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nЛокальный сервер остановлен. Для следующего запуска снова выполните python start.py.')
        sys.exit(0)
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print('\nЗапуск не завершён: %s' % error, file=sys.stderr)
        print('Сохраните текст ошибки из этого терминала. Пока сервер не запущен, адрес в браузере работать не будет.', file=sys.stderr)
        sys.exit(1)
