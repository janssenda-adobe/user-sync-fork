param(
    [parameter(Position=0, Mandatory=$true)] $action
)

function build()
{
    Write-Host "BUILD_TARGET: ${env:BUILD_TARGET}"
    Write-Host "UST_EXTENSION: ${env:UST_EXTENSION}"
    .\venv\Scripts\activate.ps1
    make standalone
    7z.exe a "release\user-sync-${env:VERSION}-${env:BUILD_ADDITION}-win64.zip" ".\dist\user-sync.exe"
    Get-ChildItem release
}

function setup()
{
    Remove-Item -Recurse -Force venv
    $venvcmd = "${env:PYTHON_HOME}\Scripts\virtualenv.exe"
    & $venvcmd venv
    .\venv\Scripts\activate.ps1

    pip install external\okta-0.0.3.1-py2.py3-none-any.whl
    pip install -e .
    pip install -e .[test]
    pip install -e .[setup]
    pip uninstall -y enum34

    Remove-Item -Recurse -Force release
    New-Item -Type Directory release
    bundle_examples
}

function bundle_examples(){
    7z.exe a -ttar -so -an examples | 7z.exe a -si release\examples.tar.gz
    7z.exe a -r release\examples.zip examples\
}

switch ($action)
{
    'setup' { setup }
    'build' { build }
    'examples' { bundle_examples }
    Default {
        throw("Invalid action ${action}")
    }
}
