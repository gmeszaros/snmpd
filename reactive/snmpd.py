import subprocess
import yaml
from charmhelpers import fetch
from charmhelpers.core import host, hookenv, unitdata
from charmhelpers.core.templating import render
from charms.reactive import (
    when, when_not, when_any, when_file_changed,
    set_state, hook)

SNMPD_CONF = '/etc/snmp/snmpd.conf'


def get_auth_pass_phrase():
    db = unitdata.kv()
    return db.get("priv_protocol")

@when_not('snmpd.installed',
          'snmpd.stopped')
def install_snmpd():
    install_apt_packages()
    start_snmpd()
    set_state('snmpd.installed')


@when('config.changed')
def start_snmpd():
    update_snmpd_conf()
    disable_snmp_v1_v2()
    if not host.service_running('snmpd'):
        hookenv.log('Starting snmpd...')
        host.service_start('snmpd')
    else:
        hookenv.log('Reloading snmpd config...')
        host.service_reload('snmpd')
    hookenv.status_set('active', 'Ready')


@when_any('config.changed.snmpv3_pass_phrase',
      'config.changed.auth_protocol',
      'config.changed.priv_protocol',
      'config.changed.security_name')
def create_user():
    config = hookenv.config()
    yaml_data = yaml.safe_load(config["snmpv3_pass_phrase"])
    auth_protocol = config['auth_protocol']
    priv_protocol = config['priv_protocol']
    security_name = config['security_name']
    auth_pass_phrase = yaml_data.get('auth_pass_phrase')
    priv_pass_phrase = yaml_data.get('priv_pass_phrase')

    host.service_stop('snmpd')
    if not host.service_running('snmpd'):
        try:
            cmd = f"net-snmp-create-v3-user -ro " \
                  f"-A {auth_pass_phrase} " \
                  f"-a {auth_protocol} " \
                  f"-X {priv_pass_phrase} " \
                  f"-x {priv_protocol} " \
                  f"{security_name}"

            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            hookenv.log(f'Failed to create user {security_name}')
            hookenv.log('Error {}'.format(e), hookenv.ERROR)

    host.service_start('snmpd')

@when('config.changed.extra_packages')
def install_apt_packages():
    config = hookenv.config()
    packages = ['snmpd', 'libsnmp-dev']
    if config['extra_packages']:
        packages += [p.strip() for p in config['extra_packages'].split(',')]
    hookenv.status_set('maintenance', 'Installing packages')
    hookenv.log("Installing apt packages " + str([pkg for pkg in packages]), hookenv.INFO)
    fetch.configure_sources()
    fetch.apt_update()
    fetch.apt_install(packages)
    hookenv.status_set('active', 'Ready')


@when_file_changed(SNMPD_CONF, hash_type='sha256')
def update_snmpd_conf():
    config = hookenv.config()
    hookenv.status_set('maintenance', 'Updating snmpd configuration.')

    options = {
        'sysLocation': config['sysLocation'],
        'sysContact': config['sysContact'],
        'acl_config': [acl.strip() for acl in config['acl_config'].splitlines()],
        'other_config': [other.strip() for other in config['other_config'].splitlines()]
    }

    render(
        'snmpd.conf',
        SNMPD_CONF,
        options,
        owner='root',
        group='root'
    )
    hookenv.status_set('active', 'Ready')


@when_any('host.available', 'host.connected')
def host_available():
    pass


@hook('stop')
def remove_snmpd():
    """
    Remove installed packages when the principal charm relation revoked
    """
    if host.service_running('snmpd'):
        hookenv.log('Stopping snmpd...')
        set_state('snmpd.stopped')
    if not host.service_running('snmpd'):
        set_state('snmpd.stopped')
    uninstall_packages()


def uninstall_packages():
    kv = unitdata.kv()
    packages = ['snmpd', 'libsnmp-dev']
    # if kv.get('extra_packages'):
    #     packages += [p.strip() for p in kv.get('extra_packages').split(',')]
    hookenv.log("Uninstalling.. " + str([pkg for pkg in packages]), hookenv.INFO)
    fetch.apt_purge(packages)

def disable_snmp_v1_v2():
    """Disable SNMP v1 and v2 in the snmpd configuration."""
    run_cmd(f"sed -i '/^rocommunity/d' {SNMPD_CONF}", b_shell=True)
    run_cmd(f"sed -i '/^rwcommunity/d' {SNMPD_CONF}", b_shell=True)
    hookenv.log('Disabled SNMP v1 and v2 in snmpd configuration')


@hook('update_status')
def check_snmpd_service():
    if not host.service_running(SNMPD_SERVICE):
        hookenv.status_set('blocked', 'snmpd service is not running')
        hookenv.log("snmpd service not in running state.Blocking the unit on juju")
