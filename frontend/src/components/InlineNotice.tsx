import type { ReactNode } from "react";

type InlineNoticeProps = {
  children: ReactNode;
  className?: string;
  title?: string;
  tone?: "info" | "success" | "warning" | "error";
};

export function InlineNotice({ children, className, title, tone = "info" }: InlineNoticeProps) {
  const role = tone === "error" ? "alert" : "status";
  const classes = ["inline-notice", `notice-${tone}`, className].filter(Boolean).join(" ");

  return (
    <div aria-live={tone === "error" ? "assertive" : "polite"} className={classes} role={role}>
      {title ? <strong>{title}</strong> : null}
      <div>{children}</div>
    </div>
  );
}
