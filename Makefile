# Generazione kit di installazione
#
# dtracker.zip:    kit completo, incluse le procedure di test
#

all: 
	zip -r dtracker.zip . -i *.py -i *.p -i README -i icons/* -i domec128.ico setup.bat

clean:
	rm -rf __pycache__
	rm -f *.zip
	rm -rf build
	rm -rf dist
