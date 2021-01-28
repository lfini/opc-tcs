# Generazione kit di installazione
#
# dtracker.zip:    kit completo, incluse le procedure di test
#

VERSION := $(shell python dtracker.py -v)

PYTHONFILES := $(shell ls *.py)
DATAFILES := $(shell ls *.p)

all: 
	mkdir dist
	cp $(PYTHONFILES) ./dist
	cp $(DATAFILES) ./dist
	cp domec128.ico ./dist
	zip -r dtracker-$(VERSION).zip README setup.bat collegamento.bat dist icons
	rm -rf dist

clean:
	rm -rf __pycache__
	rm -f *.zip
	rm -rf build
	rm -rf dist
