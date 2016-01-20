from common_fixtures import *  # NOQA

# Verify controller status
def controller_status(cport, controller):
    rval = invoke_cli(controller, ["controller-status"], cport)
    logger.info(rval)
    logger.info\
        ('Controller status is: ' + str(rval["controller-status"]))

c = cleanup()
c.kill_controller()
c.kill_replica1()
c.kill_replica2()
c.kill_replica3()

ssh_controller = connect(controller)
ssh_replica1 = connect(replica1)
ssh_replica2 = connect(replica2)
ssh_replica3 = connect(replica3)

# create replica 1
cmd = "docker exec -i 4d sh -c \"mkdir " \
      "replica1; cd replica1; echo" \
      " '/Blockstore/requests debug' > log.rc; " \
      "nohup /usr/local/bin/replica " \
      "--name vol1 --create -p 4000 " \
      "--size 1G --slab 256M  > /dev/null 2>&1 & \""
logger.info("command being executed %s", cmd)
stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
logger.info(stdout.readlines())

# Verify replica 1 is created
cmd = 'docker exec -i 4d sh -c "pgrep replica"'
logger.info("command being executed %s", cmd)
stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
assert len(stdout.readlines()) > 0

# create replica 2
cmd = "docker exec -i f1 sh -c \"mkdir replica2; " \
      "cd replica2; echo" \
      " '/Blockstore/requests debug' > log.rc; " \
      "nohup /usr/local/bin/replica " \
      "--name vol1 --create -p 4000 " \
      "--size 1G --slab 256M  > /dev/null 2>&1 & \""
logger.info("command being executed %s", cmd)
stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
logger.info(stdout.readlines())

# Verify replica 2 is created
cmd = 'docker exec -i f1 sh -c "pgrep replica"'
logger.info("command being executed %s", cmd)
stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
assert len(stdout.readlines()) > 0

# create replica 3
cmd = "docker exec -i c4 sh -c \"mkdir replica3; " \
      "cd replica3; echo" \
      " '/Blockstore/requests debug' > log.rc; " \
      "nohup /usr/local/bin/replica " \
      "--name vol1 --create -p 4001 " \
      "--size 1G --slab 256M  > /dev/null 2>&1 & \""
logger.info("command being executed %s", cmd)
stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
logger.info(stdout.readlines())

# Verify replica 3 is created
cmd = 'docker exec -i c4 sh -c "pgrep replica"'
logger.info("command being executed %s", cmd)
stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
assert len(stdout.readlines()) > 0

# controller connects to three replicas
cmd = "docker exec -i 5f sh -c \"mkdir controller; " \
      "cd controller; echo '/block/Client debug' " \
      " \n '/block/CLient/State/Trace info'> log.rc; " \
      "nohup /usr/local/bin/controller --host " \
      "159.203.244.43:4000 --host 159.203.223.170:4000 " \
      "--host 159.203.223.170:4001 > /dev/null 2>&1 & \""
logger.info("command being executed %s", cmd)
stdin, stdout, stderr = ssh_controller.exec_command(cmd)
logger.info(stdout.readlines())

time.sleep(10)
# Verify controller is successfully created
cmd = 'docker exec -i 5f sh -c "pgrep controller"'
logger.info("command being executed %s", cmd)
stdin, stdout, stderr = ssh_controller.exec_command(cmd)
assert len(stdout.readlines()) > 0

# Verify controller status
controllerstatus = controller_status(5000, "159.203.244.43")
logger.info("Controller status: %s", controllerstatus)

# kill replica 1 daemon if running,
# delete /replica1 folder if exists
cmd = "docker exec -i 4d sh -c 'pkill -f replica'"
logger.info("command being executed %s", cmd)
ssh_replica1.exec_command(cmd)
cmd = "docker exec -i 4d sh -c 'pgrep replica'"
logger.info("command being executed %s", cmd)
stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
assert len(stdout.readlines()) == 0
cmd = "docker exec -i 4d sh -c 'rm -rf replica1'"
logger.info("command being executed %s", cmd)
ssh_replica1.exec_command(cmd)

time.sleep(5)
# Verify controller status
controllerstatus = controller_status(5000, "159.203.244.43")
logger.info("Controller status: %s", controllerstatus)
