import os
import logging

CONTROLLER = os.environ.get('CONTROLLER_HOST')
REPLICA1 = os.environ.get('REPLICA1')
REPLICA2 = os.environ.get('REPLICA2')
INFRA_IMAGE_UUID = os.environ.get('INFRA_IMAGE',
                                 'docker:rancher/infra')
DEFAULT_TIMEOUT = 45
PRIVATE_KEY_FILENAME = "/tmp/private_key_host_ssh"

REPLICA_STATES = ["In-sync", "Degraded", "critical", "offline"]


root_dir = os.environ.get('TEST_ROOT_DIR',
                          os.path.join(os.path.dirname(__file__), 'tests',
                                       'validation_v2/storage'))

log_dir = os.path.join(root_dir, 'log')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
logfile = os.path.join(log_dir, 'test.log')
FORMAT = "\n[ %(asctime)s %(levelname)s %(filename)s:%(lineno)s " \
         "- %(funcName)20s() ] %(message)s \n"
logging.basicConfig(level=logging.INFO, format=FORMAT,
                    datefmt='%a, %d %b %Y %H:%M:%S')
logger = logging.getLogger(__name__)
