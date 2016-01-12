from common_fixtures import *  # NOQA
from selenium import webdriver
from test_github import URL


def test_turn_on_local_auth_ui(admin_client):
    config = {
        'enabled': None,
        'password': '',
        'username': ''
    }
    admin_client.create_local_auth_config(config)

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
    url = '{}admin/access/local'.format(base_url()[:-3])
    driver.get(url)
    inputs = driver.find_elements_by_class_name('ember-text-field')
    password = random_str()
    config = [
        random_str(),
        random_str(),
        password,
        password
    ]

    for i in range(0, len(inputs)):
        inputs[i].clear()
        inputs[i].send_keys(config[i])

    driver.find_element_by_class_name('btn-primary').click()
    time.sleep(2)
    no_auth = requests.get(URL)
    assert no_auth.status_code == 401
