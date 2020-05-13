pipeline {
	agent {
		label 'test_win'
	}
	environment {
		a_variable = 'the variable1'
	}
	stages {
		stage('Configure') {
			steps {
				script{
					echo "${a_variable}"
				}
			}
		}
		stage('Build') {
			steps {
				script{
				    powershell ".build\\.appveyor\\build_test.ps1"
//					dir("user_sync") {
//						sh 'echo hello'
//						sh 'ls'
					}
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

	post {
		always {
			node(null){
				deleteDir()
			}
		}

	}
}

