"""
A tiny poller that keeps the local cache of AWS workers up to date.

Runs a separate process with its own upstart script.
"""

import time

import ccLib

def main():
    aws = ccLib.AWS()
    session = ccLib.initDB()

    while True:
        res = ccLib.getWorkers(session, aws)
        print(res)
        for worker in res:
            if not worker.get('cc2w') and worker.get('ip'):
                # It's a live server and we haven't said hello yet.
                ccLib.Worker.sendHello(session, worker['ip'])
        time.sleep(3)

if __name__ == "__main__":
    main()
