# Kafka-connect-rabbitmq

Kafka Connect is a framework to stream data into and out of Kafka. For more information see the [documentation](https://docs.confluent.io/current/connect/concepts.html#concepts).

## Overview
This charm sets up a Kafka connect cluster in Kubernetes and configures it to send Kafka topic data (source) to RabbitMQ (sink). 
The connector used can be found [here](https://github.com/tengu-team/kafka-connect-rabbitmq).

Every Kafka topic will be written to a RabbitMQ queue in a vhost which has the juju application name.

## How to use
```bash
juju deploy kafka-connect-rabbitmq connect
juju add-relation kafka connect
juju add-relation rabbitmq-server connect
juju add-relation kubernetes-deployer connect:kubernetes
juju config connect "topics=topic1 topic2" 
```

## Caveats
This setup only handles json formatted Kafka messages.

Default values are used for Kafka connect topic creation, a detailed list of these values can be found [here](https://docs.confluent.io/current/connect/userguide.html). This charm will create three topics for kafka connect with the following naming scheme:
```
model = os.environ['JUJU_MODEL_NAME']
juju_unit_name = os.environ['JUJU_UNIT_NAME'].replace('/', '.')
offset.storage.topic = model + '.' + juju_unit_name + '.connectoffsets'
config.storage.topic = model + '.' + juju_unit_name + '.connectconfigs'
status.storage.topic = model + '.' + juju_unit_name + '.connectstatus'
``` 
These topics can be manually created before starting Kafka connect with configs that suit your needs.

This charm is not intended to scale. One charm corresponds to one Kafka connect cluster. Modify the `workers` config to scale the number of workers.

## Authors

This software was created in the [IBCN research group](https://www.ibcn.intec.ugent.be/) of [Ghent University](https://www.ugent.be/en) in Belgium. This software is used in [Tengu](https://tengu.io), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Sander Borny <sander.borny@ugent.be>
