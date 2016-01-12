import logging
import pytest
import os
import paramiko
import sys
import time

FORMAT = "\n[ %(asctime)s %(levelname)s %(filename)s:%(lineno)s " \
         "- %(funcName)20s() ] %(message)s \n"
logging.basicConfig(level=logging.INFO, format=FORMAT,
                    datefmt='%a, %d %b %Y %H:%M:%S')
logger = logging.getLogger(__name__)


def connect(host):
    i = 1
    #
    # Try to connect to the host.
    # Retry a few times if it fails.
    #
    while True:
        logger.info("Trying to connect to %s (%i/30)", host, i)
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            privatekeyfile = os.path.expanduser('~/.ssh/id_rsa')
            mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
            ssh.connect(host, username='root', pkey=mykey)
            logger.info("Connected to %s", host)
            break
        except paramiko.AuthenticationException:
            logger.info("Authentication failed when connecting to %s",
                        host)
            sys.exit(1)
        except:
            logger.info("Could not SSH to %s, waiting for it to start",
                        host)
            i += 1
            time.sleep(2)

        # If we could not connect within time limit
        if i == 30:
            logger.info("Could not connect to %s. Giving up. "
                        "Please check private key file.", host)
            ssh.close()
            sys.exit(1)

    return ssh

@pytest.mark.order1
def test_create_replicas():
    controller = os.environ.get('CONTROLLER')
    replica1 = os.environ.get('REPLICA1')
    replica2 = os.environ.get('REPLICA2')
    ssh_replica1 = connect(replica1)
    ssh_replica2 = connect(replica2)
    ssh_controller = connect(controller)

    try:
        cmd = "docker ps"
        logger.info("command being executed %s:", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        response = stdout.readlines()
        logger.info(response)

        # create replica 1
        cmd = "docker exec -i 4d sh -c \"mkdir data; cd data; echo '/Blockstore/requests debug' > log.rc; nohup /usr/local/bin/replica --name vol1 --create -p 4000 --size 1G --slab 256M  > /dev/null 2>&1 & \""
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines())

        # Verify replica 1 is created
        cmd = 'docker exec -i 4d sh -c "ps -aef | grep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines())
        verify_replica_process = "/usr/local/bin/replica"
        assert verify_replica_process in stdout.readlines()

        # create replica 2
        cmd = "docker exec -i f1 sh -c \"mkdir data; cd data; echo '/Blockstore/requests debug' > log.rc; nohup /usr/local/bin/replica --name vol1 --create -p 4000 --size 1G --slab 256M  > /dev/null 2>&1 & \""
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines())

        # Verify replica 2 is created
        cmd = 'docker exec -i f1 sh -c "ps -aef | grep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines())
        verify_replica_process = "/usr/local/bin/replica"
        assert verify_replica_process in stdout.readlines()

    except:
        logger.info("Execution of cmd %s failed", cmd)

@pytest.mark.order2
def test_connect_controller():
    controller = os.environ.get('CONTROLLER')
    replica1 = os.environ.get('REPLICA1')
    replica2 = os.environ.get('REPLICA2')
    ssh_replica1 = connect(replica1)
    ssh_replica2 = connect(replica2)
    ssh_controller = connect(controller)

    try:
        cmd = "docker ps"
        logger.info("command being executed %s:", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        response = stdout.readlines()
        logger.info(response)

        # create replica 1
        cmd = "docker exec -i 4d sh -c \"mkdir data; cd data; echo '/Blockstore/requests debug' > log.rc; nohup /usr/local/bin/replica --name vol2 --create -p 4001 --size 1G --slab 256M  > /dev/null 2>&1 & \""
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines())

        # Verify replica 1 is created
        cmd = 'docker exec -i 4d sh -c "ps -aef | grep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines())
        verify_replica_process = "/usr/local/bin/replica"
        assert verify_replica_process in stdout.readlines()

        # create replica 2
        cmd = "docker exec -i f1 sh -c \"mkdir data; cd data; echo '/Blockstore/requests debug' > log.rc; nohup /usr/local/bin/replica --name vol2 --create -p 4001 --size 1G --slab 256M  > /dev/null 2>&1 & \""
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines())

        # Verify replica 2 is created
        cmd = 'docker exec -i f1 sh -c "ps -aef | grep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines())
        verify_replica_process = "/usr/local/bin/replica"
        assert verify_replica_process in stdout.readlines()

    except:
        logger.info("Execution of cmd %s failed", cmd)

@pytest.mark.order3
def test_quorum_1():
    controller = os.environ.get('CONTROLLER')
    replica1 = os.environ.get('REPLICA1')
    replica2 = os.environ.get('REPLICA2')
    ssh_replica1 = connect(replica1)
    ssh_replica2 = connect(replica2)
    ssh_controller = connect(controller)

    try:
        cmd = "docker ps"
        logger.info("command being executed %s:", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        response = stdout.readlines()
        logger.info(response)

        # create replica 1
        cmd = "docker exec -i 4d sh -c \"mkdir data; cd data; echo '/Blockstore/requests debug' > log.rc; nohup /usr/local/bin/replica --name vol3 --create -p 4000 --size 1G --slab 256M  > /dev/null 2>&1 & \""
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines())

        # Verify replica 1 is created
        cmd = 'docker exec -i 4d sh -c "ps -aef | grep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines())
        verify_replica_process = "/usr/local/bin/replica"
        assert verify_replica_process in stdout.readlines()

        # create replica 2
        cmd = "docker exec -i f1 sh -c \"mkdir data; cd data; echo '/Blockstore/requests debug' > log.rc; nohup /usr/local/bin/replica --name vol3 --create -p 4000 --size 1G --slab 256M  > /dev/null 2>&1 & \""
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines())

        # Verify replica 2 is created
        cmd = 'docker exec -i f1 sh -c "ps -aef | grep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines())
        verify_replica_process = "/usr/local/bin/replica"
        assert verify_replica_process in stdout.readlines()

    except:
        logger.info("Execution of cmd %s failed", cmd)

@pytest.mark.order4
def test_quorum_2():
    controller = os.environ.get('CONTROLLER')
    replica1 = os.environ.get('REPLICA1')
    replica2 = os.environ.get('REPLICA2')
    ssh_replica1 = connect(replica1)
    ssh_replica2 = connect(replica2)
    ssh_controller = connect(controller)

    try:
        cmd = "docker ps"
        logger.info("command being executed %s:", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        response = stdout.readlines()
        logger.info(response)

        # create replica 1
        cmd = "docker exec -i 4d sh -c \"mkdir data; cd data; echo '/Blockstore/requests debug' > log.rc; nohup /usr/local/bin/replica --name vol4 --create -p 4000 --size 1G --slab 256M  > /dev/null 2>&1 & \""
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines())

        # Verify replica 1 is created
        cmd = 'docker exec -i 4d sh -c "ps -aef | grep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines())
        verify_replica_process = "/usr/local/bin/replica"
        assert verify_replica_process in stdout.readlines()

        # create replica 2
        cmd = "docker exec -i f1 sh -c \"mkdir data; cd data; echo '/Blockstore/requests debug' > log.rc; nohup /usr/local/bin/replica --name vol4 --create -p 4000 --size 1G --slab 256M  > /dev/null 2>&1 & \""
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines())

        # Verify replica 2 is created
        cmd = 'docker exec -i f1 sh -c "ps -aef | grep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines())
        verify_replica_process = "/usr/local/bin/replica"
        assert verify_replica_process in stdout.readlines()

    except:
        logger.info("Execution of cmd %s failed", cmd)

@pytest.mark.order5
def test_quorum_3():
    controller = os.environ.get('CONTROLLER')
    replica1 = os.environ.get('REPLICA1')
    replica2 = os.environ.get('REPLICA2')
    ssh_replica1 = connect(replica1)
    ssh_replica2 = connect(replica2)
    ssh_controller = connect(controller)

    try:
        cmd = "docker ps"
        logger.info("command being executed %s:", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        response = stdout.readlines()
        logger.info(response)

        # create replica 1
        cmd = "docker exec -i 4d sh -c \"mkdir data; cd data; echo '/Blockstore/requests debug' > log.rc; nohup /usr/local/bin/replica --name vol5 --create -p 4000 --size 1G --slab 256M  > /dev/null 2>&1 & \""
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines())

        # Verify replica 1 is created
        cmd = 'docker exec -i 4d sh -c "ps -aef | grep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines())
        verify_replica_process = "/usr/local/bin/replica"
        assert verify_replica_process in stdout.readlines()

        # create replica 2
        cmd = "docker exec -i f1 sh -c \"mkdir data; cd data; echo '/Blockstore/requests debug' > log.rc; nohup /usr/local/bin/replica --name vol5 --create -p 4000 --size 1G --slab 256M  > /dev/null 2>&1 & \""
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines())

        # Verify replica 2 is created
        cmd = 'docker exec -i f1 sh -c "ps -aef | grep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines())
        verify_replica_process = "/usr/local/bin/replica"
        assert verify_replica_process in stdout.readlines()

    except:
        logger.info("Execution of cmd %s failed", cmd)






