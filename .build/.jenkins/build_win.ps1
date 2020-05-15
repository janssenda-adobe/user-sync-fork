param(
    [String[]]$build_editions = ("standard","noext")
)

$env:VERSION = 2.6.0

$build_matrix = @{
    'standard' = @{
            BUILD_TARGET = "standalone";
            UST_EXTENSION = "1";
        };
    'noext' = @{
            BUILD_TARGET = "standalone";
            UST_EXTENSION = "0";
        };
}

function build($edition)
{
    $env_vars = $build_matrix[$edition]
    foreach ($k in $env_vars.Keys){
        [Environment]::SetEnvironmentVariable($k,$env_vars[$k])
    }

    Write-Host "Build Edition: ${edition}"
    Write-Host "BUILD_TARGET: ${env:BUILD_TARGET}"
    Write-Host "UST_EXTENSION: ${env:UST_EXTENSION}"

    make standalone 2>&1

}

#$venvcmd = "${env:PYTHON_HOME}\Scripts\virtualenv.exe"
#& $venvcmd venv
.\venv\Scripts\activate.ps1
$venv = & which python
Write-Host "Using virtualenv: ${venv}"

#pip install external\okta-0.0.3.1-py2.py3-none-any.whl
#pip install -e .
#pip install -e .[test]
#pip install -e .[setup]0
#pip uninstall -y enum34

Remove-Item -Recurse -Force release
New-Item -Type Directory release

foreach ($edition in $build_editions)
{
    build $edition
#    Get-ChildItem dist
#    7z.exe a "release\user-sync-${env:VERSION}-${edition}-win64.zip" ".\dist\user-sync.exe"
}

#7z.exe a -ttar -so -an release\examples.tar examples | 7z.exe a -si release\examples.tar.gz
#7z.exe a -r release\examples.zip examples\
#Get-ChildItem release
