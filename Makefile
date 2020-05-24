all: clean UI
	python3 setup.py sdist bdist_wheel
#	python3 -m twine upload dist/*
# Dont forget to do the UI too, it might fail
UI:
	-rm -rf vis/build;	
	cd vis; npm run-script build;
	echo `pwd`
	-rm vis/build/data.json;
	mv vis/build src/refcliq/template
clean:	
	-rm -rf dist
	-rm -rf build
	-rm -rf src/*.egg-info
	-rm -rf src/refcliq/template
