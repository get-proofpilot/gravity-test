/* ═══════════════════════════════════════════════════════
   PROOFPILOT AGENCY HUB — script.js
   Data models, rendering, terminal typewriter, agent toggle
═══════════════════════════════════════════════════════ */

/* ── DATA MODELS ── */

const CLIENTS = [
  { id: 1,  name: 'All Thingz Electric',           domain: 'allthingzelectric.com',          plan: 'Starter',    score: 74, trend: '+5',  avgRank: 9.2,  lastJob: '1 hr ago',    status: 'active',   color: '#7C3AED', initials: 'AE' },
  { id: 2,  name: 'Adam Levinstein Photography',   domain: 'adamlevinstein.com',             plan: 'Starter',    score: 62, trend: '+1',  avgRank: 14.1, lastJob: '2 hr ago',    status: 'active',   color: '#7C3AED', initials: 'AL' },
  { id: 3,  name: 'Dolce Electric',                domain: 'dolceelectric.com',              plan: 'Starter',    score: 69, trend: '→0',  avgRank: 11.8, lastJob: '3 hr ago',    status: 'active',   color: '#7C3AED', initials: 'DE' },
  { id: 4,  name: 'Integrative Sports and Spine',  domain: 'integrativesportsandspine.com',  plan: 'Agency',     score: 81, trend: '+6',  avgRank: 7.3,  lastJob: '30 min ago',  status: 'active',   color: '#0D9488', initials: 'IS' },
  { id: 5,  name: 'Saiyan Electric',               domain: 'saiyanelectric.com',             plan: 'Starter',    score: 71, trend: '+2',  avgRank: 10.6, lastJob: '4 hr ago',    status: 'active',   color: '#7C3AED', initials: 'SE' },
  { id: 6,  name: 'Cedar Gold Group',              domain: 'cedargoldgroup.com',             plan: 'Agency',     score: 85, trend: '+4',  avgRank: 6.9,  lastJob: '1 hr ago',    status: 'active',   color: '#0D9488', initials: 'CG' },
  { id: 7,  name: 'Pelican Coast Electric',        domain: 'pelicancoastelectric.com',       plan: 'Starter',    score: 67, trend: '-1',  avgRank: 13.4, lastJob: '5 hr ago',    status: 'active',   color: '#7C3AED', initials: 'PC' },
  { id: 8,  name: 'ProofPilot',                    domain: 'proofpilot.com',                 plan: 'Agency',     score: 94, trend: '+8',  avgRank: 4.1,  lastJob: '12 min ago',  status: 'active',   color: '#0051FF', initials: 'PP' },
  { id: 9,  name: 'Xsite Belize',                  domain: 'xsitebelize.com',                plan: 'Starter',    score: 58, trend: '+3',  avgRank: 16.2, lastJob: '1 day ago',   status: 'active',   color: '#7C3AED', initials: 'XB' },
  { id: 10, name: 'Power Route Electric',          domain: 'powerrouteelectric.com',         plan: 'Starter',    score: 73, trend: '+4',  avgRank: 10.1, lastJob: '3 hr ago',    status: 'active',   color: '#7C3AED', initials: 'PR' },
  { id: 11, name: 'Alpha Property Management',     domain: 'alphapropertymgmt.com',          plan: 'Agency',     score: 79, trend: '+2',  avgRank: 8.5,  lastJob: '2 hr ago',    status: 'active',   color: '#7C3AED', initials: 'AP' },
  { id: 12, name: 'Trading Academy',               domain: 'tradingacademy.com',             plan: 'Enterprise', score: 91, trend: '+5',  avgRank: 5.0,  lastJob: '20 min ago',  status: 'active',   color: '#7C3AED', initials: 'TA' },
  { id: 13, name: 'Youth Link',                    domain: 'youthlink.org',                  plan: 'Starter',    score: 55, trend: '→0',  avgRank: 18.7, lastJob: '2 days ago',  status: 'inactive', color: '#F59E3B', initials: 'YL' },
  { id: 14, name: 'LAF Counseling',                domain: 'lafcounseling.com',              plan: 'Starter',    score: 61, trend: '+1',  avgRank: 15.3, lastJob: '1 day ago',   status: 'active',   color: '#EA580C', initials: 'LC' },
];

const WORKFLOWS = [
  /* ── SEO ANALYSIS ── */
  { id: 'website-seo-audit', icon: '🔍', title: 'Website & SEO Audit',
    desc: 'Full technical SEO audit — performance, structure, local signals, backlinks, and a ranked action list.',
    time: '~8 min', status: 'active', skill: 'website-seo-audit', category: 'seo',
    preview: '# SEO Audit: All Thingz Electric — Chandler, AZ\n\n**Overall Score: 63/100** — Est. 12–18 leads/month lost to ranking gaps.\n\n## Critical Issues\n- "Panel upgrade Chandler AZ" — Position #23 (first page achievable in 90 days)\n- GBP missing 8 service categories vs. top competitor\n- 0 backlinks from local Chandler business directories\n\n## Top Priority Action\nCreate 3 service pages targeting underranked commercial keywords. Estimated ROI: 8–12 inbound calls/month within 60 days.' },
  { id: 'prospect-audit', icon: '🎯', title: 'Prospect SEO Market Analysis',
    desc: 'Sales-focused market analysis for proposals — shows the revenue gap, names competitors, and closes the deal.',
    time: '~8 min', status: 'active', skill: 'prospect-audit', category: 'seo',
    preview: '# Market Analysis: Steadfast Plumbing — Gilbert, AZ\n\n**Revenue Gap: ~$28,000/month** — Top-ranked competitor captures 3× the lead volume.\n\n## Who\'s Winning\nMesa Plumbing Pros ranks #1 for 14 commercial keywords including "water heater replacement Gilbert."\n\n## Your Opportunity\n8 high-value keywords with <45 difficulty — achievable page 1 rankings within 60 days.\n\n**Closing Insight:** 340 people searched "emergency plumber Gilbert AZ" last month. You\'re not appearing for any of them.' },
  { id: 'keyword-gap', icon: '📊', title: 'Keyword Gap Analysis',
    desc: 'Find every keyword competitors rank for that you don\'t — sorted by revenue opportunity.',
    time: '~6 min', status: 'active', skill: 'keyword-gap', category: 'seo',
    preview: '# Keyword Gap Report: All Thingz Electric vs. 3 Competitors\n\n**47 untapped keywords** your top competitors rank for — you rank for 0.\n\nTop Opportunities by Revenue:\n- "electrical panel upgrade chandler" — 210/mo searches, Difficulty 38, Est. $4,200/mo\n- "ev charger installation scottsdale" — 170/mo searches, Difficulty 31, Est. $3,400/mo\n- "electrical inspection chandler az" — 140/mo searches, Difficulty 27, Est. $2,100/mo\n\n**Priority Plan:** 3 service pages + 2 blog posts covers 74% of total opportunity.' },
  { id: 'seo-strategy-sheet', icon: '📋', title: 'SEO Strategy Spreadsheet',
    desc: '14-tab SEO strategy workbook — keyword clusters, competitor gaps, content calendar, and priority matrix.',
    time: '~4 min', status: 'soon', category: 'seo' },
  { id: 'backlink-outreach', icon: '🔗', title: 'Backlink Outreach',
    desc: 'Prospect link-building opportunities and generate personalized outreach emails at scale.',
    time: '~12 min', status: 'soon', category: 'seo' },
  { id: 'schema-generator', icon: '🧩', title: 'Schema Generator',
    desc: 'Auto-generate structured data markup for target pages — local business, FAQ, service, and article schemas.',
    time: '~2 min', status: 'soon', category: 'seo' },
  /* ── CONTENT CREATION ── */
  { id: 'seo-blog-post', icon: '✍️', title: 'SEO Blog Post',
    desc: 'Publish-ready blog post targeting informational keywords — key takeaways, FAQ, local CTA, and meta description.',
    time: '~5 min', status: 'active', skill: 'seo-blog-post', category: 'content',
    preview: 'META: How much does it cost to rewire a house in Phoenix? Real ranges ($8,000–$22,000), what drives price, and when to call a licensed Phoenix electrician.\n\n# How Much Does It Cost to Rewire a House in Phoenix, AZ?\n\n## Key Takeaways\n- Whole-home rewire in Phoenix: **$8,000–$22,000** (1,500–3,000 sq ft)\n- Permit required in Maricopa County — expect $180–$420\n- Timeline: 3–5 days for most homes\n- Summer timing matters: Phoenix heat accelerates insulation degradation\n\nIf your home was built before 1985, there\'s a reasonable chance your wiring has been sending warning signs for months...' },
  { id: 'service-page', icon: '⚡', title: 'Service Page',
    desc: 'Conversion-optimized page targeting high-intent "[service] [city]" keywords — built to rank and convert.',
    time: '~4 min', status: 'active', skill: 'service-page', category: 'content',
    preview: '# Electrical Panel Upgrade in Chandler, AZ\n\nYour circuit breaker tripping again? **A panel upgrade stops the problem at the source** — and in Chandler\'s heat-heavy summers, an undersized panel isn\'t just inconvenient, it\'s a fire risk.\n\n**Call for a free estimate: (480) 555-0182**\n\n## What\'s Included in Every Panel Upgrade\n- 200-amp service upgrade with permits pulled same day\n- All circuits mapped, labeled, and load-balanced\n- City of Chandler inspection coordinated — we handle scheduling\n- Same-day power restoration in most cases\n\n**Price range: $1,800–$3,200** depending on panel size and existing wiring.' },
  { id: 'location-page', icon: '📍', title: 'Location Page',
    desc: 'Geo-targeted page for "[service] [city]" rankings — genuinely local, not templated.',
    time: '~4 min', status: 'active', skill: 'location-page', category: 'content',
    preview: '# Plumbing Repair in Mesa, AZ | Chandler Plumbing Pros\n\nMesa\'s housing stock tells a story. **Homes in the Val Vista Lakes area** were built in the late 1980s — after 35 years, that original copper plumbing is at the stage where pinhole leaks become a Tuesday problem.\n\nBased in Chandler, we\'ve been serving Mesa homeowners for 12 years. Licensed, insured, and familiar with the specific challenges that come with **east Mesa\'s hard water** and the aging PVC systems common in Dobson Ranch.\n\n**Call for same-day service: (480) 555-0182**\n\n## Plumbing Services in Mesa\n- Emergency leak repair (2-hour response for Mesa residents)\n- Water heater replacement and tankless conversion...' },
  { id: 'home-service-content', icon: '🏠', title: 'Home Service SEO Content',
    desc: 'SEO articles for electricians, plumbers, HVAC, and other home service businesses. Built for local rank.',
    time: '~5 min', status: 'active', skill: 'home-service-seo-content', category: 'content',
    preview: '# 7 Signs Your Home Needs an Electrical Panel Upgrade\n\nMost homeowners in Chandler don\'t think about their electrical panel until something goes wrong. By then, the warning signs had been there for months — tripping breakers, flickering lights, outlets that stopped working.\n\nHere\'s what to look for, and when to call a licensed electrician:\n\n**1. Breakers That Keep Tripping**\nA breaker trips once — that\'s it doing its job. If the same breaker trips twice a week, the circuit is consistently overloaded. This is the most common panel issue in Chandler homes built before 2000...' },
  { id: 'seo-blog-generator', icon: '✍️', title: 'SEO Blog Generator',
    desc: 'Full SEO blog post workflow for service businesses — keyword-targeted, structured, and ready to publish.',
    time: '~6 min', status: 'soon', category: 'content' },
  { id: 'content-strategy-sheet', icon: '📋', title: 'Content Strategy Spreadsheet',
    desc: 'Content ecosystem mapping with psychographic profiles, funnel stages, and distribution plan per channel.',
    time: '~5 min', status: 'soon', category: 'content' },
  { id: 'google-ads-copy', icon: '📣', title: 'Google Ads Copy',
    desc: 'High-converting search ad copy — headlines, descriptions, and extensions for service-based campaigns.',
    time: '~4 min', status: 'soon', category: 'content' },
  /* ── BUSINESS TOOLS ── */
  { id: 'proposals', icon: '📄', title: 'Client Proposals',
    desc: 'Branded marketing proposals ready to send — scoped deliverables, pricing, and ProofPilot positioning built in.',
    time: '~3 min', status: 'soon', category: 'business' },
  { id: 'monthly-report', icon: '📈', title: 'Monthly Client Report',
    desc: 'White-label client report — rankings, traffic wins, and recommendations bundled to send.',
    time: '~3 min', status: 'soon', category: 'business' },
  { id: 'pnl-statement', icon: '💰', title: 'P&L Statement',
    desc: 'Monthly profit & loss statement generator — structured financials formatted and ready for review.',
    time: '~3 min', status: 'soon', category: 'business' },
  { id: 'brand-styling', icon: '🎨', title: 'Brand Styling',
    desc: 'Applies ProofPilot brand standards to .docx and .xlsx deliverables — fonts, colors, headers, and polish.',
    time: '~2 min', status: 'soon', category: 'business' },
  /* ── DEV & CREATIVE ── */
  { id: 'frontend-design', icon: '🖥️', title: 'Frontend Interface Builder',
    desc: 'Production-grade UI components and pages — distinctive design, clean code, no generic AI aesthetics.',
    time: '~8 min', status: 'soon', category: 'dev' },
  { id: 'lovable-prompting', icon: '⚡', title: 'Lovable App Builder',
    desc: 'Expert Lovable.dev prompting to build full apps — structured flows that get clean, working results fast.',
    time: '~5 min', status: 'soon', category: 'dev' },
  { id: 'property-mgmt-strategy', icon: '🏢', title: 'Property Mgmt Strategy',
    desc: 'Website and SEO strategy for property management companies — local presence, lead gen focus, and conversion flow.',
    time: '~6 min', status: 'soon', category: 'dev' },
  { id: 'competitor-gap', icon: '🎯', title: 'Competitor Gap Analysis',
    desc: 'Find keywords competitors rank for that you don\'t — instant opportunity list with difficulty scores.',
    time: '~5 min', status: 'soon', category: 'dev' },
];

const JOBS = [];
const LOG_ENTRIES = [];
const REPORTS = [];
const CONTENT = [];

// Content Library — persists workflow outputs indexed by client
// Each item: {id, job_id, client_name, client_id, workflow_id, workflow_title, created_at, has_docx, preview}
let CONTENT_ITEMS = [];

/* job progress simulation */
const jobProgresses = {};
JOBS.forEach(j => { jobProgresses[j.id] = j.pct; });

/* ── CONFIG ── */
const API_BASE = '';

/* ── VIEW ROUTING ── */
let currentView = 'dashboard';
let selectedWorkflow = null;
let agentRunning = true;
let activeClientId = null;

/* ── STREAMING STATE ── */
let terminalStreaming = false;
let streamDiv = null;
let sseBuffer = '';
let currentJobId = null;
let activeTerminalEl = null;
let monitorJobId = null;
const activeSSEJobs = new Set();

function showView(viewId) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const el = document.getElementById(`view-${viewId}`);
  if (el) el.classList.add('active');

  const nav = document.getElementById(`nav-${viewId}`);
  if (nav) nav.classList.add('active');

  const title = document.getElementById('pageTitle');
  const titles = {
    dashboard: 'Dashboard', workflows: 'Run Workflows', clients: 'Clients',
    jobs: 'Agent Tasks', reports: 'Reports', content: 'Content',
    logs: 'Activity Log', ads: 'Ad Studio', campaigns: 'Campaigns',
    'client-hub': 'Client Hub'
  };
  if (title) title.textContent = titles[viewId] || viewId;

  currentView = viewId;

  if (viewId === 'dashboard') renderDashboard();
  if (viewId === 'workflows') renderWorkflows();
  if (viewId === 'clients') renderClients();
  if (viewId === 'jobs') renderJobs('all');
  if (viewId === 'reports') renderReports();
  if (viewId === 'content') { syncContentLibrary(); }
  if (viewId === 'logs') renderLogs();
  if (viewId === 'ads') renderAds();
  if (viewId === 'client-hub') renderClientHub();
}

function showJobMonitor(jobId) {
  const job = JOBS.find(j => j.id === jobId);
  if (!job) return;

  monitorJobId = jobId;

  document.getElementById('jmJobId').textContent = job.id;
  document.getElementById('jmWfName').textContent = job.wf;
  document.getElementById('jmClient').textContent = job.client;
  updateMonitorStatus(job.status);

  const doneBar = document.getElementById('jmDoneBar');
  if (doneBar) doneBar.style.display = 'none';

  // Switch view manually so we can keep nav-jobs highlighted
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const el = document.getElementById('view-job-monitor');
  if (el) el.classList.add('active');
  document.getElementById('nav-jobs')?.classList.add('active');
  const title = document.getElementById('pageTitle');
  if (title) title.textContent = `${job.id} — ${job.wf}`;
  currentView = 'job-monitor';

  activeTerminalEl = document.getElementById('monitorTerminal');
}

function updateMonitorStatus(status) {
  const badge = document.getElementById('jmStatusBadge');
  if (!badge) return;
  badge.textContent = status.toUpperCase();
  badge.className = `jm-status-badge ${status}`;
}

function updateClientsBadge() {
  const badge = document.getElementById('navBadgeClients');
  if (badge) badge.textContent = CLIENTS.filter(c => c.status === 'active').length;
}

function updateJobsBadge() {
  const running = JOBS.filter(j => j.status === 'running').length;
  const badge = document.getElementById('navBadgeJobs');
  if (!badge) return;
  if (running > 0) {
    badge.textContent = `${running} LIVE`;
    badge.classList.add('nav-badge-live');
  } else {
    badge.textContent = JOBS.length;
    badge.classList.remove('nav-badge-live');
  }
}

/* ── DASHBOARD ── */
function renderDashboard() {
  // KPIs
  const activeClients = CLIENTS.filter(c => c.status === 'active').length;
  const activeTasks   = JOBS.filter(j => j.status === 'running').length;
  const workflowsRun  = JOBS.length;
  const docsGenerated = JOBS.filter(j => j.status === 'completed').length;

  const kpiEl = id => document.getElementById(id);
  if (kpiEl('kpiActiveClients')) kpiEl('kpiActiveClients').textContent = activeClients;
  if (kpiEl('kpiActiveTasks'))   kpiEl('kpiActiveTasks').textContent   = activeTasks;
  if (kpiEl('kpiWorkflowsRun'))  kpiEl('kpiWorkflowsRun').textContent  = workflowsRun;
  if (kpiEl('kpiDocsGenerated')) kpiEl('kpiDocsGenerated').textContent = docsGenerated;

  renderTaskQueue();
  renderCompletions();
  renderRoster();
  renderAlerts();
  renderAdPreview();
}

function renderTaskQueue() {
  const el = document.getElementById('dashTaskQueue');
  if (!el) return;
  const running = JOBS.filter(j => j.status === 'running');
  if (!running.length) {
    el.innerHTML = '<div class="empty-state">No active tasks — run a workflow to start</div>';
    return;
  }
  el.innerHTML = running.map(j => `
    <div class="task-item" onclick="showJobMonitor('${j.id}')" style="cursor:pointer;">
      <div class="task-dot td-running"></div>
      <div class="task-info">
        <div class="task-name">${j.wf}</div>
        <div class="task-client">${j.client}</div>
      </div>
      <div class="task-right">
        <span class="task-tag tt-running">Running</span>
        <span class="task-time">${j.started}</span>
      </div>
    </div>
  `).join('');
}

function dotClass(s) {
  return { running: 'td-running', queued: 'td-queued', done: 'td-done', warn: 'td-warn', blocked: 'td-blocked' }[s] || 'td-queued';
}

function tagLabel(s) {
  return { running: 'Running', queued: 'Queued', done: 'Done', warn: 'Review', blocked: 'Blocked' }[s] || s;
}

function renderCompletions() {
  const el = document.getElementById('completionsTbody');
  if (!el) return;
  const completed = JOBS.filter(j => j.status === 'completed');
  if (!completed.length) {
    el.innerHTML = '<tr><td colspan="5" class="empty-state" style="text-align:center;padding:24px;">No completed tasks yet</td></tr>';
    return;
  }
  el.innerHTML = completed.map(j => `
    <tr onclick="openJobModal('${j.id}')" style="cursor:pointer;">
      <td>${j.wf}</td>
      <td style="color:var(--text3);font-family:var(--mono);font-size:10px;">${j.client}</td>
      <td><span class="c-pill cp-kw">Workflow</span></td>
      <td class="c-outcome">Complete</td>
      <td style="color:var(--text3);font-family:var(--mono);font-size:10px;">${j.started}</td>
    </tr>
  `).join('');
}

function renderRoster() {
  const el = document.getElementById('clientRoster');
  if (!el) return;
  el.innerHTML = CLIENTS.map((c, i) => {
    const scoreClass = c.score >= 80 ? 'score-hi' : c.score >= 65 ? 'score-md' : 'score-lo';
    const trendClass = c.trend.startsWith('+') ? 'tr-up' : c.trend.startsWith('-') ? 'tr-down' : '';
    return `
      <div class="roster-item ${i === 0 ? 'selected' : ''} ${c.status === 'inactive' ? 'inactive' : ''}" onclick="selectRosterItem(this)">
        <div class="roster-avatar" style="color:${c.color};">${c.initials}</div>
        <div class="roster-info">
          <div class="roster-name client-name-link" onclick="event.stopPropagation();showClientHub(${c.id})">${c.name}</div>
          <div class="roster-domain">${c.domain}</div>
        </div>
        <div class="roster-right">
          <span class="roster-score ${scoreClass}">${c.score}</span>
          <span class="roster-trend ${trendClass}">${c.trend}</span>
        </div>
      </div>
    `;
  }).join('');
}

function selectRosterItem(el) {
  document.querySelectorAll('.roster-item').forEach(i => i.classList.remove('selected'));
  el.classList.add('selected');
}

function renderAlerts() {
  const el = document.getElementById('dashAlerts');
  if (!el) return;
  el.innerHTML = '<div class="empty-state">No alerts — system healthy</div>';
}

function renderAdPreview() {
  const el = document.getElementById('dashAdList');
  if (!el) return;
  el.innerHTML = '<div class="empty-state">No ads yet — use Ad Studio to create</div>';
}

/* ── WORKFLOWS ── */
function renderWorkflows() {
  renderClientSelect();
  renderWorkflowCards();
}

function renderClientSelect() {
  const sel = document.getElementById('wfClientSelect');
  if (!sel) return;
  const current = sel.value;
  sel.innerHTML = '<option value="">— Choose client —</option>' +
    CLIENTS.filter(c => c.status === 'active')
           .map(c => `<option value="${c.id}">${c.name}</option>`).join('');
  if (current) sel.value = current;
}

function renderWorkflowCards() {
  const el = document.getElementById('workflowCardsGrid');
  if (!el) return;

  const categories = [
    { key: 'seo',      label: 'SEO Analysis',      desc: 'Audits, gap reports, and competitive intelligence' },
    { key: 'content',  label: 'Content Creation',   desc: 'Blog posts, service pages, and location pages' },
    { key: 'business', label: 'Business Tools',     desc: 'Reports, proposals, and agency operations' },
    { key: 'dev',      label: 'Dev & Creative',     desc: 'Frontend builds, app prompting, and design' },
  ];

  let html = '';
  categories.forEach(cat => {
    const activeInCat = WORKFLOWS.filter(w => w.category === cat.key && w.status === 'active');
    const soonInCat   = WORKFLOWS.filter(w => w.category === cat.key && w.status === 'soon');
    if (!activeInCat.length && !soonInCat.length) return;

    html += `<div class="wf-category-header">
      <div class="wf-category-name">${cat.label}</div>
      <div class="wf-category-desc">${cat.desc}${activeInCat.length ? ` · <span class="wf-cat-active">${activeInCat.length} active</span>` : ''}${soonInCat.length ? ` · ${soonInCat.length} coming` : ''}</div>
    </div>`;

    activeInCat.forEach(wf => {
      html += `<div class="wf-card" data-id="${wf.id}" onclick="selectWorkflow('${wf.id}')">
        <div class="wf-card-header">
          <span class="wf-card-icon">${wf.icon}</span>
        </div>
        <div class="wf-card-title">${wf.title}</div>
        <div class="wf-card-desc">${wf.desc}</div>
        <div class="wf-card-time">⏱ ${wf.time} · <span class="wf-preview-hint">click to preview</span></div>
      </div>`;
    });

    soonInCat.forEach(wf => {
      html += `<div class="wf-card soon">
        <div class="wf-card-header">
          <span class="wf-card-icon">${wf.icon}</span>
          <span class="wf-soon-badge">SOON</span>
        </div>
        <div class="wf-card-title">${wf.title}</div>
        <div class="wf-card-desc">${wf.desc}</div>
        <div class="wf-card-time">⏱ ${wf.time}</div>
      </div>`;
    });
  });

  el.innerHTML = html;
}

function selectWorkflow(id) {
  const wf = WORKFLOWS.find(w => w.id === id);
  if (!wf || wf.status === 'soon') return;

  selectedWorkflow = id;

  // Populate modal header
  document.getElementById('modalWfIcon').textContent = wf.icon;
  document.getElementById('modalWfTitle').textContent = wf.title;
  document.getElementById('modalWfDesc').textContent = wf.desc;

  // Populate preview panel
  const previewEl = document.getElementById('wfOutputPreview');
  const previewText = document.getElementById('wfPreviewText');
  if (previewEl && previewText) {
    if (wf.preview) {
      previewText.textContent = wf.preview;
      previewEl.style.display = 'block';
    } else {
      previewEl.style.display = 'none';
    }
  }

  // Show/hide workflow-specific inputs
  const panels = {
    'modalInputsHomeService':   id === 'home-service-content',
    'modalInputsWebsiteAudit':  id === 'website-seo-audit',
    'modalInputsProspectAudit': id === 'prospect-audit',
    'modalInputsKeywordGap':    id === 'keyword-gap',
    'modalInputsSEOBlogPost':   id === 'seo-blog-post',
    'modalInputsServicePage':   id === 'service-page',
    'modalInputsLocationPage':  id === 'location-page',
    'modalInputsProgrammatic':  id === 'programmatic-content',
  };
  Object.entries(panels).forEach(([panelId, show]) => {
    const panel = document.getElementById(panelId);
    if (panel) panel.style.display = show ? 'flex' : 'none';
  });

  // Hide client dropdown for prospect-audit (prospects aren't clients yet)
  const clientFieldWrap = document.getElementById('wfClientFieldWrap');
  if (clientFieldWrap) clientFieldWrap.style.display = id === 'prospect-audit' ? 'none' : '';

  // Reset form fields
  const clientSel = document.getElementById('wfClientSelect');
  if (clientSel) clientSel.value = '';
  ['wfBusinessType','wfLocation','wfKeyword','wfServiceFocus','wfStrategyContext',
   'wfAuditDomain','wfAuditService','wfAuditLocation','wfAuditNotes',
   'wfProspectName','wfProspectDomain','wfProspectService','wfProspectLocation','wfProspectRevenue','wfProspectJobValue','wfProspectNotes',
   'wfGapDomain','wfGapService','wfGapLocation','wfGapCompetitors','wfGapNotes',
   'wfBlogBusinessType','wfBlogLocation','wfBlogKeyword','wfBlogAudience','wfBlogTone','wfBlogInternalLinks','wfBlogNotes',
   'wfSvcBusinessType','wfSvcService','wfSvcLocation','wfSvcDifferentiators','wfSvcPriceRange','wfSvcNotes',
   'wfLocBusinessType','wfLocPrimaryService','wfLocTargetLocation','wfLocHomeBase','wfLocLocalDetails','wfLocServicesList','wfLocNotes',
   'wfProgContentType','wfProgBusinessType','wfProgPrimaryService','wfProgLocation','wfProgHomeBase','wfProgItemsList','wfProgServicesList','wfProgDifferentiators','wfProgNotes'].forEach(fid => {
    const el = document.getElementById(fid);
    if (el) el.value = '';
  });

  // Reset programmatic content conditional fields
  ['progLocFields', 'progSvcBlogFields', 'progAutoDiscover'].forEach(elId => {
    const el = document.getElementById(elId);
    if (el) el.style.display = 'none';
  });
  const progItemCount = document.getElementById('progItemCount');
  if (progItemCount) progItemCount.style.display = 'none';
  // Reset discover city fields
  const discoverCity = document.getElementById('wfProgDiscoverCity');
  if (discoverCity) discoverCity.value = '';
  const discoverRadius = document.getElementById('wfProgDiscoverRadius');
  if (discoverRadius) discoverRadius.value = '15';

  checkRunReady();

  // Open modal
  document.getElementById('wfModal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeWorkflowModal(e) {
  if (e && e.target !== document.getElementById('wfModal')) return;
  document.getElementById('wfModal').classList.remove('open');
  document.body.style.overflow = '';
}

function checkRunReady() {
  const btn = document.getElementById('wfRunBtn');
  if (!btn) return;

  let ready = !!selectedWorkflow;

  if (selectedWorkflow === 'prospect-audit') {
    // Prospect-audit uses its own name field — no client dropdown needed
    const name     = document.getElementById('wfProspectName')?.value.trim();
    const domain   = document.getElementById('wfProspectDomain')?.value.trim();
    const service  = document.getElementById('wfProspectService')?.value.trim();
    const location = document.getElementById('wfProspectLocation')?.value.trim();
    ready = !!(name && domain && service && location);
  } else {
    // All other workflows require a client to be selected
    const clientVal = document.getElementById('wfClientSelect')?.value;
    ready = !!(clientVal && selectedWorkflow);

    if (selectedWorkflow === 'home-service-content' && ready) {
      const businessType = document.getElementById('wfBusinessType')?.value.trim();
      const location     = document.getElementById('wfLocation')?.value.trim();
      const keyword      = document.getElementById('wfKeyword')?.value.trim();
      ready = !!(businessType && location && keyword);
    }

    if (selectedWorkflow === 'website-seo-audit' && ready) {
      const domain   = document.getElementById('wfAuditDomain')?.value.trim();
      const service  = document.getElementById('wfAuditService')?.value.trim();
      const location = document.getElementById('wfAuditLocation')?.value.trim();
      ready = !!(domain && service && location);
    }

    if (selectedWorkflow === 'keyword-gap' && ready) {
      const domain   = document.getElementById('wfGapDomain')?.value.trim();
      const service  = document.getElementById('wfGapService')?.value.trim();
      const location = document.getElementById('wfGapLocation')?.value.trim();
      ready = !!(domain && service && location);
    }

    if (selectedWorkflow === 'seo-blog-post' && ready) {
      const businessType = document.getElementById('wfBlogBusinessType')?.value.trim();
      const location     = document.getElementById('wfBlogLocation')?.value.trim();
      const keyword      = document.getElementById('wfBlogKeyword')?.value.trim();
      ready = !!(businessType && location && keyword);
    }

    if (selectedWorkflow === 'service-page' && ready) {
      const businessType = document.getElementById('wfSvcBusinessType')?.value.trim();
      const service      = document.getElementById('wfSvcService')?.value.trim();
      const location     = document.getElementById('wfSvcLocation')?.value.trim();
      ready = !!(businessType && service && location);
    }

    if (selectedWorkflow === 'location-page' && ready) {
      const businessType     = document.getElementById('wfLocBusinessType')?.value.trim();
      const primaryService   = document.getElementById('wfLocPrimaryService')?.value.trim();
      const targetLocation   = document.getElementById('wfLocTargetLocation')?.value.trim();
      const homeBase         = document.getElementById('wfLocHomeBase')?.value.trim();
      ready = !!(businessType && primaryService && targetLocation && homeBase);
    }

    if (selectedWorkflow === 'programmatic-content' && ready) {
      const contentType  = document.getElementById('wfProgContentType')?.value;
      const businessType = document.getElementById('wfProgBusinessType')?.value.trim();
      const itemsList    = document.getElementById('wfProgItemsList')?.value.trim();

      if (!contentType || !businessType || !itemsList) {
        ready = false;
      } else if (contentType === 'location-pages') {
        const primaryService = document.getElementById('wfProgPrimaryService')?.value.trim();
        const homeBase       = document.getElementById('wfProgHomeBase')?.value.trim();
        ready = !!(primaryService && homeBase);
      } else if (contentType === 'service-pages' || contentType === 'blog-posts') {
        const location = document.getElementById('wfProgLocation')?.value.trim();
        ready = !!location;
      }
      // Enforce 50-page batch limit
      if (ready && itemsList) {
        let lines = itemsList.split('\n');
        if (lines.length === 1 && lines[0].includes(',')) lines = lines[0].split(',');
        if (lines.filter(l => l.trim()).length > 50) ready = false;
      }
      updateProgItemCount();
    }
  }

  btn.disabled = !ready;
}

function onAuditClientChange() {
  // Auto-fill domain from CLIENTS when client is selected in the audit or prospect modal
  const clientSel = document.getElementById('wfClientSelect');
  if (!clientSel) return;
  const clientId = parseInt(clientSel.value);
  const client = CLIENTS.find(c => c.id === clientId);
  if (!client) return;

  if (selectedWorkflow === 'website-seo-audit') {
    const domainEl = document.getElementById('wfAuditDomain');
    if (domainEl) domainEl.value = client.domain;
  } else if (selectedWorkflow === 'prospect-audit') {
    const domainEl = document.getElementById('wfProspectDomain');
    if (domainEl) domainEl.value = client.domain;
  } else if (selectedWorkflow === 'keyword-gap') {
    const domainEl = document.getElementById('wfGapDomain');
    if (domainEl) domainEl.value = client.domain;
  } else if (selectedWorkflow === 'seo-blog-post') {
    const locationEl = document.getElementById('wfBlogLocation');
    if (locationEl && client.location) locationEl.value = client.location;
  } else if (selectedWorkflow === 'service-page') {
    const locationEl = document.getElementById('wfSvcLocation');
    if (locationEl && client.location) locationEl.value = client.location;
  } else if (selectedWorkflow === 'location-page') {
    const homeBaseEl = document.getElementById('wfLocHomeBase');
    if (homeBaseEl && client.location) homeBaseEl.value = client.location;
  }
  checkRunReady();
}

function selectProgrammatic(contentType) {
  selectWorkflow('programmatic-content');
  // After modal opens, pre-select the content type
  setTimeout(() => {
    const sel = document.getElementById('wfProgContentType');
    if (sel) {
      sel.value = contentType;
      onProgContentTypeChange();
      checkRunReady();
    }
  }, 50);
}

function updateProgItemCount() {
  const el = document.getElementById('progItemCount');
  const textarea = document.getElementById('wfProgItemsList');
  if (!el || !textarea) return;

  const text = textarea.value.trim();
  if (!text) {
    el.style.display = 'none';
    return;
  }

  let lines = text.split('\n');
  if (lines.length === 1 && lines[0].includes(',')) {
    lines = lines[0].split(',');
  }
  const count = lines.filter(l => l.trim()).length;
  const max = 50;

  el.style.display = 'block';
  if (count > max) {
    el.innerHTML = `<span style="color:#FF4444;">${count} items — exceeds limit of ${max}</span>`;
  } else {
    el.innerHTML = `<span style="color:var(--text3);">${count} item${count !== 1 ? 's' : ''} · max ${max} per batch</span>`;
  }
}

async function discoverCities() {
  const cityInput = document.getElementById('wfProgDiscoverCity');
  const city = cityInput?.value.trim();
  const radius = document.getElementById('wfProgDiscoverRadius')?.value || '15';
  const btn = document.getElementById('btnDiscoverCities');

  if (!city) {
    showToast('Enter a center city first');
    return;
  }

  if (btn) { btn.disabled = true; btn.textContent = 'Searching...'; }

  try {
    const resp = await fetch('/api/discover-cities', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city, radius: parseInt(radius) }),
    });

    if (!resp.ok) throw new Error('Server returned ' + resp.status);

    const data = await resp.json();
    const textarea = document.getElementById('wfProgItemsList');
    if (textarea && data.cities && data.cities.length > 0) {
      textarea.value = data.cities.join('\n');
      updateProgItemCount();
      checkRunReady();
      showToast('Found ' + data.cities.length + ' cities near ' + city);
    } else {
      showToast('No cities found — try a larger radius');
    }
  } catch (err) {
    showToast('Error: ' + err.message);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Find Cities'; }
  }
}

function onProgContentTypeChange() {
  const contentType = document.getElementById('wfProgContentType')?.value;
  const locFields = document.getElementById('progLocFields');
  const svcBlogFields = document.getElementById('progSvcBlogFields');
  const itemsLabel = document.getElementById('progItemsLabel');
  const itemsTextarea = document.getElementById('wfProgItemsList');
  const itemsHint = document.getElementById('progItemsHint');
  const servicesWrap = document.getElementById('progServicesWrap');

  const autoDiscover = document.getElementById('progAutoDiscover');

  if (contentType === 'location-pages') {
    if (locFields) locFields.style.display = 'block';
    if (svcBlogFields) svcBlogFields.style.display = 'none';
    if (autoDiscover) autoDiscover.style.display = 'block';
    if (itemsLabel) itemsLabel.innerHTML = 'Locations <span class="req">*</span>';
    if (itemsTextarea) itemsTextarea.placeholder = 'One city per line, e.g.:\nMesa, AZ\nGilbert, AZ\nTempe, AZ\nScottsdale, AZ\nPhoenix, AZ';
    if (itemsHint) itemsHint.textContent = 'Each line becomes a unique location page with its own DataForSEO research';
    if (servicesWrap) servicesWrap.style.display = '';
  } else if (contentType === 'service-pages') {
    if (locFields) locFields.style.display = 'none';
    if (svcBlogFields) svcBlogFields.style.display = 'block';
    if (autoDiscover) autoDiscover.style.display = 'none';
    if (itemsLabel) itemsLabel.innerHTML = 'Services <span class="req">*</span>';
    if (itemsTextarea) itemsTextarea.placeholder = 'One service per line, e.g.:\npanel upgrade\nEV charger installation\nwhole-house rewiring\nelectrical inspection\ngenerator installation';
    if (itemsHint) itemsHint.textContent = 'Each line becomes a unique service page with competitor research';
    if (servicesWrap) servicesWrap.style.display = 'none';
  } else if (contentType === 'blog-posts') {
    if (locFields) locFields.style.display = 'none';
    if (svcBlogFields) svcBlogFields.style.display = 'block';
    if (autoDiscover) autoDiscover.style.display = 'none';
    if (itemsLabel) itemsLabel.innerHTML = 'Keywords <span class="req">*</span>';
    if (itemsTextarea) itemsTextarea.placeholder = 'One target keyword per line, e.g.:\nhow much does a panel upgrade cost\nsigns you need to rewire your house\nwhen to call an emergency electrician\nEV charger installation guide';
    if (itemsHint) itemsHint.textContent = 'Each line becomes a unique blog post with keyword research data';
    if (servicesWrap) servicesWrap.style.display = 'none';
  } else {
    if (locFields) locFields.style.display = 'none';
    if (svcBlogFields) svcBlogFields.style.display = 'none';
    if (autoDiscover) autoDiscover.style.display = 'none';
    if (itemsLabel) itemsLabel.innerHTML = 'Items <span class="req">*</span>';
    if (itemsTextarea) itemsTextarea.placeholder = 'Select a content type above to see format...';
    if (itemsHint) itemsHint.textContent = 'Enter one item per line — each becomes a unique page with its own DataForSEO research';
    if (servicesWrap) servicesWrap.style.display = 'none';
  }
  updateProgItemCount();
}

async function launchWorkflow() {
  if (!selectedWorkflow) return;

  const wf = WORKFLOWS.find(w => w.id === selectedWorkflow);
  let clientName, clientVal;

  if (selectedWorkflow === 'prospect-audit') {
    // Prospect-audit: name comes from the prospect name field, no client_id
    clientName = document.getElementById('wfProspectName')?.value.trim();
    if (!clientName) return;
    clientVal = '0';
  } else {
    const clientSel = document.getElementById('wfClientSelect');
    clientVal = clientSel?.value;
    if (!clientVal) return;
    clientName = clientSel.options[clientSel.selectedIndex].text;
  }
  const now = new Date();
  const timeStr = now.toTimeString().slice(0, 8);

  const newJob = {
    id: `JOB-${4822 + JOBS.length}`,
    wf: wf.title,
    client: clientName,
    started: 'just now',
    duration: '–',
    status: 'running',
    pct: 0,
    output: 'Streaming...'
  };
  JOBS.unshift(newJob);
  jobProgresses[newJob.id] = 0;
  LOG_ENTRIES.unshift({ time: timeStr, level: 'info', msg: `${newJob.id} started — ${wf.title} for ${clientName}` });

  // Close modal and open job monitor
  document.getElementById('wfModal').classList.remove('open');
  document.body.style.overflow = '';
  updateJobsBadge();
  showJobMonitor(newJob.id);
  startStreamingTerminal(newJob.id, wf.title, clientName);

  // Build inputs + strategy context per workflow
  let inputs = {};
  let strategyContext = '';

  if (selectedWorkflow === 'home-service-content') {
    inputs = {
      business_type: document.getElementById('wfBusinessType')?.value.trim() || '',
      location:      document.getElementById('wfLocation')?.value.trim() || '',
      keyword:       document.getElementById('wfKeyword')?.value.trim() || '',
      service_focus: document.getElementById('wfServiceFocus')?.value.trim() || '',
    };
    strategyContext = document.getElementById('wfStrategyContext')?.value.trim() || '';
  } else if (selectedWorkflow === 'website-seo-audit') {
    inputs = {
      domain:   document.getElementById('wfAuditDomain')?.value.trim() || '',
      service:  document.getElementById('wfAuditService')?.value.trim() || '',
      location: document.getElementById('wfAuditLocation')?.value.trim() || '',
      notes:    document.getElementById('wfAuditNotes')?.value.trim() || '',
    };
  } else if (selectedWorkflow === 'prospect-audit') {
    inputs = {
      domain:          document.getElementById('wfProspectDomain')?.value.trim() || '',
      service:         document.getElementById('wfProspectService')?.value.trim() || '',
      location:        document.getElementById('wfProspectLocation')?.value.trim() || '',
      monthly_revenue: document.getElementById('wfProspectRevenue')?.value.trim() || '',
      avg_job_value:   document.getElementById('wfProspectJobValue')?.value.trim() || '',
      notes:           document.getElementById('wfProspectNotes')?.value.trim() || '',
    };
  } else if (selectedWorkflow === 'keyword-gap') {
    inputs = {
      domain:             document.getElementById('wfGapDomain')?.value.trim() || '',
      service:            document.getElementById('wfGapService')?.value.trim() || '',
      location:           document.getElementById('wfGapLocation')?.value.trim() || '',
      competitor_domains: document.getElementById('wfGapCompetitors')?.value.trim() || '',
      notes:              document.getElementById('wfGapNotes')?.value.trim() || '',
    };
  } else if (selectedWorkflow === 'seo-blog-post') {
    inputs = {
      business_type:  document.getElementById('wfBlogBusinessType')?.value.trim() || '',
      location:       document.getElementById('wfBlogLocation')?.value.trim() || '',
      keyword:        document.getElementById('wfBlogKeyword')?.value.trim() || '',
      audience:       document.getElementById('wfBlogAudience')?.value.trim() || '',
      tone:           document.getElementById('wfBlogTone')?.value.trim() || '',
      internal_links: document.getElementById('wfBlogInternalLinks')?.value.trim() || '',
      notes:          document.getElementById('wfBlogNotes')?.value.trim() || '',
    };
  } else if (selectedWorkflow === 'service-page') {
    inputs = {
      business_type:   document.getElementById('wfSvcBusinessType')?.value.trim() || '',
      service:         document.getElementById('wfSvcService')?.value.trim() || '',
      location:        document.getElementById('wfSvcLocation')?.value.trim() || '',
      differentiators: document.getElementById('wfSvcDifferentiators')?.value.trim() || '',
      price_range:     document.getElementById('wfSvcPriceRange')?.value.trim() || '',
      notes:           document.getElementById('wfSvcNotes')?.value.trim() || '',
    };
  } else if (selectedWorkflow === 'location-page') {
    inputs = {
      business_type:    document.getElementById('wfLocBusinessType')?.value.trim() || '',
      primary_service:  document.getElementById('wfLocPrimaryService')?.value.trim() || '',
      target_location:  document.getElementById('wfLocTargetLocation')?.value.trim() || '',
      home_base:        document.getElementById('wfLocHomeBase')?.value.trim() || '',
      local_details:    document.getElementById('wfLocLocalDetails')?.value.trim() || '',
      services_list:    document.getElementById('wfLocServicesList')?.value.trim() || '',
      notes:            document.getElementById('wfLocNotes')?.value.trim() || '',
    };
  } else if (selectedWorkflow === 'programmatic-content') {
    inputs = {
      content_type:     document.getElementById('wfProgContentType')?.value || '',
      business_type:    document.getElementById('wfProgBusinessType')?.value.trim() || '',
      primary_service:  document.getElementById('wfProgPrimaryService')?.value.trim() || '',
      location:         document.getElementById('wfProgLocation')?.value.trim() || '',
      home_base:        document.getElementById('wfProgHomeBase')?.value.trim() || '',
      items_list:       document.getElementById('wfProgItemsList')?.value.trim() || '',
      services_list:    document.getElementById('wfProgServicesList')?.value.trim() || '',
      differentiators:  document.getElementById('wfProgDifferentiators')?.value.trim() || '',
      notes:            document.getElementById('wfProgNotes')?.value.trim() || '',
    };
  }

  const liveWorkflows = ['home-service-content', 'website-seo-audit', 'prospect-audit', 'keyword-gap', 'seo-blog-post', 'service-page', 'location-page', 'programmatic-content'];

  if (liveWorkflows.includes(selectedWorkflow)) {
    const payload = {
      workflow_id: selectedWorkflow,
      client_id: parseInt(clientVal),
      client_name: clientName,
      inputs,
      strategy_context: strategyContext,
    };

    try {
      const response = await fetch(`${API_BASE}/api/run-workflow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      sseBuffer = '';

      activeSSEJobs.add(newJob.id);
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          processSSEChunk(decoder.decode(value, { stream: true }), newJob);
        }
      } finally {
        activeSSEJobs.delete(newJob.id);
      }
    } catch (err) {
      activeSSEJobs.delete(newJob.id);
      appendErrorLineToTerminal(`Connection error: ${err.message}`);
      newJob.status = 'failed';
      newJob.output = err.message;
      terminalStreaming = false;
      streamDiv = null;
    }
  } else {
    // Mock for workflows without a live backend yet
    showToast(`▷ ${wf.title} launched for ${clientName} (mock)`);
    setTimeout(() => {
      const tb = document.getElementById('terminal');
      if (tb) {
        const mockDiv = document.createElement('div');
        mockDiv.className = 'tl-w';
        mockDiv.textContent = `  ⚠ ${wf.title} backend not yet connected — coming in a future session`;
        tb.appendChild(mockDiv);
        tb.scrollTop = tb.scrollHeight;
      }
      newJob.status = 'completed';
      newJob.output = 'Mock complete';
      terminalStreaming = false;
      streamDiv = null;
    }, 1500);
  }
}

function startStreamingTerminal(jobId, wfTitle, clientName) {
  terminalStreaming = true;
  streamDiv = null;
  sseBuffer = '';

  const tb = activeTerminalEl || document.getElementById('terminal');
  if (!tb) return;

  tb.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'tl-d';
  header.textContent = `# ProofPilot Claude Agent — ${new Date().toISOString().slice(0, 10)}`;
  tb.appendChild(header);
  tb.appendChild(document.createElement('br'));

  const jobLine = document.createElement('div');
  jobLine.className = 'tl-inf';
  jobLine.textContent = `▷ ${jobId} — ${wfTitle} for ${clientName}`;
  tb.appendChild(jobLine);
  tb.appendChild(document.createElement('br'));

  const callingLine = document.createElement('div');
  callingLine.className = 'tl-p';
  callingLine.innerHTML = '<span class="t-prompt">$ </span>Calling Claude Opus · streaming output...';
  tb.appendChild(callingLine);
  tb.appendChild(document.createElement('br'));
}

function appendTokenToTerminal(text) {
  const tb = activeTerminalEl || document.getElementById('terminal');
  if (!tb) return;
  if (!streamDiv) {
    streamDiv = document.createElement('div');
    streamDiv.className = 'tl-stream';
    tb.appendChild(streamDiv);
  }
  streamDiv.textContent += text;
  tb.scrollTop = tb.scrollHeight;
}

function appendErrorLineToTerminal(msg) {
  const tb = activeTerminalEl || document.getElementById('terminal');
  if (!tb) return;
  const errDiv = document.createElement('div');
  errDiv.className = 'tl-err';
  errDiv.textContent = `✗ ${msg}`;
  tb.appendChild(errDiv);
  tb.scrollTop = tb.scrollHeight;
}

function processSSEChunk(chunk, job) {
  sseBuffer += chunk;
  const lines = sseBuffer.split('\n');
  sseBuffer = lines.pop(); // keep last (possibly incomplete) line

  for (const line of lines) {
    if (!line.startsWith('data: ')) continue;
    try {
      const data = JSON.parse(line.slice(6));
      if (data.type === 'token') {
        appendTokenToTerminal(data.text);
        if (job) jobProgresses[job.id] = Math.min(95, (jobProgresses[job.id] || 0) + 0.25);

      } else if (data.type === 'done') {
        currentJobId = data.job_id;
        terminalStreaming = false;
        streamDiv = null;

        if (job) {
          job.status = 'completed';
          job.output = 'Complete — ready to download';
          job.server_job_id = data.job_id; // store server UUID for later lookup
          jobProgresses[job.id] = 100;
        }

        const tb = activeTerminalEl || document.getElementById('terminal');
        if (tb) {
          tb.appendChild(document.createElement('br'));
          const doneDiv = document.createElement('div');
          doneDiv.className = 'tl-ok';
          doneDiv.textContent = `✓ Complete — Job ${data.job_id}`;
          tb.appendChild(doneDiv);
          tb.scrollTop = tb.scrollHeight;
        }

        // Update job monitor done bar
        if (monitorJobId === job?.id) {
          updateMonitorStatus('completed');
          const doneBar = document.getElementById('jmDoneBar');
          const dlLink = document.getElementById('jmDownloadLink');
          const doneMsg = document.getElementById('jmDoneMsg');
          if (doneBar && dlLink && doneMsg) {
            doneMsg.textContent = `Job ${data.job_id} complete — output ready`;
            dlLink.href = `${API_BASE}/api/download/${data.job_id}`;
            doneBar.style.display = 'flex';
          }
        }

        // Add to content library
        addToContentLibrary(
          data.job_id,
          data.client_name || job?.client || '',
          0,
          data.workflow_id || selectedWorkflow || '',
          data.workflow_title || job?.wf || ''
        );

        updateJobsBadge();
        showToast(`✓ ${job?.wf || 'Workflow'} complete`);
        LOG_ENTRIES.unshift({ time: new Date().toTimeString().slice(0, 8), level: 'ok', msg: `${job?.id} completed — ${job?.wf} for ${job?.client}` });

      } else if (data.type === 'error') {
        appendErrorLineToTerminal(data.message || 'Workflow error');
        terminalStreaming = false;
        streamDiv = null;
        if (job) { job.status = 'failed'; job.output = data.message || 'Error'; }
      }
    } catch (e) { /* skip malformed lines */ }
  }
}

/* ── CLIENTS ── */
function renderClients(filter = '') {
  const el = document.getElementById('clientsTbody');
  if (!el) return;

  const filtered = filter
    ? CLIENTS.filter(c => c.name.toLowerCase().includes(filter) || c.domain.toLowerCase().includes(filter))
    : CLIENTS;

  el.innerHTML = filtered.map(c => {
    const scoreClass = c.score >= 80 ? 'score-hi' : c.score >= 65 ? 'score-md' : 'score-lo';
    const isActive = c.status === 'active';
    return `
      <tr class="${isActive ? '' : 'row-inactive'}">
        <td>
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:26px;height:26px;background:var(--dark-blue);border:1px solid rgba(0,81,255,0.3);
                        display:flex;align-items:center;justify-content:center;
                        font-family:var(--display);font-size:10px;color:${c.color};">${c.initials}</div>
            <span class="client-name-link" onclick="showClientHub(${c.id})">${c.name}</span>
          </div>
        </td>
        <td style="font-family:var(--mono);font-size:10px;color:var(--text3);">${c.domain}</td>
        <td style="color:var(--text3);">${c.plan}</td>
        <td><span class="seo-score ${scoreClass}">${c.score}</span></td>
        <td style="font-family:var(--mono);color:var(--text3);">#${c.avgRank}</td>
        <td style="font-family:var(--mono);font-size:10px;color:var(--text3);">${c.lastJob}</td>
        <td>
          <span class="pill ${isActive ? 'pill-act' : 'pill-inactive'} pill-toggle"
                onclick="toggleClientStatus(${c.id})"
                title="${isActive ? 'Click to deactivate' : 'Click to activate'}">
            ${isActive ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td style="display:flex;gap:6px;">
          <button class="tbl-btn" onclick="showClientHub(${c.id})">Hub</button>
          <button class="tbl-btn" onclick="selectWorkflowForClient(${c.id})" ${isActive ? '' : 'disabled'}>Run</button>
        </td>
      </tr>
    `;
  }).join('');
}

/* ── CLIENT HUB ── */

function showClientHub(clientId) {
  activeClientId = clientId;
  // Keep the Clients nav item highlighted when viewing the hub
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const el = document.getElementById('view-client-hub');
  if (el) el.classList.add('active');

  const navClients = document.getElementById('nav-clients');
  if (navClients) navClients.classList.add('active');

  const title = document.getElementById('pageTitle');
  const client = CLIENTS.find(c => c.id === clientId);
  if (title && client) title.textContent = client.name;

  currentView = 'client-hub';
  renderClientHub();
}

function showClientHubByName(clientName) {
  const client = CLIENTS.find(c => c.name === clientName);
  if (client) showClientHub(client.id);
}

function renderClientHub() {
  const el = document.getElementById('clientHubContent');
  if (!el) return;

  const client = CLIENTS.find(c => c.id === activeClientId);
  if (!client) {
    el.innerHTML = '<div class="empty-state">Client not found.</div>';
    return;
  }

  const clientJobs = JOBS.filter(j => j.client === client.name);
  const runningJobs = clientJobs.filter(j => j.status === 'running');
  const completedJobs = clientJobs.filter(j => j.status === 'completed' || j.status === 'complete');

  const scoreClass = client.score >= 80 ? 'score-hi' : client.score >= 65 ? 'score-md' : 'score-lo';
  const trendUp = client.trend && client.trend.startsWith('+');
  const trendDown = client.trend && client.trend.startsWith('-');

  // Plan badge class
  const planKey = (client.plan || '').toLowerCase();
  const planClass = `ch-plan-${planKey}`;

  // Stats
  const totalRun = clientJobs.length;
  const lastJobDate = clientJobs.length ? clientJobs[0].started : '—';
  const avgScore = client.score;

  // Needs Attention recommendations based on score
  let attentionTasks = [];
  if (client.score < 60) {
    attentionTasks = [
      { name: 'Technical SEO Audit overdue', desc: 'Core Web Vitals and crawl errors need immediate review.', priority: 'high' },
      { name: 'GBP optimization needed', desc: 'Google Business Profile is incomplete or out of date.', priority: 'high' },
      { name: 'Page speed issues detected', desc: 'LCP score above threshold on mobile — impacts local rankings.', priority: 'medium' },
    ];
  } else if (client.score < 76) {
    attentionTasks = [
      { name: 'Content gaps identified', desc: '12+ keywords competitors rank for that this site does not.', priority: 'medium' },
      { name: 'Link building opportunity', desc: '3 high-authority local directories have unclaimed listings.', priority: 'medium' },
      { name: 'Schema markup missing', desc: 'LocalBusiness and Service schemas not implemented.', priority: 'low' },
    ];
  } else {
    attentionTasks = [
      { name: 'Competitor monitoring active', desc: 'Top 3 competitors gained rankings in past 30 days — review now.', priority: 'low' },
      { name: 'Content calendar update due', desc: 'Next content batch should be scheduled for next month.', priority: 'low' },
      { name: 'Review acquisition momentum', desc: 'GBP review velocity slowing — consider review outreach campaign.', priority: 'medium' },
    ];
  }

  // WF icon map for content strip
  const wfIconMap = {
    'Website & SEO Audit': '🔍',
    'Prospect SEO Market Analysis': '🎯',
    'Keyword Gap Analysis': '🔍',
    'Home Service SEO Content': '🏠',
    'SEO Blog Generator': '✍️',
  };

  // ── In Progress column ──
  const inProgressHTML = runningJobs.length
    ? runningJobs.map(j => {
        const pct = Math.round(jobProgresses[j.id] || j.pct || 0);
        return `
          <div class="ch-job-card">
            <div class="ch-job-type">${j.wf}</div>
            <div class="ch-job-meta">Started ${j.started}</div>
            <div class="ch-job-progress">
              <div class="ch-job-progress-fill" style="width:${pct}%"></div>
            </div>
            <button class="ch-view-live-btn" onclick="showJobMonitor('${j.id}')">View Live</button>
          </div>
        `;
      }).join('')
    : `<div class="empty-state" style="padding:24px 16px;">No active tasks running for this client.</div>`;

  // ── Recently Completed column ──
  const completedHTML = completedJobs.length
    ? completedJobs.slice(0, 10).map(j => {
        const icon = wfIconMap[j.wf] || '📄';
        const dlBtn = j.server_job_id
          ? `<a class="ch-dl-btn" href="${API_BASE}/api/download/${j.server_job_id}" target="_blank">↓ .docx</a>`
          : `<span class="ch-dl-btn" style="opacity:0.4;cursor:default;">↓ .docx</span>`;
        return `
          <div class="ch-done-card">
            <div class="ch-done-icon">${icon}</div>
            <div class="ch-done-info">
              <div class="ch-done-title">${j.wf}</div>
              <div class="ch-done-date">${j.started}</div>
            </div>
            ${dlBtn}
          </div>
        `;
      }).join('')
    : `<div class="empty-state" style="padding:24px 16px;">No completed workflows yet — run one above.</div>`;

  // ── Needs Attention column ──
  const attentionHTML = attentionTasks.map(t => `
    <div class="ch-task-card priority-${t.priority}">
      <div class="ch-task-header">
        <span class="ch-task-name">${t.name}</span>
        <span class="ch-priority-badge">${t.priority}</span>
      </div>
      <div class="ch-task-desc">${t.desc}</div>
    </div>
  `).join('');

  // ── Content library strip items ──
  const stripHTML = completedJobs.length
    ? completedJobs.slice(0, 12).map(j => {
        const icon = wfIconMap[j.wf] || '📄';
        const hasDocx = !!j.server_job_id;
        return `
          <div class="ch-content-item">
            <div class="ch-content-item-header">
              <span class="ch-content-wf-icon">${icon}</span>
              <span class="ch-content-wf-type">${j.wf.split(' ').slice(0, 2).join(' ')}</span>
            </div>
            <div class="ch-content-title">${j.wf} — ${client.name}</div>
            <div class="ch-content-footer">
              <span class="ch-content-date">${j.started}</span>
              ${hasDocx
                ? `<a class="ch-content-dl" href="${API_BASE}/api/download/${j.server_job_id}" target="_blank">↓ .docx</a>`
                : `<span class="ch-content-dl" style="opacity:0.35;cursor:default;">↓ .docx</span>`}
            </div>
          </div>
        `;
      }).join('')
    : `<div class="ch-strip-empty">No content generated for this client yet — run a workflow to create your first piece.</div>`;

  el.innerHTML = `
    <!-- Client Header Bar -->
    <div class="ch-header">
      <button class="ch-back-btn" onclick="showView('clients')">← Clients</button>
      <div class="ch-identity">
        <div class="ch-client-name">${client.name}</div>
        <a class="ch-domain-link" href="https://${client.domain}" target="_blank" rel="noopener">${client.domain} ↗</a>
      </div>
      <div class="ch-badges">
        <span class="ch-plan-badge ${planClass}">${client.plan}</span>
        <div class="ch-score-badge ${scoreClass}">
          <span style="font-size:10px;opacity:0.6;letter-spacing:.08em;text-transform:uppercase;">SEO</span>
          <span class="ch-score-val">${client.score}</span>
          <span class="ch-score-trend ${trendUp ? 'tr-up' : trendDown ? 'tr-down' : ''}">${client.trend || '→0'}</span>
        </div>
      </div>
      <div class="ch-header-actions">
        <button class="ch-run-btn" onclick="selectWorkflowForClient(${client.id})">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          Run Workflow
        </button>
      </div>
    </div>

    <!-- Client Stats Bar -->
    <div class="ch-stats-bar">
      <div class="ch-stat">
        <div class="ch-stat-label">Workflows Run</div>
        <div class="ch-stat-value">${totalRun}</div>
        <div class="ch-stat-sub">total for this client</div>
      </div>
      <div class="ch-stat">
        <div class="ch-stat-label">Last Workflow</div>
        <div class="ch-stat-value" style="font-size:14px;padding-top:4px;">${lastJobDate}</div>
        <div class="ch-stat-sub">${completedJobs.length} completed</div>
      </div>
      <div class="ch-stat">
        <div class="ch-stat-label">SEO Score</div>
        <div class="ch-stat-value ${scoreClass}">${avgScore}</div>
        <div class="ch-stat-sub">avg rank #${client.avgRank}</div>
      </div>
      <div class="ch-stat">
        <div class="ch-stat-label">Active Since</div>
        <div class="ch-stat-value" style="font-size:16px;padding-top:4px;">2024</div>
        <div class="ch-stat-sub">${client.status === 'active' ? 'Active client' : 'Inactive'}</div>
      </div>
    </div>

    <!-- Four Status Columns -->
    <div class="ch-columns">

      <!-- In Progress -->
      <div class="ch-col ch-col-inprogress">
        <div class="ch-col-header">
          <div class="ch-col-title">
            <span class="ch-col-dot"></span>
            In Progress
          </div>
          <span class="ch-col-count">${runningJobs.length}</span>
        </div>
        <div class="ch-col-body">
          ${inProgressHTML}
        </div>
      </div>

      <!-- Recently Completed -->
      <div class="ch-col ch-col-completed">
        <div class="ch-col-header">
          <div class="ch-col-title">
            <span class="ch-col-dot"></span>
            Recently Completed
          </div>
          <span class="ch-col-count">${completedJobs.length}</span>
        </div>
        <div class="ch-col-body">
          ${completedHTML}
        </div>
      </div>

      <!-- Needs Attention -->
      <div class="ch-col ch-col-attention">
        <div class="ch-col-header">
          <div class="ch-col-title">
            <span class="ch-col-dot"></span>
            Needs Attention
          </div>
          <span class="ch-col-count">${attentionTasks.length}</span>
        </div>
        <div class="ch-col-body">
          ${attentionHTML}
        </div>
      </div>

      <!-- Upcoming Automations -->
      <div class="ch-col ch-col-upcoming">
        <div class="ch-col-header">
          <div class="ch-col-title">
            <span class="ch-col-dot"></span>
            Upcoming Automations
          </div>
          <span class="ch-col-count">0</span>
        </div>
        <div class="ch-col-body">
          <div class="ch-upcoming-empty">
            <div class="ch-upcoming-icon">🗓</div>
            <div class="ch-upcoming-text">No automations scheduled yet.<br>Schedule recurring workflows to run automatically.</div>
            <button class="ch-schedule-btn" onclick="showToast('Coming soon — scheduling is on the roadmap')">
              + Schedule Automation
            </button>
          </div>
        </div>
      </div>

    </div>

    <!-- Content Library Strip -->
    <div class="ch-content-strip">
      <div class="ch-strip-header">
        <div class="ch-strip-title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          Content Library
        </div>
        <button class="ch-view-all-link" onclick="showView('content')">View All →</button>
      </div>
      <div class="ch-strip-scroll">
        ${stripHTML}
      </div>
    </div>
  `;
}

function selectWorkflowForClient(clientId) {
  // Pre-select the client in the workflow modal and open the workflows view
  activeClientId = clientId;
  showView('workflows');
  // After a short tick so the modal client select is populated
  setTimeout(() => {
    const sel = document.getElementById('wfClientSelect');
    if (sel) {
      sel.value = clientId;
      checkRunReady();
    }
  }, 80);
}

function toggleClientStatus(id) {
  const client = CLIENTS.find(c => c.id === id);
  if (!client) return;
  client.status = client.status === 'active' ? 'inactive' : 'active';

  // Refresh all views that depend on client status
  const searchEl = document.getElementById('clientSearch');
  renderClients(searchEl ? searchEl.value.toLowerCase() : '');
  renderClientSelect();   // workflow dropdown: active clients only
  renderRoster();         // dashboard roster: dim inactive
  updateClientsBadge();   // sidebar badge
}

/* ── JOBS ── */
let jobFilter = 'all';

function renderJobs(filter) {
  jobFilter = filter;
  document.querySelectorAll('#jobFilterTabs .filter-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === filter);
  });

  const el = document.getElementById('jobsTbody');
  if (!el) return;

  const filtered = filter === 'all' ? JOBS : JOBS.filter(j => j.status === filter);

  if (!filtered.length) {
    el.innerHTML = `<tr><td colspan="7" class="empty-state" style="text-align:center;padding:32px;">No ${filter === 'all' ? '' : filter + ' '}tasks yet — run a workflow to create one</td></tr>`;
    return;
  }

  el.innerHTML = filtered.map(j => {
    const pillClass = { running: 'pill-run', completed: 'pill-ok', failed: 'pill-fail' }[j.status] || 'pill-warn';
    const pct = Math.round(jobProgresses[j.id] || j.pct);
    const progressHTML = j.status === 'running'
      ? `<div class="prog-bar" id="pb-${j.id}"><div class="prog-fill" style="width:${pct}%" id="pf-${j.id}"></div></div>`
      : '';
    return `
      <tr onclick="openJobModal('${j.id}')" style="cursor:pointer;">
        <td style="font-family:var(--mono);font-size:10px;color:var(--elec-blue);">${j.id}</td>
        <td style="color:var(--text);font-weight:600;">${j.wf}</td>
        <td><span class="client-name-link" onclick="event.stopPropagation();showClientHubByName('${j.client.replace(/'/g, "\\'")}')">${j.client}</span></td>
        <td style="font-family:var(--mono);font-size:10px;color:var(--text3);">${j.started}</td>
        <td style="font-family:var(--mono);font-size:10px;color:var(--text3);">${j.duration}</td>
        <td><span class="pill ${pillClass}">${j.status}</span></td>
        <td>${progressHTML}<span style="font-size:10px;color:var(--text3);font-family:var(--mono);">${j.output}</span></td>
      </tr>
    `;
  }).join('');
}

/* ── REPORTS ── */
function renderReports() {
  const el = document.getElementById('reportsGrid');
  if (!el) return;
  if (!REPORTS.length) {
    el.innerHTML = '<div class="empty-state" style="grid-column:1/-1;">No reports yet — completed workflows will appear here</div>';
    return;
  }
  el.innerHTML = REPORTS.map(r => `
    <div class="report-card">
      <div class="rc-type">${r.type}</div>
      <div class="rc-title">${r.title}</div>
      <div class="rc-client">${r.client} · ${r.date}</div>
      <div class="rc-actions">
        <button class="rc-btn rc-btn-primary">Preview</button>
        <button class="rc-btn rc-btn-ghost">Download</button>
      </div>
    </div>
  `).join('');
}

/* ── CONTENT LIBRARY ── */

const WF_ICONS = {
  'website-seo-audit':    '🔍',
  'prospect-audit':       '🎯',
  'home-service-content': '🏠',
  'keyword-gap':          '📊',
  'seo-blog-generator':   '✍️',
  'seo-blog-post':        '✍️',
  'service-page':         '⚡',
  'location-page':        '📍',
  'programmatic-content': '🚀',
  'seo-strategy-sheet':   '📋',
};

const WF_TYPE_LABELS = {
  'website-seo-audit':    'SEO Audit',
  'prospect-audit':       'Prospect Analysis',
  'home-service-content': 'SEO Content',
  'keyword-gap':          'Keyword Gap',
  'seo-blog-generator':   'Blog Post',
  'seo-blog-post':        'Blog Post',
  'service-page':         'Service Page',
  'location-page':        'Location Page',
  'programmatic-content': 'Programmatic Content',
  'seo-strategy-sheet':   'Strategy',
};

function wfIcon(workflowId) {
  return WF_ICONS[workflowId] || '📄';
}

function wfTypeLabel(workflowId) {
  return WF_TYPE_LABELS[workflowId] || 'Document';
}

function getClientInitials(name) {
  if (!name) return '?';
  return name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
}

function getClientColor(name) {
  // Deterministic color from client name — cycles through brand palette
  const palette = ['#0051FF', '#7C3AED', '#0D9488', '#EA580C', '#D97706', '#28A745'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) & 0xFFFFFF;
  return palette[Math.abs(hash) % palette.length];
}

function addToContentLibrary(jobId, clientName, clientId, workflowId, workflowTitle) {
  // Prevent duplicates
  if (CONTENT_ITEMS.find(c => c.job_id === jobId)) return;

  const now = new Date();
  CONTENT_ITEMS.unshift({
    id: jobId,
    job_id: jobId,
    client_name: clientName || 'Unknown Client',
    client_id: clientId || 0,
    workflow_id: workflowId || '',
    workflow_title: workflowTitle || 'Document',
    created_at: now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
    has_docx: true,
    preview: '',
  });

  // Refresh client filter dropdown if content view is active
  _populateContentClientFilter();
  renderContentLibrary();
}

function _populateContentClientFilter() {
  const sel = document.getElementById('contentClientFilter');
  if (!sel) return;
  const current = sel.value;
  const clientNames = [...new Set(CONTENT_ITEMS.map(c => c.client_name))].sort();
  sel.innerHTML = '<option value="">All Clients</option>' +
    clientNames.map(n => `<option value="${n}">${n}</option>`).join('');
  if (current) sel.value = current;
}

function renderContentLibrary(items) {
  const el = document.getElementById('contentLibraryGrid');
  if (!el) return;

  const list = items !== undefined ? items : CONTENT_ITEMS;

  if (!list.length) {
    el.innerHTML = `
      <div class="cl-empty-state">
        <div class="cl-empty-icon">📂</div>
        <div class="cl-empty-title">No content yet</div>
        <div class="cl-empty-sub">Run a workflow to generate your first document — it will appear here automatically.</div>
        <button class="btn-primary-top" onclick="showView('workflows')" style="margin-top:16px;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          Run a Workflow
        </button>
      </div>`;
    return;
  }

  // Group by client_name
  const byClient = {};
  list.forEach(item => {
    const key = item.client_name || 'Unknown Client';
    if (!byClient[key]) byClient[key] = [];
    byClient[key].push(item);
  });

  el.innerHTML = Object.entries(byClient).map(([clientName, clientItems]) => {
    const initials = getClientInitials(clientName);
    const color = getClientColor(clientName);
    const count = clientItems.length;
    const cards = clientItems.map(item => _contentCard(item)).join('');

    return `
      <div class="cl-client-section">
        <div class="cl-client-header">
          <div class="cl-client-avatar" style="background:${color}20;border-color:${color}40;color:${color};">${initials}</div>
          <span class="cl-client-name">${clientName}</span>
          <span class="cl-client-count">${count} document${count !== 1 ? 's' : ''}</span>
        </div>
        <div class="cl-cards-row">
          ${cards}
        </div>
      </div>`;
  }).join('');
}

function _contentCard(item) {
  const icon = wfIcon(item.workflow_id);
  const typeLabel = wfTypeLabel(item.workflow_id);
  const downloadBtn = item.has_docx
    ? `<button class="cl-card-btn cl-card-btn-dl" onclick="event.stopPropagation(); downloadContentItem('${item.job_id}')" title="Download .docx">
         <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
         .docx
       </button>`
    : '';

  return `
    <div class="cl-card" onclick="viewContentItem('${item.job_id}')">
      <div class="cl-card-top">
        <span class="cl-card-icon">${icon}</span>
        <span class="cl-card-type-badge">${typeLabel}</span>
      </div>
      <div class="cl-card-title">${item.workflow_title}</div>
      <div class="cl-card-meta">${item.client_name} · ${item.created_at}</div>
      ${item.preview ? `<div class="cl-card-preview">${item.preview.slice(0, 120)}${item.preview.length > 120 ? '...' : ''}</div>` : ''}
      <div class="cl-card-actions">
        <button class="cl-card-btn cl-card-btn-view" onclick="event.stopPropagation(); viewContentItem('${item.job_id}')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          View
        </button>
        ${downloadBtn}
      </div>
    </div>`;
}

function filterContentLibrary() {
  const search = (document.getElementById('contentSearch')?.value || '').toLowerCase().trim();
  const clientFilter = document.getElementById('contentClientFilter')?.value || '';
  const typeFilter = document.getElementById('contentTypeFilter')?.value || '';

  let filtered = CONTENT_ITEMS;

  if (clientFilter) {
    filtered = filtered.filter(c => c.client_name === clientFilter);
  }

  if (typeFilter) {
    filtered = filtered.filter(c => c.workflow_id === typeFilter);
  }

  if (search) {
    filtered = filtered.filter(c =>
      c.workflow_title.toLowerCase().includes(search) ||
      c.client_name.toLowerCase().includes(search) ||
      (c.preview || '').toLowerCase().includes(search)
    );
  }

  renderContentLibrary(filtered);
}

function downloadContentItem(jobId) {
  window.open(`${API_BASE}/api/download/${jobId}`, '_blank');
}

function viewContentItem(jobId) {
  // JOBS entries use "JOB-NNNN" local IDs; content library uses 8-char server UUIDs.
  // Match via server_job_id which is stored on the job object when the done SSE event fires.
  const job = JOBS.find(j => j.server_job_id === jobId);

  if (job) {
    showJobMonitor(job.id);
    // Show the done bar for completed jobs
    updateMonitorStatus('completed');
    const doneBar = document.getElementById('jmDoneBar');
    const dlLink = document.getElementById('jmDownloadLink');
    const doneMsg = document.getElementById('jmDoneMsg');
    if (doneBar && dlLink && doneMsg) {
      doneMsg.textContent = `Job ${jobId} complete — output ready`;
      dlLink.href = `${API_BASE}/api/download/${jobId}`;
      doneBar.style.display = 'flex';
    }
    return;
  }

  // No matching JOBS entry (loaded from server after refresh) — open job API in modal
  const item = CONTENT_ITEMS.find(c => c.job_id === jobId);
  const modalTitle = document.getElementById('modalTitle');
  const modalBody = document.getElementById('modalBody');
  const overlay = document.getElementById('jobModal');
  if (!modalTitle || !modalBody || !overlay) return;

  modalTitle.textContent = item ? `${item.workflow_title} — ${item.client_name}` : `Job ${jobId}`;
  modalBody.innerHTML = `
    <div class="modal-row"><span class="modal-label">Job ID</span><span class="modal-val" style="font-family:var(--mono);color:var(--elec-blue);">${jobId}</span></div>
    ${item ? `<div class="modal-row"><span class="modal-label">Client</span><span class="modal-val">${item.client_name}</span></div>` : ''}
    ${item ? `<div class="modal-row"><span class="modal-label">Workflow</span><span class="modal-val">${item.workflow_title}</span></div>` : ''}
    ${item ? `<div class="modal-row"><span class="modal-label">Created</span><span class="modal-val">${item.created_at}</span></div>` : ''}
    ${item?.has_docx ? `<div class="modal-row"><span class="modal-label">Document</span><span class="modal-val"><a href="${API_BASE}/api/download/${jobId}" target="_blank" style="color:var(--neon-green);text-decoration:none;">Download .docx</a></span></div>` : ''}
    ${item?.preview ? `<div style="margin-top:14px;padding:14px;background:rgba(0,0,0,0.3);border-radius:4px;font-family:var(--mono);font-size:11px;color:var(--text3);line-height:1.7;white-space:pre-wrap;">${item.preview}</div>` : ''}
  `;
  overlay.classList.add('open');
}

async function syncContentLibrary() {
  // Populate the client filter with any items already in memory
  _populateContentClientFilter();

  try {
    const res = await fetch(`${API_BASE}/api/content`);
    if (!res.ok) return;
    const data = await res.json();
    data.items.forEach(item => {
      if (!CONTENT_ITEMS.find(c => c.job_id === item.job_id)) {
        CONTENT_ITEMS.push({
          id: item.job_id,
          job_id: item.job_id,
          client_name: item.client_name || 'Unknown Client',
          client_id: 0,
          workflow_id: item.workflow_id,
          workflow_title: item.workflow_title,
          has_docx: item.has_docx,
          preview: item.content_preview || '',
          created_at: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
        });
      }
    });
    _populateContentClientFilter();
  } catch (e) {
    // Server may not have the endpoint yet — render with whatever is in memory
  }

  renderContentLibrary();
}

/* ── LOGS ── */
let activeLogFilter = 'all';

function setLogFilter(filter) {
  activeLogFilter = filter;
  renderLogs();
}

function renderLogs() {
  const el = document.getElementById('logStream');
  if (!el) return;

  // Update active tab highlight
  document.querySelectorAll('.log-filter-tabs .filter-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.logFilter === activeLogFilter);
  });

  let entries = LOG_ENTRIES;

  if (activeLogFilter === 'agent') {
    entries = LOG_ENTRIES.filter(e => /JOB-\d+/.test(e.msg));
  } else if (activeLogFilter === 'system') {
    entries = LOG_ENTRIES.filter(e => !/JOB-\d+/.test(e.msg) && e.level !== 'err' && e.level !== 'error');
  } else if (activeLogFilter === 'errors') {
    entries = LOG_ENTRIES.filter(e => e.level === 'err' || e.level === 'error');
  }

  if (!entries.length) {
    el.innerHTML = '<div class="empty-state">No activity yet — workflow runs will be logged here</div>';
    return;
  }
  el.innerHTML = entries.map(entry => `
    <div class="log-entry">
      <span class="log-time">${entry.time}</span>
      <span class="log-level-${entry.level}">${entry.level.toUpperCase().padEnd(4)}</span>
      <span class="log-msg">${entry.msg}</span>
    </div>
  `).join('');
}

function clearLogs() {
  LOG_ENTRIES.length = 0;
  renderLogs();
  showToast('Activity log cleared');
}

/* ── AD STUDIO VIEW ── */
function renderAds() {
  const el = document.getElementById('adsGrid');
  if (!el) return;
  el.innerHTML = '<div class="empty-state" style="grid-column:1/-1;">No ad creatives yet — Ad Studio coming soon</div>';
}

/* ── JOB MODAL ── */
function openJobModal(jobId) {
  // Navigate to the job monitor view for all jobs
  showJobMonitor(jobId);

  // If job is completed and has a docx (server_job_id was set), show the done bar immediately
  const job = JOBS.find(j => j.id === jobId);
  if (job && job.status === 'completed' && job.server_job_id) {
    updateMonitorStatus('completed');
    const doneBar = document.getElementById('jmDoneBar');
    const dlLink = document.getElementById('jmDownloadLink');
    const doneMsg = document.getElementById('jmDoneMsg');
    if (doneBar && dlLink && doneMsg) {
      doneMsg.textContent = `Job ${job.server_job_id} complete — output ready`;
      dlLink.href = `${API_BASE}/api/download/${job.server_job_id}`;
      doneBar.style.display = 'flex';
    }
  }
}

function closeModal() {
  document.getElementById('jobModal').classList.remove('open');
}

/* ── TOAST ── */
function showToast(msg, duration = 3000) {
  const t = document.getElementById('runToast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), duration);
}

/* ── AGENT TOGGLE ── */
function toggleAgent() {
  agentRunning = !agentRunning;
  const btn = document.getElementById('agentToggleBtn');
  const dot = document.getElementById('agentDot');
  const state = document.getElementById('agentState');

  if (agentRunning) {
    btn.innerHTML = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> Pause Agent`;
    dot.style.background = 'var(--neon-green)';
    dot.style.boxShadow = '0 0 8px var(--neon-green)';
    state.textContent = `Running · ${JOBS.filter(j => j.status === 'running').length} tasks active`;
    state.style.color = 'var(--neon-green)';
  } else {
    btn.innerHTML = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Resume Agent`;
    dot.style.background = 'var(--amber)';
    dot.style.boxShadow = 'none';
    state.textContent = 'Paused · tasks held';
    state.style.color = 'var(--amber)';
  }
}

/* ── LIVE CLOCK ── */
function updateClock() {
  const now = new Date();
  const t = now.toTimeString().slice(0, 8);
  const el = document.getElementById('clock');
  if (el) el.textContent = t + ' UTC';
}
updateClock();
setInterval(updateClock, 1000);

/* ── TERMINAL TYPEWRITER ── */
const TERMINAL_LINES = [
  { cls: 'tl-d', text: `# ProofPilot Claude Agent — ${new Date().toISOString().slice(0, 10)}` },
  { blank: true },
  { cls: 'tl-p', text: 'proofpilot init --env production', isPrompt: true },
  { cls: 'tl-d', text: '  → Connecting to Railway backend...', d: 700 },
  { cls: 'tl-ok', text: '  ✓ Backend connected · claude-opus-4-6 ready', d: 1300 },
  { blank: true, d: 1700 },
  { cls: 'tl-p', text: 'proofpilot status --clients', d: 2100, isPrompt: true },
  { cls: 'tl-inf', text: `  ${CLIENTS.length} clients loaded · ${CLIENTS.filter(c => c.status === 'active').length} active · ${CLIENTS.filter(c => c.status === 'inactive').length} inactive`, d: 2700 },
  { blank: true, d: 3200 },
  { cls: 'tl-p', text: 'proofpilot workflows --list-active', d: 3600, isPrompt: true },
  { cls: 'tl-d', text: `  ${WORKFLOWS.filter(w => w.status === 'active').length} active workflows · ${WORKFLOWS.filter(w => w.status === 'soon').length} in pipeline`, d: 4200 },
  { blank: true, d: 4700 },
  { cls: 'tl-inf', text: '  ✓ Agent standing by — select a workflow above to run', d: 5200 },
];

function startTerminal() {
  const tb = document.getElementById('terminal');
  if (!tb) return;

  let li = 0, ci = 0, curDiv = null;

  function tick() {
    if (terminalStreaming) { setTimeout(tick, 1000); return; }
    if (!agentRunning) { setTimeout(tick, 500); return; }
    if (li >= TERMINAL_LINES.length) {
      setTimeout(() => {
        if (tb) tb.innerHTML = `<div class="tl-d"># ProofPilot Claude Agent — ${new Date().toISOString().slice(0, 10)}</div><br>`;
        li = 0; ci = 0; curDiv = null;
        setTimeout(tick, 1500);
      }, 4000);
      return;
    }
    const l = TERMINAL_LINES[li];
    if (l.blank) {
      if (tb) tb.appendChild(document.createElement('br'));
      li++; ci = 0; curDiv = null;
      setTimeout(tick, 80);
      return;
    }
    if (!curDiv) {
      curDiv = document.createElement('div');
      curDiv.className = l.cls;
      if (l.isPrompt) {
        const pfx = document.createElement('span');
        pfx.className = 't-prompt';
        pfx.textContent = '$ ';
        curDiv.appendChild(pfx);
      }
      if (tb) tb.appendChild(curDiv);
    }
    const old = curDiv.querySelector('.t-cursor');
    if (old) old.remove();
    if (ci < l.text.length) {
      curDiv.appendChild(document.createTextNode(l.text[ci]));
      ci++;
      const cur = document.createElement('span');
      cur.className = 't-cursor';
      curDiv.appendChild(cur);
      if (tb) tb.scrollTop = tb.scrollHeight;
      setTimeout(tick, l.isPrompt ? 34 : 10);
    } else {
      li++; ci = 0; curDiv = null;
      setTimeout(tick, l.isPrompt ? 220 : 70);
    }
  }
  setTimeout(tick, 600);
}

function clearTerminal() {
  const tb = document.getElementById('terminal');
  if (tb) tb.innerHTML = '<div class="tl-d"># ProofPilot terminal cleared</div><br>';
}

/* ── JOB PROGRESS SIMULATION ── */
setInterval(() => {
  JOBS.filter(j => j.status === 'running').forEach(job => {
    // Skip jobs that have an active SSE stream — real progress updates come from processSSEChunk()
    if (activeSSEJobs.has(job.id)) return;

    const inc = Math.random() * 2.5 + 0.5;
    jobProgresses[job.id] = Math.min(100, (jobProgresses[job.id] || 0) + inc);

    const pf = document.getElementById(`pf-${job.id}`);
    if (pf) pf.style.width = jobProgresses[job.id] + '%';

    if (jobProgresses[job.id] >= 100) {
      job.status = 'completed';
      job.duration = '8m 14s';
      job.output = 'Complete';
      if (currentView === 'jobs') renderJobs(jobFilter);
      if (currentView === 'dashboard') renderTaskQueue();
    }
  });
}, 2000);

/* ── EVENT LISTENERS ── */

// Nav clicks
document.querySelectorAll('.nav-item[data-view]').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    showView(item.dataset.view);
  });
});

// Job filter tabs
document.getElementById('jobFilterTabs')?.addEventListener('click', e => {
  if (e.target.classList.contains('filter-tab')) {
    renderJobs(e.target.dataset.filter);
  }
});

// Client search
document.getElementById('clientSearch')?.addEventListener('input', e => {
  renderClients(e.target.value.toLowerCase());
});

// Workflow client select
document.getElementById('wfClientSelect')?.addEventListener('change', () => {
  checkRunReady();
  onAuditClientChange();
});

// Workflow input fields — re-validate run button as user types
['wfBusinessType', 'wfLocation', 'wfKeyword', 'wfServiceFocus',
 'wfAuditDomain', 'wfAuditService', 'wfAuditLocation',
 'wfProspectName', 'wfProspectDomain', 'wfProspectService', 'wfProspectLocation',
 'wfGapDomain', 'wfGapService', 'wfGapLocation',
 'wfBlogBusinessType', 'wfBlogLocation', 'wfBlogKeyword',
 'wfSvcBusinessType', 'wfSvcService', 'wfSvcLocation',
 'wfLocBusinessType', 'wfLocPrimaryService', 'wfLocTargetLocation', 'wfLocHomeBase',
 'wfProgContentType', 'wfProgBusinessType', 'wfProgPrimaryService', 'wfProgLocation', 'wfProgHomeBase', 'wfProgItemsList'].forEach(id => {
  document.getElementById(id)?.addEventListener('input', checkRunReady);
});

/* ── INIT ── */
updateClientsBadge();
updateJobsBadge();
showView('dashboard');
startTerminal();
