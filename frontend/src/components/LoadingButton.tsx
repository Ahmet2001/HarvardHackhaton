import type { ButtonHTMLAttributes, ReactNode } from "react";

type LoadingButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  busy?: boolean;
  busyLabel?: string;
  children: ReactNode;
  variant?: "primary" | "secondary" | "danger";
};

export function LoadingButton({
  busy = false,
  busyLabel = "Working",
  children,
  className,
  disabled,
  variant = "primary",
  ...props
}: LoadingButtonProps) {
  const classes = ["button", `button-${variant}`, busy ? "is-busy" : "", className].filter(Boolean).join(" ");

  return (
    <button {...props} aria-busy={busy || undefined} className={classes} disabled={disabled || busy}>
      {busy ? busyLabel : children}
    </button>
  );
}
