from common_fixtures import *  # NOQA
from requests.auth import AuthBase
from selenium import webdriver
from test_github import URL
from common_fixtures import _client_for_user


if_ldap = pytest.mark.skipif(not os.environ.get('API_AUTH_OPEN_LDAP_SERVER'),
                             reason='API_AUTH_OPEN_LDAP_SERVER is not set')


class OpenLDAPAuth(AuthBase):
    def __init__(self, jwt, prj_id=None):
        # setup any auth-related data here
        self.jwt = jwt
        self.prj_id = prj_id

    def __call__(self, r):
        # modify and return the request
        r.headers['Authorization'] = 'Bearer ' + self.jwt
        if self.prj_id is not None:
            r.headers['X-API-Project-Id'] = self.prj_id
        return r


def create_ldap_client(username=os.getenv('LDAP_USER1', 'devUserA'),
                       password=os.getenv('LDAP_USER1_PASSWORD', 'Password1'),
                       project_id=None):
    client = _client_for_user('user', accounts())
    client.delete_by_id = delete_by_id
    assert client.valid()
    jwt = get_authed_token(username=username, password=password)['jwt']
    client._access_key = None
    client._secret_key = None

    client._auth = OpenLDAPAuth(jwt, prj_id=project_id)
    client.reload_schema()
    assert client.valid()

    identities = client.list_identity()
    assert len(identities) > 0
    is_ldap_user = False
    for identity in identities:
        if (identity.externalIdType == 'openldap_user'):
            is_ldap_user = True
    assert is_ldap_user
    return client


def get_authed_token(username=os.getenv('LDAP_USER1', 'devUserA'),
                     password=os.getenv('LDAP_USER1_PASSWORD', 'Password1')):
    token = requests.post(base_url() + 'token', {
        'code': username + ':' + password
    })
    token = token.json()
    assert token['type'] != 'error'
    assert token['user'] == username
    assert token['userIdentity']['login'] == username
    return token


def load_config():
    config = {
        "accessMode": "unrestricted",
        'domain': os.environ.get(
            'API_AUTH_OPEN_LDAP_DOMAIN', "dc=rancher,dc=io"),
        'groupNameField': os.environ.get('API_AUTH_OPEN_LDAP_GROUP_NAME_FIELD',
                                         'name'),
        'groupObjectClass': os.environ.get(
            'API_AUTH_OPEN_LDAP_GROUP_OBJECT_CLASS', 'group'),
        'groupSearchField': os.environ.get(
            'API_AUTH_OPEN_LDAP_GROUP_SEARCH_FIELD',
            'sAMAccountName'),
        'loginDomain': os.environ.get(
            'API_AUTH_OPEN_LDAP_LOGIN_NAME', 'rancher'),
        'port': os.environ.get('API_AUTH_OPEN_LDAP_PORT', 389),
        'enabled': True,
        'server': os.environ.get('API_AUTH_OPEN_LDAP_SERVER', 'ad.rancher.io'),
        'serviceAccountPassword': os.environ.get('API_AUTH_OPEN_LDAP_'
                                                 'SERVICE_ACCOUNT_PASSWORD',
                                                 'Password1'),
        'serviceAccountUsername': os.environ.get('API_AUTH_OPEN_LDAP_'
                                                 'SERVICE_ACCOUNT_USERNAME',
                                                 'cattle'),
        'tls': False,
        'userDisabledBitMask': os.environ.get('API_AUTH_OPEN_LDAP_'
                                              'USER_DISABLED_BIT_MASK',
                                              '2'),
        'userEnabledAttribute': os.environ.get('API_AUTH_OPEN_LDAP_'
                                               'USER_ENABLED_ATTRIBUTE',
                                               'userAccountControl'),
        'userLoginField': os.environ.get('API_AUTH_OPEN_LDAP_USER_LOGIN_FIELD',
                                         'sAMAccountName'),
        'userNameField': os.environ.get('API_AUTH_OPEN_LDAP_'
                                        'USER_NAME_FIELD', 'name'),
        'userObjectClass': os.environ.get(
            'API_AUTH_OPEN_LDAP_USER_OBJECT_CLASS', 'person'),
        'userSearchField': os.environ.get(
            'API_AUTH_OPEN_LDAP_USER_SEARCH_FIELD', 'name')
    }
    return config


@pytest.fixture(scope='module')
def ldap_config(admin_client, request):
    config = load_config()
    admin_client.create_ldapconfig(config)
    service_account_dn = os.getenv('API_AUTH_OPEN_LDAP_SERVICE_ACCOUNT_DN',
                                   "cn=Cattle,"
                                   "ou=Rancher Labs,dc=rancher,dc=io")
    x = admin_client.by_id('identity', 'ldap_user:' + service_account_dn)
    assert x.login == config['serviceAccountUsername']

    def fin():
        config = load_config()
        config['enabled'] = None
        admin_client.create_ldapconfig(config)
    request.addfinalizer(fin)


@if_ldap
def test_turn_on_ldap_ui(admin_client):
    config = load_config()
    config['enabled'] = None
    admin_client.create_ldapconfig(config)

    port = int(os.getenv('PHANTOMJS_WEBDRIVER_PORT', 4444))
    phantom_bin = os.getenv('PHANTOMJS_BIN', '/usr/local/bin/phantomjs')
    driver = webdriver.PhantomJS(phantom_bin, port=port)
    driver.delete_all_cookies()
    max_wait = 60
    driver.set_page_load_timeout(max_wait)
    driver.set_script_timeout(max_wait)
    driver.implicitly_wait(10)
    driver.set_window_size(1120, 550)
    driver.get('{}logout'.format(base_url()[:-3]))
    url = '{}admin/access/openldap'.format(base_url()[:-3])
    driver.get(url)
    inputs = driver.find_elements_by_class_name('ember-text-field')
    config = [
        os.environ.get('API_AUTH_OPEN_LDAP_SERVER', 'ad.rancher.io'),
        os.environ.get('API_AUTH_OPEN_LDAP_PORT', 389),
        os.environ.get(
            'API_AUTH_OPEN_LDAP_SERVICE_ACCOUNT_USERNAME', 'cattle'),
        os.environ.get(
            'API_AUTH_OPEN_LDAP_SERVICE_ACCOUNT_PASSWORD', 'Password1'),
        os.environ.get('API_AUTH_OPEN_LDAP_DOMAIN', "dc=rancher,dc=io"),
        os.environ.get('API_AUTH_OPEN_LDAP_LOGIN_NAME', 'rancher'),
        os.environ.get('API_AUTH_OPEN_LDAP_USER_OBJECT_CLASS', 'person'),
        os.environ.get(
            'API_AUTH_OPEN_LDAP_USER_LOGIN_FIELD', 'sAMAccountName'),
        os.environ.get('API_AUTH_OPEN_LDAP_USER_NAME_FIELD', 'name'),
        os.environ.get('API_AUTH_OPEN_LDAP_USER_SEARCH_FIELD', 'name'),
        os.environ.get('API_AUTH_OPEN_LDAP_USER_ENABLED_ATTRIBUTE',
                       'userAccountControl'),
        os.environ.get(
            'API_AUTH_OPEN_LDAP_USER_DISABLED_BIT_MASK', '2'),
        os.environ.get('API_AUTH_OPEN_LDAP_GROUP_OBJECT_CLASS', 'group'),
        os.environ.get('API_AUTH_OPEN_LDAP_GROUP_NAME_FIELD', 'name'),
        os.environ.get(
            'API_AUTH_OPEN_LDAP_GROUP_SEARCH_FIELD', 'sAMAccountName'),
        os.getenv('LDAP_USER1', 'devUserA'),
        os.getenv('LDAP_USER1_PASSWORD', 'Password1')
    ]

    for i in range(0, len(inputs)):
        inputs[i].clear()
        inputs[i].send_keys(config[i])

    driver.find_element_by_class_name('btn-primary').click()
    try:
        driver.find_element_by_class_name('btn-primary').click()
    except:
        pass
    time.sleep(10)
    no_auth = requests.get(URL)
    assert no_auth.status_code == 401


@if_ldap
def test_ldap_search_get_user(admin_client, ldap_config):
    search_user = os.getenv('LDAP_USER1', 'devUserA')
    search_user_name = os.getenv('LDAP_USER_NAME', 'Dev A. User')
    user = admin_client.list_identity(name=search_user_name)[0]
    assert user.name == search_user_name
    assert user.login == search_user
    user_copy = admin_client.by_id('identity', user.id)
    assert user.name == user_copy.name
    assert user.id == user_copy.id
    assert user.login == user_copy.login
    assert user.profilePicture == user_copy.profilePicture
    assert user.profileUrl == user_copy.profileUrl


@if_ldap
def test_ldap_search_get_group(admin_client, ldap_config):
    search_group = os.getenv('LDAP_GROUP', 'qualityAssurance')
    group = admin_client.list_identity(name=search_group)[0]
    group_copy = admin_client.by_id('identity', group.id)
    assert group.name == group_copy.name
    assert group.id == group_copy.id
    assert group.login == group_copy.login
    assert group.profilePicture == group_copy.profilePicture
    assert group.profileUrl == group_copy.profileUrl


@if_ldap
def test_ldap_login(admin_client, cattle_url, ldap_config):
    create_ldap_client()


@if_ldap
def test_ldap_incorrect_login(ldap_config):
    username = os.getenv('LDAP_USER1', 'devUserA')
    token = requests.post(base_url() + 'token',
                          {
                              'code': username + ':' + random_str(),
                              'authProvider': 'ldapconfig'
    })
    assert token.status_code == 401
    token = token.json()
    assert token['type'] == 'error'
    assert token['status'] == 401
    token = requests.post(base_url() + 'token',
                          {
                              'code': username + ':' + "",
                              'authProvider': 'ldapconfig'
    })
    assert token.status_code == 401
    token = token.json()
    assert token['type'] == 'error'
    assert token['status'] == 401
    token = requests.post(base_url() + 'token',
                          {
                              'code': username + ':' + " ",
                              'authProvider': 'ldapconfig'
    })
    assert token.status_code == 401
    token = token.json()
    assert token['type'] == 'error'
    assert token['status'] == 401


@if_ldap
def test_ldap_unauthorized_login(ldap_config):
    username = os.environ.get('API_AUTH_OPEN_LDAP_'
                              'SERVICE_ACCOUNT_PASSWORD',
                              'Password1')
    password = os.environ.get('API_AUTH_OPEN_LDAP_'
                              'SERVICE_ACCOUNT_USERNAME',
                              'cattle')
    token = requests.post(base_url() + 'token',
                          {
                              'code': username + ':' + password,
                              'authProvider': 'ldapconfig'
    })
    assert token.status_code == 401
    token = token.json()
    assert token['type'] == 'error'
    assert token['status'] == 401


@if_ldap
def test_ldap_project_members(ldap_config):
    user1_client = create_ldap_client()
    user1_identity = get_authed_token()['userIdentity']
    username = os.getenv('LDAP_USER2', 'devUserB')
    password = os.getenv('LDAP_USER2_PASSWORD', 'Password1')
    user2_client = create_ldap_client(username=username, password=password)
    user2_identity = get_authed_token(username=username,
                                      password=password)['userIdentity']
    group = os.getenv('LDAP_GROUP', 'qualityAssurance')
    group = user1_client.list_identity(name=group)[0]
    project = user1_client.create_project(members=[
        idToMember(user1_identity, 'owner'),
        idToMember(user2_identity, 'member')
    ])
    project = user1_client.wait_success(project)
    user2_client.by_id('project', project.id)
    project.setmembers(members=[
        idToMember(group, 'owner')
    ])
    project = user2_client.by_id('project', project.id)
    user2_client.delete(project)


def idToMember(identity, role):
    return {
        'externalId': identity['externalId'],
        'externalIdType': identity['externalIdType'],
        'role': role
    }


@if_ldap
def test_ldap_project_create(ldap_config):
    user1_client = create_ldap_client()
    identity = get_authed_token()['userIdentity']
    members = [idToMember(identity, 'owner')]
    project = user1_client.create_project(members=members)
    project = user1_client.wait_success(project)
    assert project is not None
    user1_client.delete(project)
