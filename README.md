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
api-reference/         # API overview (generated pages in subdirs)
openapi/               # OpenAPI specs (generated from API source)
scripts/
  generate-openapi.py  # Generate specs from code inventory
  sync-openapi.sh      # Wrapper script
```

## Regenerate OpenAPI specs

Specs are generated from `service.opencard.api` route inventory — **not** from legacy swagger annotations.

```bash
npm run sync-openapi
```

When the API changes, update endpoint definitions in `scripts/generate-openapi.py` and regenerate.

## Deploy

Connect this repo to Mintlify dashboard. Custom domain: `developers.opencard.io`.
