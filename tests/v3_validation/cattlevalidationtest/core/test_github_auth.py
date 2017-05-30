from common_fixtures import *  # NOQA
from selenium import webdriver
from requests.auth import AuthBase
from github import GitHub
import requests
import json

if_test_github = pytest.mark.skipif(
    not os.environ.get('GITHUB_MAIN_USER') or
    not os.environ.get('GITHUB_MAIN_PASS') or
    not os.environ.get('GITHUB_USER_1') or
    not os.environ.get('GITHUB_USER_2') or
    not os.environ.get('GITHUB_PASS_1') or
    not os.environ.get('GITHUB_PASS_2') or
    not os.environ.get('GITHUB_ORG'),
    reason="None")

if_do_key = pytest.mark.skipif(
    not os.environ.get('DIGITALOCEAN_KEY'),
    reason="Digital Ocean key is not set")

GITHUB_CLIENT = None
GITHUB_ADMIN_TOKEN = None
GITHUB_USER1_TOKEN = None
GITHUB_USER2_TOKEN = None
CLIENT_ID = None
CLIENT_SECRET = None


class GithubAuth(AuthBase):
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


def github_client(admin_client):
    key = admin_client.create_apiKey()
    admin_client.wait_success(key)
    gh_client = from_env(url=cattle_url(),
                         access_key=key.publicValue,
                         secret_key=key.secretValue)
    global GITHUB_CLIENT
    GITHUB_CLIENT = gh_client


def idToMember(identity, role):
    return {
        'externalId': identity.externalId,
        'externalIdType': identity.externalIdType,
        'role': role
    }


def get_users_tokens():
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')
    user2 = os.getenv('GITHUB_USER_2')
    pass2 = os.getenv('GITHUB_PASS_2')
    admin_name = os.getenv('GITHUB_MAIN_USER', None)
    admin_pass = os.getenv('GITHUB_MAIN_PASS', None)
    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret
                                  )
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    r = requests.post(auth_url, data=json.dumps(data))
    assert r.ok

    # Get tokens
    user1_token = get_authed_token(username=user1,
                                   password=pass1)
    user2_token = get_authed_token(username=user2,
                                   password=pass2)
    admin_token = get_authed_token(username=admin_name,
                                   password=admin_pass)

    assert admin_token is not None
    assert user1_token is not None
    assert user2_token is not None

    global GITHUB_ADMIN_TOKEN
    GITHUB_ADMIN_TOKEN = admin_token
    global GITHUB_USER1_TOKEN
    GITHUB_USER1_TOKEN = user1_token
    global GITHUB_USER2_TOKEN
    GITHUB_USER2_TOKEN = user2_token


def get_authed_token(username=None,
                     password=None):
    port = int(os.getenv('PHANTOMJS_WEBDRIVER_PORT', 4444))
    phantom_bin = os.getenv('PHANTOMJS_BIN', '/usr/local/bin/phantomjs')
    driver = webdriver.PhantomJS(
        phantom_bin, port=port, service_args=['--load-images=yes'])
    driver.delete_all_cookies()
    max_wait = 60
    driver.set_page_load_timeout(max_wait)
    driver.set_script_timeout(max_wait)
    driver.implicitly_wait(10)
    driver.set_window_size(1120, 550)

    # driver.get('{}logout'.format(cattle_url()[:-7]))
    time.sleep(10)
    try:
        driver.get('https://github.com/logout')
        driver.find_element_by_class_name('btn').click()
    except:
        pass
    rancher_url = cattle_url()[:-7]
    driver.get('https://github.com/login')
    driver.find_element_by_id('login_field').send_keys(username)
    driver.find_element_by_id('password').send_keys(password)
    driver.find_element_by_name('commit').click()
    driver.get(rancher_url)
    time.sleep(10)
    try:
        driver.find_element_by_class_name('btn-primary').click()
        time.sleep(10)
        driver.find_element_by_class_name('btn-primary').click()
        time.sleep(10)
    except:
        pass
    driver.get(cattle_url())
    time.sleep(10)
    all_cookies = driver.get_cookies()
    token = all_cookies[1]['value']
    return token


def create_github_client(username=None,
                         password=None,
                         project_id=None,
                         token=None):
    client = from_env(url=cattle_url(project_id=project_id),
                      access_key=GITHUB_CLIENT._access_key,
                      secret_key=GITHUB_CLIENT._secret_key)
    client.delete_by_id = delete_by_id
    assert client.valid()
    jwt = token
    client._access_key = None
    client._secret_key = None
    client._auth = GithubAuth(jwt, prj_id=project_id)
    client.reload_schema()
    assert client.valid()
    return client


def get_github_config_data(username=None,
                           client_id=None,
                           secret_key=None,
                           allowed_identities=[],
                           enabled=True,
                           access_mode="unrestricted"):
    data = {
        "accessMode": access_mode,
        "allowedIdentities": allowed_identities,
        "enabled": enabled,
        "githubConfig": {
            "clientId": client_id,
            "clientSecret": secret_key,
            "hostname": None,
            "links": None,
            "scheme": "https://",
            "type": "githubconfig",
            "actionLinks": None},
        "provider": "githubconfig",
        "shibbolethConfig": {},
        "type": "config"
    }
    return data


def get_github_identites(ids):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    identities = []
    gh = GitHub(username=main_user, password=main_pass)
    for id in ids:
        id_info = gh.users(id['name']).get()
        identity = {
            "role": None,
            "projectId": None,
            "profileUrl": id_info["html_url"],
            "profilePicture": id_info["avatar_url"],
            "name": id_info["name"],
            "login": id_info["name"],
            "id": "github_user:" + str(id_info["id"]),
            "type": "identity",
            "links": None,
            "baseType": "identity",
            "actionLinks": {},
            "all": None,
            "externalId": str(id_info["id"]),
            "externalIdType": "github_user"
        }
        if id['type'] == 'org':
            identity["id"] = "github_org:" + str(id_info["id"])
            identity["externalIdType"] = "github_org"
        identities.append(identity)
    return identities


def create_oauth_app(github_oauth):
    username = os.getenv('GITHUB_MAIN_USER', None)
    password = os.getenv('GITHUB_MAIN_PASS', None)
    port = int(os.getenv('PHANTOMJS_WEBDRIVER_PORT', 4445))
    phantom_bin = os.getenv('PHANTOMJS_BIN', '/usr/local/bin/phantomjs')
    driver = webdriver.PhantomJS(phantom_bin, port=port)
    driver.delete_all_cookies()
    max_wait = 60
    driver.set_page_load_timeout(max_wait)
    driver.set_script_timeout(max_wait)
    driver.implicitly_wait(10)
    driver.set_window_size(1120, 550)
    driver.get('https://github.com/logout')
    try:
        driver.find_element_by_class_name('btn').click()
    except:
        pass
    driver.get('https://github.com/login')
    try:
        driver.find_element_by_id('login_field').send_keys(username)
        driver.find_element_by_id('password').send_keys(password)
        driver.find_element_by_name('commit').click()
    except:
        pass
    driver.get('https://github.com/settings/applications/new')
    time.sleep(10)
    inputs = driver.find_elements_by_class_name('form-control')
    inputs[2].send_keys(github_oauth)
    inputs[3].send_keys(cattle_url()[:-7])
    inputs[5].send_keys(cattle_url()[:-7])
    driver.find_elements_by_class_name('btn-primary')[0].click()
    time.sleep(10)
    try:
        client_id = driver.find_elements_by_xpath("//dd")[0].text
        client_secret = driver.find_elements_by_xpath("//dd")[1].text
        global CLIENT_ID
        CLIENT_ID = client_id
        global CLIENT_SECRET
        CLIENT_SECRET = client_secret
    except:
        pass


@pytest.fixture(scope='session', autouse=True)
def turn_on_off_github(admin_client,
                       request):
    admin_name = os.getenv('GITHUB_MAIN_USER', None)
    github_oauth = 'rancher-' + random_str()
    create_oauth_app(github_oauth)
    github_client(admin_client)
    get_users_tokens()
    main_account = GITHUB_CLIENT.list_account(name=admin_name)[0]
    account = GITHUB_CLIENT.by_id("account", main_account.id)
    GITHUB_CLIENT.wait_success(account)
    GITHUB_CLIENT.update_by_id_account(account.id, kind='admin')

    def fin2():
        auth_url = cattle_url()[:-7] + 'v1-auth/config'
        data = get_github_config_data(enabled=False)
        access_key = GITHUB_CLIENT._access_key
        secret_key = GITHUB_CLIENT._secret_key
        r = requests.post(auth_url,
                          data=json.dumps(data),
                          auth=(access_key, secret_key))
        assert r.ok

    request.addfinalizer(fin2)


# 1
@if_test_github
def test_allow_any_github_user(admin_client):
    # Set option to allow any valid user
    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    token = GITHUB_ADMIN_TOKEN
    cookies = dict(token=token)
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret
                                  )
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok
    # Authenticate with any user
    user1_token = GITHUB_USER1_TOKEN
    cookies = dict(token=user1_token)
    schemas = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert schemas.status_code == 200


# 2
@if_test_github
def test_restricted_github_user(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    user1 = os.getenv('GITHUB_USER_1')
    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=token)

    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    # Test with valid user
    user1_token = GITHUB_USER1_TOKEN

    cookies = dict(token=user1_token)
    schemas = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert schemas.status_code == 200

    # Test with invalid user
    user2_token = GITHUB_USER2_TOKEN
    cookies = dict(token=user2_token)
    bad_auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert bad_auth.status_code == 401


# 3
@if_test_github
def test_restricted_github_org(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    org = os.getenv('GITHUB_ORG')
    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    token = GITHUB_ADMIN_TOKEN
    cookies = dict(token=token)

    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': org,
            'type': 'org'
        }
    ]
    identities = get_github_identites(ids)

    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    # Test with valid user
    user1_token = GITHUB_USER1_TOKEN
    cookies = dict(token=user1_token)
    schemas = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert schemas.status_code == 200

    # Test with invalid user
    user2_token = GITHUB_USER2_TOKEN
    cookies = dict(token=user2_token)
    bad_auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert bad_auth.status_code == 401


# 4
@if_test_github
def test_restricted_github_user_with_new_env(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    user1 = os.getenv('GITHUB_USER_2')
    pass1 = os.getenv('GITHUB_PASS_2')
    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    # test creation of new env with new valid user
    user1_token = GITHUB_USER2_TOKEN

    cookies = dict(token=user1_token)
    schemas = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert schemas.status_code == 200
    time.sleep(5)
    gh_client = create_github_client(username=user1,
                                     password=pass1,
                                     token=user1_token)
    projects = gh_client.list_project()
    found = False
    for project in projects:
        if project['name'] == user1 + "-Default":
            found = True
            break
    assert found


# 5,6
@if_test_github
def test_github_create_new_env_with_member(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    user1_token = GITHUB_USER1_TOKEN

    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)
    user1_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'github_user':
            user1_identity = obj
            break

    # test creation of new env
    project = main_client.create_project(members=[
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'member')
    ])
    GITHUB_CLIENT.wait_success(project)
    assert main_client.by_id('project', project.id) is not None
    assert user1_client.by_id('project', project.id) is not None


# 7
@if_test_github
def test_github_create_new_env_with_owner(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')
    user2 = os.getenv('GITHUB_USER_2')
    pass2 = os.getenv('GITHUB_PASS_2')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        },
        {
            'name': user2,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    user1_token = GITHUB_USER1_TOKEN
    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)
    user1_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'github_user':
            user1_identity = obj
            break

    user2_token = GITHUB_USER2_TOKEN
    user2_client = create_github_client(username=user2,
                                        password=pass2,
                                        token=user2_token)
    user2_identity = None
    for obj in user2_client.list_identity():
        if obj.externalIdType == 'github_user':
            user2_identity = obj
            break

    members = [
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'owner')
    ]
    # Test creation of new new env
    project = main_client.create_project(members=members)
    GITHUB_CLIENT.wait_success(project)
    assert main_client.by_id('project', project.id) is not None
    assert user1_client.by_id('project', project.id) is not None

    # Test adding new member using the new owner
    new_members = [
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'owner'),
        idToMember(user2_identity, 'owner')
    ]
    same_project = user1_client.by_id('project', project.id)
    same_project.setmembers(members=new_members)
    assert main_client.by_id('project', project.id) is not None
    assert user1_client.by_id('project', project.id) is not None
    assert user2_client.by_id('project', project.id) is not None


# 8
@if_test_github
def test_github_create_new_env_with_org_member(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    org = os.getenv('GITHUB_ORG')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': org,
            'type': 'org'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    members = [
        idToMember(main_identity, 'owner'),
        {
            'externalId': identities[1]['externalId'],
            'externalIdType': identities[1]['externalIdType'],
            'role': 'member'
        }
    ]
    # Test creation of new new env
    project = main_client.create_project(members=members)
    GITHUB_CLIENT.wait_success(project)
    assert main_client.by_id('project', project.id) is not None

    user1_token = GITHUB_USER1_TOKEN
    cookies = dict(token=user1_token)
    auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert auth.status_code == 200


# 9
@if_test_github
def test_github_create_new_env_with_org_owner(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')
    user2 = os.getenv('GITHUB_USER_2')
    pass2 = os.getenv('GITHUB_PASS_2')
    org = os.getenv('GITHUB_ORG')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user2,
            'type': 'user'
        },
        {
            'name': org,
            'type': 'org'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    user1_token = GITHUB_USER1_TOKEN
    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)

    user2_token = GITHUB_USER2_TOKEN
    user2_client = create_github_client(username=user2,
                                        password=pass2,
                                        token=user2_token)
    user2_identity = None
    for obj in user2_client.list_identity():
        if obj.externalIdType == 'github_user':
            user2_identity = obj
            break

    members = [
        idToMember(main_identity, 'owner'),
        {
            'externalId': identities[2]['externalId'],
            'externalIdType': identities[2]['externalIdType'],
            'role': 'owner'
        }
    ]
    # Test creation of new new env
    project = main_client.create_project(members=members)
    GITHUB_CLIENT.wait_success(project)
    assert main_client.by_id('project', project.id) is not None

    cookies = dict(token=user2_token)
    auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert auth.status_code == 200

    # Test adding new member using the new owner
    # user1 now can add users
    members.append(idToMember(user2_identity, 'owner'))
    same_project = user1_client.by_id('project', project.id)
    same_project.setmembers(members=members)
    assert main_client.by_id('project', project.id) is not None
    assert user2_client.by_id('project', project.id) is not None


# 10
@if_test_github
def test_github_change_member_to_owner(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    user1_token = GITHUB_USER1_TOKEN
    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)
    user1_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'github_user':
            user1_identity = obj
            break

    # test creation of new env
    project = main_client.create_project(members=[
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'member')
    ])
    GITHUB_CLIENT.wait_success(project)
    assert main_client.by_id('project', project.id) is not None
    assert user1_client.by_id('project', project.id) is not None

    # change user2 from member to owner
    new_members = [
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'owner')
    ]
    same_project = main_client.by_id('project', project.id)
    same_project.setmembers(members=new_members)

    # user2 has ability to manipulate the env
    new_members = [
        idToMember(main_identity, 'member'),
        idToMember(user1_identity, 'owner')
    ]
    owner_project = user1_client.by_id('project', project.id)
    owner_project.setmembers(members=new_members)


# 11
@if_test_github
def test_github_change_owner_to_member(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    user1_token = GITHUB_USER1_TOKEN
    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)
    user1_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'github_user':
            user1_identity = obj
            break

    # Test creation of new env
    project = main_client.create_project(members=[
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'owner')
    ])
    GITHUB_CLIENT.wait_success(project)
    assert main_client.by_id('project', project.id) is not None
    assert user1_client.by_id('project', project.id) is not None

    # Change user1 from member to owner
    new_members = [
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'member')
    ]
    same_project = main_client.by_id('project', project.id)
    same_project.setmembers(members=new_members)

    # user1 can not manipulate the env
    new_members = [
        idToMember(main_identity, 'member'),
        idToMember(user1_identity, 'owner')
    ]
    member_project = user1_client.by_id('project', project.id)
    try:
        member_project.setmembers(members=new_members)
        assert False
    except:
        assert True


# 12
@if_test_github
def test_github_remove_owner_from_env(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    user1_token = GITHUB_USER1_TOKEN
    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)
    user1_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'github_user':
            user1_identity = obj
            break

    # Test creation of new env
    project = main_client.create_project(members=[
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'owner')
    ])
    GITHUB_CLIENT.wait_success(project)
    assert main_client.by_id('project', project.id) is not None
    assert user1_client.by_id('project', project.id) is not None

    # Remove user2 from env
    new_members = [
        idToMember(main_identity, 'owner')
    ]
    same_project = main_client.by_id('project', project.id)
    same_project.setmembers(members=new_members)

    # user1 can not access the env
    new_members = [
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'owner')
    ]
    try:
        same_project = user1_client.by_id('project', project.id)
        same_project.setmembers(members=new_members)
        assert False
    except:
        assert True


# 13
@if_test_github
def test_github_remove_member_from_env(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    user1_token = GITHUB_USER1_TOKEN
    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)
    user1_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'github_user':
            user1_identity = obj
            break

    # test creation of new env
    project = main_client.create_project(members=[
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'member')
    ])
    GITHUB_CLIENT.wait_success(project)
    assert main_client.by_id('project', project.id) is not None
    assert user1_client.by_id('project', project.id) is not None

    # remove user1 from env
    new_members = [
        idToMember(main_identity, 'owner')
    ]
    same_project = main_client.by_id('project', project.id)
    same_project.setmembers(members=new_members)

    # user1 can not access the env
    new_members = [
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'owner')
    ]
    try:
        same_project = user1_client.by_id('project', project.id)
        same_project.setmembers(members=new_members)
        assert False
    except:
        assert True


# 14,15
@if_test_github
def test_github_activate_deactivate_env(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [{'name': main_user, 'type': 'user'}]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    # Test creation of new env
    project = main_client.create_project(members=[
        idToMember(main_identity, 'owner')
    ])
    GITHUB_CLIENT.wait_success(project)
    assert main_client.by_id('project', project.id) is not None

    # Deactivate environment
    dec_project = main_client.by_id('project', project.id)
    dec_project.deactivate()
    dec_project = main_client.by_id('project', project.id)
    assert dec_project['state'] == 'inactive'

    # Activate environment back
    dec_project.activate()
    act_project = main_client.by_id('project', project.id)
    assert act_project['state'] == 'active'


# 16
@if_test_github
def test_github_remove_deactivated_env(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [{'name': main_user, 'type': 'user'}]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    # Test creation of new env
    project = main_client.create_project(members=[
        idToMember(main_identity, 'owner')
    ])
    GITHUB_CLIENT.wait_success(project)
    assert main_client.by_id('project', project.id) is not None

    # Deactivate environment
    dec_project = main_client.by_id('project', project.id)
    dec_project.deactivate()
    dec_project = main_client.by_id('project', project.id)
    assert dec_project['state'] == 'inactive'

    # Remove environment
    main_client.delete(dec_project)
    time.sleep(5)
    project = main_client.by_id('project', project.id)
    assert project.state == 'purged' or project.state == 'removed'


# 17,18
@if_test_github
def test_github_activate_deactivate_account(admin_client):
    # turn_on_github_auth()
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)

    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    # Test with valid user
    user1_token = GITHUB_USER1_TOKEN

    cookies = dict(token=user1_token)
    schemas = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert schemas.status_code == 200

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)

    # Deactivate the user1 account
    user1_account = main_client.list_account(name=user1)[0]
    account = main_client.by_id("account", user1_account.id)
    account.deactivate()
    main_client.wait_success(account)

    cookies = dict(token=user1_token)
    bad_auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert bad_auth.status_code == 401

    # Active the user1 account
    account = main_client.by_id("account", user1_account.id)
    account.activate()
    main_client.wait_success(account)

    cookies = dict(token=user1_token)
    good_auth = requests.get(cattle_url() + "schemas", cookies=cookies)
    assert good_auth.status_code == 200


# 19
@if_test_github
def test_github_purge_account(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user2 = os.getenv('GITHUB_USER_2')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)

    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user2,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)

    # Purge user2 account
    user2_account = main_client.list_account(name=user2)[0]
    account = main_client.by_id("account", user2_account.id)
    account.deactivate()
    main_client.wait_success(account)
    main_client.delete(account)

    account = main_client.wait_success(account)
    account.purge()
    main_client.wait_success(account)
    assert account.removed is not None


# 23,24,25,26,27
@if_test_github
def test_github_member_permissions(admin_client):
    # turn_on_github_auth()
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)

    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    user1_token = GITHUB_USER1_TOKEN
    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)
    user1_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'github_user':
            user1_identity = obj
            break

    # test creation of new env
    project = main_client.create_project(members=[
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'member')
    ])
    GITHUB_CLIENT.wait_success(project)
    assert main_client.by_id('project', project.id) is not None
    assert user1_client.by_id('project', project.id) is not None

    # user1 can not change, remove, or add users
    new_members = [
        idToMember(main_identity, 'member'),
        idToMember(user1_identity, 'owner')
    ]
    member_project = user1_client.by_id('project', project.id)
    try:
        member_project.setmembers(members=new_members)
        assert False
    except:
        assert True

    # user1 can't deactivate or remove environment
    try:
        dec_project = user1_client.by_id('project', project.id)
        dec_project.deactivate()
        dec_project = user1_client.by_id('project', project.id)
        assert dec_project['state'] == 'inactive'
        user1_client.delete(dec_project)
        time.sleep(5)
        project = user1_client.by_id('project', project.id)
        assert project.state == 'purged' or project.state == 'removed'
        assert False
    except:
        assert True


# 28
@if_test_github
def test_github_change_user_to_admin(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)

    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")

    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    # Test with valid user
    user1_token = GITHUB_USER1_TOKEN

    cookies = dict(token=user1_token)
    no_admin = requests.get(cattle_url()[:-7] + '/admin/processes',
                            cookies=cookies)
    assert no_admin.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    # change account from user to admin
    user1_account = main_client.list_account(name=user1)[0]
    account = main_client.by_id("account", user1_account.id)
    main_client.wait_success(account)
    main_client.update_by_id_account(account.id, kind='admin')

    cookies = dict(token=user1_token)
    admin = requests.get(cattle_url()[:-7] + '/admin/processes',
                         cookies=cookies)
    assert admin.ok


# 29
@if_test_github
def test_github_admin_list_all_env(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)

    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")

    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    # Test with valid user
    user1_token = GITHUB_USER1_TOKEN

    cookies = dict(token=user1_token)
    no_admin = requests.get(cattle_url()[:-7] + '/admin/processes',
                            cookies=cookies)
    assert no_admin.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)

    # List all projects
    projects = main_client.list_project()

    # Create new project
    project = main_client.create_project()

    # change account from user to admin
    user1_account = main_client.list_account(name=user1)[0]
    account = main_client.by_id("account", user1_account.id)
    main_client.wait_success(account)
    main_client.update_by_id_account(account.id, kind='admin')

    cookies = dict(token=user1_token)
    admin = requests.get(cattle_url()[:-7] + '/admin/processes',
                         cookies=cookies)
    assert admin.ok

    for project in projects:
        project_url = cattle_url() \
                      + "/projects/" + project.id + "/projectmembers"
        cookies = dict(token=user1_token)
        access = requests.get(project_url, cookies=cookies)
        assert access.ok

    # change account from admin to user
    user1_account = main_client.list_account(name=user1)[0]
    account = main_client.by_id("account", user1_account.id)
    main_client.wait_success(account)
    main_client.update_by_id_account(account.id, kind='user')


# 30
@if_test_github
@if_do_key
def test_github_member_add_host(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)

    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    user1_token = GITHUB_USER1_TOKEN
    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)
    user1_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'github_user':
            user1_identity = obj
            break

    # test creation of new env
    project = main_client.create_project(members=[
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'member')
    ])
    GITHUB_CLIENT.wait_success(project)
    assert main_client.by_id('project', project.id) is not None
    assert user1_client.by_id('project', project.id) is not None

    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token,
                                        project_id=project.id)
    # Add new host
    host_list = \
        add_digital_ocean_hosts(
            user1_client, 1)
    assert len(host_list) == 1

    # Remove host
    host = host_list[0]
    deactivated_host = host.deactivate()
    user1_client.wait_success(deactivated_host)

    deactivated_host.remove()

    all_hosts = user1_client.list_host()
    for h in all_hosts:
        if h.hostname == host.hostname:
            assert False


# 31
@if_test_github
def test_github_create_new_env_with_restricted_member(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    user1_token = GITHUB_USER1_TOKEN

    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)
    user1_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'github_user':
            user1_identity = obj
            break

    # test creation of new env
    default_prj_id = main_client.list_project(name=main_user+'-Default')[0].id
    default_project = main_client.by_id('project', default_prj_id)
    default_project.setmembers(members=[
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'restricted')
    ])

    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token,
                                        project_id=default_prj_id)
    # Add new host
    with pytest.raises(AttributeError) as excinfo:
        host_list = \
            add_digital_ocean_hosts(
                user1_client, 1)
        assert len(host_list) == 1

    assert "object has no attribute" in str(excinfo.value)


# 32
@if_test_github
def test_github_create_service_with_restricted_member(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    user1_token = GITHUB_USER1_TOKEN

    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)
    user1_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'github_user':
            user1_identity = obj
            break

    # test creation of new env
    default_prj_id = main_client.list_project(name=main_user+'-Default')[0].id
    default_project = main_client.by_id('project', default_prj_id)
    default_project.setmembers(members=[
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'restricted')
    ])

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token,
                                       project_id=default_prj_id)

    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token,
                                        project_id=default_prj_id)
    # Add new host
    hosts = user1_client.list_host(
                kind='docker', removed_null=True, state="active")
    if len(hosts) == 0:
        host_list = \
            add_digital_ocean_hosts(
                main_client, 1)
        assert len(host_list) == 1

    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    scale = 1
    create_env_and_svc(user1_client, launch_config, scale)


# 33,34
@if_test_github
def test_github_create_new_env_with_readonly_member(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        },
        {
            'name': user1,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="required")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    user1_token = GITHUB_USER1_TOKEN

    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)
    user1_identity = None
    for obj in user1_client.list_identity():
        if obj.externalIdType == 'github_user':
            user1_identity = obj
            break

    # test creation of new env
    default_prj_id = main_client.list_project(name=main_user+'-Default')[0].id
    default_project = main_client.by_id('project', default_prj_id)
    default_project.setmembers(members=[
        idToMember(main_identity, 'owner'),
        idToMember(user1_identity, 'readonly')
    ])

    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token,
                                        project_id=default_prj_id)

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token,
                                       project_id=default_prj_id)
    # Add new host
    with pytest.raises(AttributeError) as excinfo:
        host_list = \
            add_digital_ocean_hosts(
                user1_client, 1)
        assert len(host_list) == 1

    assert "object has no attribute" in str(excinfo.value)

    with pytest.raises(AttributeError) as excinfo:
        launch_config = {"imageUuid": TEST_IMAGE_UUID}
        scale = 1
        create_env_and_svc(user1_client, launch_config, scale)

    assert "object has no attribute" in str(excinfo.value)

    # Create service using main client
    launch_config = {"imageUuid": TEST_IMAGE_UUID}
    scale = 1
    service, env = create_env_and_svc(main_client, launch_config, scale)

    # List service using user1 client
    service = user1_client.list_service(name=service.name,
                                        stackId=env.id,
                                        removed_null=True)
    assert len(service) == 1


# 35
@if_test_github
def test_github_add_user_to_env_with_restricted_access(admin_client):
    main_user = os.getenv('GITHUB_MAIN_USER')
    main_pass = os.getenv('GITHUB_MAIN_PASS')
    user1 = os.getenv('GITHUB_USER_1')
    pass1 = os.getenv('GITHUB_PASS_1')

    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET

    main_token = GITHUB_ADMIN_TOKEN

    cookies = dict(token=main_token)
    ids = [
        {
            'name': main_user,
            'type': 'user'
        }
    ]
    identities = get_github_identites(ids)
    auth_url = cattle_url()[:-7] + 'v1-auth/config'
    data = get_github_config_data(username=None,
                                  client_id=client_id,
                                  secret_key=client_secret,
                                  allowed_identities=identities,
                                  enabled=True,
                                  access_mode="restricted")
    r = requests.post(auth_url, data=json.dumps(data), cookies=cookies)
    assert r.ok

    main_client = create_github_client(username=main_user,
                                       password=main_pass,
                                       token=main_token)
    main_identity = None
    for obj in main_client.list_identity():
        if obj.externalIdType == 'github_user':
            main_identity = obj
            break

    # Remove user from all other environments
    for project in main_client.list_project(all=True):
        project = main_client.by_id('project', project.id)
        project.setmembers(members=[
            idToMember(main_identity, 'owner')
        ])

    user1_token = GITHUB_USER1_TOKEN

    ids = [
        {
            'name': user1,
            'type': 'user'
        }
    ]

    user1_identity = get_github_identites(ids)[0]
    members = [
        idToMember(main_identity, 'owner'),
        {
            'externalId': user1_identity["externalId"],
            'externalIdType': user1_identity["externalIdType"],
            'role': "member"
        }
    ]

    project = main_client.create_project(members=members)
    GITHUB_CLIENT.wait_success(project)
    user1_client = create_github_client(username=user1,
                                        password=pass1,
                                        token=user1_token)
    assert user1_client.by_id('project', project.id) is not None

    for p in main_client.list_project(all=True):
        project_url = cattle_url(project_id=p.id)
        cookies = dict(token=user1_token)
        access = requests.get(project_url, cookies=cookies)
        if p.id != project.id:
            assert not access.ok
        else:
            assert access.ok
