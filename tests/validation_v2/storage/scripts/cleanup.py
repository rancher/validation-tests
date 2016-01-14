from common_fixtures import *  # NOQA
from multiprocessing import Process


class cleanup():

    logger.info('Running cleanup')
    replica1 = os.environ.get('REPLICA1')
    replica2 = os.environ.get('REPLICA2')
    replica3 = os.environ.get('REPLICA3')
    controller = os.environ.get('CONTROLLER')
    ssh_replica1 = connect(replica1)
    ssh_replica2 = connect(replica2)
    ssh_controller = connect(controller)

    def kill_replica1(self):
        # kill replica 1 daemon if running and delete /data folder if exists
        cmd = "docker exec -i 4d sh -c 'pkill -f replica'"
        logger.info("command being executed %s", cmd)
        self.ssh_replica1.exec_command(cmd)
        cmd = "docker exec -i 4d sh -c 'pgrep replica'"
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = self.ssh_replica1.exec_command(cmd)
        assert len(stdout.readlines()) == 0
        cmd = "docker exec -i 4d sh -c 'rm -rf data'"
        logger.info("command being executed %s", cmd)
        self.ssh_replica1.exec_command(cmd)

    def kill_replica2(self):
        # kill replica 2 daemon if running and delete /data folder if exists
        cmd = 'docker exec -i f1 sh -c "pkill -f replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = self.ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines)
        cmd = 'docker exec -i f1 sh -c "pgrep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = self.ssh_replica2.exec_command(cmd)
        assert len(stdout.readlines()) == 0
        cmd = "docker exec -i 4d sh -c 'rm -rf data'"
        logger.info("command being executed %s", cmd)
        self.ssh_replica1.exec_command(cmd)

    # def kill_replica3(self):
        # kill replica 2 daemon if running and delete /data folder if exists
        # cmd = 'docker exec -i f1 sh -c "pkill -f replica"'
        # logger.info("command being executed %s", cmd)
        # stdin, stdout, stderr = self.ssh_replica3.exec_command(cmd)
        # logger.info(stdout.readlines)
        # cmd = 'docker exec -i f1 sh -c "pgrep replica"'
        # logger.info("command being executed %s", cmd)
        # stdin, stdout, stderr = self.ssh_replica3.exec_command(cmd)
        # assert len(stdout.readlines()) == 0
        # cmd = "docker exec -i 4d sh -c 'rm -rf data'"
        # logger.info("command being executed %s", cmd)
        # self.ssh_replica1.exec_command(cmd)

    def kill_controller(self):
        # kill controller daemon if running and delete /controller
        # folder if exists
        cmd = 'docker exec -i 5f sh -c "pkill -f controller"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = self.ssh_controller.exec_command(cmd)
        logger.info(stdout.readlines)
        cmd = 'docker exec -i 5f sh -c "pgrep controller"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = self.ssh_controller.exec_command(cmd)
        assert len(stdout.readlines()) == 0
        cmd = "docker exec -i 4d sh -c 'rm -rf controller'"
        logger.info("command being executed %s", cmd)
        self.ssh_replica1.exec_command(cmd)

if __name__ == "__main__":
    c = cleanup()
    p1 = Process(target=cleanup.kill_replica1(c))
    p1.start()
    p2 = Process(target=cleanup.kill_replica2(c))
    p2.start()
    p3 = Process(target=cleanup.kill_controller(c))
    p3.start()
    # p4 = Process(target=cleanup.kill_replica3(c))
    # p4.start()
