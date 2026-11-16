@echo off
setlocal
set "ENGINE=%USERPROFILE%\Downloads\Godot_v4.7.2-stable_win64.exe\Godot.exe.exe"
if not exist "%ENGINE%" (
 echo Open project.godot with Godot 4.7 and press F6 on Crossing.tscn.
 pause
 exit /b 1
)
start "" "%ENGINE%" --path "%~dp0."
