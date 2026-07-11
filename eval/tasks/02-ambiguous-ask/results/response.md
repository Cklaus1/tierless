# Data Export — Requirements Clarification

Thanks for flagging this. "Let people export their data" is a big umbrella — there are several very different ways to build this, and the right approach depends on a few specifics. Before I start designing anything, I need to understand:

## 1. What data exactly?
- The entire account's data (all dashboards, all reports, raw events)?
- Just the current dashboard view the user is looking at?
- A specific report or metric?
- Raw event-level data, or already-aggregated numbers?

The scope here swings the build by an order of magnitude.

## 2. What format and delivery mechanism?
- A simple CSV download button on the dashboard?
- Excel (.xlsx)?
- PDF report (formatted, for sharing)?
- JSON API endpoint (for programmatic access)?
- Scheduled email (e.g., "send me a weekly CSV every Monday")?
- Push to their data warehouse (S3, BigQuery, Snowflake)?

These are fundamentally different features. A CSV button is a few hours. Warehouse push is a multi-week integration project.

## 3. Who can export — and whose data?
- Any logged-in user, or only admins?
- Can a user on Org A export Org B's data? (This is an authorization/security boundary I need to get right.)
- Per-role permissions (e.g., analysts can export, viewers cannot)?

## 4. How much data are we talking about?
- Are we talking about hundreds/thousands of rows (easy synchronous download)?
- Or millions of rows (need async job + email notification when ready)?

This alone determines whether I build a simple endpoint or an async job pipeline.

## 5. What's the driver here?
- Is a specific customer threatening to churn without this?
- Is this a compliance/GDPR data-portability requirement?
- Or is it a general "nice to have" feature request?

The "why" tells me what "done" actually looks like.

## My proposed approach given the end-of-week deadline

If you need this shipped by Friday, I'd propose we start with the smallest useful version:

**MVP**: A CSV download button on each dashboard view, available to all logged-in users, limited to the currently visible data (no raw event export), synchronous download, with proper org-level authorization checks. This is a 1-2 day build.

Then we can iterate on the harder stuff (scheduled exports, warehouse push, raw data export) after the MVP ships.

Can you tell me which of the above questions matter most right now? That'll let me scope this properly.