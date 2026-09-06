# RevenueGuard: compliance visibility, model swap, stage bar, frontend cleanup

## Context

The backend and all five integration phases are complete, but four issues remain, and
three of them share a root cause: **failures are being converted into healthy-looking
success states.**

- The Compliance page renders an empty gallery and a green 100% gauge. Not because the
  page is broken — because `evaluate_email_compliance` catches every exception and
  returns `PASS` with the error text in the `reason` field. The 429 in the Decision
  Explorer screenshot is a Gemini free-tier quota error being laundered into an
  approval, and the email ships unreviewed.
- The simulation is slow because `TICK_CONCURRENCY` is pinned to 3 to survive that same
  free-tier quota, and because the two most expensive calls are uncached.
- The stage progress bar reads `escalation_stage` while the badge next to it reads
  `status`. The two fields drift apart, so recovered invoices show one or two lit pips.
- The dashboard has real error plumbing (`QueryBoundary`, typed `ApiError`) that is
  applied to only 13 of 28 components, and the single most-used control on the app
  bypasses it entirely.

This directly violates the standing rule in `CLAUDE.md`: *"Never swallow an error to make
a symptom disappear."* The work below is mostly deleting places where that happens.

Decisions taken: compliance fails **open but flagged**; models move to a **single
`claude-sonnet-5`**; the stage bar is fixed **in the UI only**; frontend scope is
**targeted fixes plus design-system cleanup**, no visual redesign.

**No schema rebuild is required.** `AuditLog.compliance_verdict` is already
`String(10)` (`src/persistence/models.py:73`) and `"UNREVIEWED"` is exactly 10
characters. No column is added or changed, so `docker compose down -v` is not needed.

---

## Phase A — Make compliance failures visible

Work one phase at a time; this one first, because it is the correctness bug.

### A1. Stop laundering errors into PASS

`src/ai/compliance_judge.py:93-96` — replace the `except` that returns `PASS`:

```python
except Exception as e:
    logger.error("Compliance judge error: %s", e, exc_info=True)
    return {"verdict": "UNREVIEWED", "reason": f"Judge unavailable: {e}", "suggestions": ""}
```

The JSON-parse branch at `:89-91` already fails closed to `FAIL`. Leave it.

### A2. Route UNREVIEWED

- `src/graph/edges.py:79-91` — treat `UNREVIEWED` like `PASS` for routing (the draft still
  sends; that is the chosen behaviour) but **do not** feed it into the rewrite loop.
- `src/graph/nodes.py:650-685` (`evaluate_compliance`) — emit a distinct audit entry
  `event_type="COMPLIANCE_UNREVIEWED"` carrying `compliance_verdict="UNREVIEWED"` and the
  error string as `reasoning`. Nodes stay pure: mutate state and append to
  `state["audit_entries"]` only. `core_loop.py` remains the sole writer.
- `nodes.py:651-653` — the early-out for "no draft / not sending" currently sets `PASS` and
  writes no audit row. Keep it writing no row, but set the verdict to `None` rather than
  `PASS` so it cannot be counted as a genuine check.

### A3. Stop the gauge lying on empty data

`src/dashboard_api.py:297-312` (`/api/compliance/stats`):
- Return `rate: None` when `total_checked == 0` instead of the current `100.0` at `:305`.
- Add `unreviewed` to the counts and **exclude it from both** `passed` and the rate
  denominator. A rate is over `PASS + FAIL` only.

`src/dashboard_api.py:314-355` (`/api/compliance/rejected`):
- Widen the filter from `compliance_verdict == "FAIL"` to
  `compliance_verdict.in_(["FAIL", "UNREVIEWED"])` so unreviewed sends appear in the
  gallery. Return the verdict on each row so the UI can style them differently.
- While here: `:317-320` loads **all** audit logs into memory to resolve
  `approved_content`. Scope that query to the invoice ids already selected.

### A4. Surface it in the UI

- `dashboard/src/lib/constants.ts` — add a `COMPLIANCE_CONFIG` map alongside
  `STATUS_CONFIG` for `PASS` / `FAIL` / `UNREVIEWED` (green / red / amber).
- `components/compliance/ComplianceScore.tsx` — render a real "No drafts checked yet"
  empty state when `rate === null`, instead of a green 100% ring. Add the unreviewed
  count as a third counter. Note it currently passes `{null}` as `QueryBoundary`
  children (`:8-21`); give it actual children.
- `components/compliance/RejectedDraftsGallery.tsx` — render amber `UNREVIEWED` cards
  distinctly from red `FAIL` cards. These have no `approved_content` (nothing was
  rewritten), so `ComplianceDiff` needs a single-pane branch.

### A5. The DEMO_FAST caveat

`src/ai/llm.py:92-95` sends every non-hero client down a deterministic SHA-256 verdict
that never calls a model. That is legitimate demo scaffolding, but the Compliance page
presents its output as agent performance — which `CLAUDE.md` forbids for `simulate_client`
and applies equally here. Tag those audit rows with `source="deterministic"` and label
them in the gallery. Do not change the gating logic.

---

## Phase B — Anthropic key and simulation speed

### B1. Model configuration

`src/config.py:10` — `anthropic_model` default `claude-3-5-sonnet-20241022` is a legacy
dated id. Change to `claude-sonnet-5`.

Also update `.env.example:9` and **add `ANTHROPIC_MODEL` to the `api` service in
`docker-compose.yml`** — it is currently not passed through at all, so in Docker the model
cannot be overridden without editing compose.

No provider code changes. `active_provider` (`config.py:57-71`) already prefers Anthropic
when `ANTHROPIC_API_KEY` is set, and `get_llm` (`llm.py:45-52`) already has the branch.

### B2. Fix the ignored retry setting

`src/ai/llm.py:50` hardcodes `max_retries=1` on the Anthropic path, so the documented
`LLM_MAX_RETRIES` env var (plumbed through `.env.example:19` and docker-compose) has no
effect there. Use `settings.llm_max_retries` on both branches. Raise the Anthropic
timeout from `20.0` to match Google's `45.0` — a Sonnet draft can exceed 20s.

### B3. Raise concurrency

`src/config.py:37` — `tick_concurrency` default 3 exists to dodge Gemini free-tier 429s.
On a paid Anthropic key, raise the default to 12 and set `demo_fast: bool = False`, as the
comment at `config.py:34-36` already anticipates. Update the docker-compose defaults to
match. This is the single largest wall-clock win.

### B4. Prompt caching

Two large static system prompts are re-sent in full on every call: the compliance rubric
(`compliance_judge.py:11-29`) and the decision prompt in `src/ai/agent_policy.py`. Add an
Anthropic `cache_control: {"type": "ephemeral"}` breakpoint on each. Cached reads are
~10% of input cost, and the prefix is genuinely stable. Guard it so the Google path is
unaffected.

### B5. Bound the decision cache

`src/ai/agent_policy.py:221` — `_decision_cache` is an unbounded module-level dict with no
TTL and no eviction, and it survives across simulation runs. A day-30 decision can be
served from a day-1 entry in the same bucket. Add the virtual-date bucket to
`_equivalence_key` (`:224-243`) and call `clear_decision_cache()` from the reset endpoint
in `src/main.py`.

Do **not** add caching to `draft_email` — drafts should not be reused across clients.

---

## Phase C — Stage progress bar

UI-only, per the decision taken.

`dashboard/src/lib/constants.ts` — add a `STATUS_STAGE` map derived from the existing
`STATUS_CONFIG` keys:

```
ISSUED → 0   OVERDUE → 0
NOTIFIED_1 → 1   NOTIFIED_2 → 2   NOTIFIED_3 → 3
PAUSED_PTP / DISPUTE → hold at the stage already reached
LEGAL_HOLD / UNRESPONSIVE / HUMAN_ESCALATED → 4
RECOVERED → 4 (complete)
```

`components/invoices/EscalationProgress.tsx` — change the prop from `stage: string` to
accept the invoice `status`, and derive `level` from that map. Remove the silent
`default 1` at `:3` — an unknown status must render zero lit pips, not a fake STAGE_1.
Give `RECOVERED` a distinct completed treatment rather than four generic pips.

Update the three call sites: `InvoiceTable.tsx:124`, `InvoiceHeader.tsx:35`,
`ClientInvoiceList.tsx:66`.

All 11 statuses are confirmed reachable and all 11 already have `STATUS_CONFIG` entries —
no badge work needed.

---

## Phase D — Frontend fixes and design-system cleanup

### D1. Stop swallowing mutation errors

`components/command-center/SimulationController.tsx:17-19, 30-32, 40-42, 51-53` — four
bare `catch (e) { console.error(e) }` blocks. Generate, Tick, Auto-Run and Reset all fail
completely silently; the button just stops spinning. A working `ToastProvider` already
exists and is used in `approvals/page.tsx:51`. Import `useToast` and surface every
failure. Replace `res: any` at `:27, :43, :57` with types from `lib/types.ts`.

`:56-58` — `handleAutoRun` fires up to 30 sequential ticks and silently aborts the whole
run if one throws. Report which tick failed and how many completed.

### D2. Fix the blank page

`app/invoices/[id]/page.tsx:19-48` collapses `error`, `isLoading` and `!invoice` into one
branch and passes `{null}` to `QueryBoundary`. On a successful-but-empty fetch this
renders a blank page with no message and no retry. Split the three states and pass
`isEmpty` / `emptyMessage`.

### D3. Invoice table

`components/invoices/InvoiceTable.tsx`:
- Add sorting. The eight `<th>` cells at `:80-87` are static text; a 100-row table with no
  way to order by amount or days overdue is the main usability gap. Include `aria-sort`.
- Add pagination (or windowing) — all rows currently render into one scroller.
- Remove `.no-scrollbar` at `:62`; it hides the only affordance that more rows exist.
- Make rows keyboard-reachable. `onClick` on `<tr>` (`:94-98`) means no tab focus and no
  open-in-new-tab. Wrap the first cell in a `next/link` `<a>`.
- Debounce the search input (`:23-27`).
- Fix the sticky header shade `bg-[#0B0F19]/90` at `:78` — that colour is not a token.

### D4. Design system

This is the "same look, better built" pass.

- `app/globals.css:24-29` — the `@theme inline` block exposes only four tokens to
  Tailwind, which is why `#00F0FF` is pasted literally into ~15 components. Promote the
  full `:root` palette (`:3-22`) into `@theme` so `text-accent-primary` works, then
  replace the hardcoded hex across the component tree. Also fold the stray `#0B0F19`
  (a sixth background shade, used in `InvoiceTable.tsx:78`,
  `AuditTimelineEntry.tsx:17`, `Sidebar.tsx:37`) into the token set.
- `Sidebar.tsx` applies both the `.sidebar` class **and** `w-64 bg-[#0B0F19]` — two
  competing definitions of the same element. Drop the utilities, keep the class.
- `.nav-item.active` (`globals.css:160-180`) adds a 1px border the inactive state lacks,
  so the nav list shifts vertically on every route change. Give both states the border.
- Add a `prefers-reduced-motion` block. There is none.
- Delete dead CSS: the `pulse-glow` and `shimmer` keyframes (`:219-222, :234-237`) have no
  consumers, and `--sidebar-collapsed` (`:22`) has no collapse feature.
- `.glass-panel` uses `transition: all 0.3s` on a `backdrop-filter` surface across ~30
  panels. Narrow it to the properties that actually change.
- `.mono-label` is 10px cyan at 70% opacity on `#06060F` — roughly 2.9:1, below WCAG AA.
  Raise the opacity and size.

### D5. Error-handling consistency

- `lib/api.ts:4-16` defines `ApiRequestError`, duplicating `ApiError` in
  `hooks/useApi.ts:6-19`. `QueryBoundary.describe()` only `instanceof`-checks `ApiError`
  (`:32`), so mutation errors lose their status code. Delete `ApiRequestError` and use
  one class.
- Collapse the four independent `API_BASE` definitions (`lib/api.ts:1`,
  `hooks/useApi.ts:4`, `WebSocketProvider.tsx:5`, `useWebSocket.ts:5`) into one export.
- **Delete `hooks/useWebSocket.ts`.** It is unimported dead code that still contains the
  `mutate(() => true)` request-storm bug `WebSocketProvider` was written to fix, plus an
  empty `catch (e) {}` at `:39`. If it were ever mounted the app would open two sockets.
- `WebSocketProvider.tsx:98` — fixed 3000ms reconnect with no backoff, jitter or cap
  hammers a downed backend. Add exponential backoff. Surface `ws.onerror` (`:100`)
  instead of silently closing, and have the Sidebar status dot use the context's
  `connected` value rather than inferring it from a polled `/health` key
  (`Sidebar.tsx:21-22`).
- `useApi.ts:32` hardcodes `refreshInterval: 5000` for every key, so ~10 endpoints poll
  every 5s on every page even though a live WebSocket already pushes updates. Make the
  interval a per-call option and rely on the socket where it exists.
- Replace the remaining `data?.x || []` swallows with `QueryBoundary` in the components
  that lack it — `CooldownBoard.tsx:9`, `RejectedDraftsGallery.tsx:10`,
  `clients/page.tsx:22`, `approvals/page.tsx:30`, `ExecutionTrace.tsx:23`.

### D6. Accessibility floor

The codebase contains exactly one ARIA attribute. Add: `aria-label` on every icon-only
button (`QuickActions`, the `←` back link at `[id]/page.tsx:23-28`), `aria-live` on the
toast region and activity ticker, `<label>`s on the approvals note inputs
(`approvals/page.tsx:147-153`), visible `:focus-visible` styles wherever `outline-none`
is used (`InvoiceTable.tsx:37,56`, `approvals/page.tsx:152`), and `aria-hidden` on
decorative emoji.

Also: `KpiCards.tsx:73` feeds `m.recoveryRate` straight into `strokeDasharray` with no
clamp — a value over 100 or a `NaN` corrupts the gauge. Clamp it.

`approvals/page.tsx:154-167` — "Approve & resume" and "Halt collection" are irreversible
and have no confirmation step. Add one.

`approvals/page.tsx:150` uses object-spread setState from a stale closure; typing quickly
in two note fields drops keystrokes. Use the functional form.

Out of scope by decision: responsive/mobile layout. The fixed 240px sidebar and
`page-content { margin-left: 240px }` at `globals.css:54` stay as-is, and the dashboard
remains desktop-only.

---

## Verification

Per `CLAUDE.md`: **5 invoices, 5 ticks. Never run the 30-day simulation.**

No schema change is made, so a plain restart is enough:

```bash
docker compose up --build
```

1. **Compliance, error path.** Set `ANTHROPIC_API_KEY` to a deliberately invalid value,
   run 5 ticks. Confirm: audit rows carry `compliance_verdict="UNREVIEWED"`; the gallery
   shows amber cards; the gauge shows a rate over PASS+FAIL only, not 100%. Then unset
   the key entirely and confirm the empty state reads "No drafts checked yet" rather than
   a green 100% ring.
2. **Compliance, happy path.** With a valid key and `DEMO_FAST=false`, run 5 ticks and
   confirm genuine PASS/FAIL rows appear and any FAIL shows a real before/after diff.
3. **Model swap.** Confirm `active_provider` resolves to `anthropic` and that the request
   uses `claude-sonnet-5`. Verify `LLM_MAX_RETRIES` now takes effect on the Anthropic
   path (it previously did not).
4. **Speed.** Time 5 ticks at `TICK_CONCURRENCY=3` vs `12`, same seed. Record both
   numbers. Check `usage.cache_read_input_tokens` is non-zero on the second and later
   judge calls — if it is zero, the prompt-cache breakpoint is misplaced.
5. **Stage bar.** Drive one invoice to `RECOVERED` and one to `HUMAN_ESCALATED`; confirm
   pips match the badge in both, and that an invoice with a stale `escalation_stage`
   still renders correctly. Confirm an unknown status renders zero pips, not one.
6. **Frontend.** Stop the API container and load every page: each must show a
   `QueryBoundary` error with a retry button — no blank pages, no green zero-states, no
   silent buttons. Click Generate/Tick/Reset with the API down and confirm a toast
   appears for each. Tab through the invoice table and confirm rows are reachable and
   sorting announces via `aria-sort`.
7. Run `npm run build` in `dashboard/` — TypeScript strict must pass with no new `any`.
