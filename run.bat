@echo off
@echo -- !Started: %date% %time% > history.log 2>&1
type history.log
python run.py %* >> history.log 2>&1
@echo -- !Completed: %date% %time% >> history.log 2>&1
type history.log
timeout 5 > NUL