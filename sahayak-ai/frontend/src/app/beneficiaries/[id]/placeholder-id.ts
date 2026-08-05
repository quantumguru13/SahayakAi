/**
 * The single case-file path baked into the static export.
 *
 * Lives in its own module (no "use client") because the server page reads it in
 * generateStaticParams — importing it from the client component would hand the
 * server a client-reference stub instead of the string.
 */
export const PLACEHOLDER_ID = "__id__";
