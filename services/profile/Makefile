.PHONY: run start stop deps
run:
	$(SL_PYTHON) profile.py --data $(SL_DATA)

start:
	screen -S profile -dm bash -c "make run"

stop:
	-screen -S profile -p 0 -X stuff "^C"

deps:
	$(SL_PIP) install -r requirements.txt
