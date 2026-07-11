# Provider adapter policy

Provider adapters must remain provider-neutral at the service boundary.

An adapter may currently:

- describe provider capabilities;
- validate recipient and address information;
- build a shipment payload preview;
- read or normalize tracking information.

An adapter must not currently:

- create a shipment;
- create a TTN;
- order a courier or taxi;
- cancel or mutate a provider-side shipment;
- perform any other live provider write.

The base adapter raises `LiveProviderWriteDisabledError` for shipment creation.

A future live-write implementation requires separate Blueprint approval and
must include dry-run controls, manual confirmation, environment safety checks
and audit records.