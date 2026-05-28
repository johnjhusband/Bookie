I have enough research. Compiling the report now.

# Bookie Compliance Brief (US, 2026)

**Bottom line:** Single-owner LLC running it on yourself = minimal formal compliance. The moment Bookie touches anyone else's books, you become a GLBA "financial institution" and the rules get sharp.

**1. SOC 2 / ISO 27001** — Not required for self-use. SOC 2 Type II becomes table stakes the moment you have a paying client; ISO 42001 (AI management system) is the 2026 addition buyers now ask for alongside ISO 27001. For solo-LLC self-use: skip the audits, adopt the controls.

**2. Bank credentials** — Use Plaid (preferred) or MX. Both are SOC 2 + ISO 27001 and OAuth-first; for OAuth banks (Chase, BofA, Cap One, Wells, ~90% of major US banks) **no password is ever stored**. Avoid Yodlee for new builds (legacy screen-scraping fallback). Direct bank APIs require an LEI and bilateral agreements — not viable. CFPB Section 1033 is currently enjoined (Oct 2025); next deadline pushed to July 2026+.

**3. PII categories Bookie touches** — SSNs (1099s), EINs, bank account/routing, card PANs (if any), payroll. Under FTC Safeguards Rule (16 CFR 314, updated 2023+ amendments still in force): AES-256 at rest, TLS 1.2+ in transit, MFA on any system accessing customer info, encrypted logs, access logging. Under 5,000 consumers = exempt from written risk assessment/pen-test/IR plan but **not** from encryption/MFA/access controls.

**4. Records retention** — IRS Topic 305: 3-year baseline, **7 years** for bad debt/worthless securities/under-reporting &gt;25%; **employment tax 4 years**; payroll **4+ years**. States vary (CA FTB: 4 yr min, often longer). Defensible audit log = append-only, timestamped, tamper-evident (hash chain or WORM storage), captures who/what/when/why for every Bookie action, retained 7 years minimum.

**5. Tax-prep / advice boundary** — Bookkeeping (categorize, reconcile, prepare books, file sales tax, file payroll tax) does **not** require a CPA. Crosses the line when Bookie: signs returns, gives income-tax planning advice, represents you to IRS (Circular 230 territory — needs PTIN/EA/CPA/attorney). RIA registration only triggers if Bookie gives **investment** advice for compensation. Stay descriptive ("here's what your data shows") not prescriptive ("you should deduct X").

**6. AI-specific 2025-26** — **California SB 53** (Frontier AI, eff Jan 1 2026) — only applies to frontier-model developers, not you. **CCPA ADMT regs** (eff Jan 1 2026) — financial-services automated decisions on California consumers need pre-use notice + opt-out + risk assessment. **California AB 316** — kills the "the AI did it" defense. **NYDFS AI cybersecurity guidance** (May 2026) — applies if you ever serve NY-licensed entities. **EU AI Act** — irrelevant unless serving EU users. **FTC** is actively enforcing on AI misrepresentation.

**7. Liability** — Owner-operator first, always. Vendors (Plaid, model API, infra) disclaim via ToS. AB 316 means "Bookie did it" is not a defense. Carry E&amp;O / cyber liability ($1-2M) the moment you take a client.

**8. Security architecture** — Secrets in HashiCorp Vault (self-hosted on Hetzner) or AWS Secrets Manager; Plaid access tokens encrypted with envelope encryption; rotate API keys every 90 days; Bookie runs in segmented network with egress allowlist (Plaid, QBO, model API only); separate read-only and write-scoped credentials; **human-in-the-loop sign-off mandatory for any write to QBO, any tax filing, any payment**.

**9. Backup / DR** — Daily encrypted backups, 7-year retention, geographically separate (Hetzner FSN + HEL), tested restore quarterly. Must reproduce general ledger, source receipts, bank statements, prior returns within 30 days of an IRS request (IRC 6001).

**10. Agent commits a crime** — Misfiled sales tax = **owner liable** (state DOR doesn't care it was an AI). Mitigation: every external submission (sales tax, payroll tax, 1099s, bank transfers, QBO writes) gates on explicit human approval with a diff preview. Bookie proposes; John signs. Log the approval.

**Non-negotiables for v1 self-use:** OAuth-only bank connections, AES-256 + TLS 1.2+, MFA on everything, tamper-evident 7-year audit log, human-approval gate on every write, no investment/income-tax advice in the output.

Sources:
- [FTC Safeguards Rule / GLBA](https://www.ftc.gov/business-guidance/privacy-security/gramm-leach-bliley-act)
- [GLBA 2026 requirements guide](https://www.saltycloud.com/blog/glba-cybersecurity-requirements-complete-guide-2026/)
- [IRS Topic 305 Recordkeeping](https://www.irs.gov/taxtopics/tc305)
- [IRS How long to keep records](https://www.irs.gov/businesses/small-businesses-self-employed/how-long-should-i-keep-records)
- [Plaid OAuth docs](https://plaid.com/docs/link/oauth/)
- [Plaid open finance trust/security](https://plaid.com/blog/open-finance-trust-security/)
- [New California AI laws effective Jan 1 2026 (King &amp; Spalding)](https://www.kslaw.com/news-and-insights/new-state-ai-laws-are-effective-on-january-1-2026-but-a-new-executive-order-signals-disruption)
- [California AI regulations 2026 (CPRA/ADMT)](https://secureprivacy.ai/blog/california-ai-regulations-2026)
- [NYDFS AI cybersecurity guidance May 2026](https://www.dfs.ny.gov/industry-guidance/industry-letters/20260521-heightened-cybersecurity-risks-assoc-with-frontier-ai-models)
- [SOX + AI agents as financial risk](https://www.safepaas.com/blog/2026-when-every-ai-agent-becomes-a-sox-risk/)
- [AI compliance framework for financial services 2026](https://www.advisorengine.com/action-magazine/articles/navigating-ai-compliance-a-risk-based-framework-for-financial-services-in-2026)
- [Agentic AI liability gap (Clifford Chance)](https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2026/02/agentic-ai-and-the-liability-gap-your-contracts-may-not-cover.html)
- [Risks of AI for tax prep](https://www.davidovcpa.com/uncategorized/risks-of-using-ai-for-tax-preparation-what-taxpayers-must-know/)
- [Blurring the Lines (CPA Journal, Feb 2026)](https://www.cpajournal.com/2026/02/11/blurring-the-lines/)
- [Regulatory roadblocks facing AI accounting](https://thenumbersadvisors.com/ai-accounting/regulatory-roadblocks-facing-ai-accounting/)
