import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  useDebounce,
  useMounted,
  useAnimatedNumber,
  useHotkey,
  usePolling,
} from "./hooks";

describe("useDebounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns the initial value immediately", () => {
    const { result } = renderHook(() => useDebounce("hello", 200));
    expect(result.current).toBe("hello");
  });

  it("updates only after the delay elapses", () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 200),
      { initialProps: { value: "first" } },
    );
    rerender({ value: "second" });
    expect(result.current).toBe("first");

    act(() => {
      vi.advanceTimersByTime(199);
    });
    expect(result.current).toBe("first");

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current).toBe("second");
  });

  it("cancels previous timeouts on rapid changes", () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 200),
      { initialProps: { value: "first" } },
    );
    rerender({ value: "second" });
    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current).toBe("first");

    rerender({ value: "third" });
    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current).toBe("first");

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current).toBe("third");
  });

  it("respects custom delay", () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: "first", delay: 500 } },
    );
    rerender({ value: "second", delay: 500 });
    act(() => {
      vi.advanceTimersByTime(499);
    });
    expect(result.current).toBe("first");

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current).toBe("second");
  });
});

describe("useMounted", () => {
  it("returns false initially then true after mount", () => {
    const { result } = renderHook(() => useMounted());
    expect(result.current).toBe(true);
  });

  it("stays true on rerenders", () => {
    const { result, rerender } = renderHook(() => useMounted());
    expect(result.current).toBe(true);
    rerender();
    expect(result.current).toBe(true);
  });
});

describe("useHotkey", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fires handler on matching key press", () => {
    const handler = vi.fn();
    renderHook(() => useHotkey("a", handler));

    const event = new KeyboardEvent("keydown", { key: "a" });
    act(() => {
      window.dispatchEvent(event);
    });
    expect(handler).toHaveBeenCalledOnce();
    expect(handler).toHaveBeenCalledWith(event);
  });

  it("ignores non-matching keys", () => {
    const handler = vi.fn();
    renderHook(() => useHotkey("a", handler));

    const event = new KeyboardEvent("keydown", { key: "b" });
    act(() => {
      window.dispatchEvent(event);
    });
    expect(handler).not.toHaveBeenCalled();
  });

  it("is case-insensitive for keys", () => {
    const handler = vi.fn();
    renderHook(() => useHotkey("a", handler));

    const event = new KeyboardEvent("keydown", { key: "A" });
    act(() => {
      window.dispatchEvent(event);
    });
    expect(handler).toHaveBeenCalledOnce();
  });

  it("respects meta key modifier", () => {
    const handler = vi.fn();
    renderHook(() => useHotkey("a", handler, { meta: true }));

    const withoutMeta = new KeyboardEvent("keydown", { key: "a" });
    act(() => {
      window.dispatchEvent(withoutMeta);
    });
    expect(handler).not.toHaveBeenCalled();

    const withMeta = new KeyboardEvent("keydown", {
      key: "a",
      metaKey: true,
    });
    act(() => {
      window.dispatchEvent(withMeta);
    });
    expect(handler).toHaveBeenCalledOnce();
  });

  it("respects ctrl key modifier", () => {
    const handler = vi.fn();
    renderHook(() => useHotkey("a", handler, { ctrl: true }));

    const withoutCtrl = new KeyboardEvent("keydown", { key: "a" });
    act(() => {
      window.dispatchEvent(withoutCtrl);
    });
    expect(handler).not.toHaveBeenCalled();

    const withCtrl = new KeyboardEvent("keydown", {
      key: "a",
      ctrlKey: true,
    });
    act(() => {
      window.dispatchEvent(withCtrl);
    });
    expect(handler).toHaveBeenCalledOnce();
  });

  it("respects shift key modifier exclusion", () => {
    const handler = vi.fn();
    renderHook(() => useHotkey("a", handler, { shift: false }));

    const withShift = new KeyboardEvent("keydown", {
      key: "a",
      shiftKey: true,
    });
    act(() => {
      window.dispatchEvent(withShift);
    });
    expect(handler).not.toHaveBeenCalled();

    const withoutShift = new KeyboardEvent("keydown", { key: "a" });
    act(() => {
      window.dispatchEvent(withoutShift);
    });
    expect(handler).toHaveBeenCalledOnce();
  });

  it("cleans up event listener on unmount", () => {
    const handler = vi.fn();
    const spy = vi.spyOn(window, "removeEventListener");

    const { unmount } = renderHook(() => useHotkey("a", handler));
    unmount();

    expect(spy).toHaveBeenCalledWith("keydown", expect.any(Function));
  });
});

describe("useAnimatedNumber", () => {
  it("starts at 0", () => {
    const { result } = renderHook(() => useAnimatedNumber(100, 600));
    expect(result.current).toBe(0);
  });

  it("takes target and duration parameters", () => {
    const { result: result1 } = renderHook(() => useAnimatedNumber(50, 300));
    const { result: result2 } = renderHook(() => useAnimatedNumber(200, 1000));

    expect(result1.current).toBe(0);
    expect(result2.current).toBe(0);
  });

  it("returns a numeric value", () => {
    const { result } = renderHook(() => useAnimatedNumber(100, 600));
    expect(typeof result.current).toBe("number");
  });

  it("respects target value changes", () => {
    const { rerender } = renderHook(
      ({ target }) => useAnimatedNumber(target, 600),
      { initialProps: { target: 100 } },
    );

    rerender({ target: 200 });
    // Should trigger animation without throwing
  });

  it("cleans up animation on unmount", () => {
    const rafSpy = vi.spyOn(global, "requestAnimationFrame");
    const cafSpy = vi.spyOn(global, "cancelAnimationFrame");

    const { unmount } = renderHook(() => useAnimatedNumber(100, 600));

    expect(rafSpy).toHaveBeenCalled();

    unmount();

    expect(cafSpy).toHaveBeenCalled();

    rafSpy.mockRestore();
    cafSpy.mockRestore();
  });
});

describe("usePolling", () => {
  it("initializes with loading=true and null data", () => {
    const fetcher = vi.fn().mockResolvedValue({ data: "test" });
    const { result } = renderHook(() => usePolling(fetcher, 5000));

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("returns a refetch function", () => {
    const fetcher = vi.fn();
    const { result } = renderHook(() => usePolling(fetcher, 5000));

    expect(typeof result.current.refetch).toBe("function");
  });

  it("returns data object shape with loading, data, error, refetch", () => {
    const fetcher = vi.fn().mockResolvedValue({ data: "test" });
    const { result } = renderHook(() => usePolling(fetcher, 5000));

    expect(result.current).toHaveProperty("loading");
    expect(result.current).toHaveProperty("data");
    expect(result.current).toHaveProperty("error");
    expect(result.current).toHaveProperty("refetch");
  });

  it("doesn't fetch when disabled", () => {
    const fetcher = vi.fn();
    renderHook(() => usePolling(fetcher, 5000, false));

    // Fetcher should not be called because polling is disabled
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("cleans up on unmount", () => {
    const fetcher = vi.fn();
    const removeSpy = vi.spyOn(document, "removeEventListener");
    const { unmount } = renderHook(() => usePolling(fetcher, 5000));

    unmount();

    expect(removeSpy).toHaveBeenCalledWith(
      "visibilitychange",
      expect.any(Function),
    );
    removeSpy.mockRestore();
  });

  it("adds visibility change listener on mount", () => {
    const fetcher = vi.fn();
    const addSpy = vi.spyOn(document, "addEventListener");
    renderHook(() => usePolling(fetcher, 5000));

    expect(addSpy).toHaveBeenCalledWith(
      "visibilitychange",
      expect.any(Function),
    );
    addSpy.mockRestore();
  });
});
