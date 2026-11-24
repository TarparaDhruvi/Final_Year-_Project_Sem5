
/**
 * Tiny, dependency-free Markdown renderer for AI output: headings, **bold**, *italic*, `code`,
 * bullet / numbered lists, horizontal rules and paragraphs. It builds React elements (never raw HTML),
 * so AI text can't inject markup into the page.
 */
function inline(text, keyBase) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/g;
  let last = 0, m, i = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    const key = `${keyBase}-${i++}`;
    if (tok.startsWith("**")) out.push(<strong key={key}>{inline(tok.slice(2, -2), key)}</strong>);
    else if (tok.startsWith("`")) out.push(<code key={key} className="px-1 py-0.5 rounded bg-slate-200/70 dark:bg-white/10 text-[0.85em] font-mono">{tok.slice(1, -1)}</code>);
    else out.push(<em key={key}>{tok.slice(1, -1)}</em>);
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export default function Markdown({ text, className = "" }) {
  const lines = String(text || "").replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let list = null, para = [];

  const flushPara = () => { if (para.length) { blocks.push({ t: "p", text: para.join(" ") }); para = []; } };
  const flushList = () => { if (list) { blocks.push(list); list = null; } };

  for (const raw of lines) {
    const line = raw.trimEnd();
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    const ul = line.match(/^\s*[-*•]\s+(.*)$/);
    const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
    if (!line.trim()) { flushPara(); flushList(); }
    else if (/^\s*([-*_])\1{2,}\s*$/.test(line)) { flushPara(); flushList(); blocks.push({ t: "hr" }); }
    else if (h) { flushPara(); flushList(); blocks.push({ t: "h", level: h[1].length, text: h[2] }); }
    else if (ul || ol) {
      flushPara();
      const kind = ul ? "ul" : "ol";
      if (!list || list.t !== kind) { flushList(); list = { t: kind, items: [] }; }
      list.items.push((ul || ol)[1]);
    } else { flushList(); para.push(line.trim()); }
  }
  flushPara(); flushList();

  const headingClass = ["text-xl font-bold mt-4 mb-2", "text-lg font-bold mt-4 mb-2", "text-base font-semibold mt-3 mb-1.5"];
  return (
    <div className={`space-y-2 text-sm leading-relaxed ${className}`}>
      {blocks.map((b, i) => {
        if (b.t === "h") return <p key={i} className={`font-display ${headingClass[Math.min(b.level, 3) - 1]}`}>{inline(b.text, `h${i}`)}</p>;
        if (b.t === "hr") return <hr key={i} className="border-slate-200 dark:border-white/10 my-3" />;
        if (b.t === "ul") return <ul key={i} className="list-disc pl-5 space-y-1">{b.items.map((it, k) => <li key={k}>{inline(it, `u${i}-${k}`)}</li>)}</ul>;
        if (b.t === "ol") return <ol key={i} className="list-decimal pl-5 space-y-1">{b.items.map((it, k) => <li key={k}>{inline(it, `o${i}-${k}`)}</li>)}</ol>;
        return <p key={i}>{inline(b.text, `p${i}`)}</p>;
      })}
    </div>
  );
}
