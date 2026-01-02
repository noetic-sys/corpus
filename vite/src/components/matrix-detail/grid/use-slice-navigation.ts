import { useState, useMemo } from 'react'
import { useMatrixContext } from '../context/matrix-context'
import { computeMatrixDimensions } from '../utils/matrix-dimensions'
import { formatQuestionTextForDisplay } from '../utils/document-placeholder-display'
import type {EntityRole, MatrixType} from '@/client/types.gen'

export function useSliceNavigation() {
  const { matrixType, entitySets, documents, questions } = useMatrixContext()

  const dimensions = useMemo(() => {
    if (!matrixType || !entitySets) return null
    return computeMatrixDimensions(matrixType as MatrixType, entitySets)
  }, [matrixType, entitySets])

  const [currentSliceIndex, setCurrentSliceIndex] = useState(0)
  const [activeSliceAxisRole, setActiveSliceAxisRole] = useState<string>(
    dimensions?.sliceAxis?.role || 'question'
  )

  // Build available axes (all 3 dimensions for correlation matrices)
  const allAxes = useMemo(
    () => dimensions ? [...dimensions.gridAxes, dimensions.sliceAxis].filter(Boolean) : [],
    [dimensions]
  )

  const canSwapAxes = allAxes.length >= 3

  // Determine current configuration based on active slice axis
  const currentSliceAxis = useMemo(
    () => allAxes.find((axis) => axis?.role === activeSliceAxisRole) || dimensions?.sliceAxis || null,
    [allAxes, activeSliceAxisRole, dimensions]
  )

  const currentGridAxes = useMemo(
    () => allAxes.filter((axis) => axis?.role !== activeSliceAxisRole).slice(0, 2),
    [allAxes, activeSliceAxisRole]
  )

  // Get current slice entity set and members
  const sliceEntitySet = entitySets.find((es) => es.id === currentSliceAxis?.entitySetId)
  const sliceMembers = sliceEntitySet?.members || []
  const currentSliceMember = sliceMembers[currentSliceIndex]

  // Create slice filter for the current slice item
  const sliceFilter = useMemo(() => {
    return currentSliceMember
      ? {
          entitySetId: currentSliceAxis!.entitySetId,
          entityIds: [currentSliceMember.entityId],
          role: currentSliceAxis!.role as EntityRole
        }
      : undefined
  }, [currentSliceMember, currentSliceAxis])

  // Build dropdown options for slice navigation
  const sliceOptions = useMemo(() => {
    return sliceMembers.map((member, idx) => {
      if (currentSliceAxis?.role === 'question') {
        const question = questions.find((q) => q.id === member.entityId)
        const displayText = question?.questionText
          ? formatQuestionTextForDisplay(question.questionText)
          : undefined
        return {
          value: idx.toString(),
          label: question?.label || `Question ${idx + 1}`,
          description: displayText
        }
      }
      // For documents or other entity types
      const doc = documents.find((d) => d.document.id === member.entityId)
      return {
        value: idx.toString(),
        label: doc?.label || doc?.document.filename || `${currentSliceAxis?.entitySetName} ${idx + 1}`,
        description: doc?.document.filename
      }
    })
  }, [sliceMembers, currentSliceAxis, questions, documents])

  // For display: if slicing on questions, filter questions
  const currentSliceItem =
    currentSliceAxis?.role === 'question'
      ? questions.find((q) => q.id === currentSliceMember?.entityId)
      : null

  const slicedQuestions =
    currentSliceAxis?.role === 'question' && currentSliceItem ? [currentSliceItem] : questions

  const handleAxisChange = (role: string) => {
    setActiveSliceAxisRole(role)
    setCurrentSliceIndex(0)
  }

  return {
    // State
    currentSliceIndex,
    setCurrentSliceIndex,
    activeSliceAxisRole,

    // Computed values
    allAxes,
    canSwapAxes,
    currentSliceAxis,
    currentGridAxes,
    sliceFilter,
    sliceOptions,
    slicedQuestions,

    // Actions
    handleAxisChange
  }
}
