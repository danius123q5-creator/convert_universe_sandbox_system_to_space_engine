"""
us2se_sync.py — Live-синхронизатор Universe Sandbox 2 → SpaceEngine
Пути берёт из config.ini — редактируй только его.
После каждого обновления каталога перезапускает SpaceEngine.
"""

import os
import sys
import time
import subprocess
import configparser

# ─── Читаем config.ini из папки скрипта ───────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'config.ini')


def load_config():
    if not os.path.isfile(CONFIG_PATH):
        print(f"[ОШИБКА] Файл конфигурации не найден:\n         {CONFIG_PATH}")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH, encoding='utf-8')

    try:
        us2_dir       = cfg['paths']['us2_simulations'].strip()
        se_dir        = cfg['paths']['se_install'].strip()
        catalog_name  = cfg['sync']['catalog_name'].strip()
        poll_interval = float(cfg['sync']['poll_interval'].strip())
        se_exe        = cfg['apps']['se_exe'].strip()
        se_star_name  = cfg['sync'].get('se_star_name', 'Sun').strip()
    except KeyError as e:
        print(f"[ОШИБКА] В config.ini отсутствует ключ: {e}")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

    return us2_dir, se_dir, catalog_name, poll_interval, se_exe, se_star_name


# ─── Импорт конвертера ─────────────────────────────────────────────────────────
sys.path.insert(0, SCRIPT_DIR)
try:
    from us2se_converter import US2SE_Converter
except ImportError as e:
    print(f"[ОШИБКА] Не удалось импортировать us2se_converter.py: {e}")
    input("\nНажмите Enter для выхода...")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────────────────────

def get_latest_ubox(us2_dir):
    try:
        files = [
            os.path.join(us2_dir, f)
            for f in os.listdir(us2_dir)
            if f.endswith('.ubox') and os.path.isfile(os.path.join(us2_dir, f))
        ]
        if not files:
            return None, 0
        latest = max(files, key=os.path.getmtime)
        return latest, os.path.getmtime(latest)
    except FileNotFoundError:
        return None, 0


def restart_spaceengine(se_exe):
    """Закрывает SpaceEngine и запускает снова."""
    se_name = os.path.basename(se_exe)

    print(f"[SE]   Закрываю SpaceEngine...")
    se_name = os.path.basename(se_exe)  # e.g. "SpaceEngine.exe"
    subprocess.run(
        ["taskkill", "/FI", f"IMAGENAME eq {se_name}", "/F"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    # Резервный вариант через PowerShell
    stem = os.path.splitext(se_name)[0]
    subprocess.run(
        ["powershell", "-Command",
         f"Get-Process | Where-Object {{ $_.Name -match '{stem}' }} | Stop-Process -Force"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # Ждём пока процесс точно завершится
    time.sleep(2)

    print(f"[SE]   Запускаю SpaceEngine...")
    if os.path.isfile(se_exe):
        subprocess.Popen([se_exe])
        print(f"[SE]   ✓ SpaceEngine запущен.")
    else:
        print(f"[SE]   [!] Файл не найден: {se_exe}")
        print(f"           Проверь se_exe в config.ini")


def do_convert(ubox_path, converter, catalog_name, se_exe, se_star_name):
    try:
        print(f"\n[SYNC] Изменение: {os.path.basename(ubox_path)}")
        print(f"[SYNC] Конвертирую → {catalog_name}.sc ...")
        out_path = converter.convert_ubox(ubox_path, catalog_name, se_star_name)
        print(f"[SYNC] ✓ Каталог обновлён: {out_path}")

        # Перезапускаем SE чтобы подхватил новый каталог
        restart_spaceengine(se_exe)
        return True
    except Exception as e:
        print(f"[ОШИБКА] Конвертация провалилась: {e}")
        return False


def main():
    us2_dir, se_dir, catalog_name, poll_interval, se_exe, se_star_name = load_config()

    print("=" * 55)
    print("  US2SE Bridge — Live Sync")
    print("=" * 55)
    print(f"  config.ini: {CONFIG_PATH}")
    print(f"  US2 папка : {us2_dir}")
    print(f"  SE папка  : {se_dir}")
    print(f"  SE exe    : {se_exe}")
    print(f"  Каталог   : {catalog_name}.sc")
    print(f"  Интервал  : {poll_interval} сек")
    print("=" * 55)
    print("  Ctrl+C — остановить\n")

    if not os.path.isdir(us2_dir):
        print(f"[ОШИБКА] Папка симуляций не найдена:\n         {us2_dir}")
        print(f"         Исправь us2_simulations в config.ini")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

    if not os.path.isdir(se_dir):
        print(f"[ОШИБКА] Папка SpaceEngine не найдена:\n         {se_dir}")
        print(f"         Исправь se_install в config.ini")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

    converter = US2SE_Converter(se_install_dir=se_dir)

    last_mtime = 0
    last_ubox  = None
    first_run  = True

    print("[SYNC] Ожидание изменений...")

    try:
        while True:
            ubox_path, mtime = get_latest_ubox(us2_dir)

            if ubox_path is None:
                print("[SYNC] .ubox файлов не найдено, жду...", end="\r")
            elif mtime != last_mtime or ubox_path != last_ubox:
                if first_run:
                    print(f"[SYNC] Файл: {os.path.basename(ubox_path)}")
                    print(f"[SYNC] Начальная конвертация...")
                    first_run = False
                do_convert(ubox_path, converter, catalog_name, se_exe, se_star_name)
                print(f"\n[SYNC] Жду следующего сохранения в Universe Sandbox...")
                last_mtime = mtime
                last_ubox  = ubox_path

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\n\n[SYNC] Остановлено.")


if __name__ == "__main__":
    main()
