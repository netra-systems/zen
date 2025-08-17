import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { getIndustryTemplate } from '../industry-data-templates'

interface SchemaTabProps {
  industry: string
}

const generateSchemaProperties = (data: Record<string, unknown>) => {
  return Object.keys(data).reduce((acc, key) => {
    const value = data[key]
    acc[key] = {
      type: typeof value === 'object' ? 'object' : typeof value,
      description: `${key} field for industry data`,
      example: value,
      required: Math.random() > 0.3
    }
    return acc
  }, {} as Record<string, object>)
}

const generateRequiredFields = (data: Record<string, unknown>) => {
  return Object.keys(data).filter(() => Math.random() > 0.5)
}

const createJsonSchema = (industry: string) => {
  const industryData = getIndustryTemplate(industry)
  const properties = generateSchemaProperties(industryData)
  const required = generateRequiredFields(industryData)
  
  return {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": `${industry} Synthetic Data Schema`,
    "type": "object",
    "properties": properties,
    "required": required
  }
}

export default function SchemaTab({ industry }: SchemaTabProps) {
  const schema = createJsonSchema(industry)
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Data Schema</CardTitle>
        <CardDescription>
          Structure and validation rules for {industry} synthetic data
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[500px]">
          <pre className="text-xs font-mono bg-muted p-4 rounded-lg">
            {JSON.stringify(schema, null, 2)}
          </pre>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}