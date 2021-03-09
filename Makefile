output_dir = dist
output_filename = user-sync
prebuilt_dir = external

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
	python -V
	python3 -m pip install --upgrade pip
	python3 -m pip install --upgrade pyinstaller
	python3 -m pip install --upgrade setuptools
	-$(RM) $(output_dir)
	python3 .build/pre_build.py
	pyinstaller --clean --noconfirm user-sync.spec

test:
	nosetests --no-byte-compile tests
