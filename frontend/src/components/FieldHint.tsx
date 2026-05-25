import type { ReactNode } from "react";

type FieldHintProps = {
  children: ReactNode;
  id: string;
  tone?: "neutral" | "error";
};

export function FieldHint({ children, id, tone = "neutral" }: FieldHintProps) {
  return (
    <p className={`field-hint ${tone === "error" ? "field-hint-error" : ""}`} id={id}>
      {children}
    </p>
  );
}
