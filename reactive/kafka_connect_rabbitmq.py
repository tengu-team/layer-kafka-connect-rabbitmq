import os
from charms import leadership
from charms.reactive import (
    when,
    when_any,
    when_not,
    set_flag,
    clear_flag
)
from charms.reactive.relations import endpoint_from_flag
from charmhelpers.core.hookenv import (
    config,
    log,
    status_set,
    is_leader,
)
from charms.layer.kafka_connect_helpers import (
    set_worker_config, 
    register_connector,
    unregister_connector,
    get_configs_topic,
    get_offsets_topic,
    get_status_topic,
)


conf = config()
JUJU_UNIT_NAME = os.environ['JUJU_UNIT_NAME']
MODEL_NAME = os.environ['JUJU_MODEL_NAME']
RABBTMQ_CONNECTOR_NAME = (MODEL_NAME +
                         '-' + 
                         JUJU_UNIT_NAME.split('/')[0] +
                         '-rabbitmq')

@when('kafka-connect-base.ready',
      'rabbitmq.connected')
def status_set_ready():
    status_set('active', 'ready')

@when_not('rabbitmq.connected')
def blocked_for_rabbitmq():
    status_set('blocked', 'Waiting for rabbitmq relation')


@when('rabbitmq.connected',
      'leadership.is_leader')
@when_not('rabbitmq.available')
def setup_rabbitmq():
    rabbitmq = endpoint_from_flag('rabbitmq.connected')
    juju_app_name = (MODEL_NAME.replace("/", '-') +
                     '.' +
                     JUJU_UNIT_NAME.split('/')[0])
    username = JUJU_UNIT_NAME.split('/')[0]
    vhost = '/' + juju_app_name
    rabbitmq.request_access(username, vhost)
    status_set('waiting', 'Waiting on RabbitMQ to configure vhost')


@when_any('config.changed.topics',
          'config.changed.max-tasks')
def config_changed():
    clear_flag('kafka-connect-rabbitmq.running')


@when('rabbitmq.available',
      'config.set.max-tasks',
      'kafka-connect-base.topic-created',
      'leadership.is_leader')
@when_not('kafka-connect-rabbitmq.installed')
def install_kafka_connect_rabbitmq():
    worker_configs = {
        'key.converter': 'com.github.jcustenborder.kafka.connect.converters.ByteArrayConverter',
        'value.converter': 'com.github.jcustenborder.kafka.connect.converters.ByteArrayConverter',
        'key.converter.schemas.enable': 'false',
        'value.converter.schemas.enable': 'false',
        'internal.key.converter': 'org.apache.kafka.connect.json.JsonConverter',
        'internal.value.converter': 'org.apache.kafka.connect.json.JsonConverter',
        'internal.key.converter.schemas.enable': 'false',
        'internal.value.converter.schemas.enable': 'false',
        'offset.flush.interval.ms': '10000',
        'config.storage.topic': get_configs_topic(),
        'offset.storage.topic': get_offsets_topic(),
        'status.storage.topic': get_status_topic(),
    }
    set_worker_config(worker_configs)
    set_flag('kafka-connect-rabbitmq.installed')
    set_flag('kafka-connect-base.install')


@when('kafka-connect.running',
      'rabbitmq.available',
      'config.set.max-tasks',
      'leadership.is_leader')
@when_not('kafka-connect-rabbitmq.running')
def start_kafka_connect_rabbitmq():
    rabbitmq = endpoint_from_flag('rabbitmq.available')

    rabbitmq_connector_config = {
        'connector.class': 'com.github.jcustenborder.kafka.connect.rabbitmq.RabbitMQSinkConnector',
        'rabbitmq.exchange': MODEL_NAME.replace("/", '-') + '.' + JUJU_UNIT_NAME.split('/')[0],
        'rabbitmq.routing.key': '',
        'rabbitmq.auto.create': True,
        'rabbitmq.host': rabbitmq.private_address(),
        'rabbitmq.username': rabbitmq.username(),
        'rabbitmq.password': rabbitmq.password(),
        'rabbitmq.virtual.host': rabbitmq.vhost(),
        'topics': conf.get('topics').replace(' ', ','),
        'tasks.max': conf.get('max-tasks'),
    }

    response = register_connector(rabbitmq_connector_config, RABBTMQ_CONNECTOR_NAME)
    if response and (response.status_code == 200 or response.status_code == 201):
        status_set('active', 'ready')
        clear_flag('kafka-connect-rabbitmq.stopped')
        set_flag('kafka-connect-rabbitmq.running')
    else:
        log('Could not register/update connector Response: ' + str(response))
        status_set('blocked', 'Could not register/update connector, retrying next hook.')


@when('kafka-connect-rabbitmq.running',
      'leadership.is_leader')
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
