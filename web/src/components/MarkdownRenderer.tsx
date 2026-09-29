import { Box, Link, Typography } from "@mui/material";

const parseInline = (text: string) => {
  const parts = text.split(/(`[^`]+`|\[[^\]]+\]\([^\s)]+\))/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <Box
          key={`${part}-${index}`}
          component="code"
          sx={{ fontFamily: "monospace", bgcolor: "action.hover", px: 0.5, borderRadius: 0.5 }}
        >
          {part.slice(1, -1)}
        </Box>
      );
    }
    const link = /^\[([^\]]+)\]\(([^\s)]+)\)$/.exec(part);
    if (link) {
      const href = link[2].startsWith("http://") || link[2].startsWith("https://") ? link[2] : "#";
      return (
        <Link key={`${part}-${index}`} href={href} target="_blank" rel="noopener noreferrer">
          {link[1]}
        </Link>
      );
    }
    return part;
  });
};

/** Render a safe, tiny Markdown subset without injecting HTML. */
export function MarkdownRenderer({ markdown }: { markdown: string }) {
  const lines = markdown.split(/\r?\n/);
  const blocks: React.ReactNode[] = [];
  let paragraph: string[] = [];
  let list: string[] = [];
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
        <Box key={`ul-${blocks.length}`} component="ul" sx={{ pl: 3, my: 1 }}>
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
          {heading[2]}
        </Typography>,
      );
      continue;
    }
    const bullet = /^[-*]\s+(.+)$/.exec(line);
    if (bullet) {
      flushParagraph();
      list.push(bullet[1]);
      continue;
    }
    paragraph.push(line.trim());
  }
  flushParagraph();
  flushList();

  return <Box>{blocks.length ? blocks : <Typography color="text.secondary">No answer.</Typography>}</Box>;
}
