(() => {
  const form = document.getElementById("extract-form");
  const transcriptEl = document.getElementById("transcript");
  const heuristicEl = document.getElementById("heuristic");
  const statusEl = document.getElementById("status");
  const shareStatusEl = document.getElementById("share-status");
  const resultsEl = document.getElementById("results");
  const btnExtract = document.getElementById("btn-extract");
  const btnSample = document.getElementById("btn-sample");
  const btnClear = document.getElementById("btn-clear");
  const btnNew = document.getElementById("btn-new");
  const charHint = document.getElementById("char-hint");
  const countsEl = document.getElementById("counts");
  const outcomeGrid = document.querySelector(".outcome-grid");
  const actionsList = document.getElementById("actions-list");

  let lastPayload = null;
  let extracting = false;

  const isMac = /Mac|iPhone|iPad/.test(navigator.platform || "");
  const kbd = btnExtract.querySelector(".btn-kbd");
  if (kbd) kbd.textContent = isMac ? "⌘↵" : "Ctrl+Enter";

  function setStatus(msg, kind = "") {
    statusEl.textContent = msg || "";
    statusEl.classList.toggle("error", kind === "error");
    statusEl.classList.toggle("ok", kind === "ok");
  }

  function setShareStatus(msg, kind = "") {
    shareStatusEl.textContent = msg || "";
    shareStatusEl.classList.toggle("error", kind === "error");
    shareStatusEl.classList.toggle("ok", kind === "ok");
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function updatePaperChrome() {
    const len = transcriptEl.value.trim().length;
    btnClear.hidden = len === 0;
    charHint.textContent = len
      ? `${len.toLocaleString()} characters`
      : "Paste or try the sample";
  }

  function actionLine(a) {
    const owner = a.owner || "Unassigned";
    const due = a.due ? ` · due ${a.due}` : "";
    return `${owner}: ${a.task}${due}`;
  }

  function formatSingleReminder(a) {
    const due = a.due ? ` (due ${a.due})` : "";
    return `${a.owner || "Unassigned"} — ${a.task}${due}`;
  }

  function formatSingleNote(a) {
    const due = a.due ? `\nDue: ${a.due}` : "";
    const priority = a.priority ? `\nPriority: ${a.priority}` : "";
    return `Action · ${a.owner || "Unassigned"}\n${a.task}${due}${priority}`;
  }

  function formatSingleFollowUp(a) {
    const due = a.due ? ` — due ${a.due}` : "";
    return [
      "Follow-up check-in",
      "",
      `Owner: ${a.owner || "Unassigned"}`,
      `Topic: ${a.task}${due}`,
      "",
      "Goal: confirm status and next due date.",
    ].join("\n");
  }

  function formatNotes(result) {
    const lines = ["Meeting notes", ""];
    if (result.summary) {
      lines.push(result.summary, "");
    }
    if (result.attendees?.length) {
      lines.push(`Attendees: ${result.attendees.join(", ")}`, "");
    }
    if (result.decisions?.length) {
      lines.push("Decisions");
      result.decisions.forEach((d, i) => {
        const extra = d.context ? ` — ${d.context}` : "";
        lines.push(`${i + 1}. ${d.text}${extra}`);
      });
      lines.push("");
    }
    if (result.action_items?.length) {
      lines.push("Action items");
      result.action_items.forEach((a) => {
        lines.push(`• ${actionLine(a)}`);
      });
      lines.push("");
    }
    if (result.open_questions?.length) {
      lines.push("Still open");
      result.open_questions.forEach((q) => lines.push(`• ${q}`));
    }
    return lines.join("\n").trim();
  }

  function formatReminders(result) {
    const actions = result.action_items || [];
    if (!actions.length) {
      return "No action items yet — extract a longer transcript first.";
    }
    return actions.map(formatSingleReminder).join("\n");
  }

  function formatFollowUp(result) {
    const title = result.summary
      ? `Follow-up: ${result.summary.slice(0, 64)}`
      : "Follow-up meeting";
    const lines = [
      title,
      "",
      "Suggested invite",
      "When: pick a 30-minute slot this week",
      "Where: same call link as last time",
      "",
    ];

    if (result.summary) {
      lines.push(`Context: ${result.summary}`, "");
    }

    const openActions = result.action_items || [];
    if (openActions.length) {
      lines.push("Agenda — check-ins");
      openActions.forEach((a, i) => {
        const due = a.due ? ` (due ${a.due})` : "";
        lines.push(`${i + 1}. ${a.owner || "Unassigned"}: ${a.task}${due}`);
      });
      lines.push("");
    }

    const questions = result.open_questions || [];
    if (questions.length) {
      lines.push("Agenda — decide next");
      questions.forEach((q, i) => lines.push(`${i + 1}. ${q}`));
      lines.push("");
    }

    if (!openActions.length && !questions.length) {
      lines.push("Agenda");
      lines.push("1. Review last decisions");
      lines.push("2. Confirm owners and due dates");
      lines.push("");
    }

    lines.push("Close by assigning owners and due dates.");
    return lines.join("\n").trim();
  }

  function formatEmail(result) {
    const subject = result.summary
      ? `Meeting follow-up: ${result.summary.slice(0, 72)}`
      : "Meeting follow-up";
    const body = [
      "Hi team,",
      "",
      result.summary || "Quick notes from our meeting:",
      "",
    ];

    if (result.decisions?.length) {
      body.push("What we decided:");
      result.decisions.forEach((d) => body.push(`- ${d.text}`));
      body.push("");
    }

    if (result.action_items?.length) {
      body.push("Who owns what:");
      result.action_items.forEach((a) => {
        const due = a.due ? ` (due ${a.due})` : "";
        body.push(`- ${a.owner || "Unassigned"}: ${a.task}${due}`);
      });
      body.push("");
    }

    if (result.open_questions?.length) {
      body.push("Still open:");
      result.open_questions.forEach((q) => body.push(`- ${q}`));
      body.push("");
    }

    body.push("Thanks,");
    return `Subject: ${subject}\n\n${body.join("\n")}`.trim();
  }

  const shareOptions = {
    reminders: {
      build: (payload) => formatReminders(payload.result),
      ok: "Reminders ready — paste into Apple Reminders, Google Tasks, or Todoist.",
    },
    followup: {
      build: (payload) => formatFollowUp(payload.result),
      ok: "Follow-up invite draft ready — paste into Google Calendar or Outlook.",
    },
    notes: {
      build: (payload) => formatNotes(payload.result),
      ok: "Meeting notes ready — paste into Apple Notes, Notion, or OneNote.",
    },
    email: {
      build: (payload) => formatEmail(payload.result),
      ok: "Email draft ready — paste into Gmail or Outlook.",
    },
  };

  const itemActions = {
    remind: {
      build: (a) => formatSingleReminder(a),
      ok: "Reminder copied — paste into Reminders or Tasks.",
    },
    followup: {
      build: (a) => formatSingleFollowUp(a),
      ok: "Follow-up note copied — paste into a calendar invite or chat.",
    },
    notes: {
      build: (a) => formatSingleNote(a),
      ok: "Action note copied — paste into Notes or Notion.",
    },
  };

  function renderActionItem(a, index) {
    const due = a.due ? ` · due ${escapeHtml(a.due)}` : "";
    return `<li class="action-item" data-action-index="${index}">
      <span class="owner">${escapeHtml(a.owner || "Unassigned")}</span>
      <div class="action-body">
        <p>${escapeHtml(a.task)}</p>
        <p class="action-meta">
          <span class="priority-${escapeHtml(a.priority || "medium")}">${escapeHtml(a.priority || "medium")}</span>${due}
        </p>
        <div class="item-actions" role="group" aria-label="Do something with this action">
          <button type="button" class="item-act" data-item-act="remind">Remind</button>
          <button type="button" class="item-act" data-item-act="followup">Follow up</button>
          <button type="button" class="item-act" data-item-act="notes">Add to notes</button>
        </div>
      </div>
    </li>`;
  }

  function render(result, markdown) {
    lastPayload = { result, markdown };
    setShareStatus("");

    const actions = result.action_items || [];
    const decisions = result.decisions || [];
    const questions = result.open_questions || [];

    document.getElementById("result-summary").textContent =
      result.summary || "Here’s what to take forward with your team.";
    document.getElementById("result-meta").textContent =
      `Source · ${result.source}` +
      (result.attendees?.length ? ` · ${result.attendees.length} people` : "");

    countsEl.hidden = false;
    document.getElementById("c-actions").textContent = String(actions.length);
    document.getElementById("c-decisions").textContent = String(decisions.length);
    document.getElementById("c-questions").textContent = String(questions.length);
    document.getElementById("actions-count").textContent = String(actions.length);
    document.getElementById("decisions-count").textContent = String(decisions.length);
    document.getElementById("questions-count").textContent = String(questions.length);

    actionsList.innerHTML = actions.length
      ? actions.map(renderActionItem).join("")
      : `<li class="empty">No action items found — try a longer transcript, or save meeting notes below.</li>`;

    const decisionsList = document.getElementById("decisions-list");
    decisionsList.innerHTML = decisions.length
      ? decisions
          .map(
            (d) => `<li class="decision-item">
              <strong>${escapeHtml(d.text)}</strong>
              ${d.context ? `<span>${escapeHtml(d.context)}</span>` : ""}
            </li>`
          )
          .join("")
      : `<li class="empty">No clear decisions detected.</li>`;

    const questionsList = document.getElementById("questions-list");
    questionsList.innerHTML = questions.length
      ? questions.map((q) => `<li>${escapeHtml(q)}</li>`).join("")
      : `<li class="empty">Nothing left open — nice.</li>`;

    const attendees = document.getElementById("attendees-list");
    attendees.textContent = result.attendees?.length
      ? `Attendees · ${result.attendees.join(" · ")}`
      : "";

    const remindBtn = outcomeGrid?.querySelector('[data-share="reminders"]');
    if (remindBtn) {
      remindBtn.classList.toggle("primary-outcome", actions.length > 0);
      remindBtn.disabled = actions.length === 0;
      remindBtn.title = actions.length
        ? "Copy every action as reminder lines"
        : "No action items to remind yet";
    }

    resultsEl.classList.remove("hidden");
    resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function copyText(text, okMessage) {
    try {
      await navigator.clipboard.writeText(text);
      setShareStatus(okMessage, "ok");
      setStatus(okMessage, "ok");
      return true;
    } catch {
      const fail = "Could not copy — select the text and copy manually.";
      setShareStatus(fail, "error");
      setStatus(fail, "error");
      return false;
    }
  }

  async function copyShare(kind) {
    if (!lastPayload) return;
    const option = shareOptions[kind];
    if (!option) return;
    const text = option.build(lastPayload);
    await copyText(text, option.ok);
  }

  async function copyItemAction(kind, index) {
    const action = lastPayload?.result?.action_items?.[index];
    const option = itemActions[kind];
    if (!action || !option) return;
    await copyText(option.build(action), option.ok);
  }

  async function runExtract() {
    if (extracting) return;
    const transcript = transcriptEl.value.trim();
    if (!transcript) {
      setStatus("Paste a transcript, or tap Try sample.", "error");
      transcriptEl.focus();
      return;
    }

    extracting = true;
    btnExtract.disabled = true;
    btnExtract.classList.add("loading");
    setStatus("Extracting owners and next steps…");
    setShareStatus("");

    try {
      const res = await fetch("/api/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript,
          heuristic: heuristicEl.checked,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail.map((d) => d.msg || d).join(", ")
              : "Extraction failed."
        );
      }
      render(data.result, data.markdown);
      setStatus(
        data.result.source === "llm"
          ? "Done. Act on each item, or take the whole meeting forward below."
          : "Done offline. Act on each item, or take the whole meeting forward below.",
        "ok"
      );
    } catch (err) {
      setStatus(err.message || "Extraction failed.", "error");
    } finally {
      extracting = false;
      btnExtract.disabled = false;
      btnExtract.classList.remove("loading");
    }
  }

  btnSample.addEventListener("click", () => {
    transcriptEl.value = window.__SAMPLE__ || "";
    updatePaperChrome();
    setStatus("Sample loaded — hit Extract actions (or ⌘/Ctrl+Enter).");
    transcriptEl.focus();
  });

  btnClear.addEventListener("click", () => {
    transcriptEl.value = "";
    updatePaperChrome();
    setStatus("");
    transcriptEl.focus();
  });

  btnNew.addEventListener("click", () => {
    resultsEl.classList.add("hidden");
    lastPayload = null;
    setShareStatus("");
    transcriptEl.focus();
    window.scrollTo({ top: 0, behavior: "smooth" });
    setStatus("Paste another transcript whenever you’re ready.");
  });

  transcriptEl.addEventListener("input", updatePaperChrome);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    runExtract();
  });

  transcriptEl.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      runExtract();
    }
  });

  outcomeGrid?.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-share]");
    if (!btn || btn.disabled) return;
    copyShare(btn.dataset.share);
  });

  actionsList?.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-item-act]");
    if (!btn) return;
    const row = btn.closest("[data-action-index]");
    if (!row) return;
    const index = Number(row.dataset.actionIndex);
    if (Number.isNaN(index)) return;
    copyItemAction(btn.dataset.itemAct, index);
  });

  updatePaperChrome();
})();
