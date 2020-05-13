

Write-Host "Dir: ${PWD}"
$venvcmd = "C:\Program Files\Python36\Scripts\virtualenv.exe"
& $venvcmd venv
.\venv\Scripts\activate.ps1
$venv = & which python
Write-Host "Using virtualenv: ${venv}"

pip install external\okta-0.0.3.1-py2.py3-none-any.whl
pip install -e .
pip install -e .[test]
pip install -e .[setup]

make $env:BUILD_TARGET 2>&1
