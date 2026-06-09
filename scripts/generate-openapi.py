#!/usr/bin/env python3
"""Generate audience-specific OpenAPI specs for Mintlify. Run: python3 scripts/generate-openapi.py"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "openapi"

ACCOUNT_ID = {"$ref": "#/components/parameters/accountId"}
ORG_ID = {"$ref": "#/components/parameters/organizationId"}
OAUTH = {"opencard_auth": []}
BEARER = {"bearer": []}

ERR = {"type": "object", "properties": {"error": {"type": "string"}}, "example": {"error": "Access denied"}}


def ref(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}"}


def path_param(name: str, desc: str, typ: str = "integer") -> dict:
    return {"name": name, "in": "path", "required": True, "description": desc, "schema": {"type": typ}}


def json_body(schema: dict, example: dict | None = None, required: bool = True) -> dict:
    body = {"required": required, "content": {"application/json": {"schema": schema}}}
    if example:
        body["content"]["application/json"]["example"] = example
    return body


def json_resp(code: str, desc: str, schema: dict | None = None, example=None) -> dict:
    content: dict = {"application/json": {}}
    if schema:
        content["application/json"]["schema"] = schema
    if example is not None:
        content["application/json"]["example"] = example
    return {code: {"description": desc, "content": content}}


def op(paths: dict, method: str, path: str, *, tag: str, summary: str, operation_id: str,
       scope: str | list[str] | None = None, description: str = "", params: list | None = None,
       body: dict | None = None, responses: dict | None = None, security: bool = True) -> None:
    paths.setdefault(path, {})
    operation: dict = {"tags": [tag], "summary": summary, "operationId": operation_id}
    if description:
        operation["description"] = description
    if params:
        operation["parameters"] = params
    if body:
        operation["requestBody"] = body
    operation["responses"] = responses or json_resp("200", "Success", example={})
    if security:
        scopes = scope if isinstance(scope, list) else ([scope] if scope else [])
        operation["security"] = [{"opencard_auth": scopes}]
    paths[path][method] = operation


# ─── Shared examples (EMS) ───────────────────────────────────────────────────

EX = {
    "account": {
        "id": 1,
        "name_system": "Acme EMS",
        "name_legal": "Acme Expense AB",
        "organization_number": "5561234567",
        "country": "SE",
    },
    "tpa": {
        "id": 42,
        "account_id": 1,
        "card_issuer_id": 1,
        "name": "Acme AB",
        "country": "SE",
        "organization_number": "5561234567",
        "activated": False,
        "signatures_verified": False,
        "status": "pending-signatures",
    },
    "tpa_signatory": {
        "id": 7,
        "email": "ceo@acme.se",
        "name": "Anna Andersson",
        "tpa_id": 42,
        "signed": False,
        "signed_at": None,
    },
    "organization": {
        "id": 3,
        "reference_id": "client_acme_001",
        "tpa_id": 42,
        "account_id": 1,
        "name": "Acme AB",
    },
    "card_holder": {
        "id": 15,
        "reference_id": "employee_john_42",
        "organization_id": 3,
        "identity_id": 123,
        "email": "john@acme.se",
        "created_at": "2026-06-08T10:00:00.000000Z",
        "updated_at": "2026-06-08T10:30:00.000000Z",
        "meta": {
            "ssn": True,
            "signed": True,
            "signed_at": "2026-06-08T10:30:00.000000Z",
            "email_status": "delivered",
            "pdpc_url": "https://sandbox-api.opencard.io/accounts/1/pdpcs/8/sign/abc...",
            "system": "Acme EMS",
            "organization_number": "5561234567",
        },
        "identity": {
            "name": "Anna Andersson",
            "employee_id": "001",
        },
    },
    "webhook": {
        "id": 5,
        "organization_id": 3,
        "url": "https://your-app.com/hooks/opencard",
        "active": True,
        "enabled": True,
        "card_transaction_authorized": True,
        "card_transaction_cleared": True,
        "card_transaction_deleted": True,
        "receipt_fetched": True,
    },
    "identity": {
        "id": 123,
        "name": "Anna Andersson",
        "employee_id": "001",
        "cards": [{"id": 10, "last_four": "1234", "token": "ext-card-abc", "type": "corporate"}],
        "card_holders": [],
    },
    "oauth_token": {
        "token_type": "Bearer",
        "expires_in": 31536000,
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...",
    },
    "paginated": lambda data: {
        "current_page": 1,
        "data": data,
        "per_page": 15,
        "total": len(data) if isinstance(data, list) else 1,
        "last_page": 1,
    },
}

# ─── EMS API (api.opencard.io/api/v1/application) ────────────────────────────

ems_paths: dict = {}

# Account (own account only — no admin list/mode)
op(ems_paths, "get", "/accounts/{accountId}", tag="Account", summary="Get your account",
   operation_id="getAccount", scope="accounts-read", params=[ACCOUNT_ID],
   responses={**json_resp("200", "Account", example=EX["account"]), **json_resp("403", "Forbidden", example={"error": "Access denied"})})
op(ems_paths, "put", "/accounts/{accountId}", tag="Account", summary="Update your account",
   operation_id="updateAccount", scope="accounts-write", params=[ACCOUNT_ID],
   body=json_body({"type": "object", "properties": {"notify_email": {"type": "string", "format": "email"}}}),
   responses=json_resp("200", "Updated account", example=EX["account"]))

# OAuth clients
ocb = "/accounts/{accountId}/oauthclients"
op(ems_paths, "get", ocb, tag="OAuth Clients", summary="List OAuth clients", operation_id="listOAuthClients",
   scope="oauth-clients-read", params=[ACCOUNT_ID],
   responses=json_resp("200", "OAuth clients", example=EX["paginated"]([{"id": 1, "name": "Production EMS"}])))
op(ems_paths, "post", ocb, tag="OAuth Clients", summary="Create OAuth client", operation_id="createOAuthClient",
   scope="oauth-clients-write", params=[ACCOUNT_ID],
   responses={**json_resp("201", "Created", example={"id": 2, "secret": "plain-text-secret-shown-once"}), **json_resp("403", "Forbidden", example={"error": "Access denied"})})

# Public records
op(ems_paths, "get", "/accounts/{accountId}/publicrecords", tag="Public Records",
   summary="Lookup company + signing combinations", operation_id="queryPublicRecords",
   scope="public-records-read", params=[ACCOUNT_ID,
       {"name": "country", "in": "query", "required": True, "schema": {"type": "string", "enum": ["SE", "DK", "NO", "FI"]}},
       {"name": "organization_number", "in": "query", "required": True, "schema": {"type": "string"}}],
   responses=json_resp("200", "Public record", example={"name": "Acme AB", "signature_combinations": [[{"name": "Anna Andersson"}]]}))

# TPAs
tpa = "/accounts/{accountId}/tpas"
op(ems_paths, "get", tpa, tag="TPAs", summary="List TPAs", operation_id="listTpas", scope="account-tpas-read", params=[ACCOUNT_ID],
   responses=json_resp("200", "TPAs", example=EX["paginated"]([EX["tpa"]])))
op(ems_paths, "post", tpa, tag="TPAs", summary="Create TPA", operation_id="createTpa", scope="account-tpas-write", params=[ACCOUNT_ID],
   description="Creates TPA, fetches registry data, generates legal text.",
   body=json_body(ref("TpaCreate"), example={"card_issuer_id": 1, "name": "Acme AB", "country": "SE", "organization_number": "5561234567", "language": "sv"}),
   responses=json_resp("201", "TPA created", example=EX["tpa"]))
op(ems_paths, "get", f"{tpa}/{{tpaId}}", tag="TPAs", summary="Get TPA", operation_id="getTpa", scope="account-tpas-read",
   params=[ACCOUNT_ID, path_param("tpaId", "TPA ID")], responses=json_resp("200", "TPA", example=EX["tpa"]))
op(ems_paths, "delete", f"{tpa}/{{tpaId}}", tag="TPAs", summary="Delete TPA", operation_id="deleteTpa", scope="account-tpas-delete",
   params=[ACCOUNT_ID, path_param("tpaId", "TPA ID")], responses=json_resp("200", "Deleted"))

sig = f"{tpa}/{{tpaId}}/signatories"
op(ems_paths, "get", sig, tag="TPA Signatories", summary="List signatories", operation_id="listTpaSignatories",
   scope="account-tpa-signatories-read", params=[ACCOUNT_ID, path_param("tpaId", "TPA ID")],
   responses=json_resp("200", "Signatories", example=EX["paginated"]([EX["tpa_signatory"]])))
op(ems_paths, "post", sig, tag="TPA Signatories", summary="Add signatory (sends email)", operation_id="createTpaSignatory",
   scope="account-tpa-signatories-write", params=[ACCOUNT_ID, path_param("tpaId", "TPA ID")],
   body=json_body(ref("TpaSignatoryCreate"), example={"email": "ceo@acme.se", "name": "Anna Andersson"}),
   responses=json_resp("201", "Signatory created", example=EX["tpa_signatory"]))

op(ems_paths, "get", f"{tpa}/{{tpaId}}/identities", tag="Identities", summary="List identities on TPA",
   operation_id="listTpaIdentities", scope="account-tpa-identities-read",
   params=[ACCOUNT_ID, path_param("tpaId", "TPA ID"),
           {"name": "is_card_holder", "in": "query", "schema": {"type": "boolean"}}],
   description="Physical persons linked to this TPA. Use `id` as `identity_id` for instant card holder onboarding.",
   responses=json_resp("200", "Identities", example=EX["paginated"]([EX["identity"]])))

# Billings
bill = "/accounts/{accountId}/billings"
op(ems_paths, "post", bill, tag="Billings", summary="Create billing profile", operation_id="createBilling",
   scope="billings-write", params=[ACCOUNT_ID],
   body=json_body(ref("BillingCreate"), example={"name_display": "Acme AB", "name_legal": "Acme AB", "organization_number": "5561234567", "country": "SE"}),
   responses=json_resp("201", "Billing created", example={"id": 1, "name_display": "Acme AB"}))

# Card issuers on account
ci = "/accounts/{accountId}/cardissuers"
op(ems_paths, "get", ci, tag="Card Issuers", summary="List enabled issuers", operation_id="listAccountCardIssuers",
   scope="account-card-issuers-read", params=[ACCOUNT_ID],
   responses=json_resp("200", "Issuers", example=EX["paginated"]([{"id": 1, "name_display": "Corporate Card Program"}])))
op(ems_paths, "post", f"{ci}/{{cardIssuerId}}", tag="Card Issuers", summary="Enable issuer", operation_id="attachCardIssuer",
   scope="account-card-issuers-write", params=[ACCOUNT_ID, path_param("cardIssuerId", "Issuer ID")],
   responses=json_resp("201", "Attached"))

# Organizations
org = "/accounts/{accountId}/organizations"
op(ems_paths, "get", org, tag="Organizations", summary="List organizations", operation_id="listOrganizations",
   scope="organizations-read", params=[ACCOUNT_ID],
   responses=json_resp("200", "Organizations", example=EX["paginated"]([EX["organization"]])))
op(ems_paths, "post", org, tag="Organizations", summary="Create organization", operation_id="createOrganization",
   scope="organizations-write", params=[ACCOUNT_ID],
   body=json_body(ref("OrganizationCreate"), example={"reference_id": "client_acme_001", "tpa_id": 42, "name": "Acme AB"}),
   responses=json_resp("201", "Organization created", example=EX["organization"]))
op(ems_paths, "get", f"{org}/{{organizationId}}", tag="Organizations", summary="Get organization", operation_id="getOrganization",
   scope="organizations-read", params=[ACCOUNT_ID, ORG_ID], responses=json_resp("200", "Organization", example=EX["organization"]))

# Card holders
ch = f"{org}/{{organizationId}}/cardholders"
op(ems_paths, "get", ch, tag="Card Holders", summary="List card holders", operation_id="listCardHolders",
   scope="card-holders-read", params=[ACCOUNT_ID, ORG_ID],
   description="Paginated list. Each item includes `identity` (`name`, `employee_id`) when linked — no separate identities call needed for display.",
   responses=json_resp("200", "Card holders",
       schema={"type": "object", "properties": {
           "current_page": {"type": "integer"},
           "data": {"type": "array", "items": ref("CardHolder")},
           "per_page": {"type": "integer"},
           "total": {"type": "integer"},
           "last_page": {"type": "integer"},
       }},
       example=EX["paginated"]([EX["card_holder"]])))
op(ems_paths, "post", ch, tag="Card Holders", summary="Create card holder", operation_id="createCardHolder",
   scope="card-holders-write", params=[ACCOUNT_ID, ORG_ID],
   description="Path A: `email` → PDPC email + eID. Path B: `identity_id` → instant, transactions flow immediately.",
   body=json_body(ref("CardHolderCreate"), example={"reference_id": "employee_john_42", "email": "john@acme.se", "language": "sv"}),
   responses=json_resp("201", "Card holder created", example=EX["card_holder"]))
ch_one = f"{ch}/{{cardHolderId}}"
op(ems_paths, "put", ch_one, tag="Card Holders", summary="Update card holder", operation_id="updateCardHolder",
   scope="card-holders-write", params=[ACCOUNT_ID, ORG_ID, path_param("cardHolderId", "Card holder ID")],
   description="`reference_id` is required. `email` is optional — omit to keep the current value (including null for identity-linked holders). Resends PDPC email only when unsigned/no identity, `skip_pdpc_email` is false, and an email address exists. Duplicate `reference_id` within the organization returns 400.",
   body=json_body(ref("CardHolderUpdate"), example={"reference_id": "employee_john_99"}),
   responses={**json_resp("200", "Updated card holder", example=EX["card_holder"]),
              **json_resp("400", "Bad request", example={"error": "Card holder reference employee_john_42 already exists"})})
op(ems_paths, "delete", ch_one, tag="Card Holders", summary="Delete card holder", operation_id="deleteCardHolder",
   scope="card-holders-delete", params=[ACCOUNT_ID, ORG_ID, path_param("cardHolderId", "Card holder ID")],
   description="Fires `card_holder.deleted` webhook.",
   responses=json_resp("200", "Deleted"))

# Webhooks
wh = f"{org}/{{organizationId}}/webhooks"
op(ems_paths, "get", wh, tag="Webhooks", summary="List webhooks", operation_id="listWebhooks",
   scope="webhooks-read", params=[ACCOUNT_ID, ORG_ID],
   responses=json_resp("200", "Webhooks", example=EX["paginated"]([EX["webhook"]])))
op(ems_paths, "post", wh, tag="Webhooks", summary="Create webhook", operation_id="createWebhook",
   scope="webhooks-write", params=[ACCOUNT_ID, ORG_ID],
   body=json_body(ref("WebhookCreate"), example={"url": "https://your-app.com/hooks/opencard", "card_transaction_cleared": True, "card_transaction_authorized": True}),
   responses=json_resp("201", "Webhook created", example=EX["webhook"]))
op(ems_paths, "get", f"{wh}/{{webhookId}}/events", tag="Webhooks", summary="Delivery log", operation_id="listWebhookEvents",
   scope="webhook-events-read", params=[ACCOUNT_ID, ORG_ID, path_param("webhookId", "Webhook ID")],
   responses=json_resp("200", "Events", example=EX["paginated"]([{"event": "card.transaction.authorized", "status": 200}])))

# Receipt scan
op(ems_paths, "post", "/accounts/{accountId}/receipts/scan", tag="Receipt Scanner", summary="OCR scan receipt",
   operation_id="scanReceipt", scope="receipts-write", params=[ACCOUNT_ID],
   body=json_body({"type": "object", "required": ["receipt"], "properties": {"receipt": {"type": "string"}, "include": {"type": "array", "items": {"type": "string"}}}},
                  example={"receipt": "base64-image...", "include": ["line_items"]}),
   responses=json_resp("200", "OCR result", example={"merchant": "ICA", "total_amount": 109.38, "currency": "SEK", "line_items": [{"description": "Coffee", "amount": 45}]}))

EMS_SCOPES = {
    "accounts-read": "Read your account",
    "accounts-write": "Update your account",
    "oauth-clients-read": "Read OAuth clients",
    "oauth-clients-write": "Create OAuth clients",
    "public-records-read": "Company registry lookup",
    "account-tpas-read": "Read TPAs",
    "account-tpas-write": "Create TPAs",
    "account-tpas-delete": "Delete TPAs",
    "account-tpa-signatories-read": "Read TPA signatories",
    "account-tpa-signatories-write": "Add TPA signatories",
    "account-tpa-identities-read": "List identities on TPA",
    "billings-write": "Create billing profiles",
    "account-card-issuers-read": "List enabled issuers",
    "account-card-issuers-write": "Enable issuers",
    "organizations-read": "Read organizations",
    "organizations-write": "Create organizations",
    "card-holders-read": "Read card holders",
    "card-holders-write": "Create and update card holders",
    "card-holders-delete": "Delete card holders",
    "webhooks-read": "Read webhooks",
    "webhooks-write": "Create webhooks",
    "webhook-events-read": "Read webhook delivery log",
    "receipts-write": "Scan receipts (OCR)",
}

ems_spec = {
    "openapi": "3.0.3",
    "info": {
        "title": "OpenCard EMS API",
        "version": "1.0",
        "description": "API for Expense Management Systems. Manage TPAs, organizations, card holders, and webhooks. Receive transaction data via webhooks — not by polling this API.",
        "contact": {"email": "support@opencard.io"},
    },
    "servers": [
        {"url": "https://api.opencard.io/api/v1/application", "description": "Production"},
        {"url": "https://sandbox-api.opencard.io/api/v1/application", "description": "Sandbox"},
    ],
    "paths": ems_paths,
    "components": {
        "securitySchemes": {
            "opencard_auth": {
                "type": "oauth2",
                "flows": {"clientCredentials": {"tokenUrl": "https://api.opencard.io/oauth/token", "scopes": EMS_SCOPES}},
            }
        },
        "parameters": {
            "accountId": path_param("accountId", "Your account ID"),
            "organizationId": path_param("organizationId", "Organization ID"),
        },
        "schemas": {
            "TpaCreate": {"type": "object", "required": ["card_issuer_id", "name", "country", "organization_number"],
                "properties": {"card_issuer_id": {"type": "integer"}, "name": {"type": "string"}, "country": {"type": "string", "enum": ["SE", "DK", "NO", "FI"]},
                    "organization_number": {"type": "string"}, "language": {"type": "string", "enum": ["sv", "no", "da", "en", "fi"]}}},
            "TpaSignatoryCreate": {"type": "object", "required": ["email"], "properties": {"email": {"type": "string"}, "name": {"type": "string"}}},
            "OrganizationCreate": {"type": "object", "required": ["reference_id", "tpa_id"],
                "properties": {"reference_id": {"type": "string"}, "tpa_id": {"type": "integer"}, "name": {"type": "string"}}},
            "CardHolderCreate": {"type": "object", "required": ["reference_id"],
                "properties": {"reference_id": {"type": "string"}, "email": {"type": "string"}, "identity_id": {"type": "integer"},
                    "skip_pdpc_email": {"type": "boolean"}, "language": {"type": "string"}}},
            "CardHolderUpdate": {"type": "object", "required": ["reference_id"],
                "description": "Update card holder. Only `reference_id` is required; other fields are optional.",
                "properties": {
                    "reference_id": {"type": "string"},
                    "email": {"type": "string", "nullable": True, "format": "email", "description": "Omit to leave unchanged"},
                    "skip_pdpc_email": {"type": "boolean"},
                    "language": {"type": "string", "enum": ["sv", "no", "da", "en", "fi"]},
                }},
            "CardHolderIdentity": {"type": "object", "nullable": True,
                "description": "Linked identity summary on list responses. Only `name` and `employee_id` — nothing else.",
                "properties": {
                    "name": {"type": "string", "nullable": True, "description": "Person name from eID"},
                    "employee_id": {"type": "string", "nullable": True, "description": "Employee ID on the TPA client"},
                }},
            "CardHolder": {"type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "reference_id": {"type": "string"},
                    "organization_id": {"type": "integer"},
                    "identity_id": {"type": "integer", "nullable": True},
                    "email": {"type": "string", "nullable": True, "format": "email"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                    "meta": {"type": "object", "properties": {
                        "ssn": {"type": "boolean"},
                        "signed": {"type": "boolean"},
                        "signed_at": {"type": "string", "format": "date-time", "nullable": True},
                        "email_status": {"type": "string", "nullable": True, "enum": ["delivered", "failed"]},
                        "pdpc_url": {"type": "string", "nullable": True},
                        "system": {"type": "string", "nullable": True},
                        "organization_number": {"type": "string", "nullable": True},
                    }},
                    "identity": ref("CardHolderIdentity"),
                }},
            "BillingCreate": {"type": "object", "required": ["name_display", "name_legal", "organization_number", "country"],
                "properties": {"name_display": {"type": "string"}, "name_legal": {"type": "string"}, "organization_number": {"type": "string"}, "country": {"type": "string"}}},
            "WebhookCreate": {"type": "object", "required": ["url"], "properties": {
                "url": {"type": "string"}, "card_transaction_authorized": {"type": "boolean"}, "card_transaction_cleared": {"type": "boolean"},
                "card_transaction_deleted": {"type": "boolean"}, "receipt_fetched": {"type": "boolean"}, "transaction_true_vat": {"type": "boolean"}}},
        },
    },
    "x-tagGroups": [
        {"name": "Account", "tags": ["Account", "OAuth Clients", "Public Records", "Billings", "Card Issuers"]},
        {"name": "Legal", "tags": ["TPAs", "TPA Signatories", "Identities"]},
        {"name": "Organizations", "tags": ["Organizations", "Card Holders", "Webhooks"]},
        {"name": "Enrichment", "tags": ["Receipt Scanner"]},
    ],
}

# ─── OAuth ─────────────────────────────────────────────────────────────────────

oauth_spec = {
    "openapi": "3.0.3",
    "info": {"title": "OpenCard OAuth", "version": "1.0", "description": "Get bearer tokens for the EMS API."},
    "servers": [
        {"url": "https://api.opencard.io", "description": "Production"},
        {"url": "https://sandbox-api.opencard.io", "description": "Sandbox"},
    ],
    "paths": {
        "/oauth/token": {
            "post": {
                "tags": ["OAuth"],
                "summary": "Get access token",
                "operationId": "getAccessToken",
                "requestBody": json_body(
                    {"type": "object", "required": ["grant_type", "client_id", "client_secret", "scope"],
                     "properties": {"grant_type": {"type": "string", "enum": ["client_credentials"]}, "client_id": {"type": "string"},
                         "client_secret": {"type": "string"}, "scope": {"type": "string"}}},
                    example={"grant_type": "client_credentials", "client_id": "your-client-id", "client_secret": "your-secret",
                             "scope": "organizations-write webhooks-write card-holders-write"},
                ),
                "responses": json_resp("200", "Token issued", example=EX["oauth_token"]),
            }
        }
    },
}

# ─── Digital Receipts API (receipts.opencard.io) — for card issuers ────────────

CALLBACK_TX = {
    "callback_path": "/transaction/123456789",
    "callback_content_type": "text/xml",
    "transaction": {
        "id": "txn_001", "auth_amount": 99.95, "auth_currency": "SEK", "auth_date": "2026-06-08",
        "auth_time": "11:12:14", "auth_timezone": "Europe/Stockholm", "reference_no": "190102519907",
        "auth_code": "ABC123", "terminal_id": "0000000015745355", "merchant_no": "3462188",
        "merchant_name": "Espresso House", "merchant_country": "SE", "clearing": "false",
        "auth_masked_card_number": "****1234", "type": "CARD_PURCHASE", "state": "AUTHORIZED", "mcc": "5814",
    },
}

receipts_spec = {
    "openapi": "3.0.3",
    "info": {
        "title": "OpenCard Digital Receipts API",
        "version": "1.0",
        "description": "Card issuers submit transaction data for digital receipt matching. Hosted at receipts.opencard.io.",
        "contact": {"email": "support@opencard.io"},
    },
    "servers": [{"url": "https://receipts.opencard.io", "description": "Digital Receipts Service"}],
    "tags": [
        {"name": "Publishers", "description": "Merchants with active digital receipts"},
        {"name": "Callback Requests", "description": "Submit transactions for receipt matching"},
    ],
    "paths": {
        "/api/v1/marcet/publishers": {
            "get": {"tags": ["Publishers"], "summary": "List active merchants", "operationId": "queryPublishers",
                "security": [BEARER],
                "responses": json_resp("200", "Publishers", example=[{
                    "id": "79e59794-449e-4f3c-b584-0e9e9547501a", "partner_id": "3ab69d8c-3019-40e9-a6e9-afb5d3dfca5b",
                    "caids": [{"caid": "00004172235", "activated": "2014-03-31"}],
                }])},
        },
        "/api/v1/marcet/callbackrequests": {
            "post": {"tags": ["Callback Requests"], "summary": "Create callback request", "operationId": "createCallbackRequest",
                "description": "Submit transaction for receipt matching. OpenCard calls your callback_url when matched.",
                "security": [BEARER],
                "requestBody": json_body({"type": "array", "items": {"$ref": "#/components/schemas/CallbackTransaction"}}, example=[CALLBACK_TX]),
                "responses": json_resp("200", "Accepted", example=[CALLBACK_TX])},
            "get": {"tags": ["Callback Requests"], "summary": "List callback requests", "operationId": "queryCallbackRequests",
                "security": [BEARER], "responses": json_resp("200", "Callback requests", example=[CALLBACK_TX])},
        },
        "/api/v1/marcet/callbackrequests/{callbackRequestId}": {
            "get": {"tags": ["Callback Requests"], "summary": "Get callback request", "operationId": "getCallbackRequest",
                "parameters": [path_param("callbackRequestId", "Callback request ID", "string")],
                "security": [BEARER], "responses": json_resp("200", "Callback request", example=CALLBACK_TX)},
            "put": {"tags": ["Callback Requests"], "summary": "Update (e.g. clearing status)", "operationId": "updateCallbackRequest",
                "parameters": [path_param("callbackRequestId", "Callback request ID", "string")],
                "security": [BEARER], "requestBody": json_body({"type": "object"}, example={"transaction": {"clearing": "true"}}),
                "responses": json_resp("200", "Updated", example=CALLBACK_TX)},
            "delete": {"tags": ["Callback Requests"], "summary": "Delete callback request", "operationId": "deleteCallbackRequest",
                "parameters": [path_param("callbackRequestId", "Callback request ID", "string")],
                "security": [BEARER], "responses": json_resp("204", "Deleted")},
        },
    },
    "components": {
        "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}},
        "schemas": {
            "CallbackTransaction": {"type": "object", "properties": {
                "callback_path": {"type": "string"}, "callback_content_type": {"type": "string"},
                "transaction": {"type": "object"}}},
            "Error": ERR,
        },
    },
}

# ─── Receipt provider callback (inbound to api.opencard.io) ───────────────────

provider_callback_spec = {
    "openapi": "3.0.3",
    "info": {"title": "Receipt Provider Callback", "version": "1.0",
        "description": "Inbound API for receipt enrichers delivering matched data back to OpenCard."},
    "servers": [
        {"url": "https://api.opencard.io/api", "description": "Production"},
        {"url": "https://sandbox-api.opencard.io/api", "description": "Sandbox"},
    ],
    "paths": {
        "/v1/service/marcet/callback/{referenceId}": {
            "post": {"tags": ["Callback"], "summary": "Deliver receipt enrichment", "operationId": "receiptProviderCallback",
                "description": "HMAC-SHA256 via X-Data-Signature header.",
                "parameters": [
                    path_param("referenceId", "Transaction reference", "string"),
                    {"name": "X-Event", "in": "header", "required": True, "schema": {"type": "string", "enum": ["CallbackRequestResolved", "CallbackRequestDeleted"]}},
                    {"name": "X-Data-Signature", "in": "header", "required": True, "schema": {"type": "string"}},
                ],
                "responses": json_resp("200", "Accepted")},
        }
    },
}

# ─── Write ─────────────────────────────────────────────────────────────────────

OUT.mkdir(parents=True, exist_ok=True)
files = {
    "ems-api.json": ems_spec,
    "oauth.json": oauth_spec,
    "receipts-api.json": receipts_spec,
    "receipt-provider-callback.json": provider_callback_spec,
}
for name, spec in files.items():
    with open(OUT / name, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"Wrote {OUT / name} ({len(spec.get('paths', {}))} paths)")

# Remove legacy spec if present
legacy = OUT / "application-api.json"
if legacy.exists():
    legacy.unlink()
    print(f"Removed legacy {legacy}")
