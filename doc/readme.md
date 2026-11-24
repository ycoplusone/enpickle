
# 가상화 수행
source ~/enpickle/.venv/bin/activate

# flask 실행
python ~/enpickle/run.py

nohup python ~/enpickle/run.py &

# ubuntu 프로세
ps aux | grep [프로세스명]
kill -9 [PID]
