export type ViewerEvent =
  | { type: "ready" }
  | { type: "selection"; points: readonly { x: number; y: number; z: number }[] }
  | { type: "error"; message: string }
  | { type: "statistics"; vertices: number; faces: number }
  | {
      type: "scale";
      points: readonly { x: number; y: number; z: number }[];
      scaleFactor: number;
      actualDistance: number;
      unit: string;
    }
  | {
      type: "crop";
      min: { x: number; y: number; z: number };
      max: { x: number; y: number; z: number };
    }
  | {
      type: "export";
      format: "glb" | "obj" | "ply";
      textureResolution: number | null;
      targetFaceCount: number | null;
      includePointCloud: boolean;
      includeCameraPositions: boolean;
    };

type WebViewBridge = {
  postMessage(message: ViewerEvent): void;
  addEventListener(type: "message", listener: (event: MessageEvent<unknown>) => void): void;
};

declare global {
  interface Window {
    chrome?: { webview?: WebViewBridge };
  }
}

export function postHostEvent(event: ViewerEvent): void {
  window.chrome?.webview?.postMessage(event);
}

export function listenForHostMessages(listener: (message: unknown) => void): void {
  window.chrome?.webview?.addEventListener("message", (event) => listener(event.data));
}
