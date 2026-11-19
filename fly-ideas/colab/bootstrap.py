"""Pinned standalone CPython for Colab; never alters the Colab kernel or Drive."""
import hashlib
import json
import os
from pathlib import Path
import platform
import queue
import signal
import shutil
import subprocess
import threading
import tarfile
import tempfile
import urllib.request

PYTHON_VERSION = '3.12.16'
PYTHON_ARCHIVE_URL = 'https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.12.16%2B20261026-x86_64-unknown-linux-gnu-install_only.tar.gz'
PYTHON_ARCHIVE_SHA256 = '6a79e922e50006b601f29e688407659da1c2b86ebcd4e9c7254cf234be8b89de'


def clean_python_env():
    env = os.environ.copy()
    for name in ('PYTHONHOME', 'PYTHONPATH', 'VIRTUAL_ENV', 'CONDA_PREFIX'):
        env.pop(name, None)
    env['PYTHONNOUSERSITE'] = '1'
    return env


def run_with_output(command, env, heartbeat=20):
    """Stream child stdout/stderr into the notebook rather than the kernel's OS fd."""
    process_env = dict(env, PYTHONUNBUFFERED='1', PYTHONIOENCODING='utf-8')
    process = subprocess.Popen(command, env=process_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding='utf8', errors='replace', bufsize=1, start_new_session=True)
    messages = queue.Queue()
    end = object()
    def reader():
        try:
            for line in process.stdout:
                messages.put(line)
        finally:
            messages.put(end)
    threading.Thread(target=reader, name='fly-colab-output', daemon=True).start()

    def drain():
        while True:
            try:
                message = messages.get(timeout=heartbeat)
            except queue.Empty:
                if process.poll() is None:
                    print('Нет новых строк; процесс ещё работает. Это не подтверждает прогресс.', flush=True)
                else:
                    # A crashed parent must not leave worker processes running unseen.
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                continue
            if message is end:
                break
            print(message, end='', flush=True)
        return process.wait()

    try:
        code = drain()
    except KeyboardInterrupt:
        print('Запрошена остановка. Ждём сохранения доступного прогресса; не запускайте вторую копию.', flush=True)
        try:
            process.send_signal(signal.SIGINT)
        except ProcessLookupError:
            pass
        try:
            drain()
        except KeyboardInterrupt:
            print('Повторное прерывание: принудительная остановка. Несохранённые повторы могут потеряться.', flush=True)
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        raise
    if code:
        raise subprocess.CalledProcessError(code, command)
    return code


def hash_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def executable_version(executable, env):
    result = subprocess.run([str(executable), '-c', 'import sys;print(".".join(map(str,sys.version_info[:3])))'],
                            env=env, check=True, text=True, capture_output=True, timeout=30)
    return result.stdout.strip()


def safe_extract(archive, destination):
    """Permit only archive members and link targets contained within destination."""
    root = Path(destination).resolve()
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar:
            name = Path(member.name)
            if name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0] != 'python':
                raise ValueError('Архив Python содержит недопустимый путь.')
            target = (root / name).resolve()
            if target != root and root not in target.parents:
                raise ValueError('Архив Python пытается записать файл вне своей папки.')
            if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                raise ValueError('Архив Python содержит неподдерживаемый тип файла.')
            if member.issym() or member.islnk():
                link = Path(member.linkname)
                if link.is_absolute():
                    raise ValueError('Архив Python содержит абсолютную ссылку.')
                resolved = ((target.parent if member.issym() else root) / link).resolve()
                if resolved != root and root not in resolved.parents:
                    raise ValueError('Архив Python содержит ссылку за пределы папки.')
            if hasattr(tarfile, 'data_filter'):
                tar.extract(member, path=root, filter='data')
            else:
                tar.extract(member, path=root)


def ensure_python_312(base, url=PYTHON_ARCHIVE_URL, expected_sha=PYTHON_ARCHIVE_SHA256, version=PYTHON_VERSION):
    if platform.system() != 'Linux' or platform.machine().lower() not in ('x86_64', 'amd64'):
        raise RuntimeError('Нужна стандартная Linux x86-64 среда Google Colab.')
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    install = base / ('fly-shiu-python-' + version)
    python = install / 'bin/python3.12'
    marker = install / '.fly-python.json'
    env = clean_python_env()
    if install.exists():
        if install.is_symlink() or not marker.is_file() or not python.is_file():
            raise RuntimeError('Временная папка Python уже существует, но не подтверждена; она не изменена. Перезапустите среду Colab.')
        info = json.loads(marker.read_text(encoding='utf8'))
        if info.get('archive_sha256') != expected_sha or info.get('version') != version or info.get('executable_sha256') != hash_file(python) or executable_version(python, env) != version:
            raise RuntimeError('Временный Python изменён. Он не будет перезаписан; перезапустите среду Colab.')
        print('Используем проверенный Python', version, flush=True)
        return python
    print('Скачиваем отдельный Python', version, '(около 68 МБ); ядро Colab не меняется...', flush=True)
    with tempfile.TemporaryDirectory(prefix='fly-shiu-python-', dir=base) as temp:
        temp = Path(temp)
        archive = temp / 'python.tar.gz'
        digest = hashlib.sha256()
        try:
            with urllib.request.urlopen(url, timeout=90) as source, archive.open('xb') as dest:
                size = 0
                while True:
                    block = source.read(1024 * 1024)
                    if not block:
                        break
                    size += len(block)
                    if size > 150 * 1024 * 1024:
                        raise ValueError('Архив Python больше ожидаемого.')
                    digest.update(block)
                    dest.write(block)
        except Exception as exc:
            raise RuntimeError('Не удалось скачать Python с GitHub. Проверьте соединение Colab и повторите ячейку 3.') from exc
        if digest.hexdigest() != expected_sha:
            raise ValueError('Контрольная сумма архива Python не совпадает. Установка остановлена.')
        safe_extract(archive, temp)
        candidate = temp / 'python'
        executable = candidate / 'bin/python3.12'
        if not executable.is_file() or executable_version(executable, env) != version:
            raise ValueError('В архиве нет ожидаемого Python ' + version + '.')
        info = {'archive_sha256': expected_sha, 'version': version, 'executable_sha256': hash_file(executable)}
        (candidate / '.fly-python.json').write_text(json.dumps(info, sort_keys=True), encoding='utf8')
        if install.exists():
            raise RuntimeError('Временная папка Python уже создана другим процессом; она не изменена.')
        os.rename(candidate, install)
    print('Python', version, 'установлен во временную папку Colab.', flush=True)
    return python


def ensure_venv(base_python, venv, packages, env):
    venv = Path(venv)
    python = venv / 'bin/python'
    if venv.exists() and not python.is_file():
        raise RuntimeError('Временная среда Python неполна и не будет изменена; перезапустите среду Colab.')
    if not venv.exists():
        subprocess.run([str(base_python), '-m', 'venv', str(venv)], env=env, check=True)
    if executable_version(python, env) != PYTHON_VERSION:
        raise RuntimeError('Версия временной среды не совпадает. Она не будет изменена; перезапустите среду Colab.')
    print('Устанавливаем проверенные библиотеки в отдельное окружение; это может занять несколько минут...', flush=True)
    subprocess.run([str(python), '-m', 'pip', 'install', '-q', *packages], env=env, check=True)
    return python
