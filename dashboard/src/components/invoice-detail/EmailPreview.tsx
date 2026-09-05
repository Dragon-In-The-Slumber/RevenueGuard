import { Fragment, ReactNode } from "react";

/**
 * Renders a model-drafted email as React nodes rather than raw HTML.
 *
 * This previously ran the draft through a few regexes and handed the result to
 * dangerouslySetInnerHTML. The body is LLM output built from retrieved client
 * context, so a prompt-injected or merely malformed draft could inject markup
 * into the dashboard. Parsing into elements makes that structurally impossible:
 * anything not recognised as a link is rendered as text and escaped by React.
 */

const MARKDOWN_LINK = /\[([^\]]+)\]\(([^)]+)\)/g;
const PAYMENT_PLACEHOLDER = /\{\{payment_link\}\}/g;
const BARE_URL = /(https?:\/\/[^\s<>"')]+)/g;

/** Only http(s) links are rendered as anchors — no javascript:, data: or vbscript:. */
function safeHref(url: string): string | null {
  try {
    const parsed = new URL(url, "https://example.invalid");
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

function Anchor({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer nofollow"
      className="text-blue-600 hover:underline"
    >
      {children}
    </a>
  );
}

/** Split one line into text and link nodes. Everything else stays plain text. */
function renderLine(line: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let n = 0;

  // Markdown links first, so their label text is not re-scanned for bare URLs.
  for (const match of line.matchAll(MARKDOWN_LINK)) {
    const [full, label, url] = match;
    const start = match.index ?? 0;
    if (start > cursor) nodes.push(...renderPlain(line.slice(cursor, start), `${keyPrefix}-t${n++}`));

    const href = safeHref(url);
    nodes.push(
      href
        ? <Anchor key={`${keyPrefix}-a${n++}`} href={href}>{label}</Anchor>
        : <Fragment key={`${keyPrefix}-a${n++}`}>{full}</Fragment>
    );
    cursor = start + full.length;
  }

  if (cursor < line.length) nodes.push(...renderPlain(line.slice(cursor), `${keyPrefix}-t${n++}`));
  return nodes;
}

/** Handle the payment placeholder and bare URLs inside a plain-text run. */
function renderPlain(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  text.split(PAYMENT_PLACEHOLDER).forEach((chunk, i) => {
    if (i > 0) {
      nodes.push(
        <span key={`${keyPrefix}-p${i}`} className="text-blue-600 underline">
          Razorpay Secure Payment Link
        </span>
      );
    }
    chunk.split(BARE_URL).forEach((part, j) => {
      if (!part) return;
      const href = BARE_URL.test(part) ? safeHref(part) : null;
      BARE_URL.lastIndex = 0;
      nodes.push(
        href
          ? <Anchor key={`${keyPrefix}-u${i}-${j}`} href={href}>{part}</Anchor>
          : <Fragment key={`${keyPrefix}-s${i}-${j}`}>{part}</Fragment>
      );
    });
  });
  return nodes;
}

export default function EmailPreview({ emailBody }: { emailBody: string }) {
  const lines = (emailBody || "").split("\n");

  return (
    <div className="bg-white rounded-md overflow-hidden text-black shadow-inner border border-white/20 mt-3">
      <div className="bg-gray-100 border-b border-gray-200 px-4 py-2 text-xs text-gray-500 font-sans flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-red-400"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-amber-400"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-green-400"></div>
        </div>
        <span>Message Preview</span>
      </div>
      <div className="p-4 text-sm font-sans text-gray-800 leading-relaxed whitespace-pre-wrap break-words">
        {lines.map((line, i) => (
          <Fragment key={i}>
            {renderLine(line, `l${i}`)}
            {i < lines.length - 1 && <br />}
          </Fragment>
        ))}
      </div>
    </div>
  );
}
