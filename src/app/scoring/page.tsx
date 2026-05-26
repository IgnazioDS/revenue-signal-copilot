"use client";

import { useState } from "react";
import {
  Activity,
  ChevronDown,
  ChevronRight,
  FlaskConical,
  Github,
  RefreshCw,
  Target,
  TrendingUp,
} from "lucide-react";
import {
  fetchScoringLatest,
  formatDelta,
  liftOverBaseline,
  priorityBadgeVariant,
  type RankedAccount,
  type ScoringLatest,
} from "@/lib/api";
import { TopBar } from "@/components/layout/TopBar";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusDot } from "@/components/ui/status-dot";
import { Skeleton } from "@/components/ui/skeleton";
import { usePolling } from "@/lib/hooks";
import { PROJECT } from "@/lib/project";
import { cn, formatNumber, formatRelative } from "@/lib/utils";

const POLL_INTERVAL_MS = 30_000;
const FIXTURES_URL =
  "https://github.com/IgnazioDS/revenue-signal-copilot/tree/main/examples/fixtures";

// Categorical bar colors for the signal breakdown, drawn from theme tokens only.
const KIND_BAR: Record<string, string> = {
  job_change: "bg-brand",
  infra_shift: "bg-info",
  hiring: "bg-warning",
  internal_note: "bg-success",
};

export default function ScoringPage() {
  const { data, loading, refetch } = usePolling<ScoringLatest>(
    fetchScoringLatest,
    POLL_INTERVAL_MS,
  );

  const ranked = data?.ranked_accounts ?? [];
  const operational = data?.status === "operational";

  return (
    <>
      <TopBar
        title="Scoring"
        description="Latest run of the public, reproducible scoring benchmark"
        actions={
          <Button size="sm" variant="outline" onClick={refetch}>
            <RefreshCw />
            Refresh
          </Button>
        }
      />
      <div className="dot-grid grid-fade flex-1 overflow-y-auto">
        <div className="page-enter mx-auto max-w-5xl space-y-5 p-6">
          <DisclosureBanner data={data} />

          {loading && !data ? (
            <LoadingState />
          ) : !operational || ranked.length === 0 ? (
            <EmptyState />
          ) : (
            <>
              <SummaryRow data={data!} />
              <SignalBreakdown data={data!} />
              <section className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold tracking-tight text-foreground">
                    Top accounts
                  </h2>
                  <p className="text-2xs text-foreground-faint">
                    Click a row to read its full trace
                  </p>
                </div>
                <div className="space-y-2">
                  {ranked.map((account) => (
                    <AccountCard key={account.account_id} account={account} />
                  ))}
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </>
  );
}

function DisclosureBanner({ data }: { data: ScoringLatest | null }) {
  return (
    <Card className="border-brand/20 bg-brand/[0.04]">
      <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-brand/10 text-brand">
            <FlaskConical className="h-3.5 w-3.5" strokeWidth={1.75} />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">
              Scored against a synthetic, public CRM fixture
            </p>
            <p className="mt-0.5 text-2xs leading-relaxed text-foreground-muted">
              {data?.fixture ? `${data.fixture} · ` : ""}
              200 accounts, ~900 typed signals, re-scored daily. Reproducible
              from the repo, not live customer data.
            </p>
          </div>
        </div>
        <Button asChild size="sm" variant="outline">
          <a href={FIXTURES_URL} target="_blank" rel="noreferrer">
            <Github />
            Fixture
          </a>
        </Button>
      </CardContent>
    </Card>
  );
}

function SummaryRow({ data }: { data: ScoringLatest }) {
  const cal = data.calibration;
  const lift = liftOverBaseline(cal?.precision, cal?.baseline_win_rate);
  const delta = data.previous_run?.delta.high_priority_accounts ?? null;
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <SummaryStat
        icon={Target}
        label="High-priority"
        value={formatNumber(data.metrics.high_priority_accounts)}
        hint={
          data.previous_run
            ? `${formatDelta(delta)} since last run`
            : "first run"
        }
        deltaTone={delta === null ? "flat" : delta > 0 ? "up" : delta < 0 ? "down" : "flat"}
      />
      <SummaryStat
        icon={Activity}
        label="Accounts scored"
        value={formatNumber(data.metrics.accounts_scored_24h)}
        hint={`of ${formatNumber(data.metrics.accounts_total)} total`}
      />
      <SummaryStat
        icon={TrendingUp}
        label={cal ? `Precision@${cal.k}` : "Precision"}
        value={cal?.precision != null ? cal.precision.toFixed(2) : "—"}
        hint={lift ?? "vs labeled outcomes"}
      />
      <SummaryStat
        icon={FlaskConical}
        label="Signals · 24h"
        value={formatNumber(data.metrics.signals_detected_24h)}
        hint={`run ${formatRelative(data.generated_at)}`}
      />
    </div>
  );
}

function SummaryStat({
  icon: Icon,
  label,
  value,
  hint,
  deltaTone = "flat",
}: {
  icon: typeof Target;
  label: string;
  value: string;
  hint: string;
  deltaTone?: "up" | "down" | "flat";
}) {
  return (
    <Card>
      <div className="p-4">
        <div className="flex items-start justify-between">
          <p className="text-2xs font-medium uppercase tracking-wider text-foreground-faint">
            {label}
          </p>
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-surface-2 text-foreground-muted">
            <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
          </div>
        </div>
        <p className="mt-2 text-2xl font-semibold tabular-nums text-foreground">
          {value}
        </p>
        <p
          className={cn(
            "mt-0.5 text-2xs truncate",
            deltaTone === "up" && "text-success",
            deltaTone === "down" && "text-warning",
            deltaTone === "flat" && "text-foreground-subtle",
          )}
        >
          {hint}
        </p>
      </div>
    </Card>
  );
}

function SignalBreakdown({ data }: { data: ScoringLatest }) {
  const rows = data.top_signals ?? [];
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-2xs font-medium uppercase tracking-wider text-foreground-faint">
          Signal mix
        </p>
        <div className="mt-3 space-y-2.5">
          {rows.map((row) => (
            <div key={row.kind} className="flex items-center gap-3">
              <span className="w-32 shrink-0 text-xs text-foreground-muted">
                {row.label}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
                <div
                  className={cn(
                    "h-full rounded-full",
                    KIND_BAR[row.kind] ?? "bg-foreground-muted",
                  )}
                  style={{ width: `${(row.count / max) * 100}%` }}
                />
              </div>
              <span className="w-20 shrink-0 text-right text-2xs tabular-nums text-foreground-subtle">
                {formatNumber(row.count)} · {Math.round(row.share * 100)}%
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function AccountCard({ account }: { account: RankedAccount }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className="overflow-hidden transition-colors hover:border-border-strong">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-3 p-4 text-left"
        aria-expanded={open}
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-surface-2 text-2xs font-semibold tabular-nums text-foreground-muted">
          {account.rank}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-semibold text-foreground">
              {account.name}
            </p>
            <Badge variant={priorityBadgeVariant(account.priority)}>
              {account.priority}
            </Badge>
            <span className="text-2xs text-foreground-faint">{account.industry}</span>
          </div>
          <p className="mt-1 truncate text-2xs text-foreground-muted">{account.why}</p>
        </div>
        <ScoreDial score={account.score} />
        {open ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-foreground-faint" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-foreground-faint" />
        )}
      </button>
      {open && <TraceTable account={account} />}
    </Card>
  );
}

function ScoreDial({ score }: { score: number }) {
  return (
    <div className="hidden w-24 shrink-0 sm:block">
      <div className="flex items-baseline justify-end gap-1">
        <span className="text-xl font-semibold tabular-nums text-foreground">{score}</span>
        <span className="text-2xs text-foreground-faint">/100</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2">
        <div className="h-full rounded-full bg-brand" style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

function TraceTable({ account }: { account: RankedAccount }) {
  return (
    <div className="border-t border-border-subtle bg-surface-2/40 px-4 py-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-2xs font-medium uppercase tracking-wider text-foreground-faint">
          Score trace · {formatNumber(account.evidence_points)} evidence points
        </p>
        <p className="text-2xs text-foreground-subtle">
          {account.trace.length} signal{account.trace.length === 1 ? "" : "s"}
        </p>
      </div>
      <div className="space-y-1">
        {account.trace.map((entry) => (
          <div
            key={entry.signal_id}
            className="flex items-center gap-3 rounded-md border border-border-subtle bg-surface px-3 py-2"
          >
            <span className="min-w-0 flex-1 truncate text-xs text-foreground">
              {entry.reason}
            </span>
            <span className="hidden shrink-0 text-2xs text-foreground-faint sm:inline">
              {entry.source}
            </span>
            <span className="w-16 shrink-0 text-right text-2xs tabular-nums text-foreground-subtle">
              x{entry.recency_factor.toFixed(2)}
            </span>
            <span className="w-12 shrink-0 text-right text-xs font-medium tabular-nums text-foreground">
              {Math.round(entry.points)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-lg" />
        ))}
      </div>
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-16 rounded-lg" />
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 px-6 py-14 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-2 text-foreground-faint">
          <StatusDot tone="muted" size="lg" />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">No scoring run yet</p>
          <p className="mt-1 max-w-sm text-2xs leading-relaxed text-foreground-muted">
            The daily benchmark seeds this on its first run, then re-scores the
            public fixture every day and commits the result back to the repo.
          </p>
        </div>
        <Button asChild size="sm" variant="outline">
          <a href={PROJECT.github_url} target="_blank" rel="noreferrer">
            <Github />
            View the repo
          </a>
        </Button>
      </CardContent>
    </Card>
  );
}
