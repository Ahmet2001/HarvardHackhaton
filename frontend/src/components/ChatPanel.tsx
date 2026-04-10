import { FormEvent, useState } from "react";
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
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "agent",
      content: "Tell me what to do: fetch a protein, add a ligand, prepare docking, or summarize results."
    }
  ]);
  const [draft, setDraft] = useState("");
  const [ligandSmiles, setLigandSmiles] = useState("");
  const [busy, setBusy] = useState(false);

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

  return (
    <section className="panel command-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Agent command</p>
          <h2>Natural language workflow</h2>
        </div>
        <span className="session-chip">{sessionId ? sessionId : "new session"}</span>
      </div>
      <div className="chat-log" aria-live="polite">
        {messages.map((message, index) => (
          <div className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
            <span>{message.role === "user" ? "You" : "Bıdık"}</span>
            <p>{message.content}</p>
          </div>
        ))}
      </div>
      <form className="chat-form" onSubmit={submit}>
        <label>
          Command
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Fetch the 3D structure of EGFR"
            rows={3}
          />
        </label>
        <label>
          Optional SMILES for this command
          <input
            value={ligandSmiles}
            onChange={(event) => setLigandSmiles(event.target.value)}
            placeholder="CC(=O)OC1=CC=CC=C1C(=O)O"
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Working" : "Send command"}
        </button>
      </form>
    </section>
  );
}

