import subprocess
import os
import platform
import glob
import getpass

if platform.system() == "Windows":
    import winreg

def get_python_paths(reg_key):
    python_paths = {}

    try:
        i = 0
        while True:
            version = winreg.EnumKey(reg_key, i)
            version_key = winreg.OpenKey(reg_key, version)
            try:
                install_key = winreg.OpenKey(version_key, "InstallPath")
            except:
                i += 1
                continue
            install_path, _ = winreg.QueryValueEx(install_key, None)
            python_paths[version] = install_path.replace("\\", "/") + "python.exe"
            i += 1
    except OSError:
        pass

    return python_paths

def get_all_python_paths():
    paths = {}

    if platform.system() != "Windows":
        path_list = os.listdir('/home/' + getpass.getuser() + '/.pyenv/versions')
        for path in path_list:
            paths[path] = os.path.abspath('/home/' + getpass.getuser() + '/.pyenv/versions/' + path + '/bin/python')        
    else:
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Python\\PythonCore")
            paths.update(get_python_paths(reg_key))
        except:
            pass

        try:
            reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Python\\PythonCore")
            paths.update(get_python_paths(reg_key))
        except:
            pass

        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "SOFTWARE\\Python\\PythonCore")
            paths.update(get_python_paths(reg_key))
        except:
            pass

    return paths

python_paths = get_all_python_paths()
i = 0
for python_path in python_paths.values():
    try:
        if i == 0:
            subprocess.check_call([python_path, "setup.py", "sdist", "bdist_wheel"])
        else:
            subprocess.check_call([python_path, "setup.py", "bdist_wheel"])
    except:
        subprocess.check_call([python_path, "-m", "pip", "install", "wheel"])
        if i == 0:
            subprocess.check_call([python_path, "setup.py", "sdist", "bdist_wheel"])
        else:
            subprocess.check_call([python_path, "setup.py", "bdist_wheel"])

    if platform.system() == "Linux":
        machine = platform.machine()
        files = glob.glob(f"dist/tree_sitter_glsl37-*-linux_{machine}.whl")
        for file in files:
            try:
                subprocess.check_call([python_path, "-m", "auditwheel", "repair", file, f"--plat=manylinux_2_5_{machine}", "-w", "dist"])
            except:
                subprocess.check_call([python_path, "-m", "pip", "install", "auditwheel"])
                subprocess.check_call([python_path, "-m", "auditwheel", "repair", file, f"--plat=manylinux_2_5_{machine}", "-w", "dist"])
            os.remove(file)

    i += 1