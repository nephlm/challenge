import time

import ccLib

aws = ccLib.AWS()
session = ccLib.initDB()

while True:
    res = ccLib.getWorkers(session, aws)
    print(res)
    for worker in res:
        if not worker.get('cc2w') and worker.get('ip'):
            print('sending a hello')
            ccLib.Worker.sendHello(session, worker['ip'])

    time.sleep(3)

if __name__ == "__main__":
    main()
