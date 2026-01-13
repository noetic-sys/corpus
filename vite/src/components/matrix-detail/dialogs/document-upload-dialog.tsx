import { useState, useEffect, useMemo } from 'react'
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Upload, Search, Plus } from "lucide-react"
import type { DocumentResponse, EntitySetResponse } from '@/client'
import { DocumentUpload } from './document-upload'
import { DocumentSearch } from './document-search'
import { EntitySetSelectorDialog } from './entity-set-selector-dialog'
import { useDocumentSearch } from '../hooks/use-document-search'
import { useDocumentSelection } from '../hooks/use-document-selection'

interface DocumentUploadDialogProps {
  isOpen: boolean
  onClose: () => void
  matrixId: number
  entitySetId: number
  entitySets?: EntitySetResponse[]
  onDocumentUploaded: (document: DocumentResponse) => void
}

export function DocumentUploadDialog({
  isOpen,
  onClose,
  matrixId,
  entitySetId,
  entitySets = [],
  onDocumentUploaded
}: DocumentUploadDialogProps) {
  const [activeTab, setActiveTab] = useState('upload')
  const [showEntitySetSelector, setShowEntitySetSelector] = useState(false)
  const [selectedEntitySetId, setSelectedEntitySetId] = useState<number>(entitySetId)

  // Get document entity sets for selection dialog
  const documentEntitySets = useMemo(() =>
    entitySets.filter(es => es.entityType === 'document'),
    [entitySets]
  )

  // Reset selected entity set when dialog opens
  useEffect(() => {
    if (isOpen) {
      setSelectedEntitySetId(entitySetId)
    }
  }, [isOpen, entitySetId])

  const {
    searchQuery,
    searchResults,
    isSearching,
    searchDocuments,
    handleSearchInputChange,
    setSearchQuery
  } = useDocumentSearch()

  const {
    selectedDocuments,
    isAssociating,
    toggleDocumentSelection,
    associateSelectedDocuments,
    clearSelection
  } = useDocumentSelection(matrixId, selectedEntitySetId, onDocumentUploaded)

  useEffect(() => {
    if (isOpen && activeTab === 'search') {
      searchDocuments()
    }
  }, [isOpen, activeTab, searchDocuments])

  const handleClose = () => {
    setActiveTab('upload')
    setSearchQuery('')
    clearSelection()
    onClose()
  }

  const handleDocumentUploaded = (document: DocumentResponse) => {
    onDocumentUploaded(document)
    handleClose()
  }

  const handleAssociateSelected = async () => {
    await associateSelectedDocuments()
    handleClose()
  }

  // Get selected entity set name for display
  const selectedEntitySet = documentEntitySets.find(es => es.id === selectedEntitySetId)

  return (
    <>
      <Sheet open={isOpen} onOpenChange={handleClose}>
        <SheetContent side="right" className="w-full sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle>Add Documents to Matrix</SheetTitle>
            <SheetDescription>
              Upload new documents or select from existing ones to add to this matrix.
            </SheetDescription>
          </SheetHeader>

          {/* Entity set selector - only show when there are multiple document entity sets */}
          {documentEntitySets.length > 1 && (
            <div className="mt-4 p-3 bg-muted/50 rounded-lg border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Target Document Set</p>
                  <p className="text-xs text-muted-foreground">
                    {selectedEntitySet?.name || 'Select entity set'}
                  </p>
                </div>
                <Button
                  variant="outline"
                  style="blocky"
                  size="sm"
                  onClick={() => setShowEntitySetSelector(true)}
                >
                  Change
                </Button>
              </div>
            </div>
          )}

          <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-6">
            <TabsList variant="blocky" className="grid w-full grid-cols-2">
              <TabsTrigger variant="blocky" value="upload" className="flex items-center gap-2">
                <Upload className="h-4 w-4" />
                Upload New
              </TabsTrigger>
              <TabsTrigger variant="blocky" value="search" className="flex items-center gap-2">
                <Search className="h-4 w-4" />
                Search Existing
              </TabsTrigger>
            </TabsList>

            <TabsContent value="upload" className="mt-6">
              <DocumentUpload
                matrixId={matrixId}
                entitySetId={selectedEntitySetId}
                onDocumentUploaded={handleDocumentUploaded}
              />
            </TabsContent>
          
          <TabsContent value="search" className="mt-6">
            <DocumentSearch
              searchQuery={searchQuery}
              onSearchChange={handleSearchInputChange}
              isSearching={isSearching}
              searchResults={searchResults}
              selectedDocuments={selectedDocuments}
              onToggleSelection={toggleDocumentSelection}
            />
          </TabsContent>
        </Tabs>
        
        <SheetFooter className="mt-6">
          <Button 
            variant="outline" 
            style="blocky"
            onClick={handleClose}
          >
            Cancel
          </Button>
          
          {activeTab === 'search' && (
            <Button 
              style="blocky"
              onClick={handleAssociateSelected}
              disabled={selectedDocuments.length === 0 || isAssociating}
            >
              {isAssociating ? (
                <>
                  <Plus className="mr-2 h-4 w-4 animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Selected ({selectedDocuments.length})
                </>
              )}
            </Button>
          )}
        </SheetFooter>
      </SheetContent>
    </Sheet>

    {/* Entity set selector dialog */}
    <EntitySetSelectorDialog
      isOpen={showEntitySetSelector}
      onClose={() => setShowEntitySetSelector(false)}
      entitySets={documentEntitySets}
      title="Select Document Set"
      description="Choose which document set to add documents to."
      onSelect={(id) => {
        setSelectedEntitySetId(id)
        setShowEntitySetSelector(false)
      }}
    />
    </>
  )
}