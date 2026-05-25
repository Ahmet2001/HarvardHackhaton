import { useEffect, useRef, useState } from "react";

declare global {
  interface Window {
    NGL?: {
      Stage: new (element: HTMLElement, options?: Record<string, unknown>) => {
        loadFile: (url: string, options?: Record<string, unknown>) => Promise<{
          addRepresentation: (kind: string, options?: Record<string, unknown>) => void;
          autoView: () => void;
        }>;
        handleResize: () => void;
        autoView: () => void;
        removeAllComponents: () => void;
        dispose: () => void;
      };
    };
  }
}

const NGL_SCRIPT_ID = "ngl-viewer-script";
const NGL_SRC = "https://unpkg.com/ngl@2.0.0-dev.39/dist/ngl.js";

function loadNglScript(): Promise<void> {
  if (window.NGL) {
    return Promise.resolve();
  }
  const existing = document.getElementById(NGL_SCRIPT_ID) as HTMLScriptElement | null;
  if (existing) {
    if (existing.dataset.state === "loaded") {
      return window.NGL ? Promise.resolve() : Promise.reject(new Error("NGL Viewer failed to initialize."));
    }
    if (existing.dataset.state === "failed") {
      return Promise.reject(new Error("NGL Viewer failed to load."));
    }
    return new Promise((resolve, reject) => {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("NGL Viewer failed to load.")), {
        once: true
      });
    });
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.id = NGL_SCRIPT_ID;
    script.src = NGL_SRC;
    script.async = true;
    script.onload = () => {
      script.dataset.state = "loaded";
      resolve();
    };
    script.onerror = () => {
      script.dataset.state = "failed";
      reject(new Error("NGL Viewer failed to load."));
    };
    document.head.appendChild(script);
  });
}

type StructureViewerProps = {
  structureUrl?: string;
  selectedChain?: string | null;
};

type ViewerState = {
  message: string;
  tone: "idle" | "loading" | "ready" | "error";
};

export function StructureViewer({ structureUrl, selectedChain }: StructureViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const stageRef = useRef<InstanceType<NonNullable<typeof window.NGL>["Stage"]> | null>(null);
  const [viewerState, setViewerState] = useState<ViewerState>({
    message: "No structure loaded",
    tone: "idle"
  });

  useEffect(() => {
    if (!structureUrl || !containerRef.current) {
      setViewerState({ message: "No structure loaded", tone: "idle" });
      return;
    }

    let cancelled = false;
    setViewerState({ message: "Loading structure", tone: "loading" });
    loadNglScript()
      .then(() => {
        if (!window.NGL || !containerRef.current || cancelled) {
          return;
        }
        if (!stageRef.current) {
          stageRef.current = new window.NGL.Stage(containerRef.current, {
            backgroundColor: "white"
          });
        }
        const stage = stageRef.current;
        stage.removeAllComponents();
        stage
          .loadFile(structureUrl, { ext: "pdb" })
          .then((component) => {
            if (cancelled) {
              return;
            }
            component.addRepresentation("cartoon", {
              color: selectedChain ? "chainindex" : "residueindex",
              sele: selectedChain ? `:${selectedChain}` : "polymer"
            });
            component.addRepresentation("ball+stick", {
              sele: "hetero and not water",
              color: "element",
              visible: true
            });
            component.autoView();
            setViewerState({
              message: selectedChain ? `Viewing chain ${selectedChain}` : "Structure ready",
              tone: "ready"
            });
          })
          .catch((error: Error) => {
            if (!cancelled) {
              setViewerState({ message: error.message, tone: "error" });
            }
          });
      })
      .catch((error: Error) => {
        if (!cancelled) {
          setViewerState({ message: error.message, tone: "error" });
        }
      });

    const resize = () => stageRef.current?.handleResize();
    window.addEventListener("resize", resize);
    return () => {
      cancelled = true;
      window.removeEventListener("resize", resize);
    };
  }, [structureUrl, selectedChain]);

  useEffect(() => {
    return () => {
      stageRef.current?.dispose();
      stageRef.current = null;
    };
  }, []);

  return (
    <div aria-busy={viewerState.tone === "loading"} className={`viewer-shell viewer-${viewerState.tone}`}>
      <div className="viewer-toolbar">
        <span aria-live="polite" role="status">{viewerState.message}</span>
        <button type="button" onClick={() => stageRef.current?.autoView()} disabled={!structureUrl || viewerState.tone !== "ready"}>
          Reset view
        </button>
      </div>
      {viewerState.tone === "error" ? (
        <div className="viewer-fallback" role="alert">
          <strong>Viewer unavailable</strong>
          <p>{viewerState.message}</p>
          {structureUrl ? <a href={structureUrl}>Download the PDB file instead</a> : null}
        </div>
      ) : null}
      <div
        aria-label={`3D protein structure viewer. ${viewerState.message}`}
        className="structure-viewer"
        ref={containerRef}
        role="img"
        tabIndex={0}
      />
    </div>
  );
}
