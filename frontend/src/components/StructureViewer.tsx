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
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("NGL Viewer failed to load."));
    document.head.appendChild(script);
  });
}

type StructureViewerProps = {
  structureUrl?: string;
  selectedChain?: string | null;
};

export function StructureViewer({ structureUrl, selectedChain }: StructureViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const stageRef = useRef<InstanceType<NonNullable<typeof window.NGL>["Stage"]> | null>(null);
  const [status, setStatus] = useState("No structure loaded");

  useEffect(() => {
    if (!structureUrl || !containerRef.current) {
      return;
    }

    let cancelled = false;
    setStatus("Loading structure");
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
            setStatus(selectedChain ? `Viewing chain ${selectedChain}` : "Structure ready");
          })
          .catch((error: Error) => setStatus(error.message));
      })
      .catch((error: Error) => setStatus(error.message));

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
    <div className="viewer-shell">
      <div className="viewer-toolbar">
        <span>{status}</span>
        <button type="button" onClick={() => stageRef.current?.autoView()} disabled={!structureUrl}>
          Reset view
        </button>
      </div>
      <div className="structure-viewer" ref={containerRef} aria-label="3D protein structure viewer" />
    </div>
  );
}

