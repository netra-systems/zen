
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Message } from '@/types/chat';

interface MessageCardProps {
  message: Message;
}

export function MessageCard({ message }: MessageCardProps) {
  const { full_name, picture, message: messageText, payload } = message;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center gap-4">
        <Avatar className="h-8 w-8">
          {picture ? (
            <AvatarImage src={picture} alt={full_name} />
          ) : (
            <AvatarFallback>
              {full_name
                .split(' ')
                .map((n) => n[0])
                .join('')}
            </AvatarFallback>
          )}
        </Avatar>
        <p className="font-semibold">{full_name}</p>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{messageText}</p>
        {payload && (
          <Accordion type="single" collapsible>
            <AccordionItem value="item-1">
              <AccordionTrigger>Raw Data</AccordionTrigger>
              <AccordionContent>
                <pre className="text-xs">
                  {JSON.stringify(payload, null, 2)}
                </pre>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}
      </CardContent>
    </Card>
  );
}
