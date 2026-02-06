/**
 * Wrapper around the View Transitions API with progressive enhancement fallback.
 * On browsers that don't support `document.startViewTransition`, the callback
 * is executed immediately and a resolved pseudo-ViewTransition is returned.
 */
export function startViewTransition(callback: () => Promise<void> | void): ViewTransition {
  if (document.startViewTransition) {
    return document.startViewTransition(callback) as ViewTransition;
  }

  // Fallback: run callback immediately, return a resolved pseudo-transition
  let done: Promise<void>;
  try {
    done = Promise.resolve(callback()).then(() => undefined);
  } catch (e) {
    done = Promise.reject(e);
  }

  return {
    finished: done,
    ready: Promise.resolve(),
    updateCallbackDone: done,
    skipTransition: () => {},
    types: new Set<string>(),
  };
}
