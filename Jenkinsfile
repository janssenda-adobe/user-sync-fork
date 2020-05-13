pipeline {
	agent any
	environment {
		BUILD_TARGET = "standalone"
		PYTHON_HOME = "C:\\Program Files\\Python36"
		BUILD_EDITION = "full"
	}
	stages {
		stage('Configure') {
			steps {
				script{
					dir("user_sync") {
				        env.VERSION = sh returnStdout: true, script: "python -c 'import version; print(version.__version__)'"
					    echo "Building version: ${env.VERSION}"
					}
				}
			}
		}
		stage('Build') {
			steps {
				script{
				    powershell ".build\\.appveyor\\build_test.ps1"
    				//dir("windows"){
						//archiveArtifacts artifacts: "$msi_file", fingerprint: true
						//archiveArtifacts artifacts: "$cert_file", fingerprint: true
					//}
				}
			}
		}
		//stage('Release') {
		//	when {expression { env.DO_RELEASE == 'true' }}
		//	steps {

		//		}
	//		}
	//	}
	}

	post { always { deleteDir()}}
}

