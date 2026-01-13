import type { MatrixType, EntitySetResponse, EntityRole } from '@/client'

/**
 * Computes the dimensionality and axis information for a matrix.
 *
 * STANDARD matrices: 2D grid (documents × questions) + invisible 1-element slice axis
 * CROSS_CORRELATION matrices: 2D grid (left × right, same entity set) + sliceable question axis
 * GENERIC_CORRELATION matrices: 2D grid (left × right, distinct entity sets) + sliceable question axis
 *
 * This structure allows uniform treatment: all matrices have gridAxes (2D) + sliceAxis (1+)
 */
export interface MatrixDimensions {
  type: MatrixType
  /** The 2 axes that form the rendered grid (always 2D) */
  gridAxes: {
    role: EntityRole
    entitySetId: number
    entitySetName: string
    count: number
  }[]
  /** The axis to slice through (1 element for standard, N for correlation) */
  sliceAxis: {
    role: EntityRole
    entitySetId: number
    entitySetName: string
    count: number
  } | null
}

export function computeMatrixDimensions(
  matrixType: MatrixType,
  entitySets: EntitySetResponse[]
): MatrixDimensions {
  switch (matrixType) {
    case 'standard': {
      // 2D grid: DOCUMENT × QUESTION
      // Slice axis: invisible single element
      const docSet = entitySets.find(es => es.entityType === 'document')
      const questionSet = entitySets.find(es => es.entityType === 'question')

      const gridAxes: MatrixDimensions['gridAxes'] = []

      if (docSet) {
        gridAxes.push({
          role: 'document',
          entitySetId: docSet.id,
          entitySetName: docSet.name,
          count: docSet.members?.length || 0
        })
      }

      if (questionSet) {
        gridAxes.push({
          role: 'question',
          entitySetId: questionSet.id,
          entitySetName: questionSet.name,
          count: questionSet.members?.length || 0
        })
      }

      return {
        type: matrixType,
        gridAxes,
        sliceAxis: null // No slicing needed
      }
    }

    case 'cross_correlation': {
      // 2D grid: LEFT × RIGHT (same entity set, different roles - virtual projection)
      // Slice axis: QUESTION
      const docSet = entitySets.find(es => es.entityType === 'document')
      const questionSet = entitySets.find(es => es.entityType === 'question')

      const gridAxes: MatrixDimensions['gridAxes'] = []

      // Use the same document entity set for both LEFT and RIGHT axes
      if (docSet) {
        // LEFT axis
        gridAxes.push({
          role: 'left',
          entitySetId: docSet.id,
          entitySetName: docSet.name,
          count: docSet.members?.length || 0
        })

        // RIGHT axis (same set, different role)
        gridAxes.push({
          role: 'right',
          entitySetId: docSet.id,
          entitySetName: docSet.name,
          count: docSet.members?.length || 0
        })
      }

      return {
        type: matrixType,
        gridAxes,
        sliceAxis: questionSet ? {
          role: 'question',
          entitySetId: questionSet.id,
          entitySetName: questionSet.name,
          count: questionSet.members?.length || 0
        } : null
      }
    }

    case 'generic_correlation': {
      // 2D grid: LEFT × RIGHT (two distinct entity sets)
      // Slice axis: QUESTION
      const leftDocSet = entitySets.find(es => es.entityType === 'document' && es.name.toLowerCase().includes('left'))
      const rightDocSet = entitySets.find(es => es.entityType === 'document' && es.name.toLowerCase().includes('right'))
      const questionSet = entitySets.find(es => es.entityType === 'question')

      const gridAxes: MatrixDimensions['gridAxes'] = []

      // Use separate entity sets for LEFT and RIGHT axes
      if (leftDocSet) {
        gridAxes.push({
          role: 'left',
          entitySetId: leftDocSet.id,
          entitySetName: leftDocSet.name,
          count: leftDocSet.members?.length || 0
        })
      }

      if (rightDocSet) {
        gridAxes.push({
          role: 'right',
          entitySetId: rightDocSet.id,
          entitySetName: rightDocSet.name,
          count: rightDocSet.members?.length || 0
        })
      }

      return {
        type: matrixType,
        gridAxes,
        sliceAxis: questionSet ? {
          role: 'question',
          entitySetId: questionSet.id,
          entitySetName: questionSet.name,
          count: questionSet.members?.length || 0
        } : null
      }
    }

    case 'synopsis': {
      // Synopsis: Questions as columns, Documents as rows (like standard)
      // BUT: One cell per question that synthesizes ALL documents
      // Grid looks like standard but cells work differently
      const docSet = entitySets.find(es => es.entityType === 'document')
      const questionSet = entitySets.find(es => es.entityType === 'question')

      const gridAxes: MatrixDimensions['gridAxes'] = []

      // Documents as rows (axis1) - for display
      if (docSet) {
        gridAxes.push({
          role: 'document',
          entitySetId: docSet.id,
          entitySetName: docSet.name,
          count: docSet.members?.length || 0
        })
      }

      // Questions as columns (axis2)
      if (questionSet) {
        gridAxes.push({
          role: 'question',
          entitySetId: questionSet.id,
          entitySetName: questionSet.name,
          count: questionSet.members?.length || 0
        })
      }

      return {
        type: matrixType,
        gridAxes,
        sliceAxis: null
      }
    }

    default:
      throw new Error(`Unsupported matrix type: ${matrixType}`)
  }
}
