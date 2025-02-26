from cx_Freeze import setup, Executable
versions = '1.1.1'

build_exe_options = {
    "include_files": ['resource/'],
    "build_exe": f"EggManager_{versions}_cx"
}
 
exe = [Executable(f'EggManager_GUI_{versions}_cx.py', base='gui', target_name=f'EggManager_{versions}', icon='eggui', uac_admin=True)]
 
setup(
    name='EggManager',
    version = versions,
    author='TUVup',
    options = {"build_exe": build_exe_options},
    executables = exe
)