import { Grid3x3, FileText, MessageSquare, Workflow, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

interface WorkspaceGettingStartedProps {
  onCreateMatrix: () => void
}

export function WorkspaceGettingStarted({ onCreateMatrix }: WorkspaceGettingStartedProps) {
  const steps = [
    {
      number: 1,
      title: 'Create a Matrix',
      description: 'Matrices organize your documents and questions into a structured grid for extraction.',
      icon: Grid3x3,
      active: true,
    },
    {
      number: 2,
      title: 'Add Documents & Questions',
      description: 'Upload documents and define the questions you want to extract answers for.',
      icon: FileText,
      secondaryIcon: MessageSquare,
      active: false,
    },
    {
      number: 3,
      title: 'Create Workflows',
      description: 'Build automated workflows that pull answers from your matrices into reports.',
      icon: Workflow,
      active: false,
    },
  ]

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-3xl mx-auto space-y-8">
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold tracking-tight">Welcome to your workspace</h2>
          <p className="text-muted-foreground">
            Get started by creating your first matrix
          </p>
        </div>

        <div className="space-y-4">
          {steps.map((step, index) => (
            <Card
              key={step.number}
              variant="blocky"
              className={step.active ? 'border-primary' : 'opacity-60'}
            >
              <CardContent className="flex items-center gap-4 py-4">
                <div className={`
                  flex items-center justify-center w-10 h-10 rounded-full text-sm font-bold
                  ${step.active ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}
                `}>
                  {step.number}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold">{step.title}</h3>
                  <p className="text-sm text-muted-foreground">{step.description}</p>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <step.icon className="h-5 w-5" />
                  {step.secondaryIcon && (
                    <>
                      <span className="text-xs">+</span>
                      <step.secondaryIcon className="h-5 w-5" />
                    </>
                  )}
                </div>
                {index < steps.length - 1 && (
                  <ArrowRight className="h-4 w-4 text-muted-foreground/50 hidden sm:block" />
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="flex justify-center pt-4">
          <Button onClick={onCreateMatrix} size="lg" style="blocky">
            <Grid3x3 className="h-4 w-4 mr-2" />
            Create Your First Matrix
          </Button>
        </div>
      </div>
    </div>
  )
}
