# TRIAGE15 — UI IMPLEMENTATION HANDOFF SPECIFICATION

## Frontend Architecture, Component Inventory & Design System Contract

**Project:** Triage15  
**Branch:** `integration/final-mvp`  
**Target Audience:** Frontend Engineers, UI/UX Designers, Presentation Leads  
**Version:** 1.0.0 (Post-Integration Feature Freeze)  
**Date:** November 24, 2026  

---

## 1. Executive Summary & Design Contract

Triage15 is a peer-to-peer micro-mentoring platform connecting students for 15-minute focused problem-solving sessions.

The frontend is built with **React 19, TypeScript, and Vite**, with **zero external UI frameworks** (no Tailwind, Bootstrap, or component libraries). All styling is currently isolated in `frontend/src/style.css` using standard CSS custom properties and semantic HTML5 elements.

### Core Architectural Principles for Visual Restyling
1. **Zero Framework Lock-in:** Every component renders native HTML semantic tags (`<header>`, `<main>`, `<nav>`, `<section>`, `<article>`, `<button>`, `<fieldset>`, `<details>`, `<table>`). You can re-skin the entire application purely by updating CSS or replacing classes.
2. **Predictable Data Flow:** Optimistic and transactional state updates flow through the `run(task, successMessage)` helper in `App.tsx`.
3. **Continuous Background Synchronization:** Background polling runs every 4 seconds to synchronize open doubts, active session timers, mentor offers, and student point balances without page refreshes.
4. **Resilient Error Boundaries:** All user actions display immediate banner feedback (`role="alert"` for errors, `role="status"` for success notices, and disabled fieldsets during mutation).

---

## 2. Navigation Architecture & Route State

Navigation is managed via single-page top-level tabs in `frontend/src/App.tsx`:

```typescript
const TABS = [
  'Doubt board',
  'My sessions',
  'Profile & availability',
  'Assessments',
  'Benchmark',
  'ML evaluation',
  'Solution history'
];
```

### Global Header Controls
- **Branding:** `TRIAGE15` logo and tagline.
- **Identity & Session Controls (Authenticated Mode):**
  - Displays authenticated student name and points balance pill (e.g. `★ 100 pts`).
  - Displays signed-in Supabase email address.
  - "Sign Out" button calling `supabase.auth.signOut()`.
  - **Security Update:** The unrestricted `X-Demo-Student-ID` dropdown is completely removed in authenticated mode. Identity is derived strictly from the verified JWT.
- **Global System Banner:** Authoritative notice indicating Supabase ES256 authentication status, server IST time, and deterministic Hungarian matching engine.
- **System Metrics Bar:** Real-time system stats (waiting requests, active offers, resolved sessions, average rating, bounties awarded).

---

## 3. Comprehensive Component Inventory

### 3.0. Authentication Screen
- **File:** `frontend/src/components/Auth.tsx`
- **Purpose:** Provide secure email/password sign-in and account registration powered by Supabase Auth and ES256 JWT tokens.
- **Features & Key Elements:**
  - Toggle between **Sign In** and **Create Account**.
  - Form fields: Email input, Password input (min 6 chars), and optional Full Name on registration.
  - Supported Supabase Auth calls: `supabase.auth.signInWithPassword` and `supabase.auth.signUp`.
  - Email confirmation instructions banner for new signups.
  - Interactive validation and error messages (`role="alert"`).
  - Clean card container (`.card`, `.auth-wrapper`) ready for visual restyling.

### 3.1. Doubt Board & ML Skill Suggestions
- **File:** `frontend/src/components/DoubtBoard.tsx` & `frontend/src/components/SkillSuggestions.tsx`
- **Purpose:** Post new doubts with bounties, browse active requests, filter by domain/skills, trigger manual dispatch, and claim doubts.
- **Sub-Components & Key Elements:**
  - **Doubt Creation Form:**
    - Title (`<input name="title" required minLength={3} maxLength={150}>`)
    - Description (`<textarea name="description" required minLength={5} maxLength={3000}>`)
    - Domain Selector (`<select name="domain">` for Python, React, JavaScript, SQL)
    - Bounty Input (`<input name="bounty" type="number" min="0">`) with balance checks
  - **`SkillSuggestions` Component (`frontend/src/components/SkillSuggestions.tsx`):**
    - Listens to title and description changes (debounced by 300ms).
    - Calls `POST /api/ml/predict-tags` to fetch multi-label Linear SVM suggestions.
    - Renders suggestion pill buttons showing tag name and decision score margin (e.g. `pandas (+0.96)`).
    - Interactive attribution accordion (`<details>`): Displays positive feature weights (words increasing confidence like `dataframe`, `pandas`) and negative feature weights.
    - One-click click-to-accept or remove tags.
  - **Manual Dispatch Banner:**
    - "Run Dispatch (Manual)" button invoking `POST /api/dispatch/run`.
    - Allocation summary showing Hungarian vs Greedy utility comparisons, assignment counts, and unassigned explanations.
  - **Doubt Listing Cards:**
    - Cards categorized by state: `OPEN`, `MATCHED`, `CLAIMED`, `RESOLVED`, `UNMATCHED`.
    - Action buttons: "Edit Doubt", "Cancel Doubt", "Claim Doubt" (for qualified mentors).

---

### 3.2. Sessions & Mentoring Workspace
- **Files:** `frontend/src/components/Sessions.tsx` and `frontend/src/components/SessionWorkspace.tsx`
- **Purpose:** Manage mentor offers, enter active sessions, communicate via real-time messaging, exchange code snippets, run diffs, and submit resolution records.
- **Sub-Components:**
  1. **Offer Banners (`Sessions.tsx`):**
     - Prompt mentors to "Accept Offer" or "Decline Offer" within the 180-second window.
  2. **Session Workspace (`SessionWorkspace.tsx`):**
     - Authoritative countdown timer (15 minutes / 900 seconds) driven by server timestamps.
     - "Accelerate +2 min" demo button for fast judging demonstrations.
     - Tabbed sub-navigation:
       - **Chat Tab:** Real-time message exchange with message history and input box.
       - **Code Snippets Tab (`frontend/src/components/session/CodeSnippetList.tsx` & `CodeSnippetEditor.tsx`):**
         - Snippet creation modal/editor: Title, filename, language, snippet type (`ORIGINAL`, `PROPOSED_FIX`, `EXAMPLE`, `ERROR_LOG`), code textarea.
         - Snippet card: Author name, timestamp, syntax styling, copy-to-clipboard button.
       - **Diff Comparison Tab (`frontend/src/components/session/CodeComparison.tsx`):**
         - Dropdown to select Original Snippet and Proposed Fix.
         - Diff summary pill: Added count (`+N`), Removed count (`-M`), Unchanged count (`=K`).
         - Split side-by-side or unified line-by-line diff viewer highlighting additions in green and deletions in red.
       - **Resolution Tab (`frontend/src/components/session/ResolutionEditor.tsx` & `ResolutionReview.tsx`):**
         - Mentor View: Draft root cause, solution explanation, follow-up advice, and reference URLs.
         - Mentor Action: "Submit Resolution & Complete Session".
         - Requester View: Review resolution details, select 1-5 star rating, enter feedback notes, and click "Confirm Resolved" (awards bounty) or "Mark Unresolved" (refunds/retains bounty).
  3. **Meeting Panel (`frontend/src/components/session/MeetingPanel.tsx`):**
     - Attached Google Meet link indicator.
     - Input field with real-time validation regex (`https://meet.google.com/xxx-yyyy-zzz`).
     - "Join Google Meet" external link button.
     - "Remove Link" button for mentor.

---

### 3.3. Solution History Archive
- **File:** `frontend/src/components/SolutionHistory.tsx`
- **Purpose:** Provide an authoritative personal knowledge archive for students to review past sessions they participated in as mentor or requester.
- **Features & Elements:**
  - Role Filter: `All`, `As Mentor`, `As Requester`.
  - Domain Filter & Search Bar: Filter by keyword, doubt title, or skill tag.
  - Historical Record Cards:
    - Doubt title, domain, skill tags, bounty awarded (`★ X pts`).
    - Counterpart identity: "Mentored student: Jane Doe" or "Mentor: Alex Smith".
    - Session resolution box: Root cause analysis, detailed solution explanation, follow-up steps.
    - Code snippets drawer: Expandable view of original problem code vs resolved code.
    - Feedback badge: 1-5 stars rating and feedback comments.

---

### 3.4. Explainable ML Evaluation Dashboard
- **File:** `frontend/src/components/ModelEvaluation.tsx`
- **Purpose:** Showcase the machine learning model architecture, benchmark metrics, and attribution transparency to hackathon judges.
- **Features & Elements:**
  - **Model Status Card:** Displays active model (`linear_svm`), artifact path, training date, sample counts (2,675 questions), and feature vocabulary size (10,000 TF-IDF features).
  - **Global Classification Metrics Table:**
    - Micro F1: `0.8736` (87.4%)
    - Macro F1: `0.8512`
    - Overall Precision: `0.8841`
    - Overall Recall: `0.8633`
  - **Per-Label Performance Table:** Breakdowns for `python`, `pandas`, `javascript`, `react`, `sql`, `joins`, `aggregation`, `async` showing True Positives, False Positives, False Negatives, Precision, Recall, and F1.
  - **Model Competition Comparison Table:** Side-by-side comparison of Linear SVM vs Logistic Regression vs Multinomial Naive Bayes.
  - **Real-Workload Allocation Impact:** Metrics showing allocation rate changes when using ML-predicted tags vs raw student tags on real Stack Exchange doubts.

---

### 3.5. Student Profile & Availability Matrix
- **File:** `frontend/src/components/Profile.tsx`
- **Purpose:** Manage student mentor status, view verified domain assessment scores, and configure weekly availability slots.
- **Features & Elements:**
  - Mentoring active/inactive toggle.
  - Domain skill level badges (`Novice`, `Competent`, `Proficient`, `Expert`).
  - Mentor Credibility Card: Shows resolution rate percentage, total sessions completed, and average rating.
  - Weekly 7-day slot availability grid (15-minute slot blocks) with click-to-toggle availability.

---

### 3.6. Domain Skill Assessments
- **File:** `frontend/src/components/Assessment.tsx`
- **Purpose:** Allow students to take domain-specific multiple-choice quizzes to unlock or upgrade mentoring privileges.
- **Features & Elements:**
  - Domain selection (Python, React, JavaScript, SQL).
  - Question presentation with 4 options per question.
  - Instant scoring with explanations and automatic skill tier progression upon passing.

---

### 3.7. Algorithm Benchmark Dashboard
- **File:** `frontend/src/components/Benchmark.tsx`
- **Purpose:** Interactive benchmark runner demonstrating Hungarian maximum-weight matching superiority over greedy baseline.
- **Features & Elements:**
  - "Run Benchmark Suite" button (`POST /api/benchmark/run`).
  - Comparative metrics table: Total utility, matched pairs count, solver latency in milliseconds.
  - Performance proof: Demonstrates zero unassigned requests due to rectangular bipartite graph reduction.

---

## 4. CSS Class & Styling Contract

For visual redesign or UI restyling, all key components expose standard CSS classes:

| Class Name | Target Element / Purpose |
| :--- | :--- |
| `.branding` | Top-left application header brand container |
| `.identity-control` | Header demo student selector and point balance pill |
| `.metrics` | Top system stats horizontal metric card container |
| `.banner` | System-wide notices and legal / hackathon disclaimers |
| `nav button[aria-pressed="true"]` | Active navigation tab button |
| `.workspace` | Main container fieldset disabled during mutations |
| `.section-head` | Header container for section title and primary CTA button |
| `.dispatch-summary` | Highlight card showing allocation algorithm results |
| `.doubt-card` | Individual doubt card container |
| `.session-card` | Active session card container |
| `.session-workspace` | Live session workspace parent container |
| `.timer-bar` | Authoritative countdown timer container |
| `.meeting-panel` | Google Meet link attachment and launch box |
| `.snippet-card` | Code snippet display card |
| `.diff-view` | Before-and-after side-by-side / inline diff container |
| `.diff-added` | Added code line in diff viewer (green highlight) |
| `.diff-removed` | Removed code line in diff viewer (red highlight) |
| `.resolution-box` | Structured resolution record presentation container |
| `.history-card` | Searchable historical session archive card |
| `.ml-eval-container` | Model evaluation statistics and comparison tables |
| `.skill-suggestions` | ML suggested skill pills container |
| `.attribution-card` | Explainable ML feature attribution weights container |

---

## 5. Accessibility & Responsive Requirements
- All forms use explicit `<label>` elements wrapping or referencing inputs.
- Tab selection uses `aria-pressed="true|false"` on `<button>` elements.
- Live alerts use `role="alert"` for errors and `role="status"` for progress notices.
- Color contrast meets WCAG AA standards for all text elements.
- Mobile breakpoints cleanly stack flex headers, metric strips, and diff panels.
