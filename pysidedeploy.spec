[app]

# title of your application
title = Skunkworks

# project root directory. default = The parent directory of input_file
project_dir = .

# source file entry point path. default = main.py
input_file = skunkworks_app.py

# directory where the executable output is generated
exec_directory = build/deploy

# path to the project file relative to project_dir
project_file =

# application icon
icon = src/ui/assets/icons/skunkworks-app.png

[python]

# python path
python_path =

# python packages to install
packages = Nuitka==4.1.3,imageio==2.37.4

# buildozer = for deploying Android application
android_packages = buildozer==1.5.0,cython==0.29.33

[qt]

# paths to required qml files. comma separated
# normally all the qml files required by the project are added automatically
# design studio projects include the qml files using qt resources
qml_files = src/ui/qml/App.qml

# excluded qml plugin binaries
excluded_qml_plugins =

# qt modules used. comma separated
modules = Core,Gui,Qml,Quick,QuickControls2,Multimedia

# qt plugins used by the application. only relevant for desktop deployment
# for qt plugins used in android application see [android][plugins]
plugins =

[android]

# path to pyside wheel
wheel_pyside =

# path to shiboken wheel
wheel_shiboken =

# plugins to be copied to libs folder of the packaged application. comma separated
plugins =

[nuitka]

# usage description for permissions requested by the app as found in the info.plist file
# of the app bundle. comma separated
# eg = extra_args = --show-modules --follow-stdlib
macos.permissions =

# mode of using nuitka. accepts standalone or onefile. default = onefile
mode = standalone

# specify any extra nuitka arguments
extra_args = --quiet --noinclude-qt-translations --include-data-file=docs/user-guide/Skunkworks_Operator_Manual.docx=docs/user-guide/Skunkworks_Operator_Manual.docx --include-data-file=docs/user-guide/CHANGELOG.md=docs/user-guide/CHANGELOG.md --include-data-dir=src/ui/assets=src/ui/assets

[buildozer]

# build mode
# possible values = ["aarch64", "armv7a", "i686", "x86_64"]
# release creates a .aab, while debug creates a .apk
mode = debug

# path to pyside6 and shiboken6 recipe dir
recipe_dir =

# path to extra qt android .jar files to be loaded by the application
jars_dir =

# if empty, uses default ndk path downloaded by buildozer
ndk_path =

# if empty, uses default sdk path downloaded by buildozer
sdk_path =

# other libraries to be loaded at app startup. comma separated.
local_libs =

# architecture of deployed platform
arch =
