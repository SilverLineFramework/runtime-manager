.PHONY: run start stop deps
run:
	$(SL_PYTHON) manage.py makemigrations
	$(SL_PYTHON) manage.py migrate
	$(SL_PYTHON) manage.py runserver

start:
	screen -S orchestrator -dm bash -c "make run"

stop:
	-screen -S orchestrator -p 0 -X stuff "^C"

deps:
	$(SL_PIP) install -r requirements.txt

reset:
	rm -f db.sqlite3
