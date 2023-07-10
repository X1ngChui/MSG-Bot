import json
import subprocess
import threading
import atexit
from multiprocessing import Process
from flask_app import app
from bot import Bot

qsign_process = None
cqhttp_process = None
flask_thread = None


def start_qsign():
    with open(r"go-cqhttp\device.json", "r") as file:
        device = json.load(file)
    android_id = device["android_id"]

    subprocess.call([r"bin\unidbg-fetch-qsign.bat", "--host=127.0.0.1", "--port=8081",
                     "--count=2", "--library=tx", f"--android_id={android_id}"],
                    shell=True, cwd="unidbg-fetch-qsign")


def start_cqhttp():
    subprocess.call(r"go-cqhttp.bat", shell=True, cwd="go-cqhttp")


def start_flask():
    app.run(host="127.0.0.1", port=5701)


def finalize():
    global qsign_process, cqhttp_process, flask_thread

    Bot.get_instance().stop()
    qsign_process.terminate()
    cqhttp_process.terminate()
    flask_thread.join()


if __name__ == "__main__":
    atexit.register(finalize)

    qsign_process = Process(target=start_qsign)  # run qsign
    qsign_process.start()

    cqhttp_process = Process(target=start_cqhttp)  # run go-cqhttp
    cqhttp_process.start()

    flask_thread = threading.Thread(target=start_flask)  # run flask
    flask_thread.start()

    Bot.get_instance().run()  # run bot
