from common_fixtures import *  # NOQA
import re


def pytest_configure(config):
    cleanup()


def cleanup():
    logger.info('Running cleanup')
    sc = super_client(accounts())
    instance_name_format = re.compile('Test')
    # For cleaning up environment and instances that get disassociated
    # from services where deleted
    env_name_format = re.compile('Test')
    # instance_name_format_for_services =
    # re.compile('test[0-9]{1,6}_test[0-9]{1,6}_[0-9]*')

    to_delete_env = []
    for i in sc.list_environment(state='active'):
        try:
            if env_name_format.match(i.name):
                to_delete_env.append(i)
        except AttributeError:
            pass
    delete_all(sc, to_delete_env)
    logger.info("Environments Deleted")

    to_delete_lb = []
    for i in sc.list_loadBalancer(state='active'):
        try:
            if instance_name_format.match(i.name):
                to_delete_lb.append(i)
        except AttributeError:
            pass
    delete_all(sc, to_delete_lb)
    logger.info("LBs Deleted")

    to_delete_lb_config = []
    for i in sc.list_loadBalancerConfig(state='active'):
        try:
            if instance_name_format.match(i.name):
                to_delete_lb_config.append(i)
        except AttributeError:
            pass
    delete_all(sc, to_delete_lb_config)
    logger.info("LB Configs deleted")

    to_delete_lb_listener = []
    for i in sc.list_loadBalancerListener(state='active'):
        try:
            if instance_name_format.match(i.name):
                to_delete_lb_listener.append(i)
        except AttributeError:
            pass
    delete_all(sc, to_delete_lb_listener)
    logger.info("LB listeners deleted")

    to_delete = []
    for i in sc.list_instance(state='running'):
        try:
            if instance_name_format.match(i.name) or \
                    i.name.startswith("socat-test") or \
                    i.name.startswith("native-test") or \
                    i.name.startswith("target-native-test-") or \
                    i.name.startswith("rancher-compose"):
                to_delete.append(i)
        except AttributeError:
            pass

    delete_all(sc, to_delete)
    logger.info("Running Instances deleted")

    to_delete = []
    for i in sc.list_instance(state='stopped'):
        try:
            if i.name is not None:
                if instance_name_format.match(i.name) or \
                        i.name.startswith("native-test") or \
                        i.name.startswith("target-native-test-"):
                    to_delete.append(i)
        except AttributeError:
            pass

    delete_all(sc, to_delete)
    logger.info("Stopped instances deleted")
