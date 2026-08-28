import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Button({
  children,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode }) {
  return (
    <button
      className={`rounded px-3 py-1.5 text-sm font-medium bg-sky-600 text-white hover:bg-sky-500 disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
