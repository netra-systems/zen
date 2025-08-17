import { Card, CardContent } from '@/components/ui/card';
import { CorpusStats } from '../types/corpus';

interface CorpusStatsProps {
  stats: CorpusStats[];
}

export const CorpusStatsGrid = ({ stats }: CorpusStatsProps) => {
  return (
    <div className="grid grid-cols-4 gap-4">
      {stats.map((stat, index) => (
        <StatCard key={index} stat={stat} />
      ))}
    </div>
  );
};

const StatCard = ({ stat }: { stat: CorpusStats }) => {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{stat.label}</p>
            <p className="text-2xl font-bold">{stat.value}</p>
          </div>
          {stat.icon}
        </div>
      </CardContent>
    </Card>
  );
};