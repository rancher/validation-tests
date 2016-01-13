from common_fixtures import *  # NOQA
import re


def pytest_configure(config):
    cleanup()


def cleanup():
    logger.info('Running cleanup')
    replica1 = os.environ.get('REPLICA1')
    replica2 = os.environ.get('REPLICA2')
    controller = os.environ.get('CONTROLLER')
    ssh_replica1 = connect(replica1)
    ssh_replica2 = connect(replica2)
    ssh_controller = connect(controller)

    try:
        # kill replica 1 daemon if running and delete /data folder if exists
        cmd = 'docker exec -i 4d sh -c "pkill -f replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        logger.info(stdout.readlines)
        cmd = 'docker exec -i 4d sh -c "pgrep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        assert len(stdout.readlines()) == 0

        # kill replica 2 daemon if running and delete /data folder if exists
        cmd = 'docker exec -i f1 sh -c "pkill -f replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines)
        cmd = 'docker exec -i f1 sh -c "pgrep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        assert len(stdout.readlines()) == 0

        # kill controller daemon if running and delete /controller
        # folder if exists
        cmd = 'docker exec -i 5f sh -c "pkill -f controller"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_controller.exec_command(cmd)
        logger.info(stdout.readlines)
        cmd = 'docker exec -i 5f sh -c "pgrep controller"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_controller.exec_command(cmd)
        assert len(stdout.readlines()) == 0

    except:
        logger.info("Execution of cmd %s failed", cmd)