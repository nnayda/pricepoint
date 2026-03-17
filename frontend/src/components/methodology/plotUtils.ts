export function humanizeFilename(path: string): string {
  const filename = path.split("/").pop() ?? path;
  return filename
    .replace(/\.png$/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
