import os
import winreg
import configparser
import sys
from pathlib import Path

# Steam App IDs
US2_APPID = "230290"
SE_APPID = "314650"

def find_on_disks(filename_pattern, subdir=""):
    """Ищет файл в типичных местах на всех дисках (для пираток)."""
    drives = [f"{d}:\\" for d in "CDEFGHIJKLMNOP" if os.path.exists(f"{d}:\\")]
    common_roots = ["Games", "GAMES", "Program Files", "Program Files (x86)", "SteamLibrary/steamapps/common"]
    
    for drive in drives:
        for root in common_roots:
            search_path = os.path.join(drive, root)
            if not os.path.isdir(search_path):
                continue
            # Ищем во вложенных папках первого уровня
            try:
                for folder in os.listdir(search_path):
                    full_folder = os.path.join(search_path, folder)
                    if not os.path.isdir(full_folder): continue
                    
                    target = os.path.join(full_folder, subdir, filename_pattern)
                    if os.path.exists(target):
                        return os.path.abspath(full_folder)
            except PermissionError:
                continue
    return None

def get_steam_install_path(app_id):
    """Ищет путь к установке игры в реестре Steam."""
    for key_path in [
        rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App {app_id}",
        rf"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Steam App {app_id}"
    ]:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                install_path, _ = winreg.QueryValueEx(key, "InstallLocation")
                if install_path and os.path.isdir(install_path):
                    return install_path
        except FileNotFoundError:
            continue
    return None

def find_us2_simulations():
    """Ищет папку с симуляциями в папке Документы."""
    docs = Path(os.path.expanduser("~/Documents"))
    # Возможные варианты названия папки
    variants = [
        docs / "Universe Sandbox" / "Simulations",
        docs / "Universe Sandbox 2" / "Simulations",
    ]
    for v in variants:
        if v.exists():
            return str(v)
    return None

def setup():
    print("=== US2SE Bridge: Автоматическая настройка ===")
    
    # 1. Поиск путей
    se_path = get_steam_install_path(SE_APPID)
    if not se_path:
        # Пытаемся найти SpaceEngine вручную (пиратка)
        se_path = find_on_disks("SpaceEngine.exe", subdir="system")
        
    us2_path = get_steam_install_path(US2_APPID)
    if not us2_path:
        # Пытаемся найти US2 вручную (пиратка)
        us2_path = find_on_disks("Universe Sandbox.exe") or find_on_disks("Universe Sandbox x64.exe")

    sim_path = find_us2_simulations()
    
    if not se_path:
        print("[!] Не удалось найти SpaceEngine. Если у вас пиратка, укажите путь вручную в config.ini")
    else:
        print(f"[OK] Найдено SpaceEngine: {se_path}")
        
    if not us2_path:
        print("[!] Не удалось найти Universe Sandbox. Укажите путь вручную в config.ini")
    else:
        print(f"[OK] Найдено Universe Sandbox: {us2_path}")
        
    if not sim_path:
        print("[!] Не удалось найти папку симуляций US2 в Документах.")
    else:
        print(f"[OK] Найдена папка симуляций: {sim_path}")

    # 2. Подготовка конфига
    config = configparser.ConfigParser()
    example_path = "config.ini.example"
    target_path = "config.ini"
    
    if not os.path.exists(example_path):
        print(f"[ОШИБКА] Не найден файл {example_path}")
        return

    config.read(example_path, encoding='utf-8')
    
    # Заполнение найденными путями
    if sim_path:
        config['paths']['us2_simulations'] = sim_path
    if se_path:
        config['paths']['se_install'] = se_path
        
    if us2_path:
        exe_path = os.path.join(us2_path, "Universe Sandbox.exe")
        if not os.path.exists(exe_path):
             exe_path = os.path.join(us2_path, "Universe Sandbox x64.exe")
        config['apps']['us2_exe'] = exe_path
        
    if se_path:
        config['apps']['se_exe'] = os.path.join(se_path, "system", "SpaceEngine.exe")

    # 3. Сохранение
    with open(target_path, 'w', encoding='utf-8') as f:
        config.write(f)
    
    print("\n[УСПЕХ] Файл config.ini создан и настроен автоматически!")
    print("Проверьте пути в файле перед запуском START.bat.")

if __name__ == "__main__":
    setup()
    input("\nНажмите Enter, чтобы выйти...")
