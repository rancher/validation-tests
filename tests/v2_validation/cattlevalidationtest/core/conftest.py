from common_fixtures import *  # NOQA
import re
import logging

log = logging.getLogger(__name__)


def pytest_configure(config):
    cleanup()


def cleanup():
    log.info('Running cleanup')
    rancher_client = client(admin_client())
    instance_name_format = re.compile('test-[0-9]{1,6}')
    # For cleaning up environment and instances that get disassociated
    # from services where deleted
    env_name_format = re.compile('test[0-9]{1,6}')
    # instance_name_format_for_services =
    # re.compile('test[0-9]{1,6}_test[0-9]{1,6}_[0-9]*')

    to_delete_env = []
    for i in rancher_client.list_stack(state='active'):
        try:
            if env_name_format.match(i.name):
                to_delete_env.append(i)
        except AttributeError:
            pass
    delete_all(rancher_client, to_delete_env)

    to_delete = []
    for i in rancher_client.list_instance(state='running'):
        try:
            if i.name is not None:
                if instance_name_format.match(i.name) or \
                        i.name.startswith("socat-test") or \
                        i.name.startswith("host-test") or \
                        i.name.startswith("native-test") or \
                        i.name.startswith("target-native-test-") or \
                        i.name.startswith("lb-test-client") or \
                        i.name.startswith("rancher-compose"):
                    to_delete.append(i)
        except AttributeError:
            pass

    delete_all(rancher_client, to_delete)

    to_delete = []
    for i in rancher_client.list_instance(state='stopped'):
        try:
            if i.name is not None:
                if instance_name_format.match(i.name) or \
                        i.name.startswith("native-test") or \
                        i.name.startswith("host-test") or \
                        i.name.startswith("target-native-test-"):
                    to_delete.append(i)
        except AttributeError:
            pass

    delete_all(rancher_client, to_delete)

    # Delete all apiKeys created by test runs
    account = rancher_client.list_project(uuid="adminProject")[0]
    for cred in account.credentials():
        if cred.kind == 'apiKey' and \
                instance_name_format.match(cred.publicValue) \
                and cred.state == "active":
            print cred.id
            cred = rancher_client.wait_success(cred.deactivate())
            rancher_client.delete(cred)
