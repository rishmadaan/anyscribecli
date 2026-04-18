/** Shared modal primitive — used by LocalSetupModal and OnboardingWizard.
 *
 * Handles focus trap, ARIA dialog semantics, Escape-to-close, backdrop click
 * dismiss. Callers supply the content; this layer is purely containment and
 * accessibility plumbing.
 */

import { useEffect, useRef } from "react";

const FOCUSABLE_SELECTOR =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

interface ModalProps {
  children: React.ReactNode;
  onClose: () => void;
  /** When true, Escape + backdrop-click don't close. Use while work is in flight. */
  disableClose?: boolean;
  /** Visible text that labels the dialog for screen readers. */
  ariaLabel?: string;
  /** Optional: element ID whose text content labels the dialog. Preferred over ariaLabel. */
  ariaLabelledBy?: string;
  /** Width preset. Defaults to "lg" (max-w-lg). */
  size?: "sm" | "md" | "lg" | "xl" | "2xl";
}

const SIZE_CLASS: Record<NonNullable<ModalProps["size"]>, string> = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
};

export default function Modal({
  children,
  onClose,
  disableClose = false,
  ariaLabel,
  ariaLabelledBy,
  size = "lg",
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const lastActiveRef = useRef<HTMLElement | null>(null);

  // Focus management: remember who had focus before open, move focus into the
  // panel on mount, restore on unmount. Keeps screen-reader + keyboard users
  // sane.
  useEffect(() => {
    lastActiveRef.current = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    if (!panel) return;

    const focusables = panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    const first = focusables[0];
    if (first) {
      first.focus();
    } else {
      panel.focus();
    }

    return () => {
      lastActiveRef.current?.focus?.();
    };
  }, []);

  // Escape + focus trap.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !disableClose) {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab") return;

      const panel = panelRef.current;
      if (!panel) return;
      const focusables = Array.from(
        panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      ).filter((el) => !el.hasAttribute("disabled"));
      if (focusables.length === 0) {
        e.preventDefault();
        return;
      }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement as HTMLElement | null;

      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, disableClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      onClick={() => {
        if (!disableClose) onClose();
      }}
      role="presentation"
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabelledBy ? undefined : ariaLabel}
        aria-labelledby={ariaLabelledBy}
        tabIndex={-1}
        className={`relative w-full ${SIZE_CLASS[size]} rounded-xl border border-border-subtle bg-surface p-5 shadow-2xl animate-fade-in outline-none`}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
