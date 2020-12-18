# Generazione kit di installazione
#
# dtracker.zip:    kit completo, incluse le procedure di test
#
# dtrackerW10.zip: solo dtracker versione per generazione di eseguibile Windows con pyinstaller

W10_FILES = astro.py configure.py dtracker.py interpolator.py \
           setup.py telecomm.py widgets.py

all: 
	zip -r dtrackerW10.zip . -i $(W10_FILES) -i *.p -i README -i icons/*  -i domec128.ico
	zip -r dtracker.zip . -i *.py -i *.p -i README -i icons/* -i domec128.ico

clean:
	rm -rf __pycache__
	rm -f *.zip
