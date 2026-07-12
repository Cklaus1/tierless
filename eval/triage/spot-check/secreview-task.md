# Security review: file-export endpoints

You are reviewing a pull request that adds a "document export" feature to an existing internal-facing SaaS app (Node/Express, Postgres via `pg`). Users can export one of their saved reports to a file and download it, and admins can preview any report. The team says "it's fine, it's behind our SSO / VPN and only employees use it."

Review the diff below. Produce a security review that, for each real finding, gives: `file:line`, the vulnerability, a severity (critical/high/medium/low), a **concrete exploit path** (the actual request/steps an attacker would take), and a specific fix. Then give a one-line verdict: SHIP / FIX FIRST / BLOCKED. Do not recite categories that don't apply, and don't mark everything critical.

Assume `requireLogin` (used on the router) only verifies the session is authenticated; it sets `req.user = { id, role }`. The `reports` table has columns `id, owner_id, title, body`.

```js
// routes/export.js
 1  const express = require('express');
 2  const { execSync } = require('child_process');
 3  const fs = require('fs');
 4  const path = require('path');
 5  const db = require('../db'); // node-postgres pool
 6  const router = express.Router();
 7
 8  const EXPORT_DIR = '/var/app/exports';
 9  const PANDOC_TOKEN = 'pk_live_8f3a1c9d2b4e6f70'; // license key for pandoc cloud
10
11  router.use(requireLogin);
12
13  // Export a report to a file on disk, return a download id
14  router.post('/reports/:id/export', async (req, res) => {
15    const { id } = req.params;
16    const { format } = req.body; // 'pdf' | 'html' | 'docx'
17    const r = await db.query(`SELECT * FROM reports WHERE id = ${id}`);
18    if (r.rows.length === 0) return res.status(404).send('not found');
19    const report = r.rows[0];
20
21    const outName = `${report.title}.${format}`;
22    const outPath = path.join(EXPORT_DIR, outName);
23
24    // render markdown body to the requested format via pandoc
25    fs.writeFileSync('/tmp/in.md', report.body);
26    execSync(`pandoc /tmp/in.md -o "${outPath}" --token ${PANDOC_TOKEN}`);
27
28    res.json({ download: outName });
29  });
30
31  // Download a previously exported file
32  router.get('/download', async (req, res) => {
33    const { name } = req.query;
34    const full = path.join(EXPORT_DIR, name);
35    res.sendFile(full);
36  });
37
38  // Admin-only: preview any report's raw body in the browser
39  router.get('/reports/:id/preview', async (req, res) => {
40    const r = await db.query('SELECT * FROM reports WHERE id = $1', [req.params.id]);
41    if (r.rows.length === 0) return res.status(404).send('not found');
42    res.send(`<div class="report">${r.rows[0].body}</div>`);
43  });
44
45  module.exports = router;
```

```js
// client/report.js  (runs in the browser)
 1  async function exportReport(id, format) {
 2    if (currentUser.role !== 'admin') { hidePreviewButton(); }
 3    const res = await fetch(`/api/reports/${id}/export`, {
 4      method: 'POST',
 5      headers: { 'Content-Type': 'application/json' },
 6      body: JSON.stringify({ format }),
 7    });
 8    return res.json();
 9  }
```
