import csv
import os.path
import sys
import time

import boto.ec2.keypair

import sqlalchemy as DB
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

import requests

# path to the downloaded AWS credential file
# Assumed to have the standard header
# Name, accessKey, secretKey
# Normally this would just automatically use the credentials in
# ~/.boto but I'd like to keep these credentials separate.
DEFAULT_CREDENTIAL_PATH='../credentials.csv'


# These are the stock ubuntu server 14.04 AMIs.
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
    """
    Wrapper around boto for our specific use cases. It would be
    best to only have a single instance of this object so connection
    caching can be used.
    """
    def __init__(self, credentialPath=DEFAULT_CREDENTIAL_PATH):
        try:
            with open(credentialPath, 'r') as f:
                reader = csv.reader(f)
                self.credentials = list(reader)[1] # downloaded file has a header
                self.accessKey = self.credentials[1]
                self.secretKey = self.credentials[2]
        except (IOError, IndexError):
            print('Could not read credentials from %s or bad format.' % credentialPath)
            raise
            sys.exit(1)


        self.conns = {} # connection cache

    def getConn(self, region):
        """
        Gets, caches and returns and ec2 connection for the given
        region.

        @param region: string repr of the region (i.e. 'us-east-1')

        @returns: boto connection object.
        """
        if not self.conns.get(region):
            conn = boto.ec2.connect_to_region(region,
                        aws_access_key_id=self.accessKey,
                        aws_secret_access_key=self.secretKey)
            self.conns[region] = conn
        return self.conns[region]

    def createKeypairs(self):
        """
        Generates missing keys and saves them to file.

        One key for each region is generated if it doesn't already
        exist.  They are created in src/keys and the files are
        named for the region they apply to.

        If you delete keypairs through the AWS UI you'll have to delete
        the corresponding file locally.
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

    def pushSecurityGroups(self, sgName):
        """
        Convenience method.

        Takes the 'worker' security group and copies it to other
        regions if they do not already have a 'worker' security
        group.

        Once copied they are not linked and so any changes won't
        propagate, but if you delete the 'worker' SG in regions
        other than 'us-east-1' it will be copied fresh if this
        method is called.
        """
        conn = self.getConn('us-east-1')
        for sGroup in conn.get_all_security_groups([sgName]):
            for region in REGIONS:
                try:
                    dstConn = self.getConn(region)
                    sGroup.copy_to_region(dstConn.region)
                except boto.exception.EC2ResponseError:
                    #group already exists
                    pass


    def getRegions(self):
        """
        Request the regions from AWS.  The results are filterd by
        the contents of the REGIONS constant.

        @returns: list of tuples (id, human_name)
        """
        regions = boto.ec2.regions(
                aws_access_key_id=self.accessKey,
                aws_secret_access_key=self.secretKey)
        # filter to just a few regions for the moment.
        regions = [r for r in regions if r.name in REGIONS]
        # [('us-east-1', 'Virginia'), ...]
        return [(r.name, REGIONS.get(r.name, {}).get('name', r.name))
                    for r in regions
                    if r.name not in ('cn-north-1', 'us-gov-west-1')]


    @classmethod
    def generateStartScript(cls):
        """
        This is the script that will be automatically run by root when
        a worker is created. It is passed to the new node by the
        user_data parameter in run_instances.

        @returns: string script.
        """
        script = ''
        script += '#!/bin/sh\n\n'
        script += 'echo "hello" > /tmp/runStartScript.txt\n\n'
        script += 'apt-get update\n'
        script += 'apt-get install git -y\n'
        script += 'git clone https://github.com/nephlm/verodin /tmp/verodin\n\n'
        script += 'chmod -R 755 /tmp/verodin\n'
        script += 'chown -R ubuntu:ubuntu /tmp/verodin\n'
        script += 'echo "CC_IP=\'%s\'" >> /tmp/verodin/src/worker/config.py\n\n' % getMyIPAddress()
        script += 'sh /tmp/verodin/src/worker/install.sh\n\n'
        return script

    def startWorker(self, region):
        """
        Start a new worker in the specified region.
        Created instances with be tagged with the 'role' or 'worker'.
        This is used for monitoring.

        @param region: string representation of the region
        (i.e. 'us-east-1')
        """
        conn = self.getConn(region)
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

        @parma region: string - region (i.e. 'us-east-1')
        @param id: string - AWS instance id
        """
        conn = self.getConn(region)
        instances = conn.get_only_instances([id])
        for instance in instances:
            instance.terminate()


    def getWorkers(self):
        """
        Retrieve a list of worker instances from all regions.

        @returns: list of dict.  Each dict contains the following:
            {
            'id': string -- AWS instance id,
            'ip': string -- public IP address of instance.
            'state': string -- Human desc or state.
            'state_code': int -- Numeric state of instance.
            'region': string -- region where instance is running.
            'region_human': string -- Human friendly version or region.
            }
        """
        allInstances = []
        for region in REGIONS:
            conn = self.getConn(region)
            instances = conn.get_only_instances()
            # if instances:
            #     print(instances[1].tags.get('role', ''))
            allInstances += instances
        ret = [{'awsID': x.id,
                'ip': x.ip_address,
                'state': x.state,
                'state_code': x.state_code,
                'region': x.connection.region.name,
                'region_human': REGIONS.get(x.connection.region.name, {}).get('name', x.connection.region.name)}
                for x in allInstances
                if x.tags.get('role', '') == 'worker'
                and x.state_code not in (STOPPED, TERMINATED)]
        return ret


# import sqlalchemy.sql
# import sqlalchemy.orm as orm
# from sqlalchemy.orm.exc import NoResultFound
# from sqlalchemy.orm.exc import MultipleResultsFound

# Gunicorn runs muliple processes and so state needs to be maintained
# outside of the app.  A simple sqlite3 db is used for this purpose.

Base = declarative_base()

class Worker(Base):
    """
    Data about workers.  Primarily if they've said hello.
    """
    __tablename__ = 'worker'
    id = DB.Column(DB.Integer, primary_key=True)
    ip = DB.Column(DB.String,nullable=False, unique=True)
    aws_id = DB.Column(DB.String,nullable=False, unique=True)
    state = DB.Column(DB.String)
    state_code = DB.Column(DB.Integer)
    region = DB.Column(DB.String)
    region_human = DB.Column(DB.String)
    cc2w = DB.Column(DB.Boolean)
    w2cc = DB.Column(DB.Boolean)
    time_stamp = DB.Column(DB.Float)

    @classmethod
    def isStale(cls, session):
        if session.query(cls).filter(cls.time_stamp < (time.time() - 10)).count() \
                or session.query(cls).filter(cls.state_code != RUNNING).count() \
                or session.query(cls).count() == 0:
            return True
        else:
            return False

    @classmethod
    def getAll(cls, session):
        workers = session.query(cls).\
            filter(cls.state_code != TERMINATED).\
            order_by(cls.region).all()
        return [{'awsID': w.aws_id,
                'ip': w.ip,
                'state': w.state,
                'state_code': w.state_code,
                'region': w.region,
                'region_human': w.region_human,
                'cc2w': w.cc2w,
                'w2cc': w.w2cc,
                'time_stamp': w.time_stamp}
                for w in workers]

    @classmethod
    def getWorker(cls, session, ip, awsID=None):
        worker = None
        worker = session.query(cls).\
            filter(cls.ip == ip).\
            with_for_update().first()
        if not worker and awsID:
            worker = cls(ip=ip, aws_id=awsID)
            session.add(worker)
        return worker

    @classmethod
    def updateAll(cls, session, awsWorkers):
        for worker in awsWorkers:
            Worker.update(session, worker)
        validIds = [x['awsID'] for x in awsWorkers]
        session.query(cls).\
            filter(cls.aws_id.notin_(validIds)).\
            delete(synchronize_session=False)
        session.expire_all()


    @classmethod
    def update(cls, session, instance):
        if instance['ip'] is None:
            # Shutting down, no longer relevant to us.
            # In a perfect world we'd make sure it shut down properly,
            # but out of scope for this.
            session.query(cls).filter(cls.aws_id == instance['awsID']).delete()
        else:
            worker = cls.getWorker(session, instance['ip'], instance['awsID'])
            if worker:
                worker.state = instance['state']
                worker.state_code = instance['state_code']
                worker.region = instance['region']
                worker.region_human = instance['region_human']
                worker.time_stamp = time.time()
                session.commit()
                if not worker.cc2w:
                    worker.sendHello(session, worker.ip)

    @classmethod
    def gotHello(cls, session, ip):
        worker = cls.getWorker(session, ip)
        if worker:
            worker.w2cc = True
            session.commit()
        cls.sendHello(session, ip)

    @classmethod
    def sendHello(cls, session, ip):
        try:
            print('http://%s:%s/api/hello' % (ip, 6000))
            resp = requests.get('http://%s:%s/api/hello' % (ip, 6000))
            resp.raise_for_status()
            print(resp.text)
            worker = cls.getWorker(session, ip)
            if worker:
                worker.cc2w = True
                session.commit()
        except (requests.ConnectionError, requests.HTTPError):
            print('send failed')
            raise
            pass


class Job(Base):
    """
    Data about the state of a job including the result if it has
    been completed.

    For this version, urls are enforced unique.  That's probably not
    appropriate for a more realistic situation.
    """
    __tablename__ = 'job'
    id = DB.Column(DB.Integer, primary_key=True)
    url = DB.Column(DB.String, nullable=False, unique=True)
    submit = DB.Column(DB.Float)
    start = DB.Column(DB.Float)
    complete = DB.Column(DB.Float)
    worker = DB.Column(DB.String)
    result = DB.Column(DB.Text)

    def __init__(self, url):
        """
        @param url: string -- URL to retrieve.
        """
        self.url = url
        self.submit = time.time()

    @classmethod
    def add(cls, session, urls):
        """
        Add list of URLs to storage.  Duplicates will not (can not)
        be added twice since cls.url is defined as unique.

        @param session: DB Session -- access to DB
        @param ulrs: list of stings -- list of URLs to add.
        """
        success = False
        while not success:
            try:
                exist = [x.url for x in
                        session.query(cls).
                        filter(cls.url.in_(urls)).
                        all()]
                dedupe = [x for x in urls if x not in exist]
                for url in dedupe:
                    job = cls(url)
                    session.add(job)
                    session.add(job)
                session.commit()
                success = True
            except IntegrityError:

                # duplicate, skip it
                session.rollback()

    @classmethod
    def claim(cls, session, worker):
        """
        Called when a worker is looking for work.  Associates a job
        with a specific worker.

        @param worker: string -- worker ID; assumed to be the ip
            address but as long as it's consistent it could be
            something else.
        @returns: string or None -- URL to retrieve or None if no
            job is available.

        @TODO: If a worker asks for a job but is still working on
        a job then fail the job.
        """
        # jobs = session.query(cls).filter(cls.start == None).order_by(cls.submit).all()
        # print([(x.url, x.submit) for x in jobs])
        job = session.query(cls).\
            filter(cls.start == None).\
            order_by(cls.submit).\
            with_for_update().first()
        if job:
            job.start = time.time()
            job.worker = worker
            session.commit()
            return job.url
        else:
            return None

    @classmethod
    def finishJob(cls, session, url, worker, data):
        """
        Called when a worker completes a job and returns results.

        @param session: DB Session -- access to DB
        @param url: string -- URL of job being completed.
        @param worker: string -- id of the worker completing the job.
        @param data: string -- The result of the job (RAW HTML)

        @NOTE: We could immediately assign a new job, but based on the
        assignment I'm assuming the delay is intentional.
        """
        job = session.query(cls).\
            filter(cls.start is not None, cls.worker == worker, cls.url == url).\
            with_for_update().first()
        job.complete = time.time()
        job.result = data
        session.commit()

    @classmethod
    def failJob(cls, session, url, worker, data):
        """
        Called when a worker completes a job and returns results.
        At present failed tasks are just immediately resubmitted.

        @param session: DB Session -- access to DB
        @param url: string -- URL of job being failed.
        @param worker: string -- id of the worker failing the job.
        @param data: string -- Any information about the failure.

        @NOTE: We could immediately assign a new job, but based on the
        assignment I'm assuming the delay is intentional.
        """
        job = session.query(cls).\
            filter(cls.start is not None, cls.worker == worker, cls.url == url).\
            with_for_update().first()
        if job:
            job.submit = time.time()
            job.start = None
            job.complete = None
            job.worker = None
            job.result = None
            session.commit()

    @classmethod
    def getJobs(cls, session, count=None):
        """
        Returns the next count jobs to process.  If count is None,
        returns all jobs.

        @returns dict --
                {
                'cnt': int -- total depth of the queue
                'jobs': list (count long) -- the next count jobs; jobs
                        are repr'd as a dict
                        {
                        'url': string -- UrL
                        'submit' float -- timestamp when job was submitted.
                        }
                }
        """
        query = session.query(cls).\
            filter(cls.start == None).\
            order_by(cls.submit)
        if count:
            query = query.limit(count)
        jobs = query.all()
        cnt = session.query(cls).filter(cls.start == None).count()
        jobList = [{'url': j.url, 'submit': j.submit} for j in jobs]
        return {'cnt': cnt, 'jobs': jobList}

    @classmethod
    def delete(cls, session):
        """
        delete all jobs
        """
        session.query(cls).delete()

def getDB():
    """
    Create the DB engine object.
    """
    db = DB.create_engine('sqlite:///verodin.db')
    return db

def initDB():
    """
    Set up the db if it doesn't exist. Create the session.
    """
    Session = sessionmaker(bind=getDB())
    session = Session()
    Base.metadata.create_all(getDB())
    session.commit()
    return session

def getWorkers(session, aws, force=False):
    """
    Wrapper that decides whether to return cached values or query
    AWS and update the cache.

    @param session: db session object
    @param aws: AWS object

    @TODO: Decide if an AWS call is warranted or if our cache is okay.
    @TODO: Update the local copy of the workers
    """
    if force or Worker.isStale(session):
        awsWorkers = aws.getWorkers()
        Worker.updateAll(session, awsWorkers)
    return Worker.getAll(session)


def getMyIPAddress():
    """
    Returns the public facing IP address of localhost.  Depending on
    network engineering there may be no way to reach localhost by
    using this address, but it will certainly be where traffic from
    localhost will appear to originate.

    @returns: str -- external ip address of localhost
    """
    return requests.get('https://api.ipify.org').text
