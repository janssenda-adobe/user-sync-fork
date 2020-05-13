
Write-Host "Dir: ${PWD}"
Write-Host "Version: ${env:VERSION}"
Write-Host "Edition: ${env:BUILD_EDITION}"

$venvcmd = "${env:PYTHON_HOME}\Scripts\virtualenv.exe"
& $venvcmd venv
.\venv\Scripts\activate.ps1
$venv = & which python
Write-Host "Using virtualenv: ${venv}"

pip install external\okta-0.0.3.1-py2.py3-none-any.whl
pip install -e .
pip install -e .[test]
pip install -e .[setup]
pip uninstall -y enum34

make $env:BUILD_TARGET 2>&1
dir dist
mkdir release

cp dist\user-sync.exe release\
cd release
7z.exe a "user-sync-${env:VERSION}${env:BUILD_EDITION}-win64.zip" user-sync.exe
cd ..
7z.exe a -ttar -r release\examples.tar examples
7z.exe a -tgzip release\examples.tar.gz release\examples.tar
7z.exe a -r release\examples.zip examples\
dir release
