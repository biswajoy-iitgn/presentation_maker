# 26. Client-facing UI and user stories

`13` defines the frontend stack and code layout. This document defines who the product is for, what they need to do, the user stories with acceptance criteria, the screens and their interactions, and the API additions the stories require. P9 tickets implement these stories, and Playwright journeys (`25`, section 9) test them.

## 1. Personas

| Id | Persona | Context | Main job | Success for them |
|---|---|---|---|---|
| P1 | Strategy manager (primary) | corporate strategy or transformation office, builds board and leadership decks every month | turn a question and some data into a board-ready deck fast, keep control of the storyline | a deck they would present after light edits, in under an hour of their own time |
| P2 | Analyst | prepares data, iterates slides, checks numbers | get the numbers right and traceable, fix slides quickly | every number traceable, revisions in seconds or minutes |
| P3 | Executive reviewer | CXO or business head who reviews and approves | understand the story, comment, approve | a clear storyline, comments addressed |
| P4 | Brand owner | marketing or communications | keep decks on brand | template adopted correctly, no off-brand slides |
| P5 | Org admin | IT or ops | deploy, manage users, keys, data policies | secure, on-prem, auditable, predictable cost |
| P6 | Integration developer | builds internal tools | create decks from other systems | stable API, webhooks, A2A and MCP access |
| P7 | Solo consultant (lite mode) | one person on a laptop | professional decks without a server | installs in minutes, runs offline |

## 2. Core journeys

| Journey | Steps | Personas |
|---|---|---|
| J1 First deck | sign in, create project, upload data, write brief, answer questions, approve storyline, review deck, revise two slides, download PPTX | P1, P2 |
| J2 Monthly refresh | duplicate last month's project, replace data file, regenerate with the same storyline, compare versions, download | P1, P2 |
| J3 Review and approve | open shared deck, read storyline, comment on slides, see comments resolved, approve | P3 |
| J4 Brand setup | upload template, review extracted design system, adjust colours and fonts, set as org default | P4 |
| J5 Admin setup | install, invite users, set roles, configure SSO, set data policies, view usage | P5 |
| J6 API generation | create API key, call API (or A2A) with brief and data, receive webhook, fetch PPTX | P6 |
| J7 Laptop install | install, doctor picks tier, first deck offline | P7 |

## 3. User stories

Format: `US-<epic>.<n>`, persona, story, acceptance criteria (AC, testable). Every story maps to tickets in `18` and a Playwright journey.

### E1 Workspace and onboarding

**US-1.1 (P1)** As a strategy manager, I want to create a project with a name and description, so that briefs, data and decks for one engagement stay together.
- AC1: Given I am an editor, when I create a project, then it appears at the top of my project list within 1 second.
- AC2: The project page shows tabs Briefs, Data, Design, Decks, with empty states that explain the next action.

**US-1.2 (P1)** I want to duplicate a project with its brief, storyline and design choice but new data, so that monthly refreshes take minutes.
- AC1: Duplicate copies briefs, design system choice and the last approved plan, not decks or data files.
- AC2: A banner asks me to upload new data files.

**US-1.3 (P7)** As a solo consultant, I want a first-run wizard that checks my machine and picks the right model, so that I can start without technical knowledge.
- AC1: The wizard shows detected RAM, GPU and the chosen tier (`22`, section 5), and whether LibreOffice is present.
- AC2: Missing pieces have one-click instructions for my OS.

### E2 Data

**US-2.1 (P2)** As an analyst, I want to drag and drop Excel or CSV files and see each table understood (columns, types, units), so that I trust what the system will use.
- AC1: Upload shows progress, then a profile per table within 30 seconds for files under 10 MB.
- AC2: Each column shows type, unit and sample values. Low-confidence columns are highlighted.
- AC3: Rejected files show the reason in plain words (macro file, encrypted, too large).

**US-2.2 (P2)** I want to correct a column's type or unit, so that analyses use the right meaning.
- AC1: Editing a type saves immediately and shows "used in the next run".
- AC2: The correction is recorded as a training label (no visible effect for the user).

**US-2.3 (P2)** I want warnings about data problems (missing periods, totals that do not add up, duplicates), so that I can fix the source before generating.
- AC1: The data analyst summary lists problems with the affected rows.

### E3 Brief

**US-3.1 (P1)** I want a guided brief form (topic, audience, decision asked, what to show, slide range, data, style), so that I give the system what it needs.
- AC1: Required fields are topic and audience. Everything else is optional with helpful placeholders.
- AC2: A brief quality meter shows gaps (audience, decision, data sufficiency, time horizon) as I type, from Laya gap checks, updated within 1 second of pausing.

**US-3.2 (P1)** I want to attach reference documents (PDF, DOCX), so that the deck uses our internal material.
- AC1: Attached documents show extraction status and page count. Pages with injected instructions are flagged as quarantined.

**US-3.3 (P1)** I want to choose research on or off, and dummy data on or off, so that I control external access and placeholders.
- AC1: Research is disabled with an explanation when the org policy forbids it.
- AC2: When dummy data is allowed, the brief summary warns which analyses lack data.

### E4 Generation and live progress

**US-4.1 (P1)** I want to start generation and see progress by stage with time estimates, so that I know what is happening.
- AC1: The run page shows stages (understand, plan, ground, compose, render, assure) with the current step and a live count (for example "Composing slides 6 of 15").
- AC2: Updates arrive within 1 second of the event (SSE). After a network drop the page reconnects and catches up without losing events.

**US-4.2 (P1)** I want slides to appear as they are rendered, so that I can start reading before the run ends.
- AC1: Slide thumbnails fill in as `slide.rendered` events arrive.

**US-4.3 (P1)** I want to cancel a run, so that I can stop a run with a wrong brief.
- AC1: Cancel takes effect within 10 seconds and the run shows "cancelled" with the partial plan kept.

### E5 Clarifications and storyline review

**US-5.1 (P1)** I want to answer clarifying questions in one place with the reason each was asked, so that the system plans correctly.
- AC1: At most three questions, each with a "why" line and suggested answers where possible.
- AC2: I can skip a question, and the plan records the assumption it made.

**US-5.2 (P1)** I want to review the storyline as a board of slide cards (governing thought, sections, slide intents, frameworks, data status) before slides are built, so that I fix the logic early.
- AC1: I can edit text, reorder cards by drag or keyboard, delete and add slides, change a framework from a shortlist.
- AC2: Each card shows data status (provided, research, dummy) with colour and text, never colour alone.
- AC3: Approve continues the run. "Ask to revise" with an instruction re-plans and returns to this board.
- AC4: Invalid edits (for example removing the executive summary) show the validator message inline.

### E6 Deck studio: review and revise

**US-6.1 (P1)** I want a deck studio with a large slide view, a filmstrip and a side panel (facts, sources, QA, comments, history), so that I review efficiently.
- AC1: Arrow keys move between slides. The large view loads in under 300 ms from cache.

**US-6.2 (P1)** I want to ask for a change in plain words on a slide or the whole deck ("make the title sharper", "show this as a map", "add a slide on pricing"), so that I revise without editing PowerPoint.
- AC1: The request shows who is handling it (for example "Copywriter") and progress.
- AC2: A new deck version appears with the changed slides marked. Unchanged slides keep their content.
- AC3: Typical slide-level revisions finish in under 60 seconds on the reference server.

**US-6.3 (P2)** I want to edit a title or commentary point inline, so that small wording fixes are instant.
- AC1: Inline edits create a new version without an LLM call, re-run checks on that slide, and show any new defects.
- AC2: Numbers typed by hand that do not match a fact are flagged.

**US-6.4 (P1)** I want to see two or three alternative versions of a key slide and pick one, so that I choose the strongest framing.
- AC1: Alternatives are ranked (best first) with their QA scores. Choosing one creates a new version.

**US-6.5 (P1)** I want to compare two deck versions side by side, so that I see what changed.
- AC1: Changed slides are listed. For each, before and after snapshots and a text diff of title and commentary.

**US-6.6 (P2)** I want to undo a revision by restoring a previous version, so that mistakes are cheap.
- AC1: Restore creates a new version identical to the chosen one.

### E7 Trust: facts, sources, QA

**US-7.1 (P2)** I want every number on a slide to show where it came from (data cell, calculation, research citation or dummy), so that I can defend it.
- AC1: Clicking a number shows its fact id, value, provenance and, for research, the source with quote and date.
- AC2: Dummy values carry an ILLUSTRATIVE sticker on the slide and a list in the side panel.

**US-7.2 (P1)** I want QA findings shown on the slide with the problem area outlined and plain-language evidence, so that I understand what is wrong.
- AC1: Findings show severity, standard, evidence and a box on the snapshot.
- AC2: I can dismiss a finding as "accepted" with a reason. Dismissals are recorded.

**US-7.3 (P1)** I want to see what the system fixed automatically, so that I trust the QA loop.
- AC1: A history trail per slide lists findings, owner agent, attempts and outcome.

**US-7.4 (P3)** I want a reasoning view (problem, issue tree, frameworks and why they were chosen), so that I can judge the logic.
- AC1: The plan report renders with framework cards and decisions with confidence.

### E8 Export and hand-off

**US-8.1 (P1)** I want to download an editable PPTX that opens cleanly in PowerPoint, so that I can finish and present.
- AC1: Charts are editable, text is editable, the template's masters are used, notes contain sources.

**US-8.2 (P1)** I want PDF and PNG exports, so that I can share read-only copies.
- AC1: Export options for PDF and a ZIP of PNGs.

**US-8.3 (P2)** I want an Excel file of the data behind every chart, so that finance can verify.
- AC1: One sheet per exhibit with the exact series used.

### E9 Brand and templates

**US-9.1 (P4)** I want to upload our PowerPoint template and see how DeckForge interprets it, so that decks look like ours.
- AC1: The design studio shows extracted colours with roles, fonts, layouts and logo, plus a 6-slide preview.
- AC2: Warnings for low-contrast colours and missing fonts, with automatic adjustments listed.

**US-9.2 (P4)** I want to adjust colours, fonts and the layout map and set the template as the org default, so that every new project uses it.
- AC1: Each save creates a new design-system version and refreshes the preview.

### E10 Collaboration

**US-10.1 (P1)** I want to share a project with colleagues as viewer or editor, so that we work together.
- AC1: Shared users see the project in their list with the granted role.

**US-10.2 (P3)** I want to comment on a slide or an area of a slide, so that feedback is specific.
- AC1: Comments anchor to an element or a drawn box, support replies, and can be resolved.

**US-10.3 (P1)** I want to turn a comment into a revision request with one click, so that feedback is acted on.
- AC1: The revision uses the comment text as the instruction and links back to the comment.

**US-10.4 (P3)** I want to mark a deck version approved, so that the team knows which version is final.
- AC1: Approval records approver and time, and the version shows an "Approved" badge.

### E11 Administration and governance

**US-11.1 (P5)** I want to manage members and roles, so that access is controlled.
**US-11.2 (P5)** I want SSO with our identity provider, so that users sign in with company accounts.
**US-11.3 (P5)** I want to set data policies (research allowed, retention days, training on our data allowed), so that we comply with internal rules.
- AC1: The admin page shows which external services the org's data can reach under current settings.

**US-11.4 (P5)** I want usage and capacity dashboards (runs, tokens, GPU time, queue), so that I can plan capacity.
**US-11.5 (P4)** I want to maintain house rules and terminology (preferred terms, banned phrases, disclaimers), so that every deck follows them.
- AC1: Org knowledge cards (`28`, section 10) can be created, edited, exported and imported as YAML.

**US-11.6 (P5)** I want an audit log, so that I can answer who did what.

### E12 API and integrations

**US-12.1 (P6)** I want API keys with scopes, so that integrations are secure.
**US-12.2 (P6)** I want to create a run with a brief and files in one API call and get a webhook when it finishes, so that I can automate decks.
- AC1: Webhook payloads are signed and retried (`05`, section 6.6).

**US-12.3 (P6)** I want DeckForge available to our agent platform over A2A and MCP, so that our agents can request decks.
- AC1: The Agent Card is served at `/.well-known/agent-card.json` and the `generate_deck` skill works end to end.

### E13 Notifications

**US-13.1 (P1)** I want a notification when a run needs my input or finishes, so that I do not watch the screen.
- AC1: In-app notifications always. Email when configured by the admin.

## 4. Information architecture

```text
Top bar: Projects | Knowledge (house style) | Admin (admins) | Help | user menu
Projects
└── Project
    ├── Briefs ── Brief composer
    ├── Data ── File profile
    ├── Design ── Design studio
    └── Decks ── Run page (progress, questions, storyline board)
                 └── Deck studio (slides, side panel, compare, export)
Knowledge: org cards (house rules, terminology, preferred frameworks)
Admin: Members, SSO, Policies, API keys, Credentials, Usage, Audit, Decision models (read-only), Gold review (superadmin)
```

## 5. Key screens (wireframes)

### 5.1 Brief composer

```text
+----------------------------------------------------------------------------------+
| < Project: Margin recovery                                   [Save draft] [Generate] |
+----------------------------------------------+-----------------------------------+
| Topic *  [Restoring EBITDA margin to 15%    ]| Brief quality                     |
| Audience * (Board v)   Deck type (auto v)    |  Audience        clear            |
| Decision asked [Approve the 3-wave plan     ]|  Decision asked  clear            |
| What to show  [margin bridge] [peer gap] [+] |  Data            2 gaps  (details)|
| Requirements                                 |  Time horizon    missing          |
| [ textarea with guidance placeholder       ] |                                   |
| Slides  [8] to [16]   Language (English v)   | Data files                        |
| Style   (Org template: Acme 2026 v)          |  [x] financials_fy25.xlsx  ready  |
| Research [off]  Dummy data [on]              |  [x] plants.csv            ready  |
| Ask clarifying questions [on]  Auto-approve [off]| References                    |
|                                              |  [x] board_memo.pdf  12 pages     |
+----------------------------------------------+-----------------------------------+
```

### 5.2 Run page with storyline board

```text
+--------------------------------------------------------------------------------------+
| Restoring EBITDA margin to 15%    Waiting for your review    04:12    [Cancel]        |
+----------------------+---------------------------------------------------------------+
| Understand   done    | Governing thought: [Margin can recover to 14.4% within 24 months]|
| Plan         review  | S: [...]  C: [...]  R: [...]                                     |
| Ground       -       |                                                                 |
| Compose      -       | Section 1 Diagnosis          Section 2 Benchmark               |
| Render       -       | +-------------------------+  +-------------------------+        |
| Assure       -       | | 4 Revenue vs margin      |  | 7 Peer gap on 6 drivers |        |
|                      | | F051 columns over line   |  | F040 gap bars           |        |
| Questions answered 2 | | data: provided           |  | data: provided          |        |
| Assumptions 1        | +-------------------------+  +-------------------------+        |
|                      | | 5 Margin bridge          |  | 8 Plant map             |        |
|                      | | F050 waterfall  provided |  | F072 site map  dummy    |        |
|                      | +-------------------------+  +-------------------------+        |
|                      |                       [Ask to revise...]  [Save edits] [Approve] |
+----------------------+---------------------------------------------------------------+
```

### 5.3 Deck studio

```text
+--------------------------------------------------------------------------------------------+
| Margin recovery  v3  QA 88 pass  [Compare v2] [Alternatives] [Approve] [Export v]           |
+----+-------------------------------------------------------------+-------------------------+
| 1  |                                                             | Facts | Sources | QA (2) |
| 2  |                 [ large slide preview 16:9 ]                |   | Comments (1) | History|
| 3  |       QA boxes overlaid when the QA tab is open             |-------------------------|
| 4> |                                                             | ! major DS-CHART-03     |
| 5  |                                                             |  Map crowded (box)      |
| 6  |                                                             |  Owner: Viz designer    |
| .. |                                                             |  [Fix] [Accept]         |
|    | Title: Pune and Chakan account for 89% of ... [edit]        |-------------------------|
|    +-------------------------------------------------------------+ Ask for a change:       |
|    | Ask for a change on this slide [ show fewer labels on the ] | [ text            ][Go] |
+----+-------------------------------------------------------------+-------------------------+
```

### 5.4 Design studio

```text
+--------------------------------------------------------------------------------------+
| Design: Acme 2026 template  v2      [Set as org default]                              |
+-----------------------------+--------------------------------------------------------+
| Colours                     | Preview (6 sample slides)                              |
|  ink      #0B1F3A  AA ok    |  [cover] [agenda] [exhibit] [kpi sidebar] [matrix] [decisions] |
|  accent   #E4002B  AA ok    |                                                        |
|  negative #B42318  adjusted |                                                        |
| Fonts                       | Warnings                                               |
|  titles  Acme Serif -> Gelasio for previews | accent2 too light for text, darkened   |
|  body    Arial               |                                                        |
| Layout map                  |                                                        |
|  exhibit -> "Title and Content" v                                                     |
+-----------------------------+--------------------------------------------------------+
```

## 6. Interaction details

| Interaction | Behaviour |
|---|---|
| Revision request | Free text plus optional slide selection. Shows routed agent and scope, then progress. Result opens the compare view for changed slides |
| Inline edit | Click title or commentary to edit. Enter saves. Validation of facts tokens runs on save. A typed number not matching a fact shows a warning with "link to fact" |
| Alternatives | Up to 3 variants per slide in a horizontal strip with QA score. Hover shows differences |
| QA overlay | Toggle in the QA tab. Boxes coloured by severity with icons and labels (never colour alone) |
| Comments | Select an element or draw a box, type, post. Mentions notify users. Resolve hides the thread |
| Keyboard | Left and right slides, `E` edit title, `C` comment, `R` revision box, `?` shortcut list |
| Autosave | Drafts of briefs and plan edits save every 3 seconds to the server |

## 7. States, performance and accessibility

| Topic | Rule |
|---|---|
| Empty states | every list explains the next action with one primary button |
| Loading | skeletons for lists and previews. No spinner longer than 1 second without text |
| Errors | problem+json mapped to plain messages with a retry action and the request id for support |
| Offline (lite) | the app works fully offline. Features needing network (research, stock images) show as unavailable with the reason |
| Perceived speed | interactions respond within 100 ms. Slide previews load progressively (thumbnail then full) |
| Accessibility | WCAG 2.2 AA, keyboard reachable, focus visible, screen reader labels, live region for run progress, colour never the only signal |
| Localisation | English at launch with Indian and international number formats (lakh and crore or million and billion) as a user preference. Strings externalised for later languages |
| Responsive | full studio from 1280 px wide. Run status, comments and downloads usable on tablets and phones |

## 8. API additions required by the stories

Added to `05` in the tickets that implement the stories:

| Method | Path | Story |
|---|---|---|
| POST | `/projects/{id}/duplicate` | US-1.2 |
| POST | `/briefs/{id}/check` | US-3.1 (brief quality meter, synchronous Laya gap check) |
| POST, GET | `/runs/{id}/revisions` | US-6.2 (W2) |
| PATCH | `/runs/{id}/slides/{key}/copy` | US-6.3 |
| POST, GET | `/runs/{id}/slides/{key}/variants`, POST `/variants/{id}/choose` | US-6.4 |
| GET | `/runs/{id}/decks/{v}/diff?against={v2}` | US-6.5 |
| POST | `/runs/{id}/decks/{v}/restore` | US-6.6 |
| GET | `/runs/{id}/decks/{v}/facts/{fact_id}` | US-7.1 |
| PATCH | `/defects/{id}` (`status`, `reason`) | US-7.2 |
| POST | `/runs/{id}/exports` (`format`: pptx, pdf, png_zip, xlsx_data) | US-8.x |
| GET, POST, DELETE | `/projects/{id}/shares` | US-10.1 |
| GET, POST | `/decks/{version_id}/comments`, PATCH `/comments/{id}` | US-10.2 |
| POST | `/comments/{id}/to-revision` | US-10.3 |
| POST | `/runs/{id}/decks/{v}/approve` | US-10.4 |
| GET, POST, PATCH, DELETE | `/org/knowledge` (org cards, YAML import and export) | US-11.5 |
| GET, PATCH | `/me/notifications` | US-13.1 |
| GET | `/.well-known/agent-card.json` and the A2A endpoints | US-12.3 |

## 9. Product metrics (install-local, privacy-preserving)

| Metric | Definition |
|---|---|
| Time to first deck | brief created to first downloadable version |
| User time per deck | active time in the UI per deck (focus time), the real cost to P1 |
| Acceptance rate | decks downloaded or approved with at most 2 slide revisions |
| Revision rate | revisions per deck, by type (copy, exhibit, imagery, storyline) |
| Edit distance | inline edit size relative to generated text |
| QA dismissals | findings dismissed as accepted, by standard (signals false positives) |

These feed the north-star metrics in `24`, section 8. They are computed inside the install and never sent to the vendor unless the customer opts in.
