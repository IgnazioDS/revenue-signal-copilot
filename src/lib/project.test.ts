import { describe, expect, it } from "vitest";
import { PROJECT } from "./project";

describe("PROJECT", () => {
  it("has all required identity fields", () => {
    expect(PROJECT.slug).toBe("revenue-signal-copilot");
    expect(PROJECT.name).toBe("Revenue Signal Copilot");
    expect(PROJECT.category).toBe("Business Tool");
    expect(PROJECT.track).toBe("AI/ML");
  });

  it("has well-formed URLs", () => {
    expect(PROJECT.github_url).toMatch(/^https:\/\//);
    expect(PROJECT.eleventh_url).toMatch(/^https:\/\//);
    expect(PROJECT.live_url).toMatch(/^https:\/\//);
    expect(PROJECT.fleet_url).toMatch(/^https:\/\//);
  });

  it("has stack array with technologies", () => {
    expect(Array.isArray(PROJECT.stack)).toBe(true);
    expect(PROJECT.stack.length).toBeGreaterThan(0);
    expect(PROJECT.stack).toContain("Python");
  });

  it("has MVP list with features", () => {
    expect(Array.isArray(PROJECT.mvp)).toBe(true);
    expect(PROJECT.mvp.length).toBeGreaterThan(0);
    expect(PROJECT.mvp[0]).toMatch(/^[A-Z]/);
  });

  it("has problem and users descriptions", () => {
    expect(PROJECT.problem.length).toBeGreaterThan(10);
    expect(PROJECT.users.length).toBeGreaterThan(5);
  });

  it("has system_slug matching the primary slug", () => {
    expect(PROJECT.system_slug).toBe(PROJECT.slug);
  });

  it("has builder attribution", () => {
    expect(PROJECT.builder).toBe("Eleventh Solutions");
  });
});
