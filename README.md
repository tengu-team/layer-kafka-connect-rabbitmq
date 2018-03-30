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

## Authors

This software was created in the [IBCN research group](https://www.ibcn.intec.ugent.be/) of [Ghent University](https://www.ugent.be/en) in Belgium. This software is used in [Tengu](https://tengu.io), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Sander Borny <sander.borny@ugent.be>
