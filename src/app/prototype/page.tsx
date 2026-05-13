import {
  ArrowRight,
  FileJson,
  GitBranchPlus,
  PlayCircle,
  Radar,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { TopBar } from "@/components/layout/TopBar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock } from "@/components/ui/code-block";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  PROTOTYPE_ACCOUNTS,
  PROTOTYPE_COMMANDS,
  PROTOTYPE_SIGNAL_SCHEMA,
  type PrototypeAccount,
} from "@/lib/prototype";

export const metadata = { title: "Prototype" };

export default function PrototypePage() {
  const topAccount = PROTOTYPE_ACCOUNTS[0];
  const activeSignals = PROTOTYPE_ACCOUNTS.reduce(
    (sum, account) => sum + account.signals.length,
    0,
  );

  return (
    <>
      <TopBar
        title="Prototype"
        description="Real local MVP: typed signals, recency-decayed scoring, traceable priorities, and account briefs."
        actions={
          <Button asChild size="sm" variant="outline">
            <a href="/capabilities">
              Compare to MVP claims
              <ArrowRight />
            </a>
          </Button>
        }
      />
      <div className="dot-grid grid-fade flex-1 overflow-y-auto">
        <div className="page-enter mx-auto max-w-6xl space-y-5 p-6">
          <Card className="overflow-hidden">
            <CardContent className="grid gap-5 p-6 lg:grid-cols-[1.3fr,0.9fr]">
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="brand">Local MVP</Badge>
                  <Badge variant="success">Explainable scoring</Badge>
                  <Badge variant="outline">CSV → trace → brief</Badge>
                </div>
                <div className="space-y-2">
                  <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                    The scoring thesis is now executable, not just described.
                  </h2>
                  <p className="max-w-2xl text-sm leading-relaxed text-foreground-muted">
                    This route mirrors the current Python prototype: accounts ingest typed
                    signals, each signal decays over time, and the resulting priority score
                    is explained by named factors instead of a black-box confidence number.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  <MetricCard
                    label="Accounts scored"
                    value={String(PROTOTYPE_ACCOUNTS.length)}
                    hint="sample CSV export"
                    icon={PlayCircle}
                  />
                  <MetricCard
                    label="Signals traced"
                    value={String(activeSignals)}
                    hint="all named, all decayed"
                    icon={Radar}
                  />
                  <MetricCard
                    label="Top account"
                    value={`${topAccount.score}/100`}
                    hint={topAccount.accountName}
                    icon={Sparkles}
                  />
                </div>
              </div>

              <Card className="border-border-strong bg-surface-2">
                <CardHeader>
                  <CardTitle>Prototype contract</CardTitle>
                  <CardDescription>
                    The shortest honest summary of what the MVP now proves.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-sm text-foreground-muted">
                  <p>
                    The repo can now ingest a CSV export, validate signal kinds, apply
                    explicit half-life decay, rank accounts, and generate a brief that
                    remains grounded in the underlying score trace.
                  </p>
                  <Separator />
                  <ul className="space-y-2">
                    <li className="flex gap-2">
                      <GitBranchPlus className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand" />
                      typed signal taxonomy with named weights
                    </li>
                    <li className="flex gap-2">
                      <GitBranchPlus className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand" />
                      recency decay as a first-class scoring rule
                    </li>
                    <li className="flex gap-2">
                      <GitBranchPlus className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand" />
                      deterministic account briefs from explainable trace data
                    </li>
                    <li className="flex gap-2">
                      <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
                      still no live CRM integration or persistent signal ledger
                    </li>
                  </ul>
                </CardContent>
              </Card>
            </CardContent>
          </Card>

          <Tabs defaultValue="accounts">
            <TabsList>
              <TabsTrigger value="accounts">Accounts</TabsTrigger>
              <TabsTrigger value="schema">Signal schema</TabsTrigger>
              <TabsTrigger value="cli">CLI</TabsTrigger>
            </TabsList>

            <TabsContent value="accounts" className="space-y-4">
              <div className="grid gap-4 xl:grid-cols-[0.95fr,1.05fr]">
                <Card>
                  <CardHeader>
                    <CardTitle>Ranked scorecards</CardTitle>
                    <CardDescription>
                      Current sample accounts sorted by explainable priority score.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {PROTOTYPE_ACCOUNTS.map((account, index) => (
                      <div
                        key={account.accountId}
                        className="rounded-lg border border-border-subtle bg-surface-2 p-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-xs uppercase tracking-[0.18em] text-foreground-faint">
                              Rank {index + 1}
                            </p>
                            <h3 className="mt-1 text-base font-semibold text-foreground">
                              {account.accountName}
                            </h3>
                            <p className="mt-1 text-sm text-foreground-muted">
                              {account.accountId}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-2xl font-semibold tabular-nums text-foreground">
                              {account.score}
                            </p>
                            <p className="text-xs text-foreground-faint">/100</p>
                          </div>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          <Badge variant={badgeForStatus(account.status)}>
                            {account.status}
                          </Badge>
                          <Badge variant="muted">
                            Net {account.totalPoints.toFixed(1)} pts
                          </Badge>
                          <Badge variant="muted">
                            +{account.positivePoints.toFixed(1)} / -{account.negativePoints.toFixed(1)}
                          </Badge>
                        </div>
                        <p className="mt-3 text-sm leading-relaxed text-foreground-muted">
                          {account.recommendedAction}
                        </p>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <div className="space-y-4">
                  {PROTOTYPE_ACCOUNTS.map((account) => (
                    <Card key={account.accountId}>
                      <CardHeader>
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <CardTitle>{account.accountName}</CardTitle>
                            <CardDescription>
                              Explainable trace, brief framing, and recommended action.
                            </CardDescription>
                          </div>
                          <Badge variant={badgeForStatus(account.status)}>
                            {account.score}/100
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid gap-4 lg:grid-cols-[1fr,1fr]">
                          <div className="space-y-3">
                            <SectionLabel>Brief</SectionLabel>
                            <div className="rounded-lg border border-border-subtle bg-surface-2 p-4">
                              <ul className="space-y-2">
                                {account.brief.map((line) => (
                                  <li
                                    key={line}
                                    className="flex gap-2 text-sm leading-relaxed text-foreground-muted"
                                  >
                                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                                    {line}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>
                          <div className="space-y-3">
                            <SectionLabel>Outreach angle</SectionLabel>
                            <div className="rounded-lg border border-border-subtle bg-surface-2 p-4 text-sm leading-relaxed text-foreground-muted">
                              {account.outreachAngle}
                            </div>
                            <SectionLabel>Recommended next step</SectionLabel>
                            <div className="rounded-lg border border-border-subtle bg-surface-2 p-4 text-sm leading-relaxed text-foreground-muted">
                              {account.recommendedAction}
                            </div>
                          </div>
                        </div>

                        <div className="space-y-3">
                          <SectionLabel>Score trace</SectionLabel>
                          <div className="space-y-2">
                            {account.signals.map((signal) => (
                              <div
                                key={`${account.accountId}-${signal.kind}-${signal.source}`}
                                className="flex flex-col gap-3 rounded-lg border border-border-subtle bg-surface-2 p-4 md:flex-row md:items-start md:justify-between"
                              >
                                <div className="space-y-1">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <p className="text-sm font-medium text-foreground">
                                      {signal.label}
                                    </p>
                                    <Badge
                                      variant={
                                        signal.sentiment === "positive" ? "success" : "warning"
                                      }
                                    >
                                      {signal.source}
                                    </Badge>
                                    <Badge variant="outline">{signal.ageDays}d old</Badge>
                                  </div>
                                  <p className="text-sm leading-relaxed text-foreground-muted">
                                    {signal.summary}
                                  </p>
                                </div>
                                <div className="text-right">
                                  <p
                                    className={
                                      signal.effectivePoints >= 0
                                        ? "text-lg font-semibold tabular-nums text-success"
                                        : "text-lg font-semibold tabular-nums text-warning"
                                    }
                                  >
                                    {signal.effectivePoints >= 0 ? "+" : ""}
                                    {signal.effectivePoints.toFixed(1)}
                                  </p>
                                  <p className="text-xs text-foreground-faint">effective points</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="schema">
              <div className="grid gap-4 lg:grid-cols-[0.9fr,1.1fr]">
                <Card>
                  <CardHeader>
                    <CardTitle>Required CSV columns</CardTitle>
                    <CardDescription>
                      The local MVP is strict on shape so the signal contract stays auditable.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {PROTOTYPE_SIGNAL_SCHEMA.requiredColumns.map((column) => (
                        <li
                          key={column}
                          className="rounded-md border border-border-subtle bg-surface-2 px-3 py-2 font-mono text-sm text-foreground-muted"
                        >
                          {column}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle>Supported signal kinds</CardTitle>
                    <CardDescription>
                      Each kind maps to an explicit base weight and half-life in the Python prototype.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-wrap gap-2">
                    {PROTOTYPE_SIGNAL_SCHEMA.supportedSignalKinds.map((kind) => (
                      <Badge key={kind} variant="muted" className="px-3 py-1 font-mono">
                        {kind}
                      </Badge>
                    ))}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="cli">
              <div className="grid gap-4 lg:grid-cols-[1fr,1fr]">
                <Card>
                  <CardHeader>
                    <CardTitle>Human-readable scoring</CardTitle>
                    <CardDescription>
                      The repo now demonstrates a full local path from CSV import to ranked accounts.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <CodeBlock language="bash">{PROTOTYPE_COMMANDS.scoreCsv}</CodeBlock>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle>Account brief</CardTitle>
                    <CardDescription>
                      Deterministic brief generation stays grounded in the exact score trace.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <CodeBlock language="bash">{PROTOTYPE_COMMANDS.briefAccount}</CodeBlock>
                  </CardContent>
                </Card>
                <Card className="lg:col-span-2">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileJson className="h-4 w-4 text-brand" />
                      Machine-readable export
                    </CardTitle>
                    <CardDescription>
                      The CLI also emits JSON so the prototype can feed a service or UI without parsing text output.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <CodeBlock language="bash">{PROTOTYPE_COMMANDS.scoreJson}</CodeBlock>
                    <p className="text-sm leading-relaxed text-foreground-muted">
                      This is the bridge from local CLI to future API packaging: the score trace is now both
                      readable by humans and exportable as structured data.
                    </p>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </>
  );
}

function MetricCard({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string;
  hint: string;
  icon: typeof Sparkles;
}) {
  return (
    <div className="rounded-lg border border-border-subtle bg-surface-2 p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-[0.18em] text-foreground-faint">{label}</p>
        <Icon className="h-4 w-4 text-brand" />
      </div>
      <p className="mt-3 text-2xl font-semibold tabular-nums text-foreground">{value}</p>
      <p className="mt-1 text-sm text-foreground-muted">{hint}</p>
    </div>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <p className="text-xs font-medium uppercase tracking-[0.18em] text-foreground-faint">
      {children}
    </p>
  );
}

function badgeForStatus(status: PrototypeAccount["status"]) {
  if (status === "high urgency") return "success";
  if (status === "worth active pursuit") return "brand";
  if (status === "monitor") return "warning";
  return "muted";
}
