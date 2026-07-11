# Local test data policy

Fixtures under `examples/fixtures/` exist only for local logistics testing.

They are:

- non-canonical;
- not a client database;
- not an order database;
- not production address-book truth;
- safe placeholder data only.

Every recipient fixture must be marked:

```yaml
non_canonical: true
purpose: local logistics testing only

Real frequent recipients may later be maintained locally only under an
explicitly documented owner-controlled workflow.

Such local records must not silently become canonical client ownership.


---