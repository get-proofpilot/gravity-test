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
  /* ── ACTIVE SKILLS ── */
  { id: 'website-seo-audit',       icon: '🔍', title: 'Website & SEO Audit',        desc: 'Full technical SEO audit for home service businesses — performance, structure, local signals, and ranked opportunity list.',  time: '~8 min',  status: 'active', skill: 'website-seo-audit' },
  { id: 'seo-blog-generator',      icon: '✍️', title: 'SEO Blog Generator',          desc: 'Full SEO blog post workflow for service businesses — keyword-targeted, structured, and ready to publish.',                    time: '~6 min',  status: 'active', skill: 'seo-blog-generator' },
  { id: 'home-service-content',    icon: '🏠', title: 'Home Service SEO Content',    desc: 'SEO articles tuned for electricians, plumbers, HVAC, and other home service businesses. Built for local rank.',             time: '~5 min',  status: 'active', skill: 'home-service-seo-content' },
  { id: 'seo-strategy-sheet',      icon: '📊', title: 'SEO Strategy Spreadsheet',    desc: '14-tab SEO strategy workbook — keyword clusters, competitor gaps, content calendar, and priority matrix.',                   time: '~4 min',  status: 'active', skill: 'seo-strategy-spreadsheet' },
  { id: 'content-strategy-sheet',  icon: '📋', title: 'Content Strategy Spreadsheet',desc: 'Content ecosystem mapping with psychographic profiles, funnel stages, and distribution plan per channel.',                   time: '~5 min',  status: 'active', skill: 'content-strategy-spreadsheet' },
  { id: 'proposals',               icon: '📄', title: 'Client Proposals',            desc: 'Branded marketing proposals ready to send — scoped deliverables, pricing, and ProofPilot positioning built in.',             time: '~3 min',  status: 'active', skill: 'proofpilot-proposals' },
  { id: 'brand-styling',           icon: '🎨', title: 'Brand Styling',               desc: 'Applies ProofPilot brand standards to .docx and .xlsx deliverables — fonts, colors, headers, and polish.',                  time: '~2 min',  status: 'active', skill: 'proofpilot-brand' },
  { id: 'pnl-statement',           icon: '💰', title: 'P&L Statement',               desc: 'Monthly profit & loss statement generator — structured financials formatted and ready for review.',                           time: '~3 min',  status: 'active', skill: 'proofpilot-pnl' },
  { id: 'property-mgmt-strategy',  icon: '🏢', title: 'Property Mgmt Strategy',      desc: 'Website and SEO strategy for property management companies — local presence, lead gen focus, and conversion flow.',          time: '~6 min',  status: 'active', skill: 'property-management-website-strategy' },
  { id: 'frontend-design',         icon: '🖥️', title: 'Frontend Interface Builder',  desc: 'Production-grade UI components and pages — distinctive design, clean code, no generic AI aesthetics.',                     time: '~8 min',  status: 'active', skill: 'frontend-design' },
  { id: 'lovable-prompting',       icon: '⚡', title: 'Lovable App Builder',          desc: 'Expert Lovable.dev prompting to build full apps — structured flows that get clean, working results fast.',                  time: '~5 min',  status: 'active', skill: 'lovable-prompting' },
  /* ── COMING SOON ── */
  { id: 'backlink-outreach',       icon: '🔗', title: 'Backlink Outreach',           desc: 'Prospect link-building opportunities and generate personalized outreach emails at scale.',                                    time: '~12 min', status: 'soon' },
  { id: 'competitor-gap',          icon: '🎯', title: 'Competitor Gap Analysis',      desc: 'Find keywords competitors rank for that you don\'t — instant opportunity list with difficulty scores.',                      time: '~5 min',  status: 'soon' },
  { id: 'monthly-report',          icon: '📈', title: 'Monthly Client Report',        desc: 'White-label client report — GSC data, rankings, traffic wins, and recommendations bundled to send.',                        time: '~3 min',  status: 'soon' },
  { id: 'google-ads-copy',         icon: '📣', title: 'Google Ads Copy',             desc: 'High-converting search ad copy — headlines, descriptions, and extensions for service-based campaigns.',                     time: '~4 min',  status: 'soon' },
  { id: 'schema-generator',        icon: '🧩', title: 'Schema Generator',            desc: 'Auto-generate structured data markup for target pages — local business, FAQ, service, and article schemas.',                 time: '~2 min',  status: 'soon' },
];

const TASK_QUEUE = [
  { id: 'tq-1', name: 'Keyword Research — Full Crawl', client: 'techcorp.io · started 12m ago', status: 'running', tag: 'tt-running', time: '~8m left' },
  { id: 'tq-2', name: 'Link Outreach — Batch 2/4', client: 'growthlab.co · started 34m ago', status: 'running', tag: 'tt-running', time: '~3m left' },
  { id: 'tq-3', name: 'Technical Audit — LCP Fix Queue', client: 'meridian.agency · review req.', status: 'warn', tag: 'tt-warn', time: '–' },
  { id: 'tq-4', name: 'Monthly Reports × 3', client: 'Multiple clients · sched 06:00', status: 'queued', tag: 'tt-queued', time: '06:00' },
  { id: 'tq-5', name: 'Content Brief — "best SaaS tools"', client: 'nexusdigital.io · awaiting KW', status: 'blocked', tag: 'tt-blocked', time: '–' },
];

const COMPLETIONS = [
  { task: 'Keyword Cluster Report', client: 'techcorp.io', type: 'cp-kw', typeLabel: 'Keywords', outcome: '<strong>847</strong> opportunities', time: '2h ago' },
  { task: 'Blog Reoptimization ×5', client: 'growthlab.co', type: 'cp-con', typeLabel: 'Content', outcome: '<strong>+18%</strong> avg word score', time: '4h ago' },
  { task: 'Outreach Batch 1/4', client: 'meridian.agency', type: 'cp-link', typeLabel: 'Links', outcome: '<strong>63</strong> sent · <strong>9</strong> replies', time: '5h ago' },
  { task: 'Core Web Vitals Audit', client: 'nexusdigital.io', type: 'cp-tech', typeLabel: 'Technical', outcome: '<strong>47</strong> issues found', time: '7h ago' },
  { task: 'February Client Report', client: 'apexretail.com', type: 'cp-rep', typeLabel: 'Report', outcome: 'Delivered to client', time: '9h ago' },
];

const ALERTS = [
  { type: 'warn', msg: '<strong>Review required</strong> — Technical audit found LCP regression on meridian.agency/pricing. Agent waiting for approval before queuing fixes.', time: '38 minutes ago' },
  { type: 'warn', msg: '<strong>Apex Retail</strong> ranking score dropped 3pts. Agent flagged 2 pages losing position to new competitor content.', time: '2 hours ago' },
  { type: 'ok', msg: '<strong>18 backlinks</strong> secured for Orbis Health and NexusDigital this week — above target by 3.', time: '4 hours ago' },
  { type: 'info', msg: 'Monthly reports for <strong>6 clients</strong> scheduled for 06:00 UTC delivery tomorrow.', time: '6 hours ago' },
];

const ADS = [
  { label: 'A', headline: 'Protect What You\'ve Built', type: 'Lead Magnet', platform: 'Facebook Feed', status: 'ap-live', statusLabel: 'Live', bg: 'linear-gradient(135deg,#003380,#0051FF)' },
  { label: 'B', headline: 'Dominate Local Search', type: 'Brand Awareness', platform: 'Google Display', status: 'ap-live', statusLabel: 'Live', bg: 'linear-gradient(135deg,#001030,#00184D)' },
  { label: 'C', headline: '47% More Leads in 60 Days', type: 'Retargeting', platform: 'FB + IG Story', status: 'ap-review', statusLabel: 'Review', bg: 'linear-gradient(135deg,#1a0a00,#3a1a00)' },
  { label: 'D', headline: 'Your Competitors Found a Cheat', type: 'Lead Gen', platform: 'LinkedIn', status: 'ap-draft', statusLabel: 'Draft', bg: 'linear-gradient(135deg,#0a0a1a,#1a1a3a)' },
];

const JOBS = [
  { id: 'JOB-4821', wf: 'Full Site Audit', client: 'TechCorp', started: '12m ago', duration: '6m 12s', status: 'running', pct: 82, output: 'In progress...' },
  { id: 'JOB-4820', wf: 'Keyword Research', client: 'Growth Labs', started: '34m ago', duration: '4m 02s', status: 'running', pct: 65, output: 'In progress...' },
  { id: 'JOB-4819', wf: 'Monthly Report', client: 'Meridian', started: '1h ago', duration: '3m 18s', status: 'running', pct: 49, output: 'In progress...' },
  { id: 'JOB-4818', wf: 'Content Brief', client: 'NexusDigital', started: '2h ago', duration: '5m 47s', status: 'completed', pct: 100, output: '3 briefs → Notion' },
  { id: 'JOB-4817', wf: 'Backlink Outreach', client: 'Orbis Health', started: '3h ago', duration: '8m 33s', status: 'completed', pct: 100, output: '8 emails sent' },
  { id: 'JOB-4816', wf: 'Rank Monitor Sweep', client: 'Apex Retail', started: '4h ago', duration: '2m 01s', status: 'completed', pct: 100, output: 'Report saved' },
  { id: 'JOB-4815', wf: 'Keyword Research', client: 'SolarVerde', started: '5h ago', duration: '–', status: 'failed', pct: 0, output: 'GSC token expired' },
];

const LOG_ENTRIES = [
  { time: '22:44:31', level: 'ok', msg: 'JOB-4818 completed — 3 content briefs pushed to Notion for NexusDigital' },
  { time: '22:44:12', level: 'info', msg: 'JOB-4820 started — Keyword research for Growth Labs (3,841 seeds)' },
  { time: '22:43:55', level: 'ok', msg: 'JOB-4817 completed — 8 outreach emails sent for Orbis Health' },
  { time: '22:41:10', level: 'warn', msg: 'JOB-4819 LCP regression detected on meridian.agency/pricing (4.1s) — pausing, review required' },
  { time: '22:38:47', level: 'err', msg: 'JOB-4815 failed — GSC token expired for SolarVerde. Action required.' },
  { time: '22:35:00', level: 'info', msg: 'Monthly report emailed to client@meridian.agency' },
  { time: '22:30:14', level: 'ok', msg: 'New client added: Voxel Labs — onboarding workflow queued' },
  { time: '22:28:55', level: 'info', msg: 'Agent connected to Ahrefs API — 8 client domains synced' },
];

const REPORTS = [
  { type: 'Monthly Report', title: 'February 2026 — TechCorp SEO Report', client: 'techcorp.io', date: 'Feb 18, 2026' },
  { type: 'Audit Report', title: 'Full Site Audit — Growth Labs', client: 'growthlab.co', date: 'Feb 16, 2026' },
  { type: 'Monthly Report', title: 'February 2026 — NexusDigital Report', client: 'nexusdigital.io', date: 'Feb 15, 2026' },
  { type: 'Technical', title: 'Core Web Vitals Fix Plan — Meridian', client: 'meridian.agency', date: 'Feb 14, 2026' },
  { type: 'Monthly Report', title: 'February 2026 — SolarVerde Report', client: 'solarverde.com', date: 'Feb 13, 2026' },
  { type: 'Keyword Report', title: 'Keyword Cluster Map — Orbis Health', client: 'orbishealth.io', date: 'Feb 12, 2026' },
];

const CONTENT = [
  { type: 'Content Brief', title: '"Best SaaS Tools 2026" — Cluster Brief', client: 'nexusdigital.io', words: '1,240' },
  { type: 'Full Draft', title: 'Local SEO Guide for HVAC Companies', client: 'techcorp.io', words: '3,800' },
  { type: 'Content Brief', title: '"Gold IRA vs 401k" — Comparison Page', client: 'solarverde.com', words: '980' },
  { type: 'Blog Post', title: 'How to Fix Core Web Vitals in 7 Steps', client: 'meridian.agency', words: '2,100' },
  { type: 'Landing Page', title: 'Emergency Plumbing Services — Phoenix, AZ', client: 'orbishealth.io', words: '640' },
  { type: 'Full Draft', title: 'Backlink Outreach Templates That Get Replies', client: 'growthlab.co', words: '1,750' },
];

/* job progress simulation */
const jobProgresses = {};
JOBS.forEach(j => { jobProgresses[j.id] = j.pct; });

/* ── VIEW ROUTING ── */
let currentView = 'dashboard';
let selectedWorkflow = null;
let agentRunning = true;

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
    logs: 'Activity Log', ads: 'Ad Studio', campaigns: 'Campaigns'
  };
  if (title) title.textContent = titles[viewId] || viewId;

  currentView = viewId;

  if (viewId === 'dashboard') renderDashboard();
  if (viewId === 'workflows') renderWorkflows();
  if (viewId === 'clients') renderClients();
  if (viewId === 'jobs') renderJobs('all');
  if (viewId === 'reports') renderReports();
  if (viewId === 'content') renderContent();
  if (viewId === 'logs') renderLogs();
  if (viewId === 'ads') renderAds();
}

/* ── DASHBOARD ── */
function renderDashboard() {
  renderTaskQueue();
  renderCompletions();
  renderRoster();
  renderAlerts();
  renderAdPreview();
}

function renderTaskQueue() {
  const el = document.getElementById('dashTaskQueue');
  if (!el) return;
  el.innerHTML = TASK_QUEUE.map(t => `
    <div class="task-item">
      <div class="task-dot ${dotClass(t.status)}"></div>
      <div class="task-info">
        <div class="task-name">${t.name}</div>
        <div class="task-client">${t.client}</div>
      </div>
      <div class="task-right">
        <span class="task-tag ${t.tag}">${tagLabel(t.status)}</span>
        <span class="task-time">${t.time}</span>
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
  el.innerHTML = COMPLETIONS.map(c => `
    <tr>
      <td>${c.task}</td>
      <td style="color:var(--text3);font-family:var(--mono);font-size:10px;">${c.client}</td>
      <td><span class="c-pill ${c.type}">${c.typeLabel}</span></td>
      <td class="c-outcome">${c.outcome}</td>
      <td style="color:var(--text3);font-family:var(--mono);font-size:10px;">${c.time}</td>
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
          <div class="roster-name">${c.name}</div>
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
  el.innerHTML = ALERTS.map(a => `
    <div class="alert-item">
      <div class="alert-icon ai-${a.type}">${a.type === 'warn' ? '!' : a.type === 'ok' ? '✓' : 'i'}</div>
      <div>
        <div class="alert-text">${a.msg}</div>
        <div class="alert-time" style="font-family:var(--mono);font-size:9px;color:var(--text3);margin-top:2px;">${a.time}</div>
      </div>
    </div>
  `).join('');
}

function renderAdPreview() {
  const el = document.getElementById('dashAdList');
  if (!el) return;
  el.innerHTML = ADS.map(a => `
    <div class="ad-item" onclick="showView('ads')">
      <div class="ad-swatch" style="background:${a.bg};">${a.label}</div>
      <div class="ad-info">
        <div class="ad-headline">${a.headline}</div>
        <div class="ad-meta"><span>${a.type}</span><span>·</span><span>${a.platform}</span></div>
      </div>
      <div><span class="ad-pill ${a.status}">${a.statusLabel}</span></div>
    </div>
  `).join('');
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

  const active = WORKFLOWS.filter(w => w.status === 'active');
  const soon   = WORKFLOWS.filter(w => w.status === 'soon');

  const activeCards = active.map(wf => `
    <div class="wf-card" data-id="${wf.id}" onclick="selectWorkflow('${wf.id}')">
      <div class="wf-card-header">
        <span class="wf-card-icon">${wf.icon}</span>
        <span class="wf-skill-tag">${wf.skill}</span>
      </div>
      <div class="wf-card-title">${wf.title}</div>
      <div class="wf-card-desc">${wf.desc}</div>
      <div class="wf-card-time">⏱ ${wf.time}</div>
    </div>
  `).join('');

  const soonCards = soon.map(wf => `
    <div class="wf-card soon" data-id="${wf.id}">
      <div class="wf-card-header">
        <span class="wf-card-icon">${wf.icon}</span>
        <span class="wf-soon-badge">SOON</span>
      </div>
      <div class="wf-card-title">${wf.title}</div>
      <div class="wf-card-desc">${wf.desc}</div>
      <div class="wf-card-time">⏱ ${wf.time}</div>
    </div>
  `).join('');

  el.innerHTML = `
    <div class="wf-section-label">ACTIVE SKILLS — ${active.length} BUILT</div>
    ${activeCards}
    <div class="wf-section-label">COMING SOON — ${soon.length} IN PIPELINE</div>
    ${soonCards}
  `;
}

function selectWorkflow(id) {
  const wf = WORKFLOWS.find(w => w.id === id);
  if (!wf || wf.status === 'soon') return;

  selectedWorkflow = id;
  document.querySelectorAll('.wf-card').forEach(c => c.classList.remove('selected'));
  const card = document.querySelector(`.wf-card[data-id="${id}"]`);
  if (card) card.classList.add('selected');

  document.getElementById('wfRunIcon').textContent = wf.icon;
  document.getElementById('wfRunTitle').textContent = wf.title;
  document.getElementById('wfRunDesc').textContent = wf.desc;

  checkRunReady();
}

function checkRunReady() {
  const clientVal = document.getElementById('wfClientSelect')?.value;
  const btn = document.getElementById('wfRunBtn');
  if (btn) btn.disabled = !(clientVal && selectedWorkflow);
}

function launchWorkflow() {
  const clientSel = document.getElementById('wfClientSelect');
  const clientVal = clientSel?.value;
  if (!clientVal || !selectedWorkflow) return;

  const wf = WORKFLOWS.find(w => w.id === selectedWorkflow);
  const client = clientSel.options[clientSel.selectedIndex].text;

  const newJob = {
    id: `JOB-${4822 + JOBS.length}`,
    wf: wf.title,
    client,
    started: 'just now',
    duration: '–',
    status: 'running',
    pct: 0,
    output: 'Starting...'
  };
  JOBS.unshift(newJob);
  jobProgresses[newJob.id] = 0;

  showToast(`▷ ${wf.title} launched for ${client}`);

  // Add log entry
  const now = new Date();
  const timeStr = now.toTimeString().slice(0, 8);
  LOG_ENTRIES.unshift({ time: timeStr, level: 'info', msg: `${newJob.id} started — ${wf.title} for ${client}` });
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
            <span style="font-weight:600;color:var(--text);">${c.name}</span>
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
        <td>
          <button class="tbl-btn" onclick="showView('workflows')" ${isActive ? '' : 'disabled'}>Run</button>
        </td>
      </tr>
    `;
  }).join('');
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
        <td style="color:var(--text3);">${j.client}</td>
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

/* ── CONTENT ── */
function renderContent() {
  const el = document.getElementById('contentGrid');
  if (!el) return;
  el.innerHTML = CONTENT.map(c => `
    <div class="content-card">
      <div class="rc-type">${c.type}</div>
      <div class="rc-title">${c.title}</div>
      <div class="rc-client">${c.client} · ${c.words} words</div>
      <div class="rc-actions">
        <button class="rc-btn rc-btn-primary">Open</button>
        <button class="rc-btn rc-btn-ghost">Export</button>
      </div>
    </div>
  `).join('');
}

/* ── LOGS ── */
function renderLogs() {
  const el = document.getElementById('logStream');
  if (!el) return;
  el.innerHTML = LOG_ENTRIES.map(entry => `
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
  el.innerHTML = ADS.map(a => `
    <div class="ad-card">
      <div class="ad-card-preview" style="background:${a.bg};">
        <div class="ad-card-headline">${a.headline}</div>
      </div>
      <div class="ad-card-body">
        <div>
          <div class="ad-card-meta">${a.type}</div>
          <div class="ad-card-platform">${a.platform}</div>
        </div>
        <span class="ad-pill ${a.status}">${a.statusLabel}</span>
      </div>
    </div>
  `).join('');
}

/* ── JOB MODAL ── */
function openJobModal(jobId) {
  const job = JOBS.find(j => j.id === jobId);
  if (!job) return;

  document.getElementById('modalTitle').textContent = `${job.id} — ${job.wf}`;
  document.getElementById('modalBody').innerHTML = `
    <div class="modal-row"><span class="modal-label">JOB ID</span><span class="modal-val" style="font-family:var(--mono);color:var(--elec-blue);">${job.id}</span></div>
    <div class="modal-row"><span class="modal-label">WORKFLOW</span><span class="modal-val">${job.wf}</span></div>
    <div class="modal-row"><span class="modal-label">CLIENT</span><span class="modal-val">${job.client}</span></div>
    <div class="modal-row"><span class="modal-label">STARTED</span><span class="modal-val" style="font-family:var(--mono);">${job.started}</span></div>
    <div class="modal-row"><span class="modal-label">DURATION</span><span class="modal-val" style="font-family:var(--mono);">${job.duration}</span></div>
    <div class="modal-row"><span class="modal-label">STATUS</span><span class="modal-val">${job.status.toUpperCase()}</span></div>
    <div class="modal-row"><span class="modal-label">PROGRESS</span><span class="modal-val" style="color:var(--neon-green);">${Math.round(jobProgresses[job.id] || job.pct)}%</span></div>
    <div class="modal-row"><span class="modal-label">OUTPUT</span><span class="modal-val">${job.output}</span></div>
  `;

  document.getElementById('jobModal').classList.add('open');
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
    state.textContent = 'Running · 3 tasks active';
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
  { cls: 'tl-d', text: '# ProofPilot Claude Agent — Session 2026-02-18' },
  { blank: true },
  { cls: 'tl-p', text: 'proofpilot run --all-clients', isPrompt: true },
  { cls: 'tl-d', text: '  Connecting to Ahrefs API...', d: 700 },
  { cls: 'tl-inf', text: '  ✓ Connected · pulling keyword data', d: 1300 },
  { blank: true, d: 1700 },
  { cls: 'tl-p', text: 'task:kw-research client=techcorp.io', d: 2100, isPrompt: true },
  { cls: 'tl-d', text: '  → Analyzing 1,204 keyword candidates...', d: 2700 },
  { cls: 'tl-ok', text: '  ✓ 847 opportunities clustered by topic', d: 3600 },
  { blank: true, d: 4000 },
  { cls: 'tl-p', text: 'task:outreach client=growthlab.co batch=2', d: 4400, isPrompt: true },
  { cls: 'tl-d', text: '  → Personalizing 63 outreach emails...', d: 5000 },
  { cls: 'tl-d', text: '  → Sending via SMTP (throttled)...', d: 5700 },
  { cls: 'tl-ok', text: '  ✓ 63 sent · 9 new replies in inbox', d: 6600 },
  { blank: true, d: 7000 },
  { cls: 'tl-p', text: 'task:audit client=meridian.agency', d: 7400, isPrompt: true },
  { cls: 'tl-d', text: '  → Running Core Web Vitals checks...', d: 8000 },
  { cls: 'tl-w', text: '  ⚠ LCP regression on /pricing (4.1s)', d: 8700 },
  { cls: 'tl-w', text: '  Pausing — human review required', d: 9200 },
  { blank: true, d: 9600 },
  { cls: 'tl-p', text: 'task:content-audit client=nexusdigital.io', d: 10000, isPrompt: true },
  { cls: 'tl-d', text: '  → Scoring 156 pages vs SERP benchmarks...', d: 10600 },
  { cls: 'tl-ok', text: '  ✓ 34 pages queued for reoptimization', d: 11500 },
  { blank: true, d: 11900 },
  { cls: 'tl-inf', text: '  All tasks running. Next check: 06:00 UTC', d: 12300 },
];

function startTerminal() {
  const tb = document.getElementById('terminal');
  if (!tb) return;

  let li = 0, ci = 0, curDiv = null;

  function tick() {
    if (!agentRunning) { setTimeout(tick, 500); return; }
    if (li >= TERMINAL_LINES.length) {
      setTimeout(() => {
        if (tb) tb.innerHTML = '<div class="tl-d"># ProofPilot Claude Agent — Session 2026-02-18</div><br>';
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
document.getElementById('wfClientSelect')?.addEventListener('change', checkRunReady);

/* ── INIT ── */
showView('dashboard');
startTerminal();
