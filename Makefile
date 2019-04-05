all: clean
	python3 setup.py sdist bdist_wheel
	# python3 -m twine upload dist/*
clean:	
	-rm -rf dist
	-rm -rf build
	-rm -rf src/*.egg-info
