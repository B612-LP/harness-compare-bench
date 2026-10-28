// Explicit ZERO-NETWORK interface preflight, not a model response or agent comparison.
// The frozen real capture still validates route/low/budget/tool schema before this sentinel.
globalThis.fetch=async()=>{throw new Error('ZERO_API_RUNTIME_PRECHECK_COMPLETE_NO_NETWORK');};
await import('./capture-preload.mjs');
