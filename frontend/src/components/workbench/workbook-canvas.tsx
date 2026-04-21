import { useEffect, useRef } from 'react'

declare global {
  interface Window {
    TableEnvCanvas?: {
      renderWorkbookSceneToCanvas: (canvas: HTMLCanvasElement, scene: Record<string, unknown>) => void
    }
  }
}

type WorkbookCanvasProps = {
  scene: Record<string, unknown> | null
}

export function WorkbookCanvas({ scene }: WorkbookCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    if (!canvasRef.current || !scene || !window.TableEnvCanvas) {
      return
    }
    window.TableEnvCanvas.renderWorkbookSceneToCanvas(canvasRef.current, scene)
  }, [scene])

  if (!scene) {
    return (
      <div className="flex min-h-[720px] items-center justify-center rounded-lg border border-dashed border-border bg-background text-sm text-muted-foreground">
        세션을 시작하면 이곳에 표가 렌더링됩니다.
      </div>
    )
  }

  return <canvas ref={canvasRef} className="rounded-lg bg-white shadow-sm" />
}
