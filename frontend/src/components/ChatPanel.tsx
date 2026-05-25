import { FormEvent, useEffect, useRef, useState } from "react";
import { FieldHint } from "./FieldHint";
import { LoadingButton } from "./LoadingButton";
import type { AgentResponse, DockingParameters } from "../types";

type ChatMessage = {
  role: "user" | "agent";
  content: string;
};

type ChatPanelProps = {
  sessionId?: string;
  dockingParameters: DockingParameters;
  onAgentResponse: (response: AgentResponse) => void;
  onError: (message: string) => void;
  sendMessage: (
    message: string,
    sessionId?: string,
    ligandSmiles?: string,
    dockingParameters?: DockingParameters
  ) => Promise<AgentResponse>;
};

export function ChatPanel({
  sessionId,
  dockingParameters,
  onAgentResponse,
  onError,
  sendMessage
}: ChatPanelProps) {
  const logRef = useRef<HTMLDivElement | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "agent",
      content: "Tell me what you want to do. For example: fetch EGFR, use aspirin as the ligand, prepare docking, or summarize results."
    }
  ]);
  const [draft, setDraft] = useState("");
  const [ligandSmiles, setLigandSmiles] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [messages]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || busy) {
      return;
    }
    setMessages((current) => [...current, { role: "user", content: message }]);
    setDraft("");
    setBusy(true);
    try {
      const response = await sendMessage(message, sessionId, ligandSmiles.trim(), dockingParameters);
      setLigandSmiles("");
      setMessages((current) => [...current, { role: "agent", content: response.message }]);
      onAgentResponse(response);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Agent request failed.";
      setMessages((current) => [...current, { role: "agent", content: detail }]);
      onError(detail);
    } finally {
      setBusy(false);
    }
  }

  const canSubmit = draft.trim().length > 0 && !busy;

  return (
    <section aria-labelledby="agent-panel-title" className="panel command-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Agent command</p>
          <h2 id="agent-panel-title">Natural language workflow</h2>
        </div>
        <span className="session-chip" title={sessionId ? `Active session ${sessionId}` : "A session starts after the first command"}>
          {sessionId ? sessionId : "new session"}
        </span>
      </div>
      <div
        aria-busy={busy}
        aria-live="polite"
        aria-relevant="additions text"
        className="chat-log"
        ref={logRef}
        role="log"
      >
        {messages.map((message, index) => (
          <article aria-label={message.role === "user" ? "User message" : "BioDockX response"} className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
            <span>{message.role === "user" ? "You" : "BioDockX"}</span>
            <p>{message.content}</p>
          </article>
        ))}
      </div>
      <form className="chat-form" onSubmit={submit}>
        <label htmlFor="command-input">
          Command
          <textarea
            aria-describedby="command-help"
            id="command-input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Fetch the 3D structure of EGFR"
            rows={3}
          />
        </label>
        <FieldHint id="command-help">Use natural language. BioDockX keeps the active protein, ligand, and last docking job in the current session.</FieldHint>
        <label htmlFor="command-smiles">
          Optional SMILES for this command
          <input
            aria-describedby="command-smiles-help"
            id="command-smiles"
            value={ligandSmiles}
            onChange={(event) => setLigandSmiles(event.target.value)}
            placeholder="CC(=O)OC1=CC=CC=C1C(=O)O"
          />
        </label>
        <FieldHint id="command-smiles-help">Paste a ligand only when the command needs one, such as "dock this protein with this ligand".</FieldHint>
        <LoadingButton type="submit" busy={busy} busyLabel="BioDockX is working" disabled={!canSubmit}>
          Send command
        </LoadingButton>
      </form>
    </section>
  );
}
