--
-- PostgreSQL database dump
--

\restrict 6Gk2bs6e0mJlojFvrGdxPz23EMvtIFrkj5qaXEVwvmhfLrH5A0kakwJNUPJRqbB

-- Dumped from database version 15.19
-- Dumped by pg_dump version 15.19

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: invoices; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.invoices VALUES (1474, 340000, 'Globex Solutions', 'accounts@globexsolutions.com', '2026-08-25 06:34:11.938551', 'HUMAN_ESCALATED', NULL, 'STAGE_1', 0, NULL, NULL, 1, NULL);
INSERT INTO public.invoices VALUES (1475, 7500000, 'Pinnacle Industries', 'ap@pinnacleindustries.com', '2026-07-23 06:34:11.938551', 'HUMAN_ESCALATED', NULL, 'STAGE_1', 0, NULL, NULL, 1, NULL);
INSERT INTO public.invoices VALUES (1476, 80000, 'NovaTech Labs', 'arjun@novatechlabs.com', '2026-08-02 06:34:11.938551', 'NOTIFIED_1', NULL, 'STAGE_1', 1, 'plink_mock_1476_1788676461', NULL, 1, 'https://rzp.io/l/1476_1788676461');
INSERT INTO public.invoices VALUES (1473, 1250000, 'Acme Corp', 'finance@acmecorp.com', '2026-08-15 06:34:11.938551', 'RECOVERED', NULL, 'STAGE_1', 1, 'plink_mock_1473_1788676460', NULL, 1, 'https://rzp.io/l/1473_1788676460');
INSERT INTO public.invoices VALUES (1477, 1644135, 'Prakash-Reddy', 'finance@prakash-reddy.com', '2026-08-05 06:34:11.938551', 'RECOVERED', NULL, 'STAGE_1', 1, 'plink_mock_1477_1788676462', NULL, 1, 'https://rzp.io/l/1477_1788676462');


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.audit_logs VALUES (27425, 1473, '2026-09-07 06:34:11.855945', 'STATUS_CHANGED', 'Due date passed', NULL, 'Marked as OVERDUE', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27426, 1473, '2026-09-07 06:34:11.856945', 'AGENT_DECISION', 'Acme Corp is a Tier 1 client with an excellent payment history, and their delays are known to be caused by internal approval cycles rather than cash flow issues. Since this is the first contact for an invoice 22 days overdue, sending a polite Stage 1 reminder via email with accounts@acme.com CC''d respects the relationship and aligns with their preferred channel.', 'Alternatives considered: WAIT, OFFER_DISCOUNT, SPLIT_INVOICE, ESCALATE_TO_HUMAN', 'Chose SEND_EMAIL at STAGE_1 | confidence 0.95', 'Expected outcome: Rajesh Kumar will forward the reminder to the internal approval team and process the payment within the next few days without friction.
Decision source: llm', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27427, 1473, '2026-09-07 06:34:11.857945', 'COMPLIANCE_PASSED', 'The email draft successfully adheres to all mandatory compliance rules. It avoids any threats of legal action and aggressive language, includes a payment link and the correct invoice number (#1473) and amount (₹12,50,000), and respects the opt-out/legal hold check (none applicable). The tone properly matches STAGE_1 (warm, helpful, assuming good intent), and the word count is well under the 200-word limit.', 'Compliance Judge', 'Approved email draft', 'Subject: Friendly Reminder: Outstanding Invoice #1473 for Acme Corp (₹12,50,000)

Dear Rajesh,

I hope this email finds you well. 

I am writing to follow up on Invoice #1473 for ₹12,50,000, which was due on August 15, 2026, under our Net-60 payment terms. 

Given our strong ongoing partnership and your history of timely payments, we understand that this might simply be tied up in an internal approval cycle. However, as this invoice is now past due, could you please provide an update on its payment status?

For your convenience, you can process the payment directly using our secure portal here: {payment_link}.

If payment has already been initiated, please disregard this note and kindly share the remittance advice. 

Thank you for your prompt attention to this matter.

Best regards,

[Your Name]  
[Your Title]  
[Your Company]', 'PASS', 'llm');
INSERT INTO public.audit_logs VALUES (27428, 1473, '2026-09-07 06:34:11.858945', 'TOOL_CALL', 'Created a mock Razorpay payment link for INR 1,250,000', 'All side effects flow through audited tools', 'create_payment_link(amount=1250000.0, description=Payment for Invoice 1473)', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27429, 1473, '2026-09-07 06:34:11.859945', 'TOOL_CALL', 'Dispatched the STAGE_1 email to finance@acmecorp.com', 'All side effects flow through audited tools', 'send_email(to=finance@acmecorp.com, subject=Invoice 1473 - payment reminder, stage=STAGE_1)', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27430, 1473, '2026-09-07 06:34:11.860945', 'EMAIL_SENT', 'STAGE_1 Escalation (contact 1 of 5)', NULL, 'Drafted and sent STAGE_1 email', 'Subject: Friendly Reminder: Outstanding Invoice #1473 for Acme Corp (₹12,50,000)

Dear Rajesh,

I hope this email finds you well. 

I am writing to follow up on Invoice #1473 for ₹12,50,000, which was due on August 15, 2026, under our Net-60 payment terms. 

Given our strong ongoing partnership and your history of timely payments, we understand that this might simply be tied up in an internal approval cycle. However, as this invoice is now past due, could you please provide an update on its payment status?

For your convenience, you can process the payment directly using our secure portal here: {payment_link}.

If payment has already been initiated, please disregard this note and kindly share the remittance advice. 

Thank you for your prompt attention to this matter.

Best regards,

[Your Name]  
[Your Title]  
[Your Company]', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27431, 1473, '2026-09-07 06:34:11.861945', 'NO_RESPONSE', '[SIMULATED ENVIRONMENT] No response. base 0.34 x stage 1.0 x action 1.00 (standard escalation email) x relationship 1.0 = 0.340', NULL, 'Client did not respond', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27432, 1473, '2026-09-07 06:34:11.862945', 'GRAPH_PATH', 'decide_action -> validate_action -> draft_email -> evaluate_compliance -> call_razorpay_tools -> execute_action -> simulate_client', NULL, 'Traversed 7 nodes', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27433, 1474, '2026-09-07 06:34:11.855945', 'STATUS_CHANGED', 'Due date passed', NULL, 'Marked as OVERDUE', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27434, 1474, '2026-09-07 06:34:11.856945', 'AGENT_DECISION', 'The invoice is currently 12 days overdue and no prior contact attempts have been made for this specific bill. Since the current escalation stage is STAGE_1 and the relationship score remains at 1.0, initiating a professional Stage 1 email to Priya Mehta is the appropriate first step while referencing the Net-30 terms.', 'Alternatives considered: WAIT, OFFER_DISCOUNT, SPLIT_INVOICE, ESCALATE_TO_HUMAN', 'Chose SEND_EMAIL at STAGE_1 | confidence 0.95', 'Expected outcome: Priya Mehta will acknowledge the invoice and either initiate the payment or respond regarding their cash flow status within the next few days.
Decision source: llm', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27435, 1474, '2026-09-07 06:34:11.857945', 'COMPLIANCE_FAILED', 'The email is assigned to STAGE_1 (Warm, helpful, assumes good intent), but the context notes that the client has broken two Promise-to-Pay commitments in 2024. Rule 7 states: ''If a previous Promise-to-Pay was broken, the email MUST reference it professionally.'' The draft fails to mention the broken promises.', 'Compliance Judge', 'Rejected email draft', 'Subject: Payment Reminder: Invoice #1474 Overdue (Globex Solutions)

Dear Priya,

I hope this email finds you well. 

I am writing to follow up on Invoice #1474 for ₹3,40,000, which was due on August 25, 2026, and is now past due. 

As per our Service Agreement, Net-30 payment terms apply, along with a 1.5% monthly late fee clause for overdue balances. Given your past payment patterns and cash flow considerations, we want to work with you to resolve this promptly before additional late fees accrue. 

Please process the payment at your earliest convenience using our secure direct payment link below:

{payment_link}

If you have already initiated this transfer, please share the remittance advice so we can update our records. Should you have any questions or require assistance regarding this invoice, please let me know.

Best regards,

[Your Name]  
Accounts Receivable Team', 'FAIL', 'llm');
INSERT INTO public.audit_logs VALUES (27436, 1474, '2026-09-07 06:34:11.858945', 'COMPLIANCE_FAILED', 'The email tone does not match the required escalation stage. STAGE_1 requires a warm, helpful tone that assumes good intent. However, this draft includes language typical of a later stage (referencing broken prior commitments, late fees from contract terms, and a firm payment schedule), which violates rule 6. Furthermore, referencing broken promises in STAGE_1 contradicts the rule that STAGE_1 should be warm and helpful.', 'Compliance Judge', 'Rejected email draft', 'Subject: Following up: Overdue Invoice #1474 for Globex Solutions (₹3,40,000)

Dear Priya,

I hope you’re having a good week. 

I’m writing to follow up on Invoice #1474 for ₹3,40,000, which was due on August 25, 2026. As we have not yet received payment or a status update, I wanted to check in and see how we can assist in getting this processed.

I also wanted to gently revisit our previous discussions regarding payment timelines. Given that our prior commitments have regrettably lapsed past their promised dates, it is very important that we establish a firm and reliable payment schedule for this balance moving forward. 

Per our Service Agreement, please note that accounts past their due date are subject to a 1.5% monthly late fee, and we want to help you avoid any additional charges. 

You can review and settle the invoice directly using our secure payment link below:
{payment_link}

If there are any current bottlenecks in your budget cycle that we should be aware of, please let me know so we can work together on a realistic resolution. 

Best regards,

[Your Name]  
[Your Title]  
[Your Company]', 'FAIL', 'llm');
INSERT INTO public.audit_logs VALUES (27437, 1474, '2026-09-07 06:34:11.859945', 'STATUS_CHANGED', 'Max compliance retries reached', NULL, 'Routed to human', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27438, 1474, '2026-09-07 06:34:11.860945', 'HUMAN_ESCALATED', 'Compliance judge rejected every rewrite attempt.', 'Human handoff: COMPLIANCE_EXHAUSTED', 'Notified human via console', '[RevenueGuard] Human review needed - COMPLIANCE_EXHAUSTED
Invoice #1474 | Globex Solutions | INR 340000.0
Compliance judge rejected every rewrite attempt.', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27439, 1474, '2026-09-07 06:34:11.861945', 'GRAPH_PATH', 'decide_action -> validate_action -> draft_email -> evaluate_compliance -> draft_email -> evaluate_compliance -> execute_action', NULL, 'Traversed 7 nodes', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27440, 1475, '2026-09-07 06:34:11.855945', 'STATUS_CHANGED', 'Due date passed', NULL, 'Marked as OVERDUE', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27441, 1475, '2026-09-07 06:34:11.856945', 'AGENT_DECISION', 'Pinnacle Industries has a history of disputing consulting hours (Milestone 2 charges) while accepting Milestone 1 deliverables. Per the policy guardrails and client profile, we must issue separate payment links for undisputed and disputed portions before sending any Stage 2+ communication to VP Vikram Singh.', 'Alternatives considered: SEND_EMAIL, WAIT, OFFER_DISCOUNT, ESCALATE_TO_HUMAN', 'Chose SPLIT_INVOICE | confidence 0.95', 'Expected outcome: The invoice will be successfully split into separate links, allowing us to cleanly pursue the undisputed amount and resolve the dispute without alienating this high-value enterprise client.
Decision source: llm', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27442, 1475, '2026-09-07 06:34:11.857945', 'ACTION_VETOED', 'INR 7,500,000 exceeds the high-value threshold.', 'Guard rule 4: Invoices above INR 5,000,000 allow only a standard email autonomously', 'Blocked SPLIT_INVOICE -> substituted ESCALATE_TO_HUMAN', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27443, 1475, '2026-09-07 06:34:11.858945', 'TOOL_CALL', 'Invoices above INR 5,000,000 allow only a standard email autonomously', 'All side effects flow through audited tools', 'update_invoice_status(new_status=HUMAN_ESCALATED, reason=Invoices above INR 5,000,000 allow only a standard email autonomously)', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27444, 1475, '2026-09-07 06:34:11.859945', 'HUMAN_ESCALATED', 'Invoices above INR 5,000,000 allow only a standard email autonomously', 'Human handoff: GUARD_VETO', 'Notified human via console', '[RevenueGuard] Human review needed - GUARD_VETO
Invoice #1475 | Pinnacle Industries | INR 7500000.0
Invoices above INR 5,000,000 allow only a standard email autonomously', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27445, 1475, '2026-09-07 06:34:11.860945', 'GRAPH_PATH', 'decide_action -> validate_action -> act_escalate', NULL, 'Traversed 3 nodes', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27446, 1476, '2026-09-07 06:34:11.855945', 'STATUS_CHANGED', 'Due date passed', NULL, 'Marked as OVERDUE', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27447, 1476, '2026-09-07 06:34:11.856945', 'AGENT_DECISION', 'NovaTech Labs is 35 days overdue on an INR 80,000 invoice with zero contact attempts made so far. Given the client profile indicates extreme risk and a history of ghosting, we must begin formal outreach at Stage 1 before considering human escalation or discounts.', 'Alternatives considered: WAIT, OFFER_DISCOUNT, SPLIT_INVOICE, ESCALATE_TO_HUMAN', 'Chose SEND_EMAIL at STAGE_1 | confidence 0.95', 'Expected outcome: The CEO, Arjun Patel, will receive the first formal reminder and either engage or provide visibility into their cash runway.
Decision source: llm', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27448, 1476, '2026-09-07 06:34:11.857945', 'COMPLIANCE_PASSED', 'The email draft successfully complies with all mandatory rules. It avoids threats of legal action and aggressive language, includes a payment link, references the correct invoice number (#1476) and amount (₹80,000), and maintains a warm, helpful tone appropriate for STAGE_1. The word count is well under 200 words.', 'Compliance Judge', 'Approved email draft', 'Subject: Friendly check-in: Invoice #1476 for NovaTech Labs

Hi Arjun,

I hope you’re doing well and that things are moving along smoothly over at NovaTech Labs. 

I’m following up regarding Invoice #1476 for ₹80,000, which was due on August 2, 2026. As a seed-stage startup, we know how hectic things can get, so I wanted to bring this back to the top of your inbox. 

To help clear this balance, you can securely process the payment directly here: {payment_link}. 

If cash flow is currently tight, let’s chat. We’d be happy to discuss a flexible resolution, such as a 10% early payment discount if settled by the end of this week, or a structured payment plan to help ease the load. 

Please let me know how we can support you on this. 

Best regards,

[Your Name]  
[Your Title/Company]', 'PASS', 'llm');
INSERT INTO public.audit_logs VALUES (27449, 1476, '2026-09-07 06:34:11.858945', 'TOOL_CALL', 'Created a mock Razorpay payment link for INR 80,000', 'All side effects flow through audited tools', 'create_payment_link(amount=80000.0, description=Payment for Invoice 1476)', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27450, 1476, '2026-09-07 06:34:11.859945', 'TOOL_CALL', 'Dispatched the STAGE_1 email to arjun@novatechlabs.com', 'All side effects flow through audited tools', 'send_email(to=arjun@novatechlabs.com, subject=Invoice 1476 - payment reminder, stage=STAGE_1)', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27451, 1476, '2026-09-07 06:34:11.860945', 'EMAIL_SENT', 'STAGE_1 Escalation (contact 1 of 5)', NULL, 'Drafted and sent STAGE_1 email', 'Subject: Friendly check-in: Invoice #1476 for NovaTech Labs

Hi Arjun,

I hope you’re doing well and that things are moving along smoothly over at NovaTech Labs. 

I’m following up regarding Invoice #1476 for ₹80,000, which was due on August 2, 2026. As a seed-stage startup, we know how hectic things can get, so I wanted to bring this back to the top of your inbox. 

To help clear this balance, you can securely process the payment directly here: {payment_link}. 

If cash flow is currently tight, let’s chat. We’d be happy to discuss a flexible resolution, such as a 10% early payment discount if settled by the end of this week, or a structured payment plan to help ease the load. 

Please let me know how we can support you on this. 

Best regards,

[Your Name]  
[Your Title/Company]', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27452, 1476, '2026-09-07 06:34:11.861945', 'NO_RESPONSE', '[SIMULATED ENVIRONMENT] No response. base 0.07 x stage 1.0 x action 1.00 (standard escalation email) x relationship 1.0 = 0.070', NULL, 'Client did not respond', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27453, 1476, '2026-09-07 06:34:11.862945', 'GRAPH_PATH', 'decide_action -> validate_action -> draft_email -> evaluate_compliance -> call_razorpay_tools -> execute_action -> simulate_client', NULL, 'Traversed 7 nodes', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27454, 1477, '2026-09-07 06:34:11.855945', 'STATUS_CHANGED', 'Due date passed', NULL, 'Marked as OVERDUE', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27455, 1477, '2026-09-07 06:34:11.856945', 'AGENT_DECISION', '32 days overdue at OVERDUE; no day(s) since last contact meets the 4-day patience threshold for this client. STAGE_1 is within the autonomous limit of STAGE_3. [selected by deterministic policy - DEMO_FAST: non-hero invoice]', 'Alternatives considered: WAIT, OFFER_DISCOUNT, SPLIT_INVOICE, ESCALATE_TO_HUMAN', 'Chose SEND_EMAIL at STAGE_1 | confidence 0.65', 'Expected outcome: Client responds to the STAGE_1 notice or pays.
Decision source: policy_heuristic', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27456, 1477, '2026-09-07 06:34:11.857945', 'COMPLIANCE_PASSED', 'Mock pass (DEMO_FAST: non-hero invoice)', 'Compliance Judge', 'Approved email draft', '[FALLBACK DRAFT - template, not AI-generated | DEMO_FAST: non-hero invoice]
[STAGE_1]
Dear Prakash-Reddy,
Invoice 1477 for INR 1644135.0 is overdue. Please arrange payment.
Link: {{payment_link}}', 'PASS', 'deterministic');
INSERT INTO public.audit_logs VALUES (27457, 1477, '2026-09-07 06:34:11.858945', 'TOOL_CALL', 'Created a mock Razorpay payment link for INR 1,644,135', 'All side effects flow through audited tools', 'create_payment_link(amount=1644135.0, description=Payment for Invoice 1477)', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27458, 1477, '2026-09-07 06:34:11.859945', 'TOOL_CALL', 'Dispatched the STAGE_1 email to finance@prakash-reddy.com', 'All side effects flow through audited tools', 'send_email(to=finance@prakash-reddy.com, subject=Invoice 1477 - payment reminder, stage=STAGE_1)', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27459, 1477, '2026-09-07 06:34:11.860945', 'EMAIL_SENT', 'STAGE_1 Escalation (contact 1 of 5)', NULL, 'Drafted and sent STAGE_1 email', '[FALLBACK DRAFT - template, not AI-generated | DEMO_FAST: non-hero invoice]
[STAGE_1]
Dear Prakash-Reddy,
Invoice 1477 for INR 1644135.0 is overdue. Please arrange payment.
Link: https://rzp.io/l/1477_1788676462', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27460, 1477, '2026-09-07 06:34:11.861945', 'NO_RESPONSE', '[SIMULATED ENVIRONMENT] No response. base 0.15 x stage 1.0 x action 1.00 (standard escalation email) x relationship 1.0 = 0.150', NULL, 'Client did not respond', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27461, 1477, '2026-09-07 06:34:11.862945', 'GRAPH_PATH', 'decide_action -> validate_action -> draft_email -> evaluate_compliance -> call_razorpay_tools -> execute_action -> simulate_client', NULL, 'Traversed 7 nodes', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27462, 1473, '2026-09-08 06:34:11.855945', 'AGENT_DECISION', 'Acme Corp is a Tier 1 client with a strong payment history where delays stem from internal approval cycles rather than cash flow issues. Given that the first Stage 1 email was sent zero days ago and the escalation patience is 11 days, waiting is the correct policy-aligned action to preserve the high-value relationship.', 'Alternatives considered: SEND_EMAIL, OFFER_DISCOUNT, SPLIT_INVOICE, ESCALATE_TO_HUMAN', 'Chose WAIT for 11d | confidence 0.95', 'Expected outcome: Acme Corp will process the invoice through their internal approval cycle and settle the payment within the waiting period without requiring further escalation.
Decision source: llm', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27463, 1473, '2026-09-08 06:34:11.856945', 'AGENT_WAIT', 'Acme Corp is a Tier 1 client with a strong payment history where delays stem from internal approval cycles rather than cash flow issues. Given that the first Stage 1 email was sent zero days ago and the escalation patience is 11 days, waiting is the correct policy-aligned action to preserve the high-value relationship.', 'WAIT is a first-class action, not an absence of one', 'Took no action; next review 2026-09-19 (11d)', 'Expected outcome: Acme Corp will process the invoice through their internal approval cycle and settle the payment within the waiting period without requiring further escalation.', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27464, 1473, '2026-09-08 06:34:11.857945', 'PAYMENT_RECEIVED', '[SIMULATED ENVIRONMENT] base 0.34 x stage 1.0 x action 1.40 (reliable payer left to their own approval cycle) x relationship 1.0 = 0.476', NULL, 'Marked as RECOVERED', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27465, 1473, '2026-09-08 06:34:11.858945', 'GRAPH_PATH', 'decide_action -> validate_action -> act_wait -> simulate_client', NULL, 'Traversed 4 nodes', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27466, 1476, '2026-09-08 06:34:11.855945', 'AGENT_DECISION', 'NovaTech Labs is currently at Stage 1 with only one contact attempt made on the same day, and the client profile indicates a history of ghosting on past invoices. We should progress to Stage 2 to maintain pressure while staying within our policy limit before human escalation becomes mandatory.', 'Alternatives considered: WAIT, OFFER_DISCOUNT, SPLIT_INVOICE, ESCALATE_TO_HUMAN', 'Chose SEND_EMAIL at STAGE_2 | confidence 0.90', 'Expected outcome: Arjun Patel will read the Stage 2 email, but given his history of ghosting, this will likely require the subsequent human escalation specified in the policy notes.
Decision source: llm', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27467, 1476, '2026-09-08 06:34:11.856945', 'ACTION_VETOED', 'Last contact was 0 day(s) ago.', 'Guard rule 1: Max 1 contact per 4 days', 'Blocked SEND_EMAIL at STAGE_2 -> substituted WAIT', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27468, 1476, '2026-09-08 06:34:11.857945', 'AGENT_WAIT', 'NovaTech Labs is currently at Stage 1 with only one contact attempt made on the same day, and the client profile indicates a history of ghosting on past invoices. We should progress to Stage 2 to maintain pressure while staying within our policy limit before human escalation becomes mandatory.', 'WAIT is a first-class action, not an absence of one', 'Took no action; next review 2026-09-12 (4d)', 'Expected outcome: Arjun Patel will read the Stage 2 email, but given his history of ghosting, this will likely require the subsequent human escalation specified in the policy notes.', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27469, 1476, '2026-09-08 06:34:11.858945', 'NO_RESPONSE', '[SIMULATED ENVIRONMENT] No response. base 0.07 x stage 1.0 x action 0.35 (waiting on an unreliable payer rarely produces payment) x relationship 1.0 = 0.025', NULL, 'Client did not respond', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27470, 1476, '2026-09-08 06:34:11.859945', 'GRAPH_PATH', 'decide_action -> validate_action -> act_wait -> simulate_client', NULL, 'Traversed 4 nodes', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27471, 1477, '2026-09-08 06:34:11.855945', 'AGENT_DECISION', 'Last contact was 0 day(s) ago and this client''s escalation patience is 4 days. No written profile on file. Apply standard collections policy. Escalating now risks an INR 0 relationship over a delay that historically resolves itself. [selected by deterministic policy - DEMO_FAST: non-hero invoice]', 'Alternatives considered: SEND_EMAIL, OFFER_DISCOUNT, SPLIT_INVOICE, ESCALATE_TO_HUMAN', 'Chose WAIT for 4d | confidence 0.75', 'Expected outcome: Client pays unprompted within 4 day(s).
Decision source: policy_heuristic', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27472, 1477, '2026-09-08 06:34:11.856945', 'AGENT_WAIT', 'Last contact was 0 day(s) ago and this client''s escalation patience is 4 days. No written profile on file. Apply standard collections policy. Escalating now risks an INR 0 relationship over a delay that historically resolves itself.', 'WAIT is a first-class action, not an absence of one', 'Took no action; next review 2026-09-12 (4d)', 'Expected outcome: Client pays unprompted within 4 day(s).', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27473, 1477, '2026-09-08 06:34:11.857945', 'NO_RESPONSE', '[SIMULATED ENVIRONMENT] No response. base 0.15 x stage 1.0 x action 0.35 (waiting on an unreliable payer rarely produces payment) x relationship 1.0 = 0.052', NULL, 'Client did not respond', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27474, 1477, '2026-09-08 06:34:11.858945', 'GRAPH_PATH', 'decide_action -> validate_action -> act_wait -> simulate_client', NULL, 'Traversed 4 nodes', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27475, 1476, '2026-09-09 06:34:11.855945', 'AGENT_DECISION', 'NovaTech Labs is currently at Stage 1 with only one contact attempt made on the same day, and the client profile indicates a history of ghosting on past invoices. We should progress to Stage 2 to maintain pressure while staying within our policy limit before human escalation becomes mandatory. [selected by deterministic policy - None]', 'Alternatives considered: WAIT, OFFER_DISCOUNT, SPLIT_INVOICE, ESCALATE_TO_HUMAN', 'Chose SEND_EMAIL at STAGE_2 | confidence 0.90', 'Expected outcome: Arjun Patel will read the Stage 2 email, but given his history of ghosting, this will likely require the subsequent human escalation specified in the policy notes.
Decision source: llm_cached', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27476, 1476, '2026-09-09 06:34:11.856945', 'ACTION_VETOED', 'Last contact was 1 day(s) ago.', 'Guard rule 1: Max 1 contact per 4 days', 'Blocked SEND_EMAIL at STAGE_2 -> substituted WAIT', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27477, 1476, '2026-09-09 06:34:11.857945', 'AGENT_WAIT', 'NovaTech Labs is currently at Stage 1 with only one contact attempt made on the same day, and the client profile indicates a history of ghosting on past invoices. We should progress to Stage 2 to maintain pressure while staying within our policy limit before human escalation becomes mandatory.', 'WAIT is a first-class action, not an absence of one', 'Took no action; next review 2026-09-12 (3d)', 'Expected outcome: Arjun Patel will read the Stage 2 email, but given his history of ghosting, this will likely require the subsequent human escalation specified in the policy notes.', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27478, 1476, '2026-09-09 06:34:11.858945', 'NO_RESPONSE', '[SIMULATED ENVIRONMENT] No response. base 0.07 x stage 1.0 x action 0.35 (waiting on an unreliable payer rarely produces payment) x relationship 1.0 = 0.025', NULL, 'Client did not respond', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27479, 1476, '2026-09-09 06:34:11.859945', 'GRAPH_PATH', 'decide_action -> validate_action -> act_wait -> simulate_client', NULL, 'Traversed 4 nodes', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27480, 1477, '2026-09-09 06:34:11.855945', 'AGENT_DECISION', 'Last contact was 1 day(s) ago and this client''s escalation patience is 4 days. No written profile on file. Apply standard collections policy. Escalating now risks an INR 0 relationship over a delay that historically resolves itself. [selected by deterministic policy - DEMO_FAST: non-hero invoice]', 'Alternatives considered: SEND_EMAIL, OFFER_DISCOUNT, SPLIT_INVOICE, ESCALATE_TO_HUMAN', 'Chose WAIT for 3d | confidence 0.75', 'Expected outcome: Client pays unprompted within 3 day(s).
Decision source: policy_heuristic', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27481, 1477, '2026-09-09 06:34:11.856945', 'AGENT_WAIT', 'Last contact was 1 day(s) ago and this client''s escalation patience is 4 days. No written profile on file. Apply standard collections policy. Escalating now risks an INR 0 relationship over a delay that historically resolves itself.', 'WAIT is a first-class action, not an absence of one', 'Took no action; next review 2026-09-12 (3d)', 'Expected outcome: Client pays unprompted within 3 day(s).', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27482, 1477, '2026-09-09 06:34:11.857945', 'NO_RESPONSE', '[SIMULATED ENVIRONMENT] No response. base 0.15 x stage 1.0 x action 0.35 (waiting on an unreliable payer rarely produces payment) x relationship 1.0 = 0.052', NULL, 'Client did not respond', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27483, 1477, '2026-09-09 06:34:11.858945', 'GRAPH_PATH', 'decide_action -> validate_action -> act_wait -> simulate_client', NULL, 'Traversed 4 nodes', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27484, 1476, '2026-09-10 06:34:11.855945', 'AGENT_DECISION', 'NovaTech Labs is currently at Stage 1 with only one contact attempt made on the same day, and the client profile indicates a history of ghosting on past invoices. We should progress to Stage 2 to maintain pressure while staying within our policy limit before human escalation becomes mandatory. [selected by deterministic policy - None]', 'Alternatives considered: WAIT, OFFER_DISCOUNT, SPLIT_INVOICE, ESCALATE_TO_HUMAN', 'Chose SEND_EMAIL at STAGE_2 | confidence 0.90', 'Expected outcome: Arjun Patel will read the Stage 2 email, but given his history of ghosting, this will likely require the subsequent human escalation specified in the policy notes.
Decision source: llm_cached', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27485, 1476, '2026-09-10 06:34:11.856945', 'ACTION_VETOED', 'Last contact was 2 day(s) ago.', 'Guard rule 1: Max 1 contact per 4 days', 'Blocked SEND_EMAIL at STAGE_2 -> substituted WAIT', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27486, 1476, '2026-09-10 06:34:11.857945', 'AGENT_WAIT', 'NovaTech Labs is currently at Stage 1 with only one contact attempt made on the same day, and the client profile indicates a history of ghosting on past invoices. We should progress to Stage 2 to maintain pressure while staying within our policy limit before human escalation becomes mandatory.', 'WAIT is a first-class action, not an absence of one', 'Took no action; next review 2026-09-12 (2d)', 'Expected outcome: Arjun Patel will read the Stage 2 email, but given his history of ghosting, this will likely require the subsequent human escalation specified in the policy notes.', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27487, 1476, '2026-09-10 06:34:11.858945', 'NO_RESPONSE', '[SIMULATED ENVIRONMENT] No response. base 0.07 x stage 1.0 x action 0.35 (waiting on an unreliable payer rarely produces payment) x relationship 1.0 = 0.025', NULL, 'Client did not respond', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27488, 1476, '2026-09-10 06:34:11.859945', 'GRAPH_PATH', 'decide_action -> validate_action -> act_wait -> simulate_client', NULL, 'Traversed 4 nodes', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27489, 1477, '2026-09-10 06:34:11.855945', 'AGENT_DECISION', 'Last contact was 2 day(s) ago and this client''s escalation patience is 4 days. No written profile on file. Apply standard collections policy. Escalating now risks an INR 0 relationship over a delay that historically resolves itself. [selected by deterministic policy - DEMO_FAST: non-hero invoice]', 'Alternatives considered: SEND_EMAIL, OFFER_DISCOUNT, SPLIT_INVOICE, ESCALATE_TO_HUMAN', 'Chose WAIT for 2d | confidence 0.75', 'Expected outcome: Client pays unprompted within 2 day(s).
Decision source: policy_heuristic', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27490, 1477, '2026-09-10 06:34:11.856945', 'AGENT_WAIT', 'Last contact was 2 day(s) ago and this client''s escalation patience is 4 days. No written profile on file. Apply standard collections policy. Escalating now risks an INR 0 relationship over a delay that historically resolves itself.', 'WAIT is a first-class action, not an absence of one', 'Took no action; next review 2026-09-12 (2d)', 'Expected outcome: Client pays unprompted within 2 day(s).', NULL, NULL);
INSERT INTO public.audit_logs VALUES (27491, 1477, '2026-09-10 06:34:11.857945', 'PAYMENT_RECEIVED', '[SIMULATED ENVIRONMENT] base 0.15 x stage 1.0 x action 0.35 (waiting on an unreliable payer rarely produces payment) x relationship 1.0 = 0.052', NULL, 'Marked as RECOVERED', NULL, NULL, NULL);
INSERT INTO public.audit_logs VALUES (27492, 1477, '2026-09-10 06:34:11.858945', 'GRAPH_PATH', 'decide_action -> validate_action -> act_wait -> simulate_client', NULL, 'Traversed 4 nodes', NULL, NULL, NULL);


--
-- Data for Name: webhook_events; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 27492, true);


--
-- Name: invoices_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.invoices_id_seq', 1477, true);


--
-- Name: webhook_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.webhook_events_id_seq', 1, true);


--
-- PostgreSQL database dump complete
--

\unrestrict 6Gk2bs6e0mJlojFvrGdxPz23EMvtIFrkj5qaXEVwvmhfLrH5A0kakwJNUPJRqbB

