import { createFileRoute } from '@tanstack/react-router'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Grid3X3, Bot, Zap, ArrowRight, MessageSquare, Users } from 'lucide-react'

export const Route = createFileRoute('/landing')({
  component: LandingPage,
})

// Background decorations - documents on left, grid on right
function BackgroundShapes() {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      {/* Left 1/3 - Stacked documents */}
      <div className="absolute left-[8%] top-1/2 -translate-y-1/2">
        {/* Back document */}
        <div className="absolute -left-6 -top-4 w-[280px] h-[360px] border-2 border-muted-foreground/[0.08] rounded-lg bg-background rotate-[-8deg]">
          <div className="p-6 space-y-3">
            <div className="h-3 w-32 bg-muted-foreground/[0.08] rounded" />
            <div className="h-3 w-44 bg-muted-foreground/[0.08] rounded" />
            <div className="h-3 w-36 bg-muted-foreground/[0.08] rounded" />
            <div className="h-3 w-40 bg-muted-foreground/[0.08] rounded" />
            <div className="h-3 w-28 bg-muted-foreground/[0.08] rounded" />
            <div className="h-3 w-48 bg-muted-foreground/[0.08] rounded" />
            <div className="h-3 w-32 bg-muted-foreground/[0.08] rounded" />
          </div>
        </div>
        {/* Front document */}
        <div className="relative left-6 top-4 w-[280px] h-[360px] border-2 border-muted-foreground/[0.08] rounded-lg bg-background rotate-[4deg]">
          <div className="p-6 space-y-3">
            <div className="h-3 w-40 bg-muted-foreground/[0.08] rounded" />
            <div className="h-3 w-32 bg-muted-foreground/[0.08] rounded" />
            <div className="h-3 w-48 bg-muted-foreground/[0.08] rounded" />
            <div className="h-3 w-36 bg-muted-foreground/[0.08] rounded" />
            <div className="h-3 w-44 bg-muted-foreground/[0.08] rounded" />
            <div className="h-3 w-28 bg-muted-foreground/[0.08] rounded" />
            <div className="h-3 w-40 bg-muted-foreground/[0.08] rounded" />
          </div>
        </div>
      </div>

      {/* Right 1/3 - Matrix/Grid representation */}
      <div className="absolute right-[8%] top-1/2 -translate-y-1/2 rotate-[6deg]">
        <div className="w-[320px] h-[280px] border-2 border-muted-foreground/[0.08] rounded-lg bg-background p-4">
          {/* Header row */}
          <div className="flex gap-2 mb-3">
            <div className="w-20 h-6 bg-muted-foreground/[0.06] rounded" />
            <div className="w-16 h-6 bg-muted-foreground/[0.08] rounded" />
            <div className="w-16 h-6 bg-muted-foreground/[0.08] rounded" />
            <div className="w-16 h-6 bg-muted-foreground/[0.08] rounded" />
          </div>
          {/* Data rows */}
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex gap-2 mb-2">
              <div className="w-20 h-8 bg-muted-foreground/[0.06] rounded" />
              <div className="w-16 h-8 bg-muted-foreground/[0.05] rounded" />
              <div className="w-16 h-8 bg-muted-foreground/[0.05] rounded" />
              <div className="w-16 h-8 bg-muted-foreground/[0.05] rounded" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function LandingPage() {
  const { login, isAuthenticated } = useAuth()

  const handleGetStarted = () => {
    if (isAuthenticated) {
      window.location.href = '/workspaces'
    } else {
      login()
    }
  }

  return (
    <div className="min-h-screen bg-background relative flex flex-col">
      <BackgroundShapes />

      {/* Hero Section */}
      <div className="relative z-10">
        <div className="max-w-4xl mx-auto px-6 pt-16 pb-10">
          <div className="text-center space-y-4">
            <h1 className="text-5xl font-bold tracking-tight text-foreground">
              Corpus
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Every question, every document. Structured knowledge you can build on.
            </p>
          </div>
        </div>
      </div>

      {/* Features as a Matrix */}
      <div className="w-full max-w-5xl mx-auto px-6 relative z-10">
        <div className="border-2 border-border">
          <Table noWrapper className="w-full table-fixed">
            <TableHeader variant="blocky">
              <TableRow variant="blocky" className="flex">
                <TableHead variant="blocky" className="w-40 flex-shrink-0 bg-muted h-14 flex items-center px-4 border-r-2 border-border">
                </TableHead>
                <TableHead variant="blocky" className="flex-1 min-w-0 bg-muted h-14 px-4 border-r-2 border-border">
                  <div className="flex items-center gap-2 h-full">
                    <MessageSquare className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="font-medium text-sm">What is it?</span>
                  </div>
                </TableHead>
                <TableHead variant="blocky" className="flex-1 min-w-0 bg-muted h-14 px-4 border-r-2 border-border">
                  <div className="flex items-center gap-2 h-full">
                    <MessageSquare className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="font-medium text-sm">How does it work?</span>
                  </div>
                </TableHead>
                <TableHead variant="blocky" className="flex-1 min-w-0 bg-muted h-14 px-4">
                  <div className="flex items-center gap-2 h-full">
                    <MessageSquare className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="font-medium text-sm">When would I use it?</span>
                  </div>
                </TableHead>
              </TableRow>
            </TableHeader>

            <TableBody variant="blocky">
              {/* Row 1: Matrices */}
              <TableRow variant="blocky" className="flex">
                <TableCell variant="blocky" className="w-40 flex-shrink-0 bg-muted/50 px-4 py-4 border-r-2 border-border">
                  <div className="flex items-center gap-2">
                    <Grid3X3 className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="font-medium text-sm">Matrices</span>
                  </div>
                </TableCell>
                <TableCell variant="blocky" className="flex-1 min-w-0 px-4 py-4 border-r-2 border-border align-top">
                  <p className="text-sm leading-relaxed whitespace-normal break-words">
                    Structured grids for analyzing documents. Documents as rows, questions as columns, AI-generated answers in each cell.
                  </p>
                </TableCell>
                <TableCell variant="blocky" className="flex-1 min-w-0 px-4 py-4 border-r-2 border-border align-top">
                  <p className="text-sm leading-relaxed whitespace-normal break-words">
                    Upload documents, add questions, and the AI fills in answers with citations. Results are saved and can be exported.
                  </p>
                </TableCell>
                <TableCell variant="blocky" className="flex-1 min-w-0 px-4 py-4 align-top">
                  <p className="text-sm leading-relaxed whitespace-normal break-words">
                    Comparing contracts, analyzing research papers, auditing compliance docs, or any task where you need the same questions answered across multiple files.
                  </p>
                </TableCell>
              </TableRow>

              {/* Row 2: Agentic QA */}
              <TableRow variant="blocky" className="flex">
                <TableCell variant="blocky" className="w-40 flex-shrink-0 bg-muted/50 px-4 py-4 border-r-2 border-border">
                  <div className="flex items-center gap-2">
                    <Bot className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="font-medium text-sm">Agentic QA</span>
                  </div>
                </TableCell>
                <TableCell variant="blocky" className="flex-1 min-w-0 px-4 py-4 border-r-2 border-border align-top">
                  <p className="text-sm leading-relaxed whitespace-normal break-words">
                    Multi-step AI reasoning for questions that require connecting information across document sections.
                  </p>
                </TableCell>
                <TableCell variant="blocky" className="flex-1 min-w-0 px-4 py-4 border-r-2 border-border align-top">
                  <p className="text-sm leading-relaxed whitespace-normal break-words">
                    The AI searches, reads, and reasons through documents iteratively. You can see each step of its thinking process.
                  </p>
                </TableCell>
                <TableCell variant="blocky" className="flex-1 min-w-0 px-4 py-4 align-top">
                  <p className="text-sm leading-relaxed whitespace-normal break-words">
                    Complex questions like "What are all the termination clauses and their conditions?" that need synthesis across multiple sections.
                  </p>
                </TableCell>
              </TableRow>

              {/* Row 3: Workflows */}
              <TableRow variant="blocky" className="flex">
                <TableCell variant="blocky" className="w-40 flex-shrink-0 bg-muted/50 px-4 py-4 border-r-2 border-border">
                  <div className="flex items-center gap-2">
                    <Zap className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="font-medium text-sm">Workflows</span>
                  </div>
                </TableCell>
                <TableCell variant="blocky" className="flex-1 min-w-0 px-4 py-4 border-r-2 border-border align-top">
                  <p className="text-sm leading-relaxed whitespace-normal break-words">
                    Turn your matrix into polished outputs like reports, summaries, or slide decks.
                  </p>
                </TableCell>
                <TableCell variant="blocky" className="flex-1 min-w-0 px-4 py-4 border-r-2 border-border align-top">
                  <p className="text-sm leading-relaxed whitespace-normal break-words">
                    Use the matrix as a dense knowledge base. Workflows pull from those answers to generate well-contextualized deliverables.
                  </p>
                </TableCell>
                <TableCell variant="blocky" className="flex-1 min-w-0 px-4 py-4 align-top">
                  <p className="text-sm leading-relaxed whitespace-normal break-words">
                    When you need to go from analysis to output: executive summaries, comparison reports, or presentation slides based on your matrix data.
                  </p>
                </TableCell>
              </TableRow>

              {/* Row 4: Teams */}
              <TableRow variant="blocky" className="flex border-b-0">
                <TableCell variant="blocky" className="w-40 flex-shrink-0 bg-muted/50 px-4 py-4 border-r-2 border-border">
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <span className="font-medium text-sm">Teams</span>
                  </div>
                </TableCell>
                <TableCell variant="blocky" className="flex-1 min-w-0 px-4 py-4 border-r-2 border-border align-top">
                  <p className="text-sm leading-relaxed whitespace-normal break-words">
                    Shared workspaces where your organization's documents, matrices, and analyses live together.
                  </p>
                </TableCell>
                <TableCell variant="blocky" className="flex-1 min-w-0 px-4 py-4 border-r-2 border-border align-top">
                  <p className="text-sm leading-relaxed whitespace-normal break-words">
                    Everyone on your team sees the same documents and can collaborate on the same matrices. All data stays within your organization.
                  </p>
                </TableCell>
                <TableCell variant="blocky" className="flex-1 min-w-0 px-4 py-4 align-top">
                  <p className="text-sm leading-relaxed whitespace-normal break-words">
                    Any team that needs shared access to document analysis: legal teams, research groups, compliance departments, due diligence teams.
                  </p>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        {/* CTA Button */}
        <div className="text-center pt-8">
          <Button size="lg" style="blocky" onClick={handleGetStarted}>
            Get Started
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t relative z-10 mt-auto">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Corpus</span>
            <span>&copy; {new Date().getFullYear()}</span>
          </div>
        </div>
      </div>
    </div>
  )
}