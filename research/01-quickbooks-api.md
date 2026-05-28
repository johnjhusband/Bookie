I have enough to deliver a concrete report.

# QuickBooks API Surface for Bookie (May 2026)

**1. Current entry point.** QBO is still the system of record. REST v3 at `https://quickbooks.api.intuit.com/v3/company/{realmId}/{entity}`, JSON, SQL-like `/query` endpoint. No public GraphQL. The big 2026 development: Intuit + Anthropic multi-year partnership announced Sept 2025 — businesses build custom agents using **Claude Agent SDK on the Intuit platform**, rolling out spring 2026. For a self-hosted agent like Bookie, the REST API is still the path; the Anthropic integration is a hosted runtime, not a replacement API.

**2. OAuth for headless workers.** OAuth 2.0 authorization code flow only — there is no client-credentials/service-account path. Access token = 1 hour, refresh token rotates on every use. Refresh-token policy changed Nov 2025: **max validity is now 5 years** (was effectively forever if used every 100 days). First `com.quickbooks.accounting`-scoped tokens issued post-Oct 2023 expire Oct 2028. Each refresh response now returns an `x_refresh_token_expires_in` field — use it to schedule re-consent. Bookie needs a one-time interactive auth from John, then a persistent refresh loop, with a re-consent UX every ~5 years (or sooner if revoked / password reset / MFA event). Scope: `com.quickbooks.accounting` (plus `com.intuit.quickbooks.payment` if processing payments).

**3. Sandbox.** Each developer account auto-provisions sandbox companies (up to 5) at `https://sandbox-quickbooks.api.intuit.com/v3/...`, pre-seeded with sample data. Identical rate limits. Caveats: webhook delivery and some error codes differ from prod.

**4. Read/write surface.** Full CRUD for Invoice, Bill, BillPayment, JournalEntry, Account, Customer, Vendor, Item, Payment, Purchase, PurchaseOrder, Deposit, Transfer, CreditMemo, SalesReceipt, RefundReceipt, Estimate, TimeActivity, Attachable (file attachments via multipart). Reports endpoint is read-only (P&amp;L, Balance Sheet, etc.). Things the agent CANNOT do via API: bank-feed connection setup, payroll setup, 1099 e-filing initiation, sales-tax agency setup, user/permission management, closing-the-books password, some company-preference toggles, and most onboarding flows. John will need the UI a few times a year (year-end close, new bank connections, tax filings).

**5. Rate limits.** 500 req/min per realm, 10 concurrent, batch endpoint = 40 req/min (30 ops/batch), heavy report endpoints ~200/min. 429s carry `Retry-After`. Use the batch endpoint and exponential backoff with jitter. Idempotency: pass a `RequestId` query param on writes (UUID) — Intuit dedupes within ~24h.

**6. Pricing.** App Partner Program (live July 2025): tiers Builder / Silver / Gold / Platinum, $0–$4,500/mo. **Core (data-in: create/update) calls are free and unlimited; CorePlus (data-out: read/query/reports) is metered** — ~$0.25 per 1,000 calls at Platinum. Builder tier has no program fee; Silver+ have flat monthly fees. For a single-tenant agent on John's books, Builder tier with the included CorePlus credits is almost certainly enough. There is no separate "AI agent" API tier — agentic access goes through the same App Partner pricing.

**7. Recent breaking changes.** (a) Refresh-token 5-year cap (Nov 2025). (b) **Webhook payload migrates to CloudEvents format, mandatory by May 15, 2026** — payloads now batch events across multiple companies per notification. (c) App Partner Program metering went live July 28, 2025.

**8. Webhooks.** Real-time push, no polling needed. Subscribe in the developer portal to Create/Update/Delete (also Void/Merge) on: Account, Bill, BillPayment, Budget, Class, CreditMemo, Customer, Deposit, Employee, Estimate, Invoice, Item, JournalEntry, Payment, Purchase, PurchaseOrder, RefundReceipt, SalesReceipt, TimeActivity, Transfer, Vendor, VendorCredit. Payload contains only `{entity, id, operation, realmId}` — Bookie must fetch the changed record. HMAC-SHA256 signature in `intuit-signature` header. Bookie needs a public HTTPS endpoint.

**9. SDKs.** Official Intuit SDKs: Java, .NET, PHP, Node.js (`node-quickbooks` ecosystem + `intuit-oauth`), Python (`python-quickbooks` + `intuit-oauth`), Ruby. No official TypeScript SDK — community `Nytely-Official/quickbooks-api` exists. For Bookie, **Python `intuit-oauth` + `python-quickbooks`** is the cleanest; the official `intuit-developer-nodejs` starter is the Node.js equivalent. SDKs are thin REST wrappers; you'll still hand-write the webhook handler and batch logic.

**10. Official agentic programs.** Intuit Enterprise Suite ships first-party AI agents (Accounting Agent, Payments Agent, etc.) — those are Intuit's product, not an API for third parties. The developer-facing agentic story is the **Anthropic partnership / Claude Agent SDK on Intuit platform (spring 2026)** plus the App Partner Program tiers. No dedicated "AI agent sandbox grant" program exists yet beyond the standard sandbox.

**Concrete recommendation for Bookie:** Builder-tier App Partner registration → Python SDK (`intuit-oauth` + `python-quickbooks`) → one-time interactive OAuth from John → persistent refresh loop watching `x_refresh_token_expires_in` → public webhook endpoint on CloudEvents format → batch endpoint for bulk reads → flag the ~handful of UI-only operations for John.

Sources:
- [QBO Accounting API docs (Intuit)](https://developer.intuit.com/app/developer/qbo/docs/develop)
- [REST API features / schema](https://developer.intuit.com/app/developer/qbo/docs/learn/rest-api-features)
- [Platform release notes](https://developer.intuit.com/app/developer/qbo/docs/release-notes/platform-release-notes)
- [OAuth 2.0 setup](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- [OAuth/auth FAQ](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/faq)
- [Refresh token validity policy (5-year cap)](https://help.developer.intuit.com/s/article/Validity-of-Refresh-Token)
- [Refresh token policy change announcement (Nov 2025)](https://blogs.intuit.com/2025/11/12/important-changes-to-refresh-token-policy)
- [Webhooks docs](https://developer.intuit.com/app/developer/qbo/docs/develop/webhooks)
- [Webhooks CloudEvents migration (May 2026 deadline)](https://blogs.intuit.com/2025/11/12/upcoming-change-to-webhooks-payload-structure/)
- [API call limits and throttling](https://help.developer.intuit.com/s/article/API-call-limits-and-throttling)
- [App Partner Program FAQ](https://developer.intuit.com/app/developer/qbo/docs/get-started/partner-faq)
- [App Partner platform service fees](https://help.developer.intuit.com/s/article/platform-service-fees)
- [API classification (Core vs CorePlus)](https://help.developer.intuit.com/s/article/API-classification-for-the-Intuit-App-Partner-Program)
- [Intuit + Anthropic partnership announcement](https://investors.intuit.com/news-events/press-releases/detail/1305/intuit-and-anthropic-partner-to-bring-trusted-financial-intelligence-and-custom-ai-agents-to-consumers-and-businesses)
- [Intuit AI agents product page](https://www.intuit.com/enterprise/ai-agents/)
- [Node.js SDK starter (official)](https://github.com/intuit/intuit-developer-nodejs)
- [JournalEntry API reference](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/journalentry)
