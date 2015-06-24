from common_fixtures import *  # NOQA
import re


@pytest.fixture(autouse=True, scope='session')
def cleanup(super_client):
    instance_name_format = re.compile('test-[0-9]{1,6}')
    # For cleaning up environment and instances that get disassociated
    # from services where deleted
    env_name_format = re.compile('test[0-9]{1,6}')
    instance_name_format_for_services = \
        re.compile('test[0-9]{1,6}_test[0-9]{1,6}_[0-9]*')

    to_delete_env = []
    for i in super_client.list_environment(state='active'):
        try:
            if env_name_format.match(i.name):
                to_delete_env.append(i)
        except AttributeError:
            pass
    delete_all(super_client, to_delete_env)

    to_delete = []
    for i in super_client.list_instance(state='running'):
        try:
            if instance_name_format.match(i.name) or \
                    instance_name_format_for_services.match(i.name):
                to_delete.append(i)
        except AttributeError:
            pass

    delete_all(super_client, to_delete)

    to_delete = []
    for i in super_client.list_instance(state='stopped'):
        try:
            if i.name is not None:
                if instance_name_format.match(i.name) or \
                        instance_name_format_for_services.match(i.name):
                    to_delete.append(i)
        except AttributeError:
            pass

    delete_all(super_client, to_delete)

    to_delete_lb = []
    for i in super_client.list_loadBalancer(state='active'):
        try:
            if instance_name_format.match(i.name):
                to_delete_lb.append(i)
        except AttributeError:
            pass
    delete_all(super_client, to_delete_lb)

    to_delete_lb_config = []
    for i in super_client.list_loadBalancerConfig(state='active'):
        try:
            if instance_name_format.match(i.name):
                to_delete_lb_config.append(i)
        except AttributeError:
            pass
    delete_all(super_client, to_delete_lb_config)

    to_delete_lb_listener = []
    for i in super_client.list_loadBalancerListener(state='active'):
        try:
            if instance_name_format.match(i.name):
                to_delete_lb_listener.append(i)
        except AttributeError:
            pass

    delete_all(super_client, to_delete_lb_listener)
