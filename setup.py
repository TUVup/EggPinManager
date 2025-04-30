from cx_Freeze import setup, Executable
versions = '1.2.7'

build_exe_options = {
    "packages": ["comtypes"],
    "include_files": ['resource/'],
    "build_exe": f"EggManager_{versions}"
}
 
exe = [Executable(f'EggManager_GUI.py', base='gui', target_name=f'EggManager_{versions}', icon='resource/eggui', uac_admin=True)]
 
setup(
    name='EggManager',
    version = versions,
    author='TUVup',
    options = {"build_exe": build_exe_options},
    executables = exe
)