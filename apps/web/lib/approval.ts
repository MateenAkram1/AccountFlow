export type SectionKey = "emails" | "crm" | "tasks";
export type SectionStatus = "pending" | "approved" | "rejected";

export interface EditableEmail {
  mode: string;
  toStr: string;
  subject: string;
  body: string;
  evidence_quotes: string[];
  selected: boolean;
}

export interface EditableCrm {
  field: string;
  value: string;
  evidence_quote: string;
  confidence: number;
  selected: boolean;
}

export interface EditableTask {
  summary: string;
  description: string;
  owner: string;
  due_date: string;
  evidence_quote: string;
  confidence: number;
  selected: boolean;
}

export interface ApprovalDraft {
  emails: EditableEmail[];
  crm_updates: EditableCrm[];
  tasks: EditableTask[];
  sectionStatus: Record<SectionKey, SectionStatus>;
  jiraProjectKey: string;
}

export function draftFromRun(run: any): ApprovalDraft {
  const pkg = run?.action_package;
  const approved = run?.approved;
  const sourceEmails = approved?.emails ?? pkg?.emails ?? [];
  const sourceCrm = approved?.crm_updates ?? pkg?.crm_updates ?? [];
  const sourceTasks = approved?.tasks ?? pkg?.tasks ?? [];

  const sections = approved?.sections;
  const sectionStatus: Record<SectionKey, SectionStatus> = {
    emails: sections?.emails ? "approved" : sections === undefined ? "pending" : "rejected",
    crm: sections?.crm ? "approved" : sections === undefined ? "pending" : "rejected",
    tasks: sections?.tasks ? "approved" : sections === undefined ? "pending" : "rejected",
  };

  if (run?.status === "awaiting_approval" && !approved) {
    sectionStatus.emails = "pending";
    sectionStatus.crm = "pending";
    sectionStatus.tasks = "pending";
  }

  return {
    emails: sourceEmails.map((e: any) => ({
      mode: e.mode ?? "external",
      toStr: (e.to ?? []).join(", "),
      subject: e.subject ?? "",
      body: e.body ?? "",
      evidence_quotes: e.evidence_quotes ?? [],
      selected: true,
    })),
    crm_updates: sourceCrm.map((c: any) => ({
      field: c.field ?? "",
      value: c.value ?? "",
      evidence_quote: c.evidence_quote ?? "",
      confidence: c.confidence ?? 0,
      selected: true,
    })),
    tasks: sourceTasks.map((t: any) => ({
      summary: t.summary ?? "",
      description: t.description ?? "",
      owner: t.owner ?? "",
      due_date: t.due_date ?? "",
      evidence_quote: t.evidence_quote ?? "",
      confidence: t.confidence ?? 0,
      selected: true,
    })),
    sectionStatus,
    jiraProjectKey:
      approved?.jira_project_key ||
      approved?.sections?.jira_project_key ||
      "",
  };
}

export function buildApprovedPayload(draft: ApprovalDraft, workflow: string) {
  const includeEmails = draft.sectionStatus.emails === "approved";
  const includeCrm = draft.sectionStatus.crm === "approved";
  const includeTasks = draft.sectionStatus.tasks === "approved";

  return {
    emails: includeEmails
      ? draft.emails
          .filter((e) => e.selected)
          .map((e) => ({
            mode: e.mode,
            to: e.toStr.split(",").map((s) => s.trim()).filter(Boolean),
            subject: e.subject,
            body: e.body,
            evidence_quotes: e.evidence_quotes,
          }))
      : [],
    crm_updates: includeCrm
      ? draft.crm_updates
          .filter((c) => c.selected)
          .map((c) => ({
            field: c.field,
            value: c.value,
            evidence_quote: c.evidence_quote,
            confidence: c.confidence,
          }))
      : [],
    tasks: includeTasks
      ? draft.tasks
          .filter((t) => t.selected)
          .map((t) => ({
            summary: t.summary,
            description: t.description,
            owner: t.owner || null,
            due_date: t.due_date || null,
            evidence_quote: t.evidence_quote,
            confidence: t.confidence,
          }))
      : [],
    jira_project_key: draft.jiraProjectKey || null,
    sections: {
      emails: includeEmails && draft.emails.some((e) => e.selected),
      crm: includeCrm && draft.crm_updates.some((c) => c.selected),
      tasks: includeTasks && draft.tasks.some((t) => t.selected),
      workflow,
      jira_project_key: draft.jiraProjectKey || null,
    },
  };
}

export function hasApprovedSection(draft: ApprovalDraft): boolean {
  return (["emails", "crm", "tasks"] as SectionKey[]).some((key) => {
    if (draft.sectionStatus[key] !== "approved") return false;
    if (key === "emails") return draft.emails.some((e) => e.selected);
    if (key === "crm") return draft.crm_updates.some((c) => c.selected);
    return draft.tasks.some((t) => t.selected);
  });
}
