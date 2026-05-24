import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

/**
 * Renders the orchestrator's final reply as GitHub-flavored markdown.
 * Styling is tuned to fit inside the assistant chat bubble: tight vertical
 * rhythm, monospace code, subtle borders/backgrounds drawn from theme tokens.
 */
export function Markdown({
  children,
  className,
}: {
  children: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        // Block spacing: first/last child flush with bubble padding.
        "text-sm leading-relaxed",
        "[&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
        // Paragraphs.
        "[&_p]:my-2 [&_p]:whitespace-pre-wrap",
        // Headings.
        "[&_h1]:text-base [&_h1]:font-semibold [&_h1]:mt-4 [&_h1]:mb-2",
        "[&_h2]:text-sm [&_h2]:font-semibold [&_h2]:mt-4 [&_h2]:mb-2",
        "[&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mt-3 [&_h3]:mb-1.5",
        "[&_h4]:text-sm [&_h4]:font-medium [&_h4]:mt-3 [&_h4]:mb-1",
        // Lists.
        "[&_ul]:my-2 [&_ul]:pl-5 [&_ul]:list-disc [&_ul]:space-y-1",
        "[&_ol]:my-2 [&_ol]:pl-5 [&_ol]:list-decimal [&_ol]:space-y-1",
        "[&_li]:marker:text-muted-foreground",
        "[&_li>p]:my-0",
        // Inline emphasis.
        "[&_strong]:font-semibold [&_em]:italic",
        // Links.
        "[&_a]:text-primary [&_a]:underline [&_a]:underline-offset-2 hover:[&_a]:opacity-80",
        // Inline code.
        "[&_code]:font-mono [&_code]:text-[0.85em] [&_code]:bg-background/60 [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:border [&_code]:border-border",
        // Code blocks (pre wrapper resets inline code styles).
        "[&_pre]:my-2 [&_pre]:p-3 [&_pre]:bg-background [&_pre]:border [&_pre]:border-border [&_pre]:rounded-md [&_pre]:overflow-x-auto",
        "[&_pre_code]:bg-transparent [&_pre_code]:border-0 [&_pre_code]:p-0 [&_pre_code]:text-xs [&_pre_code]:leading-relaxed",
        // Blockquote.
        "[&_blockquote]:my-2 [&_blockquote]:pl-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:text-muted-foreground",
        // Horizontal rule.
        "[&_hr]:my-3 [&_hr]:border-border",
        // Tables (remark-gfm).
        "[&_table]:my-2 [&_table]:w-full [&_table]:border-collapse [&_table]:text-xs",
        "[&_th]:text-left [&_th]:font-semibold [&_th]:border [&_th]:border-border [&_th]:px-2 [&_th]:py-1 [&_th]:bg-background/60",
        "[&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_td]:align-top",
        // Task list checkboxes (remark-gfm).
        "[&_input[type=checkbox]]:mr-1.5 [&_input[type=checkbox]]:align-middle",
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Open external links in a new tab safely.
          a: ({ node: _node, ...props }) => (
            <a
              {...props}
              target="_blank"
              rel="noopener noreferrer"
            />
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
