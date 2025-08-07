
import ApexOptimizerAgentV2 from './components/apex-optimizer-agent-v2';
import { AgentProvider } from './providers/AgentProvider';
import { UserProvider } from './providers/UserProvider';

export default function ApexOptimizerAgentPage() {
    return (
        <div className="h-full">
            <UserProvider>
                <AgentProvider>
                    <ApexOptimizerAgentV2 />
                </AgentProvider>
            </UserProvider>
        </div>
    );
}
