#!/usr/bin/env python3
"""
Generate OpenAPI specs from service.opencard.api route inventory.
Run from repo root: python3 scripts/generate-openapi.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "openapi"

ACCOUNT_ID = {"$ref": "#/components/parameters/accountId"}
ORG_ID = {"$ref": "#/components/parameters/organizationId"}

OAUTH_SECURITY = {"opencard_auth": []}
BEARER = {"bearer_auth": []}


def ref(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}"}


def path_param(name: str, desc: str, typ: str = "integer") -> dict:
    return {"name": name, "in": "path", "required": True, "description": desc, "schema": {"type": typ}}


def json_body(schema: dict, required: bool = True) -> dict:
    return {
        "required": required,
        "content": {"application/json": {"schema": schema}},
    }


def resp(code: str, desc: str, schema: dict | None = None) -> dict:
    r: dict = {"description": desc}
    if schema:
        r["content"] = {"application/json": {"schema": schema}}
    return r


def op(
    method: str,
    path: str,
    *,
    tag: str,
    summary: str,
    operation_id: str,
    scope: str | list[str] | None = None,
    description: str = "",
    params: list | None = None,
    body: dict | None = None,
    responses: dict | None = None,
    security: bool = True,
) -> None:
    paths.setdefault(path, {})
    operation: dict = {
        "tags": [tag],
        "summary": summary,
        "operationId": operation_id,
    }
    if description:
        operation["description"] = description
    if params:
        operation["parameters"] = params
    if body:
        operation["requestBody"] = body
    operation["responses"] = responses or {"200": resp("200", "Success")}
    if security:
        scopes = scope if isinstance(scope, list) else ([scope] if scope else [])
        operation["security"] = [{"opencard_auth": scopes}]
    paths[path][method] = operation


paths: dict = {}

# ─── Application API ─────────────────────────────────────────────────────────

# Me
op("get", "/me", tag="Me", summary="Get current user", operation_id="getMe", scope="me-read")
op(
    "put",
    "/me",
    tag="Me",
    summary="Update current user",
    operation_id="updateMe",
    scope="me-write",
    body=json_body(
        {
            "type": "object",
            "required": ["first_name", "last_name", "email"],
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "email": {"type": "string", "format": "email"},
            },
        }
    ),
)
op("get", "/me/cards", tag="Me", summary="List my cards", operation_id="listMyCards", scope="me-cards-read")
op(
    "put",
    "/me/cards/{cardId}",
    tag="Me",
    summary="Update my card",
    operation_id="updateMyCard",
    scope="me-cards-write",
    params=[path_param("cardId", "Card ID")],
    body=json_body({"type": "object", "required": ["opencard_enabled"], "properties": {"opencard_enabled": {"type": "boolean"}}}),
)
op(
    "get",
    "/me/cards/mastercard_token",
    tag="Me",
    summary="Get MasterCard consent token",
    operation_id="getMastercardToken",
    scope="me-cards-read",
    params=[{"name": "pdpc_id", "in": "query", "required": True, "schema": {"type": "integer"}}],
)
op("get", "/me/clients", tag="Me", summary="List my PDPC consents", operation_id="listMyPdpcs", scope="me-pdpcs-read")
op("get", "/me/tokens", tag="Me", summary="List my access tokens", operation_id="listMyTokens", scope="me-tokens-read")

# Accounts
op("get", "/accounts", tag="Accounts", summary="List all accounts (admin)", operation_id="listAccounts", scope="accounts-full")
op("get", "/accounts/{accountId}", tag="Accounts", summary="Get account", operation_id="getAccount", scope="accounts-read", params=[ACCOUNT_ID])
op(
    "put",
    "/accounts/{accountId}",
    tag="Accounts",
    summary="Update account",
    operation_id="updateAccount",
    scope="accounts-write",
    params=[ACCOUNT_ID],
    body=json_body(
        {
            "type": "object",
            "properties": {
                "logo_base64": {"type": "string", "description": "Base64-encoded JPEG logo"},
                "notify_email": {"type": "string", "format": "email", "nullable": True},
            },
        }
    ),
)
op(
    "put",
    "/accounts/{accountId}/mode",
    tag="Accounts",
    summary="Update account mode (admin)",
    operation_id="updateAccountMode",
    scope="accounts-full",
    params=[ACCOUNT_ID],
)

# OAuth clients
base = "/accounts/{accountId}/oauthclients"
op("get", base, tag="OAuth Clients", summary="List OAuth clients", operation_id="listOAuthClients", scope="oauth-clients-read", params=[ACCOUNT_ID])
op("post", base, tag="OAuth Clients", summary="Create OAuth client", operation_id="createOAuthClient", scope="oauth-clients-write", params=[ACCOUNT_ID], responses={"201": resp("201", "Client created with plain-text secret")})
op("get", f"{base}/{{oauthclientId}}", tag="OAuth Clients", summary="Get OAuth client", operation_id="getOAuthClient", scope="oauth-clients-read", params=[ACCOUNT_ID, path_param("oauthclientId", "OAuth client ID")])
op("put", f"{base}/{{oauthclientId}}", tag="OAuth Clients", summary="Update OAuth client scopes", operation_id="updateOAuthClient", scope="oauth-clients-write", params=[ACCOUNT_ID, path_param("oauthclientId", "OAuth client ID")])

# Public records
op(
    "get",
    "/accounts/{accountId}/publicrecords",
    tag="Public Records",
    summary="Lookup company registry + signing combinations",
    operation_id="queryPublicRecords",
    scope="public-records-read",
    params=[
        ACCOUNT_ID,
        {"name": "country", "in": "query", "required": True, "schema": {"type": "string", "enum": ["SE", "DK", "NO", "FI"]}},
        {"name": "organization_number", "in": "query", "required": True, "schema": {"type": "string"}},
    ],
    description="Returns company info and authorized signatory combinations from public registry. Used before TPA creation.",
)

# TPAs
tpa_base = "/accounts/{accountId}/tpas"
op("get", tpa_base, tag="TPAs", summary="List TPAs", operation_id="listTpas", scope="account-tpas-read", params=[ACCOUNT_ID])
op(
    "post",
    tpa_base,
    tag="TPAs",
    summary="Create TPA",
    operation_id="createTpa",
    scope="account-tpas-write",
    params=[ACCOUNT_ID],
    description="Creates a Transaction Processing Authorization. Fetches company data from public registry, generates legal text snapshot, links card issuer.",
    body=json_body(ref("TpaCreate")),
    responses={"201": resp("201", "TPA created", ref("Tpa"))},
)
op("get", f"{tpa_base}/{{tpaId}}", tag="TPAs", summary="Get TPA", operation_id="getTpa", scope="account-tpas-read", params=[ACCOUNT_ID, path_param("tpaId", "TPA ID")])
op("delete", f"{tpa_base}/{{tpaId}}", tag="TPAs", summary="Delete TPA", operation_id="deleteTpa", scope="account-tpas-delete", params=[ACCOUNT_ID, path_param("tpaId", "TPA ID")])
op("get", f"{tpa_base}/{{tpaId}}/signeddocuments", tag="TPAs", summary="Download signed TPA PDF", operation_id="getTpaSignedDocument", scope="account-tpas-read", params=[ACCOUNT_ID, path_param("tpaId", "TPA ID")], responses={"200": {"description": "application/pdf"}})

# TPA Signatories
sig_base = f"{tpa_base}/{{tpaId}}/signatories"
op("get", sig_base, tag="TPA Signatories", summary="List signatories", operation_id="listTpaSignatories", scope="account-tpa-signatories-read", params=[ACCOUNT_ID, path_param("tpaId", "TPA ID")])
op(
    "post",
    sig_base,
    tag="TPA Signatories",
    summary="Add signatory + send signing email",
    operation_id="createTpaSignatory",
    scope="account-tpa-signatories-write",
    params=[ACCOUNT_ID, path_param("tpaId", "TPA ID")],
    description="Creates signatory with 40-char token. Queues email with signing link. Signatory signs via eID (BankID/MitID/etc) on web page — no API login required.",
    body=json_body(ref("TpaSignatoryCreate")),
    responses={"201": resp("201", "Signatory created, email queued", ref("TpaSignatory"))},
)
op(
    "put",
    f"{sig_base}/{{tpaSignatoryId}}",
    tag="TPA Signatories",
    summary="Update signatory email (unsigned only)",
    operation_id="updateTpaSignatory",
    scope="account-tpa-signatories-write",
    params=[ACCOUNT_ID, path_param("tpaId", "TPA ID"), path_param("tpaSignatoryId", "Signatory ID")],
    body=json_body({"type": "object", "required": ["email"], "properties": {"email": {"type": "string", "format": "email"}}}),
)
op(
    "delete",
    f"{sig_base}/{{tpaSignatoryId}}",
    tag="TPA Signatories",
    summary="Delete signatory (unsigned only)",
    operation_id="deleteTpaSignatory",
    scope="account-tpa-signatories-delete",
    params=[ACCOUNT_ID, path_param("tpaId", "TPA ID"), path_param("tpaSignatoryId", "Signatory ID")],
)
op(
    "get",
    f"{tpa_base}/{{tpaId}}/identities",
    tag="TPAs",
    summary="List identities (physical persons) on TPA",
    operation_id="listTpaIdentities",
    scope="account-tpa-identities-read",
    params=[
        ACCOUNT_ID,
        path_param("tpaId", "TPA ID"),
        {
            "name": "is_card_holder",
            "in": "query",
            "required": False,
            "description": "true = only with card holders, false = only without, omit = all",
            "schema": {"type": "boolean"},
        },
    ],
    description="Returns identities linked to this TPA's client — people who may already have cards. Use identity.id when creating card holders for instant onboarding (no email/eID wait).",
    responses={
        "200": resp(
            "200",
            "Paginated identities with cards and card_holders",
            {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer", "description": "Use as identity_id when creating card holder"},
                                "name": {"type": "string"},
                                "employee_id": {"type": "string", "nullable": True},
                                "cards": {"type": "array", "items": {"type": "object"}},
                                "card_holders": {"type": "array", "items": {"type": "object"}},
                            },
                        },
                    }
                },
            },
        )
    },
)

# Billings
bill_base = "/accounts/{accountId}/billings"
op("get", bill_base, tag="Billings", summary="List billings", operation_id="listBillings", scope="billings-read", params=[ACCOUNT_ID])
op(
    "post",
    bill_base,
    tag="Billings",
    summary="Create billing profile",
    operation_id="createBilling",
    scope="billings-write",
    params=[ACCOUNT_ID],
    body=json_body(ref("BillingCreate")),
    responses={"201": resp("201", "Billing created")},
)
op("get", f"{bill_base}/{{billingId}}", tag="Billings", summary="Get billing", operation_id="getBilling", scope="billings-read", params=[ACCOUNT_ID, path_param("billingId", "Billing ID")])
op("put", f"{bill_base}/{{billingId}}", tag="Billings", summary="Update billing", operation_id="updateBilling", scope="billings-write", params=[ACCOUNT_ID, path_param("billingId", "Billing ID")])

# Card issuers on account
ci_base = "/accounts/{accountId}/cardissuers"
op("get", ci_base, tag="Account Card Issuers", summary="List enabled card issuers", operation_id="listAccountCardIssuers", scope="account-card-issuers-read", params=[ACCOUNT_ID])
op("get", f"{ci_base}/{{cardIssuerId}}", tag="Account Card Issuers", summary="Check issuer enabled", operation_id="getAccountCardIssuer", scope="account-card-issuers-read", params=[ACCOUNT_ID, path_param("cardIssuerId", "Card issuer ID")])
op("post", f"{ci_base}/{{cardIssuerId}}", tag="Account Card Issuers", summary="Enable card issuer", operation_id="attachCardIssuer", scope="account-card-issuers-write", params=[ACCOUNT_ID, path_param("cardIssuerId", "Card issuer ID")], responses={"201": resp("201", "Issuer attached")})
op("delete", f"{ci_base}/{{cardIssuerId}}", tag="Account Card Issuers", summary="Disable card issuer", operation_id="detachCardIssuer", scope="account-card-issuers-delete", params=[ACCOUNT_ID, path_param("cardIssuerId", "Card issuer ID")])

# Organizations
org_base = "/accounts/{accountId}/organizations"
op("get", org_base, tag="Organizations", summary="List organizations", operation_id="listOrganizations", scope="organizations-read", params=[ACCOUNT_ID])
op(
    "post",
    org_base,
    tag="Organizations",
    summary="Create organization",
    operation_id="createOrganization",
    scope="organizations-write",
    params=[ACCOUNT_ID],
    body=json_body(ref("OrganizationCreate")),
    responses={"201": resp("201", "Organization created", ref("Organization"))},
)
op("get", f"{org_base}/{{organizationId}}", tag="Organizations", summary="Get organization", operation_id="getOrganization", scope="organizations-read", params=[ACCOUNT_ID, ORG_ID])
op("put", f"{org_base}/{{organizationId}}", tag="Organizations", summary="Update organization", operation_id="updateOrganization", scope="organizations-write", params=[ACCOUNT_ID, ORG_ID], body=json_body(ref("OrganizationCreate")))
op("delete", f"{org_base}/{{organizationId}}", tag="Organizations", summary="Delete organization", operation_id="deleteOrganization", scope="organizations-delete", params=[ACCOUNT_ID, ORG_ID])

# Card holders
ch_base = f"{org_base}/{{organizationId}}/cardholders"
op("get", ch_base, tag="Card Holders", summary="List card holders", operation_id="listCardHolders", scope="card-holders-read", params=[ACCOUNT_ID, ORG_ID])
op(
    "post",
    ch_base,
    tag="Card Holders",
    summary="Create card holder + send PDPC email",
    operation_id="createCardHolder",
    scope="card-holders-write",
    params=[ACCOUNT_ID, ORG_ID],
    description="Two onboarding modes: (A) provide email — PDPC email sent, user signs with eID, transactions flow after identification. (B) provide identity_id from GET .../tpas/{tpaId}/identities — instant identification, retroactive transactions dispatched immediately. Provide email OR identity_id, not both required.",
    body=json_body(ref("CardHolderCreate")),
    responses={"201": resp("201", "Card holder created", ref("CardHolder"))},
)
op("put", f"{ch_base}/{{cardHolderId}}", tag="Card Holders", summary="Update card holder", operation_id="updateCardHolder", scope="card-holders-write", params=[ACCOUNT_ID, ORG_ID, path_param("cardHolderId", "Card holder ID")], body=json_body(ref("CardHolderUpdate")))
op("delete", f"{ch_base}/{{cardHolderId}}", tag="Card Holders", summary="Delete card holder", operation_id="deleteCardHolder", scope="card-holders-delete", params=[ACCOUNT_ID, ORG_ID, path_param("cardHolderId", "Card holder ID")])

# Webhooks
wh_base = f"{org_base}/{{organizationId}}/webhooks"
op("get", wh_base, tag="Webhooks", summary="List webhooks", operation_id="listWebhooks", scope="webhooks-read", params=[ACCOUNT_ID, ORG_ID])
op(
    "post",
    wh_base,
    tag="Webhooks",
    summary="Create webhook",
    operation_id="createWebhook",
    scope="webhooks-write",
    params=[ACCOUNT_ID, ORG_ID],
    description="Creates webhook and runs challenge verification. Returns active=false until challenge passes.",
    body=json_body(ref("WebhookCreate")),
    responses={"201": resp("201", "Webhook created", ref("Webhook"))},
)
op("get", f"{wh_base}/{{webhookId}}", tag="Webhooks", summary="Get webhook", operation_id="getWebhook", scope="webhooks-read", params=[ACCOUNT_ID, ORG_ID, path_param("webhookId", "Webhook ID")])
op("put", f"{wh_base}/{{webhookId}}", tag="Webhooks", summary="Update webhook", operation_id="updateWebhook", scope="webhooks-write", params=[ACCOUNT_ID, ORG_ID, path_param("webhookId", "Webhook ID")], body=json_body(ref("WebhookCreate")))
op(
    "post",
    f"{wh_base}/{{webhookId}}/test/{{event}}",
    tag="Webhooks",
    summary="Send test webhook event",
    operation_id="testWebhook",
    scope="webhooks-write",
    params=[ACCOUNT_ID, ORG_ID, path_param("webhookId", "Webhook ID"), path_param("event", "Event name", "string")],
)
op("get", f"{wh_base}/{{webhookId}}/events", tag="Webhook Events", summary="List delivery log", operation_id="listWebhookEvents", scope="webhook-events-read", params=[ACCOUNT_ID, ORG_ID, path_param("webhookId", "Webhook ID")])

# Webhook headers
hdr_base = f"{wh_base}/{{webhookId}}/headers"
op("get", hdr_base, tag="Webhook Headers", summary="List custom headers", operation_id="listWebhookHeaders", scope="webhook-headers-read", params=[ACCOUNT_ID, ORG_ID, path_param("webhookId", "Webhook ID")])
op(
    "post",
    hdr_base,
    tag="Webhook Headers",
    summary="Add custom header",
    operation_id="createWebhookHeader",
    scope="webhook-headers-write",
    params=[ACCOUNT_ID, ORG_ID, path_param("webhookId", "Webhook ID")],
    body=json_body({"type": "object", "required": ["key", "value"], "properties": {"key": {"type": "string"}, "value": {"type": "string"}}}),
)
op("delete", f"{hdr_base}/{{headerId}}", tag="Webhook Headers", summary="Delete header", operation_id="deleteWebhookHeader", scope="webhook-headers-delete", params=[ACCOUNT_ID, ORG_ID, path_param("webhookId", "Webhook ID"), path_param("headerId", "Header ID")])

# Receipt scan
op(
    "post",
    "/accounts/{accountId}/receipts/scan",
    tag="Receipts",
    summary="OCR scan a receipt image",
    operation_id="scanReceipt",
    scope="receipts-write",
    params=[ACCOUNT_ID],
    body=json_body(
        {
            "type": "object",
            "required": ["receipt"],
            "properties": {
                "receipt": {"type": "string", "description": "Base64-encoded image. Recommended width ~800px."},
                "include": {"type": "array", "items": {"type": "string", "enum": ["line_items", "environmental_impact"]}},
            },
        }
    ),
)

# Transactions
op("get", "/transactions", tag="Transactions", summary="Query transactions (admin)", operation_id="listTransactions", scope="transactions-read")
op("get", "/transactions/{transactionId}", tag="Transactions", summary="Get transaction", operation_id="getTransaction", scope="transactions-read", params=[path_param("transactionId", "Transaction ID")])

# Open endpoints
op("get", "/open/legaltexts", tag="Open", summary="List available legal text languages", operation_id="listLegalTextLanguages", security=False, params=[{"name": "type", "in": "query", "required": True, "schema": {"type": "string", "enum": ["tpa", "pdpc", "account"]}}])

application_spec = {
    "openapi": "3.0.3",
    "info": {
        "title": "OpenCard Application API",
        "version": "1.0",
        "description": "EMS integration API. Generated from service.opencard.api source — not from legacy swagger.",
        "contact": {"email": "support@opencard.io"},
    },
    "servers": [
        {"url": "https://api.opencard.io/api/v1/application", "description": "Production"},
        {"url": "https://sandbox-api.opencard.io/api/v1/application", "description": "Sandbox"},
    ],
    "paths": paths,
    "components": {
        "securitySchemes": {
            "opencard_auth": {
                "type": "oauth2",
                "flows": {
                    "clientCredentials": {
                        "tokenUrl": "https://api.opencard.io/oauth/token",
                        "scopes": {
                            "me-read": "Read profile",
                            "me-write": "Write profile",
                            "accounts-read": "Read account",
                            "accounts-write": "Write account",
                            "oauth-clients-read": "Read OAuth clients",
                            "oauth-clients-write": "Write OAuth clients",
                            "public-records-read": "Read company registry",
                            "account-tpas-read": "Read TPAs",
                            "account-tpas-write": "Write TPAs",
                            "account-tpa-signatories-read": "Read TPA signatories",
                            "account-tpa-signatories-write": "Write TPA signatories",
                            "account-tpa-signatories-delete": "Delete TPA signatories",
                            "billings-read": "Read billings",
                            "billings-write": "Write billings",
                            "account-card-issuers-read": "Read account card issuers",
                            "account-card-issuers-write": "Write account card issuers",
                            "organizations-read": "Read organizations",
                            "organizations-write": "Write organizations",
                            "organizations-delete": "Delete organizations",
                            "card-holders-read": "Read card holders",
                            "card-holders-write": "Write card holders",
                            "card-holders-delete": "Delete card holders",
                            "webhooks-read": "Read webhooks",
                            "webhooks-write": "Write webhooks",
                            "webhook-events-read": "Read webhook events",
                            "webhook-headers-read": "Read webhook headers",
                            "webhook-headers-write": "Write webhook headers",
                            "webhook-headers-delete": "Delete webhook headers",
                            "receipts-write": "Scan receipts",
                            "transactions-read": "Read transactions",
                        },
                    }
                },
            }
        },
        "parameters": {
            "accountId": path_param("accountId", "Your OpenCard account ID"),
            "organizationId": path_param("organizationId", "Organization ID"),
        },
        "schemas": {
            "TpaCreate": {
                "type": "object",
                "required": ["card_issuer_id", "name", "country", "organization_number"],
                "properties": {
                    "card_issuer_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "country": {"type": "string", "enum": ["SE", "DK", "NO", "FI"]},
                    "organization_number": {"type": "string", "description": "SE: 10 digits, NO: 9, DK: 8, FI: XXXXXXX-X"},
                    "language": {"type": "string", "enum": ["sv", "no", "da", "en", "fi"]},
                },
            },
            "Tpa": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "account_id": {"type": "integer"},
                    "card_issuer_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "country": {"type": "string"},
                    "organization_number": {"type": "string"},
                    "activated": {"type": "boolean"},
                    "signatures_verified": {"type": "boolean"},
                    "signed_document_path": {"type": "string", "nullable": True},
                    "status": {"type": "string", "enum": ["pending-signatures", "pending-approval", "pending-activation", "activated"]},
                },
            },
            "TpaSignatoryCreate": {
                "type": "object",
                "required": ["email"],
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "name": {"type": "string"},
                    "country_code": {"type": "string"},
                    "phone_number": {"type": "string"},
                },
            },
            "TpaSignatory": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "email": {"type": "string"},
                    "name": {"type": "string"},
                    "tpa_id": {"type": "integer"},
                    "signed": {"type": "boolean"},
                    "signed_at": {"type": "string", "format": "date-time", "nullable": True},
                },
            },
            "OrganizationCreate": {
                "type": "object",
                "required": ["reference_id", "tpa_id"],
                "properties": {
                    "reference_id": {"type": "string", "description": "Your internal client ID"},
                    "tpa_id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            },
            "Organization": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "reference_id": {"type": "string"},
                    "tpa_id": {"type": "integer"},
                    "account_id": {"type": "integer"},
                },
            },
            "CardHolderCreate": {
                "type": "object",
                "required": ["reference_id"],
                "properties": {
                    "reference_id": {"type": "string"},
                    "email": {"type": "string", "format": "email", "description": "Required unless identity_id provided"},
                    "identity_id": {"type": "integer", "description": "Link existing identity from TPA"},
                    "skip_pdpc_email": {"type": "boolean", "default": False},
                    "language": {"type": "string", "enum": ["sv", "no", "da", "en", "fi"]},
                },
            },
            "CardHolderUpdate": {
                "type": "object",
                "required": ["email", "reference_id"],
                "properties": {
                    "reference_id": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "skip_pdpc_email": {"type": "boolean"},
                    "language": {"type": "string"},
                },
            },
            "CardHolder": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "reference_id": {"type": "string"},
                    "organization_id": {"type": "integer"},
                    "meta": {"type": "object", "description": "Includes signed, signed_at, pdpc_url, email delivery status"},
                },
            },
            "BillingCreate": {
                "type": "object",
                "required": ["name_display", "name_legal", "organization_number", "country"],
                "properties": {
                    "name_display": {"type": "string"},
                    "name_legal": {"type": "string"},
                    "organization_number": {"type": "string"},
                    "country": {"type": "string", "enum": ["SE", "DK", "NO", "FI"]},
                    "email_invoice": {"type": "string"},
                    "your_reference_invoice": {"type": "string"},
                },
            },
            "WebhookCreate": {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {"type": "string", "format": "uri"},
                    "secret": {"type": "string", "description": "Auto-generated if omitted"},
                    "enabled": {"type": "boolean", "default": True},
                    "authentication_type": {"type": "string", "enum": ["none", "basic", "oauth", "custom"]},
                    "basic_username": {"type": "string"},
                    "basic_password": {"type": "string"},
                    "custom_key": {"type": "string"},
                    "custom_value": {"type": "string"},
                    "card_holder_created": {"type": "boolean"},
                    "card_holder_identified": {"type": "boolean"},
                    "card_holder_signed_pdpc": {"type": "boolean"},
                    "card_holder_deleted": {"type": "boolean"},
                    "card_holder_email_delivered": {"type": "boolean"},
                    "card_holder_email_failed": {"type": "boolean"},
                    "card_transaction_authorized": {"type": "boolean"},
                    "card_transaction_cleared": {"type": "boolean"},
                    "card_transaction_deleted": {"type": "boolean"},
                    "card_transaction_invoiced": {"type": "boolean"},
                    "receipt_fetched": {"type": "boolean"},
                    "transaction_true_vat": {"type": "boolean"},
                    "transaction_line_items": {"type": "boolean"},
                    "aland_index": {"type": "boolean"},
                    "deedster": {"type": "boolean"},
                    "tpa_signed": {"type": "boolean"},
                },
            },
            "Webhook": {
                "allOf": [{"$ref": "#/components/schemas/WebhookCreate"}, {"type": "object", "properties": {"id": {"type": "integer"}, "active": {"type": "boolean"}, "organization_id": {"type": "integer"}}}],
            },
        },
    },
    "x-tagGroups": [
        {"name": "Profile", "tags": ["Me"]},
        {"name": "Account Setup", "tags": ["Accounts", "OAuth Clients", "Public Records", "Billings", "Account Card Issuers"]},
        {"name": "Legal", "tags": ["TPAs", "TPA Signatories"]},
        {"name": "Organizations", "tags": ["Organizations", "Card Holders", "Webhooks", "Webhook Events", "Webhook Headers"]},
        {"name": "Data", "tags": ["Transactions", "Receipts"]},
        {"name": "Open", "tags": ["Open"]},
    ],
}

# ─── OAuth spec ──────────────────────────────────────────────────────────────

oauth_spec = {
    "openapi": "3.0.3",
    "info": {"title": "OpenCard OAuth", "version": "1.0", "description": "Token endpoint for all OpenCard APIs."},
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
                "description": "Client credentials grant only. Request scopes as space-separated string.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "required": ["grant_type", "client_id", "client_secret", "scope"],
                                "properties": {
                                    "grant_type": {"type": "string", "enum": ["client_credentials"]},
                                    "client_id": {"type": "string"},
                                    "client_secret": {"type": "string"},
                                    "scope": {"type": "string", "description": "Space-separated scopes"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Token issued",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "token_type": {"type": "string", "example": "Bearer"},
                                        "expires_in": {"type": "integer"},
                                        "access_token": {"type": "string"},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        }
    },
}

# ─── Issuer API ──────────────────────────────────────────────────────────────

issuer_paths = {
    "/v1/issuers/zevoy/cards": {
        "get": {"tags": ["Zevoy"], "summary": "List cards", "operationId": "zevoyListCards", "security": [OAUTH_SECURITY]},
        "post": {
            "tags": ["Zevoy"],
            "summary": "Create card",
            "operationId": "zevoyCreateCard",
            "security": [{"opencard_auth": ["issuer-zevoy-cards-write"]}],
            "requestBody": json_body({"type": "object", "required": ["id", "last_four", "bin_number", "liability", "scheme", "identity"], "properties": {"id": {"type": "string"}, "last_four": {"type": "string"}, "bin_number": {"type": "string"}, "liability": {"type": "string"}, "scheme": {"type": "string"}, "identity": {"type": "object"}}}),
            "responses": {"201": resp("201", "Card created")},
        },
    },
    "/v1/issuers/zevoy/cards/{cardId}": {
        "get": {"tags": ["Zevoy"], "summary": "Get card", "operationId": "zevoyGetCard", "parameters": [path_param("cardId", "Zevoy external card ID", "string")], "security": [{"opencard_auth": ["issuer-zevoy-cards-read"]}]},
        "put": {"tags": ["Zevoy"], "summary": "Update card", "operationId": "zevoyUpdateCard", "parameters": [path_param("cardId", "Card ID", "string")], "security": [{"opencard_auth": ["issuer-zevoy-cards-write"]}]},
        "delete": {"tags": ["Zevoy"], "summary": "Delete card", "operationId": "zevoyDeleteCard", "parameters": [path_param("cardId", "Card ID", "string")], "security": [{"opencard_auth": ["issuer-zevoy-cards-delete"]}], "responses": {"204": resp("204", "Deleted")}},
    },
    "/v1/issuers/zevoy/cards/{cardId}/transaction_states": {
        "post": {
            "tags": ["Zevoy"],
            "summary": "Post transaction state",
            "operationId": "zevoyCreateTransactionState",
            "parameters": [path_param("cardId", "Card ID", "string")],
            "security": [{"opencard_auth": ["issuer-zevoy-transaction-states-write"]}],
            "requestBody": json_body(ref("IssuerTransactionState")),
            "responses": {"202": resp("202", "Accepted")},
        }
    },
    "/v1/issuers/nordea/cards/{cardId}/transaction_states": {
        "post": {
            "tags": ["Nordea"],
            "summary": "Post transaction state",
            "operationId": "nordeaCreateTransactionState",
            "parameters": [path_param("cardId", "OpenCard card ID")],
            "security": [{"opencard_auth": ["issuer-nordea-transaction-states-write"]}],
            "requestBody": json_body(ref("IssuerTransactionState")),
            "responses": {"202": resp("202", "Accepted")},
        }
    },
    "/v1/issuer/nordea/partner-event": {
        "post": {
            "tags": ["Nordea"],
            "summary": "Partner event batch (mTLS)",
            "operationId": "nordeaPartnerEvent",
            "description": "Requires mTLS. Headers: X-SSL-Client-CN, X-SSL-Client-Fingerprint",
            "security": [],
            "responses": {"201": resp("201", "Accepted")},
        }
    },
    "/v1/issuers/entercard/cards": {
        "post": {"tags": ["Entercard"], "summary": "Create card", "operationId": "entercardCreateCard", "security": [OAUTH_SECURITY], "responses": {"201": resp("201", "Created")}}
    },
    "/v1/issuers/entercard/cards/{cardId}": {
        "delete": {"tags": ["Entercard"], "summary": "Delete card", "operationId": "entercardDeleteCard", "parameters": [path_param("cardId", "Card ID")], "security": [OAUTH_SECURITY], "responses": {"204": resp("204", "Deleted")}}
    },
    "/v1/issuers/entercard/cards/{cardId}/transaction_states": {
        "post": {
            "tags": ["Entercard"],
            "summary": "Post transaction state",
            "operationId": "entercardCreateTransactionState",
            "parameters": [path_param("cardId", "Card ID")],
            "security": [OAUTH_SECURITY],
            "requestBody": json_body(ref("IssuerTransactionState")),
            "responses": {"202": resp("202", "Accepted")},
        }
    },
}

issuer_spec = {
    "openapi": "3.0.3",
    "info": {"title": "OpenCard Card Issuer API", "version": "1.0", "contact": {"email": "support@opencard.io"}},
    "servers": [
        {"url": "https://api.opencard.io/api", "description": "Production"},
        {"url": "https://sandbox-api.opencard.io/api", "description": "Sandbox"},
    ],
    "paths": issuer_paths,
    "components": {
        "securitySchemes": {
            "opencard_auth": {
                "type": "oauth2",
                "flows": {"clientCredentials": {"tokenUrl": "https://api.opencard.io/oauth/token", "scopes": {}}},
            }
        },
        "schemas": {
            "IssuerTransactionState": {
                "type": "object",
                "required": ["id", "state", "type", "original_amount", "original_currency", "accounting_amount", "accounting_currency", "exchange_rate", "purchase_merchant", "purchase_time", "purchase_country", "mcc_code", "merchant_number", "terminal_id", "rrn", "auth_code"],
                "properties": {
                    "id": {"type": "string"},
                    "state": {"type": "string", "enum": ["authorized", "cleared", "invoiced", "deleted"]},
                    "type": {"type": "string", "enum": ["CARD_PURCHASE", "CASH_WITHDRAWAL", "FEE_AND_DISCOUNT"]},
                    "invoice_number": {"type": "string", "nullable": True},
                    "original_amount": {"type": "number"},
                    "original_currency": {"type": "string", "minLength": 3, "maxLength": 3},
                    "accounting_amount": {"type": "number"},
                    "accounting_currency": {"type": "string", "minLength": 3, "maxLength": 3},
                    "exchange_rate": {"type": "number"},
                    "vat_rate": {"type": "number", "nullable": True},
                    "vat_amount": {"type": "number", "nullable": True},
                    "vat_currency": {"type": "string", "nullable": True},
                    "purchase_merchant": {"type": "string"},
                    "purchase_time": {"type": "string", "format": "date-time"},
                    "purchase_country": {"type": "string", "minLength": 2, "maxLength": 2},
                    "purchase_city": {"type": "string", "nullable": True},
                    "mcc_code": {"type": "string"},
                    "merchant_number": {"type": "string"},
                    "terminal_id": {"type": "string"},
                    "rrn": {"type": "string"},
                    "auth_code": {"type": "string"},
                },
            }
        },
    },
}

# ─── Receipt provider callback ───────────────────────────────────────────────

receipt_callback_spec = {
    "openapi": "3.0.3",
    "info": {"title": "OpenCard Receipt Provider Callback", "version": "1.0", "description": "Inbound webhook for receipt enrichers delivering matched receipts to OpenCard."},
    "servers": [{"url": "https://api.opencard.io/api"}, {"url": "https://sandbox-api.opencard.io/api"}],
    "paths": {
        "/v1/service/marcet/callback/{referenceId}": {
            "post": {
                "summary": "Deliver receipt enrichment",
                "operationId": "receiptProviderCallback",
                "parameters": [
                    path_param("referenceId", "Transaction reference ID", "string"),
                    {"name": "X-Event", "in": "header", "required": True, "schema": {"type": "string", "enum": ["CallbackRequestResolved", "CallbackRequestDeleted"]}},
                    {"name": "X-CallbackRequest-Id", "in": "header", "required": True, "schema": {"type": "string"}},
                    {"name": "X-Data-Signature", "in": "header", "required": True, "schema": {"type": "string", "description": "HMAC-SHA256 of raw body using shared secret"}},
                ],
                "requestBody": {"required": True, "content": {"application/xml": {"schema": {"type": "string"}}, "application/json": {"schema": {"type": "object"}}}},
                "responses": {"200": resp("200", "Accepted"), "403": resp("403", "Invalid signature")},
            }
        }
    },
}

# ─── Write files ─────────────────────────────────────────────────────────────

OUT.mkdir(parents=True, exist_ok=True)
files = {
    "application-api.json": application_spec,
    "oauth.json": oauth_spec,
    "issuer-api.json": issuer_spec,
    "receipt-provider-callback.json": receipt_callback_spec,
}

for name, spec in files.items():
    path = OUT / name
    with open(path, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"Wrote {path} ({len(spec.get('paths', {}))} paths)")
