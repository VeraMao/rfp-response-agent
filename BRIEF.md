# Case: RFP Response Agent

Northwind Analytics sells a B2B analytics platform. When a prospect sends an RFP
(Request for Proposal), sales, product, security and legal spend 2-3 weeks finding
answers in scattered documents and writing a response. Leadership wants that cut to a day.

Build a prototype that takes an RFP and produces a draft response a sales rep can review.

You have:
- data/rfps/                 RFPs from prospects (Meridian Health, Harbor Bank, Lumen Retail)
- data/knowledge/            internal company documents (the only source of truth)

Requirements:
- Every claim in the draft must be backed by a company document.
- Never claim a capability the documents don't support.
- A human approves the draft before anything is sent.

Time: ~3.5 hours build, then a 10-minute presentation.
