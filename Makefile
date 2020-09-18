output_dir = dist
signed_dir = signed

ifeq ($(OS),Windows_NT)
	rm_path := $(shell python -c "import distutils.spawn; print(distutils.spawn.find_executable('rm'))")
    ifeq ($(rm_path),None)
        RM := rmdir /S /Q
    else
	    RM := $(rm_path) -rf
    endif
else
    RM := rm -rf
endif

standalone:
	python -m pip install --upgrade pip
	python -m pip install --upgrade pyinstaller
	python -m pip install --upgrade setuptools
	-$(RM) $(output_dir)
	python .build/pre_build.py
	pyinstaller --clean --noconfirm user-sync.spec

test:
	nosetests --no-byte-compile tests

sign:
	@mkdir ${signed_dir}
	java -jar "${BAST_HOME}\client.jar" -s \
	-b "${output_dir}" \
	-d "${signed_dir}" \
	-ri "${UST_SIGN_RULEID}" \
	-u "${UST_SIGN_USERID}" \
	-p "${UST_SIGN_PASSWORD}" \
	-k "${BAST_HOME}\sehkmet"
