export function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export const inputClassName =
  "mt-1 block w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm";

export const labelClassName = "block text-sm font-medium";

export const buttonPrimaryClassName =
  "rounded-md bg-[var(--color-primary-fill)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50";

export const buttonSecondaryClassName =
  "rounded-md border border-[var(--color-border)] px-4 py-2 text-sm font-medium disabled:opacity-50";
