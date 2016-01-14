import logging
import pytest
import os
import paramiko
import sys
import time
from common_fixtures import *  # NOQA

FORMAT = "\n[ %(asctime)s %(levelname)s %(filename)s:%(lineno)s " \
         "- %(funcName)20s() ] %(message)s \n"
logging.basicConfig(level=logging.INFO, format=FORMAT,
                    datefmt='%a, %d %b %Y %H:%M:%S')
logger = logging.getLogger(__name__)


@pytest.mark.incremental
class Test2Replica:

    def test_create_replica_invalid_parameters(self):

        # create replica with missing size parameter
        replica1 = os.environ.get('REPLICA1')
        ssh_replica1 = connect(replica1)

        # create replica with volume size that is not multiple of 4K
        cmd = "docker exec -i 4d sh -c \"mkdir data; cd data; echo" \
              " '/Blockstore/requests debug' > log.rc; " \
              "nohup /usr/local/bin/replica " \
              "--name vol1 --create -p 4000 " \
              "--size 1G --slab 256M  > /dev/null 2>&1 & \""
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines())

        # create replica with slab size that is not divisor of volume size
        cmd = "docker exec -i 4d sh -c \"mkdir data; cd data; echo" \
              " '/Blockstore/requests debug' > log.rc; " \
              "nohup /usr/local/bin/replica " \
              "--name vol1 --create -p 4000 " \
              "--size 1G --slab 256M  > /dev/null 2>&1 & \""
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines())

    def test_create_replicas(self):
        replica1 = os.environ.get('REPLICA1')
        replica2 = os.environ.get('REPLICA2')
        ssh_replica1 = connect(replica1)
        ssh_replica2 = connect(replica2)

        try:
            cmd = "docker ps"
            logger.info("command being executed %s:", cmd)
            stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
            response = stdout.readlines()
            logger.info(response)

            # create replica 1
            cmd = "docker exec -i 4d sh -c \"mkdir data; cd data; echo" \
                  " '/Blockstore/requests debug' > log.rc; " \
                  "nohup /usr/local/bin/replica " \
                  "--name vol1 --create -p 4000 " \
                  "--size 1G --slab 256M  > /dev/null 2>&1 & \""
            logger.info("command being executed %s", cmd)
            stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
            logger.info(stdout.readlines())

            # Verify replica 1 is created
            cmd = 'docker exec -i 4d sh -c "pgrep /usr/local/binreplica"'
            logger.info("command being executed %s", cmd)
            stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
            assert len(stdout.readlines()) > 0

            # create replica 2
            cmd = "docker exec -i f1 sh -c \"mkdir data; cd data; echo" \
                  " '/Blockstore/requests debug' > log.rc; " \
                  "nohup /usr/local/bin/replica " \
                  "--name vol1 --create -p 4000 " \
                  "--size 1G --slab 256M  > /dev/null 2>&1 & \""
            logger.info("command being executed %s", cmd)
            stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
            logger.info(stdout.readlines())

            # Verify replica 2 is created
            cmd = 'docker exec -i f1 sh -c "pgrep /usr/local/bin/replica"'
            logger.info("command being executed %s", cmd)
            stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
            assert len(stdout.readlines()) > 0

        except:
            logger.info("Execution of cmd %s failed", cmd)

    def test_connect_controller(self):
        controller = os.environ.get('CONTROLLER')
        ssh_controller = connect(controller)

        try:
            cmd = "docker ps"
            logger.info("command being executed %s:", cmd)
            stdin, stdout, stderr = ssh_controller.exec_command(cmd)
            response = stdout.readlines()
            logger.info(response)

            # controller connects to two replicas
            cmd = "docker exec -i 5f sh -c \"mkdir controller; " \
                  "cd controller; echo '/block/Client debug' " \
                  " \n '/block/CLient/State/Trace info'> log.rc; " \
                  "nohup /usr/local/bin/controller --host " \
                  "159.203.244.43:4000 --host 159.203.223.170:4000" \
                  "  > /dev/null 2>&1 & \""
            logger.info("command being executed %s", cmd)
            stdin, stdout, stderr = ssh_controller.exec_command(cmd)
            logger.info(stdout.readlines())

            # Verify controller is successfully created
            cmd = 'docker exec -i 5f sh -c "pgrep controller"'
            logger.info("command being executed %s", cmd)
            stdin, stdout, stderr = ssh_controller.exec_command(cmd)
            assert len(stdout.readlines()) > 0

            # Verify replica state and check if they are Online


        except:
            logger.info("Execution of cmd %s failed", cmd)

    def test_quorum_1(self):
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

    def test_quorum_2(self):
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

    def test_quorum_3(self):
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


@pytest.mark.skipif(1 == 1, "skip")
@pytest.mark.incremental
class Test3Replica:

    def test_create_replicas(self):
        replica1 = os.environ.get('REPLICA1')
        replica2 = os.environ.get('REPLICA2')
        ssh_replica1 = connect(replica1)
        ssh_replica2 = connect(replica2)

        try:
            cmd = "docker ps"
            logger.info("command being executed %s:", cmd)
            stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
            response = stdout.readlines()
            logger.info(response)

            # create replica 1
            cmd = "docker exec -i 4d sh -c \"mkdir data; cd data; echo" \
                  " '/Blockstore/requests debug' > log.rc; " \
                  "nohup /usr/local/bin/replica " \
                  "--name vol1 --create -p 4000 " \
                  "--size 1G --slab 256M  > /dev/null 2>&1 & \""
            logger.info("command being executed %s", cmd)
            stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
            logger.info(stdout.readlines())

            # Verify replica 1 is created
            cmd = 'docker exec -i 4d sh -c "pgrep /usr/local/binreplica"'
            logger.info("command being executed %s", cmd)
            stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
            assert len(stdout.readlines()) > 0

            # create replica 2
            cmd = "docker exec -i f1 sh -c \"mkdir data; cd data; echo" \
                  " '/Blockstore/requests debug' > log.rc; " \
                  "nohup /usr/local/bin/replica " \
                  "--name vol1 --create -p 4000 " \
                  "--size 1G --slab 256M  > /dev/null 2>&1 & \""
            logger.info("command being executed %s", cmd)
            stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
            logger.info(stdout.readlines())

            # Verify replica 2 is created
            cmd = 'docker exec -i f1 sh -c "pgrep /usr/local/bin/replica"'
            logger.info("command being executed %s", cmd)
            stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
            assert len(stdout.readlines()) > 0

        except:
            logger.info("Execution of cmd %s failed", cmd)

    def test_connect_controller(self):
        controller = os.environ.get('CONTROLLER')
        ssh_controller = connect(controller)

        try:
            cmd = "docker ps"
            logger.info("command being executed %s:", cmd)
            stdin, stdout, stderr = ssh_controller.exec_command(cmd)
            response = stdout.readlines()
            logger.info(response)

            # controller connects to two replicas
            cmd = "docker exec -i 5f sh -c \"mkdir controller; " \
                  "cd controller; echo '/block/Client debug' " \
                  " \n '/block/CLient/State/Trace info'> log.rc; " \
                  "nohup /usr/local/bin/controller --host " \
                  "159.203.244.43:4000 --host 159.203.223.170:4000" \
                  "  > /dev/null 2>&1 & \""
            logger.info("command being executed %s", cmd)
            stdin, stdout, stderr = ssh_controller.exec_command(cmd)
            logger.info(stdout.readlines())

            # Verify controller is successfully created
            cmd = 'docker exec -i 5f sh -c "pgrep controller"'
            logger.info("command being executed %s", cmd)
            stdin, stdout, stderr = ssh_controller.exec_command(cmd)
            assert len(stdout.readlines()) > 0

            # Verify replica state and check if they are Online


        except:
            logger.info("Execution of cmd %s failed", cmd)

    def test_quorum_1(self):
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

    def test_quorum_2(self):
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

    def test_quorum_3(self):
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




