import { MatrixSliceViewer } from './grid/matrix-slice-viewer'

export function MatrixDetail() {
  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* MatrixSliceViewer renders both header (with slice controls if needed) and grid */}
      <MatrixSliceViewer />
    </div>
  )
}