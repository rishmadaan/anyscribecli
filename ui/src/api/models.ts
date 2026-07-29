import type { Provider } from "./types";

/** Default model for a provider: the pinned one, else the provider's first. */
export function defaultModelFor(
  provider: Provider | undefined,
  pinned: Record<string, string> | undefined
): string {
  if (!provider) return "";
  return (pinned ?? {})[provider.name] ?? provider.models?.[0] ?? "";
}

/** True when the provider offers a real choice worth rendering a control for. */
export function hasModelChoice(provider: Provider | undefined): boolean {
  return !!provider && (provider.freeform_model || (provider.models?.length ?? 0) > 1);
}
