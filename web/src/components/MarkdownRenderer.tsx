import { Box, Link, Typography } from "@mui/material";

const inlinePattern = /`[^`]+`|\[[^\]]+\]\([^\s)]+\)|\*\*(.+?)\*\*|_(.+?)_/g;
const italicOpens = (text: string, index: number) => index === 0 || /[\s("']/.test(text[index - 1]);
const italicCloses = (text: string, end: number) => end === text.length || /[\s.,;:!?)"']/.test(text[end]);

/** Parse inline code, links, **bold** and _italic_ into React nodes (never HTML). */
const parseInline = (text: string, keyPrefix = "i"): React.ReactNode[] => {
  const nodes: React.ReactNode[] = [];
  const pattern = new RegExp(inlinePattern.source, "g");
  let cursor = 0;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    const [token, bold, italic] = match;
    const end = match.index + token.length;
    // `_` inside identifiers such as order_items is not emphasis.
    if (italic !== undefined && (!italicOpens(text, match.index) || !italicCloses(text, end))) {
      pattern.lastIndex = match.index + 1;
      continue;
    }
    if (match.index > cursor) nodes.push(text.slice(cursor, match.index));
    const key = `${keyPrefix}-${match.index}`;
    if (bold !== undefined) {
      nodes.push(<strong key={key}>{parseInline(bold, key)}</strong>);
    } else if (italic !== undefined) {
      nodes.push(<em key={key}>{parseInline(italic, key)}</em>);
    } else if (token.startsWith("`")) {
      nodes.push(
        <Box
          key={key}
          component="code"
          sx={{ fontFamily: "monospace", bgcolor: "action.hover", px: 0.5, borderRadius: 0.5 }}
        >
          {token.slice(1, -1)}
        </Box>,
      );
    } else {
      const link = /^\[([^\]]+)\]\(([^\s)]+)\)$/.exec(token);
      const href = link && (link[2].startsWith("http://") || link[2].startsWith("https://")) ? link[2] : "#";
      nodes.push(
        <Link key={key} href={href} target="_blank" rel="noopener noreferrer">
          {link ? link[1] : token}
        </Link>,
      );
    }
    cursor = end;
  }
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes;
};

/** Render a safe, tiny Markdown subset without injecting HTML. */
export function MarkdownRenderer({ markdown }: { markdown: string }) {
  const lines = markdown.split(/\r?\n/);
  const blocks: React.ReactNode[] = [];
  let paragraph: string[] = [];
  let list: string[] = [];
  let listKind: "ul" | "ol" = "ul";
  let code: string[] | null = null;

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push(
        <Typography key={`p-${blocks.length}`} sx={{ mb: 1.5 }}>
          {parseInline(paragraph.join(" "))}
        </Typography>,
      );
      paragraph = [];
    }
  };
  const flushList = () => {
    if (list.length) {
      blocks.push(
        <Box key={`${listKind}-${blocks.length}`} component={listKind} sx={{ pl: 3, my: 1 }}>
          {list.map((item, index) => (
            <li key={`${item}-${index}`}>
              <Typography component="span">{parseInline(item)}</Typography>
            </li>
          ))}
        </Box>,
      );
      list = [];
    }
  };

  for (const line of lines) {
    if (line.startsWith("```")) {
      if (code) {
        blocks.push(
          <Box
            key={`code-${blocks.length}`}
            component="pre"
            sx={{ overflow: "auto", p: 2, borderRadius: 2, bgcolor: "action.hover" }}
          >
            <code>{code.join("\n")}</code>
          </Box>,
        );
        code = null;
      } else {
        flushParagraph();
        flushList();
        code = [];
      }
      continue;
    }
    if (code) {
      code.push(line);
      continue;
    }
    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }
    const heading = /^(#{1,3})\s+(.+)$/.exec(line);
    if (heading) {
      flushParagraph();
      flushList();
      const variant = heading[1].length === 1 ? "h6" : "subtitle1";
      blocks.push(
        <Typography key={`h-${blocks.length}`} variant={variant} sx={{ mt: 1.5, mb: 1, fontWeight: 700 }}>
          {parseInline(heading[2])}
        </Typography>,
      );
      continue;
    }
    const bullet = /^\s*[-*]\s+(.+)$/.exec(line);
    const numbered = /^\s*\d+[.)]\s+(.+)$/.exec(line);
    if (bullet || numbered) {
      flushParagraph();
      const kind = numbered ? "ol" : "ul";
      if (list.length && kind !== listKind) flushList();
      listKind = kind;
      list.push((numbered ?? bullet)![1]);
      continue;
    }
    paragraph.push(line.trim());
  }
  flushParagraph();
  flushList();

  return <Box>{blocks.length ? blocks : <Typography color="text.secondary">No answer.</Typography>}</Box>;
}
