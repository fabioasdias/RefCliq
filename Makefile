all: clean UI
	python3 setup.py sdist bdist_wheel
	# python3 -m twine upload dist/*
UI:
	- cd vis;	rm -rf build;	
	cd vis; npm run build;	rm build/data.json;	mv build ../template
clean:	
	-rm -rf dist
	-rm -rf build
	-rm -rf src/*.egg-info
	-rm -rf template
