from cx_Freeze import setup, Executable
versions = '1.1.0'

build_exe_options = {
    "include_files": [
        'resources/',  # 리소스 폴더 전체
        'LICENSE',
        'README.md'
    ],
    "build_exe": f"EggManager_{versions}_cx"
}
 
exe = [Executable(
    'main.py', 
    base='gui', 
    target_name=f'EggManager_{versions}', 
    icon='resources/eggui.ico', 
    uac_admin=True
)]
 
setup(
    name='EggPinManager',
    version = versions,
    author='TUVup',
    options = {"build_exe": build_exe_options},
    executables = exe
)