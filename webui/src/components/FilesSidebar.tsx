import { useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FileMeta } from "@/lib/api";
import {
  File as FileIcon,
  FileText,
  FileSpreadsheet,
  FileImage,
  FileCode,
  FileArchive,
  FileAudio,
  FileVideo,
  Paperclip,
  Upload,
  X,
  Loader2,
} from "lucide-react";

function iconFor(mime: string, name: string) {
  const m = (mime || "").toLowerCase();
  const ext = name.toLowerCase().split(".").pop() ?? "";
  if (m.startsWith("image/")) return FileImage;
  if (m.startsWith("audio/")) return FileAudio;
  if (m.startsWith("video/")) return FileVideo;
  if (m === "application/pdf" || ext === "pdf") return FileText;
  if (
    m.includes("spreadsheet") ||
    m === "text/csv" ||
    ["xlsx", "xls", "csv", "tsv"].includes(ext)
  )
    return FileSpreadsheet;
  if (
    m.includes("zip") ||
    m.includes("tar") ||
    ["zip", "tar", "gz", "7z", "rar"].includes(ext)
  )
    return FileArchive;
  if (
    m.startsWith("text/") ||
    ["md", "txt", "log"].includes(ext)
  )
    return FileText;
  if (
    [
      "js", "ts", "tsx", "jsx", "py", "go", "rs", "rb", "java", "c", "cpp",
      "h", "hpp", "sh", "yaml", "yml", "json", "html", "css",
    ].includes(ext)
  )
    return FileCode;
  return FileIcon;
}

function fmtSize(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function FilesSidebar({
  files,
  uploading,
  onUpload,
  onDelete,
}: {
  files: FileMeta[];
  uploading: boolean;
  onUpload: (files: FileList) => void;
  onDelete: (file_id: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Paperclip className="size-4" />
          Files
          <span className="text-xs font-normal text-muted-foreground ml-auto">
            {files.length}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col gap-3 min-h-0">
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              onUpload(e.target.files);
              e.target.value = "";
            }
          }}
        />
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          {uploading ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <Upload className="size-3.5" />
          )}
          Upload files
        </Button>

        <div className="flex-1 overflow-y-auto -mx-1 px-1 space-y-1">
          {files.length === 0 && (
            <div className="text-xs text-muted-foreground italic px-1 py-2">
              No files in this conversation yet. Uploads are passed to every
              agent the orchestrator routes to.
            </div>
          )}
          {files.map((f) => {
            const Icon = iconFor(f.mime, f.name);
            return (
              <div
                key={f.file_id}
                className="group flex items-start gap-2 rounded-md px-2 py-1.5 hover:bg-accent/40 transition-colors"
              >
                <Icon className="size-4 mt-0.5 text-muted-foreground shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm truncate" title={f.name}>
                    {f.name}
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {fmtSize(f.size)} · {f.mime || "unknown"}
                  </div>
                </div>
                <button
                  onClick={() => onDelete(f.file_id)}
                  className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground transition-opacity"
                  title="Remove"
                >
                  <X className="size-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
