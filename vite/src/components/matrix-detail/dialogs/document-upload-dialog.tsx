import { useState, useEffect } from 'react'
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
import type { DocumentResponse } from '@/client'
import { DocumentUpload } from './document-upload'
import { DocumentSearch } from './document-search'
import { useDocumentSearch } from '../hooks/use-document-search'
import { useDocumentSelection } from '../hooks/use-document-selection'

interface DocumentUploadDialogProps {
  isOpen: boolean
  onClose: () => void
  matrixId: number
  entitySetId: number
  onDocumentUploaded: (document: DocumentResponse) => void
}

export function DocumentUploadDialog({
  isOpen,
  onClose,
  matrixId,
  entitySetId,
  onDocumentUploaded
}: DocumentUploadDialogProps) {
  const [activeTab, setActiveTab] = useState('upload')

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
  } = useDocumentSelection(matrixId, onDocumentUploaded)

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

  return (
    <Sheet open={isOpen} onOpenChange={handleClose}>
      <SheetContent side="right" className="w-full sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>Add Documents to Matrix</SheetTitle>
          <SheetDescription>
            Upload new documents or select from existing ones to add to this matrix.
          </SheetDescription>
        </SheetHeader>
        
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
              entitySetId={entitySetId}
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
  )
}