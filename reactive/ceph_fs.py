from charms.reactive import (
    when,
    set_state
)
from charmhelpers.core.hookenv import (
    log,
    config,
    status_set,
)
from rados import Error as RadosError
from ceph_api import ceph_command

CRITICAL = "CRITICAL"
ERROR = "ERROR"
WARNING = "WARNING"
INFO = "INFO"
DEBUG = "DEBUG"


set_state('ceph_fs.installed')

"""
Steps:
    1. Create CephFS pools if version > 0.84  # Use ceph_api
        ceph osd pool create cephfs_data <pg_num>
        ceph osd pool create cephfs_metadata <pg_num>
    2. Enable CephFS
        ceph fs new <fs_name> <metadata> <data>
    3. Start the mds services if needed
    4. Export the url to the client allowing them to mount the FS:

        Client needs to specify either nothing or a deep mount if they want to
        without cephx:
        sudo mount -t ceph 192.168.0.1:6789:/ /mnt/mycephfs
        with cephx:
        sudo mount -t ceph 192.168.0.1:6789:/ /mnt/mycephfs -o name=admin,secret=AQATSKdNGBnwLhAAnNDKnH65FmVKpXZJVasUeQ==
"""


@when('mon-related')
def setup_mds():
    # TODO: Update with the conf file location
    osd = ceph_command.OsdCommand('/etc/ceph/ceph.conf')
    mds = ceph_command.MdsCommand('/etc/ceph/ceph.conf')

    try:
        log("Creating cephfs_data pool", level=INFO)
        # TODO: Update with better pg values
        osd.osd_pool_create('cephfs_data', 256)

        log("Creating cephfs_metadata pool", level=INFO)
        # TODO: Update with better pg values
        osd.osd_pool_create('cephfs_metadata', 256)

        log("Creating ceph fs", level=INFO)
        mds.mds_newfs(metadata='cephfs_metadata', data='cephfs_data', sure=["--yes-i-really-mean-it"])
    except RadosError as err:
        log(message='Error: {}'.format(err.message), level=ERROR)


@when('config.changed', 'ceph.installed')
@when('leadership.set.fsid')
def config_changed():
    # Check if an upgrade was requested
    # check_for_upgrade()

    log('MDS hosts are ' + repr(get_mds_hosts()))

    # emit_cephconf()

    # Support use of single node ceph
    if not is_bootstrapped() and int(config('monitor-count')) == 1:
        status_set('maintenance', 'Bootstrapping single Ceph MON')
        bootstrap_monitor_cluster(
            charms.leadership.leader_get('monitor_secret'))
        wait_for_bootstrap()
