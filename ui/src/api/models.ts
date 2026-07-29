import type { Config, Provider } from "./types";

/** Default model for a provider: the pinned one, else the provider's first. */
export function defaultModelFor(
  provider: Provider | undefined,
  pinned: Record<string, string> | undefined
): string {
  if (!provider) return "";
  return (pinned ?? {})[provider.name] ?? provider.models?.[0] ?? "";
}

/**
 * What a quality tier resolves to right now, e.g. "deepgram · nova-3".
 * `local` has no model list — its choice lives in config.local_model.
 */
export function tierSummary(
  tier: string,
  config: Config,
  providers: Provider[]
): { provider: string; model: string; hasKey: boolean } {
  const name = (config._quality_tiers ?? {})[tier] ?? "";
  const p = providers.find((x) => x.name === name);
  return {
    provider: name,
    model:
      name === "local" ? config.local_model : defaultModelFor(p, config.provider_models),
    // Providers not loaded yet → assume fine, so no false "needs API key".
    hasKey: p ? p.has_key : true,
  };
}

/** User-added model slugs for a provider (openrouter only, by design). */
export function extraModelsFor(config: Config, provider: string): string[] {
  return (config.extra_models ?? {})[provider] ?? [];
}
