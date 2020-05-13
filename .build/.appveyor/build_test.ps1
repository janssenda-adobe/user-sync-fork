
Write-Host "Dir: ${PWD}"
$venvcmd = "C:\Program Files\Python36\Scripts\virtualenv.exe"
& $venvcmd venv
.\venv\Scripts\activate.ps1
which python
ls

