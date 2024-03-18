@echo off
setlocal

:: Check if a filename is provided
if "%~1"=="" (
    echo Error: Filename required.
    exit /b 1
)

:: Set default input directory and override if the second argument is provided
set "InputDir=C:\Users\happy\Downloads"
if not "%~2"=="" set "InputDir=%~2"

:: Set the output directory to the specified path
set "OutputDir=G:\My Drive\Audios_To_Knowledge\mp3_files"

:: Check if the input file exists
if not exist "%InputDir%\%~1" (
    echo Error: Input file does not exist: "%InputDir%\%~1"
    exit /b 2
)

:: Check if the output directory exists, exit with error if it doesn't
if not exist "%OutputDir%" (
    echo Error: Output directory does not exist: "%OutputDir%"
    exit /b 3
)

:: Proceed with conversion, ensuring paths with spaces are quoted
echo Converting "%InputDir%\%~1" to MP3 format...
ffmpeg -i "%InputDir%\%~1" -vn -ar 16000 -ac 1 -acodec libmp3lame -q:a 0 "%OutputDir%\%~n1.mp3"

if "%ERRORLEVEL%" neq "0" (
    echo Error: Conversion failed.
    exit /b 4
) else (
    echo Success: Conversion completed.
)

endlocal
