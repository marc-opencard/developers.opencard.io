# developers.opencard.io

OpenCard developer documentation — built for [Mintlify](https://mintlify.com).

## Quick start

```bash
npm install
npm run dev
```

Opens local docs preview at `http://localhost:3000`.

## Project structure

```
docs.json              # Mintlify navigation + theme
introduction/          # Welcome, how it works, glossary
getting-started/       # Register, auth, quickstart
ems/                   # EMS integration guides
card-issuers/          # Issuer integration guides
receipt-providers/     # Receipt provider guides
api-reference/
  ems/                 # EMS API (api.opencard.io/application)
  receipts/            # Digital Receipts API (receipts.opencard.io) — card issuers
openapi/               # OpenAPI specs (ems, oauth, issuer, receipts, callback)
```

## OpenAPI specs

The files in `openapi/` are the source of the API reference pages and are edited by hand — they are **not** generated from the swagger annotations in `service.opencard.api`.

When the API changes, update the matching spec in `openapi/` and the guide page that describes the endpoint.

## Deploy

Connect this repo to Mintlify dashboard. Custom domain: `developers.opencard.io`.
