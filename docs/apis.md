# EVOK APIs

For more information see our api documentation at [api-docs].

Evok APIs listening on default hostname '127.0.0.1' on port '8080'.
You can change this setting in [configuration](./configs/evok_configuration.md).

## REST ([doc](./apis/rest.md))
The REST API provides a simple interface for sending and receiving data in a stateless, cacheable communications.
This protocol do not support multiple write in one request.
It is suitable for hand-make requests.

## JSON ([doc](./apis/json.md))
The JSON API provides a simple interface for sending and receiving data in a stateless, cacheable communications.
This protocol do not support multiple write in one request.
It is suitable for automated requests thanks JSON protocol, which is better machine-processed.

## BULK ([doc](./apis/bulk.md))
The BULK API is designed to provide an efficient way for clients to update, create or delete large amounts of data.
This protocol support multiple write in one request.
It is suitable for automated requests thanks JSON protocol, which is better machine-processed.

## Websocket ([doc](./apis/websocket.md))
The WebSocket API allows for two-way communication between the client and server over an open connection.
Evok sends changes to every connected client.
A list of reflected devices can be defined.
It is suitable if you need to immediately react to events in your application.

## RPC ([doc](./apis/rpc.md))
The RPC (Remote Procedure Call) API is used for invoking procedures, functions or methods across a network.
It is suitable for automated request.

## Webhook ([doc](./apis/webhook.md))
The Webhook API provides a mechanism for pushing real-time updates to clients.
Evok sends the changes to the specified hostname and port.
A list of reflected devices can be defined.
It is suitable for collecting information about the running of the application.

[api-docs]:https://kb.unipi.technology/en:sw:02-apis:01-evok:apidoc