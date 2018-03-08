import os
from charms.reactive import when, when_any, when_not, set_flag, clear_flag
from charms.reactive.relations import endpoint_from_flag
from charmhelpers.core.hookenv import config, log, status_set
from charms.layer.kafka_connect_helpers import (
    set_worker_config, 
    register_connector,
    unregister_connector,
)


conf = config()
JUJU_UNIT_NAME = os.environ['JUJU_UNIT_NAME']
RABBTMQ_CONNECTOR_NAME = JUJU_UNIT_NAME.split('/')[0] + '-rabbitmq'


@when_not('rabbitmq.connected')
def blocked_for_rabbitmq():
    status_set('blocked', 'Waiting for rabbitmq relation')


@when('rabbitmq.connected')
@when_not('rabbitmq.available')
def setup_rabbitmq():
    rabbitmq = endpoint_from_flag('rabbitmq.connected')
    juju_app_name = JUJU_UNIT_NAME.split('/')[0]
    username = JUJU_UNIT_NAME.split('/')[0]
    vhost = '/' + juju_app_name
    rabbitmq.request_access(username, vhost)
    status_set('waiting', 'Waiting on RabbitMQ to configure vhost')


@when_any('config.changed.topics',
          'config.changed.max-tasks')
def config_changed():
    clear_flag('kafka-connect-rabbitmq.running')


@when('rabbitmq.available',
      'config.set.max-tasks')
@when_not('kafka-connect-rabbitmq.installed')
def install_kafka_connect_rabbitmq():
    juju_unit_name = JUJU_UNIT_NAME.replace('/', '.')
    worker_configs = {
        'key.converter': 'org.apache.kafka.connect.json.JsonConverter',
        'value.converter': 'org.apache.kafka.connect.json.JsonConverter',
        'key.converter.schemas.enable': 'false',
        'value.converter.schemas.enable': 'false',
        'internal.key.converter': 'org.apache.kafka.connect.json.JsonConverter',
        'internal.value.converter': 'org.apache.kafka.connect.json.JsonConverter',
        'internal.key.converter.schemas.enable': 'false',
        'internal.value.converter.schemas.enable': 'false',
        'offset.storage.topic': juju_unit_name + '.connectoffsets',
        'offset.flush.interval.ms': '10000',
        'config.storage.topic': juju_unit_name + '.connectconfigs',
        'status.storage.topic': juju_unit_name + '.connectstatus',
        'config.storage.replication.factor': 1,
    }
    set_worker_config(worker_configs)
    set_flag('kafka-connect-rabbitmq.installed')
    set_flag('kafka-connect-base.install')


@when('kafka-connect.running',
      'rabbitmq.available',
      'config.set.max-tasks')
@when_not('kafka-connect-rabbitmq.running')
def start_kafka_connect_rabbitmq():
    rabbitmq = endpoint_from_flag('rabbitmq.available')

    rabbitmq_connector_config = {
        'connector.class': 'com.github.jcustenborder.kafka.connect.rabbitmq.RabbitMQSinkConnector',
        'rabbitmq.exchange': JUJU_UNIT_NAME.split('/')[0],
        'rabbitmq.routing.key': '',
        'rabbitmq.auto.create': True,
        'rabbitmq.host': rabbitmq.private_address(),
        'rabbitmq.username': rabbitmq.username(),
        'rabbitmq.password': rabbitmq.password(),
        'rabbitmq.virtual.host': rabbitmq.vhost(),
        'topics': conf.get('topics').replace(' ', ','),
    }

    response = register_connector(rabbitmq_connector_config, RABBTMQ_CONNECTOR_NAME)
    if response and (response.status_code == 200 or response.status_code == 201):
        status_set('active', 'ready')
        clear_flag('kafka-connect-rabbitmq.stopped')
        set_flag('kafka-connect-rabbitmq.running')        
    else:
        log('Could not register/update connector Response: ' + response)
        status_set('blocked', 'Could not register/update connector, retrying next hook.')


@when('kafka-connect-rabbitmq.running')
@when_not('rabbitmq.connected', 'kafka-connect-rabbitmq.stopped')
def stop_rabbitmq_connect():
    response = unregister_connector(RABBTMQ_CONNECTOR_NAME)
    if response and (response.status_code == 204 or response.status_code == 404):
        set_flag('kafka-connect-rabbitmq.stopped')
        clear_flag('kafka-connect-rabbitmq.running')

@when('kafka-connect-rabbitmq.running')
@when_not('kafka-connect.running')
def stop_running():
    clear_flag('kafka-connect-rabbitmq.running')
