
Write-Host "Building in ${PWD}"
& virtualenv venv
.\venv\Scripts\activate.ps1
$venv = & which python
Write-Host "Using virtualenv: ${venv}"

pip install external\okta-0.0.3.1-py2.py3-none-any.whl
pip install external\umapi_client-2.14X-py2.py3-none-any.whl
pip install -e .
pip install -e .[test]
pip install -e .[setup]
pip uninstall -y enum34

make $env:BUILD_TARGET 2>&1