install:
	pip install -r requirements.txt

run:
	sudo python3 main.py targets.txt

clean:
	rm -rf output/*.json output/*.txt