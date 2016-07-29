import csv
import os.path
import sys
import time

import boto.ec2.keypair

# path to the dowloaed AWS credential file
# Assumed to have the standard header
# Name, accessKey, secretKey
DEFAULT_CREDENTIAL_PATH='../credentials.csv'

REGIONS = {
    'us-east-1': {'name': 'Virginia', 'ami': 'ami-2d39803a'},
    'us-west-1': {'name': 'California', 'ami': 'ami-48db9d28'},
    'us-west-2': {'name': 'Oregon', 'ami': 'ami-d732f0b7'},
#     'ap-northeast-1': {'name': 'Tokyo', 'ami': 'ami-'},
#     'ap-northeast-2': {'name': 'Seoul', 'ami': 'ami-'},
#     'ap-southeast-1': {'name': 'Singapore', 'ami': 'ami-'},
#     'ap-southeast-2': {'name': 'Sydney', 'ami': 'ami-'},
#     'ap-south-1': {'name': 'Mumbai', 'ami': 'ami-'},
#     'sa-east-1': {'name': 'Sao Paulo', 'ami': 'ami-'},
#     'eu-central-1': {'name': 'Frankfurt', 'ami': 'ami-'},
#     'eu-west-1': {'name': 'Ireland', 'ami': 'ami-'},
}

# aws instance states
RUNNING = 16
TERMINATED = 48
STOPPED = 80

class AWS(object):
    def __init__(self, credentialPath=DEFAULT_CREDENTIAL_PATH):
        try:
            with open(credentialPath, 'r') as f:
                reader = csv.reader(f)
                self.credentials = list(reader)[1] # downloaded file has a header
                print(self.credentials)
                self.accessKey = self.credentials[1]
                self.secretKey = self.credentials[2]
        except (IOError, IndexError):
            print('Could not read credentials from %s or bad format.' % credentialPath)
            raise
            sys.exit(1)
        print((self.accessKey, self.secretKey))

        self.conns = {}

    def getConn(self, region):
        if not self.conns.get(region):
            conn = boto.ec2.connect_to_region(region,
                        aws_access_key_id=self.accessKey,
                        aws_secret_access_key=self.secretKey)
            self.conns[region] = conn
        return self.conns[region]

    def createKeypairs(self):
        """
        Generates missing keys and saves them to file.
        """
        keyDir = os.path.abspath('./keys')
        if not os.path.isdir(keyDir):
            os.mkdir(keyDir, 0700)
        for region in REGIONS:
            keyPath = os.path.abspath(os.path.join(keyDir, region + '.pem'))
            if not os.path.exists(keyPath):
                # if we don't have a keypair, create it.
                conn = self.getConn(region)
                try:
                    keys = conn.get_all_key_pairs([region])
                    for key in keys:
                            key.delete()
                except boto.exception.EC2ResponseError:
                    # Probably doesn't exist, so this is expected.
                    pass
                keypair = conn.create_key_pair(region)
                keypair.save(os.path.abspath('./keys'))

    def pushSecurityGroups(self):
        conn = self.getConn('us-east-1')
        for sGroup in conn.get_all_security_groups(['worker']):
            for region in REGIONS:
                try:
                    dstConn = self.getConn(region)
                    sGroup.copy_to_region(dstConn.region)
                    print('copy')
                except boto.exception.EC2ResponseError:
                    #group already exists
                    print('pass')
                    pass
                    # raise


    def getRegions(self):
        """
        Request the regions from AWS.
        @returns: list of tuples (id, human_name)
        """
        regions = boto.ec2.regions(
                aws_access_key_id=self.accessKey,
                aws_secret_access_key=self.secretKey)
        print(dir(regions[0]))
        # filter to just a few regions for the moment.
        regions = [r for r in regions if r.name in REGIONS]
        return [(r.name, REGIONS[r.name]['name']) for r in regions if r.name not in ('cn-north-1', 'us-gov-west-1')]

    def generateStartScript(self):
        script = ''
        script += '#!/bin/sh\n\n'
        script += 'echo "hello" > /tmp/testHello.txt\n\n'
        script += 'apt-get update\n'
        script += 'apt-get install git -y\n'
        script += 'git clone https://github.com/nephlm/verodin /tmp/verodin\n\n'
        script += '/tmp/verodin/src/worker/install.sh'
        return script

    def startWorker(self, region):
        """
        Start a new worker in the specified region.
        """
        conn = self.getConn(region)
        print(REGIONS[region]['ami'])
        print(region)
        script = self.generateStartScript()

        reservation = conn.run_instances(
            image_id=REGIONS[region]['ami'],
            instance_type='t2.micro',
            key_name=region,
            security_groups=['worker'],
            #security_group_ids=['sg-713a230a'],
            user_data=script
            )
        for inst in reservation.instances:
            inst.add_tag('role', 'worker')

    def stopWorker(self, region, id):
        """
        Terminate the specified region/id instance.  Any data on the
        instance will be lost.
        """
        conn = self.getConn(region)
        instances = conn.get_only_instances([id])
        for instance in instances:
            instance.terminate()


    def getWorkers(self):
        """
        Retrieve a list of worker instances from all regions.
        """
        allInstances = []
        for region in REGIONS:
            conn = self.getConn(region)
            instances = conn.get_only_instances()
            # if instances:
            #     print(instances[1].tags.get('role', ''))
            allInstances += instances
        ret = [{'id': x.id,
                'ip': x.ip_address,
                'state': x.state,
                'state_code': x.state_code,
                'region': x.connection.region.name,
                'region_human': REGIONS[x.connection.region.name]['name']}
                for x in allInstances
                if x.tags.get('role', '') == 'worker'
                and x.state_code not in (STOPPED, TERMINATED)]
        return ret


import sqlalchemy as DB
from sqlalchemy.ext.declarative import declarative_base, declared_attr
# import sqlalchemy.sql
# import sqlalchemy.orm as orm
from sqlalchemy.orm import sessionmaker
# from sqlalchemy.orm.exc import NoResultFound
# from sqlalchemy.orm.exc import MultipleResultsFound

Base = declarative_base()

class Worker(Base):
    __tablename__ = 'worker'
    id = DB.Column(DB.Integer, primary_key=True)
    ip = DB.Column(DB.String)
    cc2w = DB.Column(DB.Boolean)
    w2cc = DB.Column(DB.Boolean)

class Job(Base):
    __tablename__ = 'job'
    id = DB.Column(DB.Integer, primary_key=True)
    url = DB.Column(DB.String)
    submit = DB.Column(DB.Float)
    start = DB.Column(DB.Float)
    complete = DB.Column(DB.Float)
    worker = DB.Column(DB.String)
    result = DB.Column(DB.Text)

    def __init__(self, url):
        self.url = url
        self.submit = time.time()

    @classmethod
    def submit(cls, session, urls):
        for url in urls:
            job = cls(url)
            session.add(job)
        session.add(job)
        session.commit()

    @classmethod
    def claim(cls, worker):
        job = session.query(cls).\
            filter(cls.start is None).\
            order_by(cls.submit).\
            with_for_update().first()
        job.submit = time.time()
        job.worker = worker
        session.commit()

    @classmethod
    def finishJob(cls, url, worker, data):
        job = session.query(cls).\
            filter(cls.start is not None, cls.worker == worker, cls.url == url).\
            with_for_update().first()
        job.complete = time.time()
        job.result = data
        session.commit()

    @classmethod
    def failJob(cls, url, worker, data):
        job = session.query(cls).\
            filter(cls.start is not None, cls.worker == worker, cls.url == url).\
            with_for_update().first()
        job.submit = time.time()
        job.start = None
        job.complete = None
        job.worker = None
        job.result = None
        session.commit()



def getDB():
    db = DB.create_engine('sqlite:///verodin.db')
    return db

def initDB():
    Session = sessionmaker(bind=getDB())
    session = Session()
    Base.metadata.create_all(getDB())
    session.commit()
    return session


def getMyIPAddress():
    """
    Returns the public facing IP address of localhost.  Depending on
    network engineering there may be no way to reach localhost by
    using this address, but it will certainly be where traffic from
    localhost will appear to originate.

    @returns: str -- external ip address of localhost
    """
    return requests.get('https://api.ipify.org').text
